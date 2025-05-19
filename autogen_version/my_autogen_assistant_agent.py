import asyncio
from autogen_core.models import ModelFamily
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from autogen_agentchat.messages import MultiModalMessage, BaseChatMessage, BaseAgentEvent
from autogen_ext.tools.code_execution import PythonCodeExecutionTool
from autogen_ext.tools.mcp import StdioServerParams, SseServerParams, SseMcpToolAdapter
from tools.my_search_tool import tavily_search
from prompts.search_web_agent_prompt import SEARCH_WEB_AGENT_PROMPT
from prompts.planning_agent_prompt import PLANNING_AGENT_PROMPT
from prompts.selector_prompt import SELECTOR_PROMPT
from prompts.command_executor_prompt import EXECUTOR_PROMPT
from typing import List, Sequence
from tools.save_file_tool import save_file
from agentscope.service import (
    execute_shell_command,
    create_file,
    create_directory,
    list_directory_content,
    get_current_directory,
    read_text_file,
    write_text_file,
)
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import os

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


async def main() -> None:
    # Create the agents.
    model_client = OpenAIChatCompletionClient(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.UNKNOWN
        },
    )

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

    web_search_agent = AssistantAgent(
        "WebSearchAgent",
        description="An agent for searching information on the web.",
        tools=[tavily_search],
        model_client=model_client,
        system_message=SEARCH_WEB_AGENT_PROMPT,
    )

    user_proxy_agent = UserProxyAgent("UserProxyAgent",
                                      description="A proxy for the user to approve or disapprove tasks.")

    # fetch_mcp_server = SseServerParams(
    #     url="http://127.0.0.1:8000/sse",
    #     timeout=30,  # Connection timeout in seconds
    # )
    # # Get the translation tool from the server
    # adapter = await SseMcpToolAdapter.from_server_params(fetch_mcp_server, "translate")
    # web_search_agent = AssistantAgent(
    #     name="WebSearchAgent",
    #     description="An agent for searching information on the web.",
    #     model_client=model_client,
    #     tools=[adapter],
    #     system_message=SEARCH_WEB_AGENT_PROMPT
    # )

    def selector_func_with_user_proxy(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
        if messages[-1].source != planning_agent.name and messages[-1].source != user_proxy_agent.name:
            # Planning agent should be the first to engage when given a new task, or check progress.
            return planning_agent.name
        if messages[-1].source == planning_agent.name:
            if messages[-2].source == user_proxy_agent.name and "APPROVE" in messages[
                -1].content.upper():  # type: ignore
                # User has approved the plan, proceed to the next agent.
                return None
            # Use the user proxy agent to get the user's approval to proceed.
            return user_proxy_agent.name
        if messages[-1].source == user_proxy_agent.name:
            # If the user does not approve, return to the planning agent.
            if "APPROVE" not in messages[-1].content.upper():  # type: ignore
                return planning_agent.name
        return None

    text_mention_termination = TextMentionTermination("TERMINATE")
    max_messages_termination = MaxMessageTermination(max_messages=15)
    termination = text_mention_termination | max_messages_termination

    team = SelectorGroupChat(
        [planning_agent, web_search_agent, command_executor_agent, user_proxy_agent],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=SELECTOR_PROMPT,
        selector_func=selector_func_with_user_proxy,
        allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
    )

    task = "最近什么电影好看？整理成一个markdown文件"
    await Console(team.run_stream(task=task))


if __name__ == "__main__":
    asyncio.run(main())
