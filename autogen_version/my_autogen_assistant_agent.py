import asyncio
from autogen_core.models import ModelFamily
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams, mcp_server_tools
from autogen_version.deepseek_adapter import MyDeepSeekClient
from tools.my_search_tool import tavily_search
from prompts.search_web_agent_prompt import SEARCH_WEB_AGENT_PROMPT
from prompts.planning_agent_prompt import PLANNING_AGENT_PROMPT
from prompts.selector_prompt import SELECTOR_PROMPT
from prompts.command_executor_prompt import EXECUTOR_PROMPT
from typing import List, Sequence
from tools.save_file_tool import save_file
from stop_condition.stop_condition import stop
from stop_condition.stop_condition import FunctionCallTermination
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from dotenv import load_dotenv
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


async def main() -> None:
    # Create the agents.
    # model_client = OpenAIChatCompletionClient(
    #     model="deepseek-chat",
    #     api_key=DEEPSEEK_API_KEY,
    #     base_url="https://api.deepseek.com/v1",
    #     model_info={
    #         "vision": False,
    #         "function_calling": True,
    #         "json_output": True,
    #         "family": ModelFamily.UNKNOWN,
    #         "structured_output": True,
    #     },
    # )

    model_client = MyDeepSeekClient(model="deepseek-chat", api_key=DEEPSEEK_API_KEY)

    planning_agent = AssistantAgent(
        "PlanningAgent",
        description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
        model_client=model_client,
        system_message=PLANNING_AGENT_PROMPT,
    )

    command_executor_tools = [save_file]
    command_executor_agent = AssistantAgent(
        "CommandExecutorAgent",
        description="An agent for executing commands.",
        model_client=model_client,
        tools=command_executor_tools,
        system_message=EXECUTOR_PROMPT,
    )

    user_proxy_agent = UserProxyAgent("UserProxyAgent",
                                      description="A proxy for the user to approve or disapprove tasks.")

    stop_agent = AssistantAgent(
        name="StopAgent",
        description="An agent for stopping the conversation.",
        model_client=model_client,
        tools=[stop]
    )

    fetch_mcp_server = SseServerParams(
        url="http://127.0.0.1:8000/sse",
        headers={"content-type": "text/event-stream; charset=utf-8"}
    )
    tools = await mcp_server_tools(fetch_mcp_server)
    web_search_agent = AssistantAgent(
        name="WebSearchAgent",
        description="An agent for searching information on the web.",
        model_client=model_client,
        tools=tools,
        reflect_on_tool_use=True,
        system_message=SEARCH_WEB_AGENT_PROMPT
    )

    function_call_termination = FunctionCallTermination(function_name="stop")
    max_messages_termination = MaxMessageTermination(max_messages=15)
    termination = function_call_termination | max_messages_termination

    team = SelectorGroupChat(
        [planning_agent, web_search_agent, command_executor_agent, stop_agent],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=SELECTOR_PROMPT,
        allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
    )

    task = "最近什么电影好看？整理成一个markdown文件"
    await Console(team.run_stream(task=task))


if __name__ == "__main__":
    asyncio.run(main())
