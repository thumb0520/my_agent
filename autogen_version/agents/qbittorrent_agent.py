import asyncio

from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams, mcp_server_tools
from autogen_version.deepseek_adapter import MyDeepSeekClient
from autogen_version.prompts.qbittorrent_planning_agent_prompt import PLANNING_AGENT_PROMPT
from autogen_version.prompts.selector_prompt import SELECTOR_PROMPT
from autogen_version.prompts.qbittorrent_tool_agnet_prompt import (
    QBITTORRENT_TOOL_AGENT_PROMPT,
    MAGNET_SEARCH_AGENT_PROMPT
)
from autogen_version.stop_condition.stop_condition import stop
from autogen_version.stop_condition.stop_condition import FunctionCallTermination
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_version.config.env_config import env_config

DEEPSEEK_API_KEY = env_config.get("DEEPSEEK_API_KEY")
QB_MCP_SERVER_ADDRESS = f"http://127.0.0.1:{env_config.get("QBITTORRENT_MCP_SERVER_PORT")}/sse"
MAGENT_SEARCH_ADDRESS = f"http://127.0.0.1:{env_config.get("MAGNET_SEARCH_MCP_SERVER_PORT")}/sse"


class QbittorrentAgent:
    def __init__(self, task: str):
        self.task = task

    async def run(self):
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
            url=QB_MCP_SERVER_ADDRESS,
            headers={"content-type": "text/event-stream; charset=utf-8"}
        )
        tools = await mcp_server_tools(qb_mcp_server)
        qbittorrent_tool_agent = AssistantAgent(
            name="QbittorrentToolAgent",
            description="A helpful agent that provides the capability to download magnet links.",
            model_client=model_client,
            tools=tools,
            reflect_on_tool_use=True,
            system_message=QBITTORRENT_TOOL_AGENT_PROMPT
        )

        magnet_search_mcp_server = SseServerParams(
            url=MAGENT_SEARCH_ADDRESS,
            headers={"content-type": "text/event-stream; charset=utf-8"}
        )
        magnet_tools = await mcp_server_tools(magnet_search_mcp_server)
        magnet_search_agent = AssistantAgent(
            name="MagnetSearchAgent",
            description="A helpful agent that provides the capability to search magnet links.",
            model_client=model_client,
            tools=magnet_tools,
            reflect_on_tool_use=True,
            system_message=MAGNET_SEARCH_AGENT_PROMPT
        )

        function_call_termination = FunctionCallTermination(function_name="stop")
        max_messages_termination = MaxMessageTermination(max_messages=15)
        termination = function_call_termination | max_messages_termination

        team = SelectorGroupChat(
            [planning_agent, qbittorrent_tool_agent, magnet_search_agent, stop_agent],
            model_client=model_client,
            termination_condition=termination,
            selector_prompt=SELECTOR_PROMPT,
            allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
        )
        console = Console(team.run_stream(task=self.task))
        await console


if __name__ == "__main__":
    task = "下载电影: Before sunrise"
    asyncio.run(QbittorrentAgent(task).run())
