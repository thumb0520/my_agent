import asyncio
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams, mcp_server_tools
from autogen_version.deepseek_adapter import MyDeepSeekClient
from autogen_version.prompts.qbittorrent_planning_agent_prompt import PLANNING_AGENT_PROMPT
from autogen_version.prompts.selector_prompt import SELECTOR_PROMPT
from autogen_version.prompts.qbittorrent_tool_agnet_prompt import QBITTORRENT_TOOL_AGENT_PROMPT
from autogen_version.stop_condition.stop_condition import stop
from autogen_version.stop_condition.stop_condition import FunctionCallTermination
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from dotenv import load_dotenv
from autogen_version.config.mcp_server_config import QBITTORRENT_MCP_SERVER_CONFIG, get_default_address
import os

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


async def main() -> None:
    model_client = MyDeepSeekClient(model="deepseek-chat", api_key=DEEPSEEK_API_KEY)

    planning_agent = AssistantAgent(
        "PlanningAgent",
        description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
        model_client=model_client,
        system_message=PLANNING_AGENT_PROMPT,
    )

    stop_agent = AssistantAgent(
        name="StopAgent",
        description="An agent for stopping the conversation.",
        model_client=model_client,
        tools=[stop]
    )

    qb_mcp_server = SseServerParams(
        url=get_default_address(QBITTORRENT_MCP_SERVER_CONFIG),
        headers={"content-type": "text/event-stream; charset=utf-8"}
    )
    tools = await mcp_server_tools(qb_mcp_server)
    qbittorrent_tool_agent = AssistantAgent(
        name="QbittorrentToolAgent",
        description="A helpful agent that provides the capability to search magnet links and download them.",
        model_client=model_client,
        tools=tools,
        reflect_on_tool_use=True,
        system_message=QBITTORRENT_TOOL_AGENT_PROMPT
    )

    function_call_termination = FunctionCallTermination(function_name="stop")
    max_messages_termination = MaxMessageTermination(max_messages=15)
    termination = function_call_termination | max_messages_termination

    team = SelectorGroupChat(
        [planning_agent, qbittorrent_tool_agent, stop_agent],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=SELECTOR_PROMPT,
        allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
    )

    task = "下载电影: Before sunrise"
    await Console(team.run_stream(task=task))


if __name__ == "__main__":
    asyncio.run(main())
