import asyncio
import json
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
from autogen_agentchat.teams import SelectorGroupChat, BaseGroupChat
from autogen_agentchat.ui import Console
from ui.WebUiResponseConsole import WebUiResponseConsole
from autogen_version.config.env_config import env_config

DEEPSEEK_API_KEY = env_config.get("DEEPSEEK_API_KEY")
QB_MCP_SERVER_ADDRESS = f"http://127.0.0.1:{env_config.get("QBITTORRENT_MCP_SERVER_PORT")}/sse"
MAGENT_SEARCH_ADDRESS = f"http://127.0.0.1:{env_config.get("MAGNET_SEARCH_MCP_SERVER_PORT")}/sse"


class QbittorrentAgent:
    def __init__(self, task: str):
        self.task = task

    async def create_team(self) -> BaseGroupChat:
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

        return SelectorGroupChat(
            [planning_agent, qbittorrent_tool_agent, magnet_search_agent, stop_agent],
            model_client=model_client,
            termination_condition=termination,
            selector_prompt=SELECTOR_PROMPT,
            allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
        )

    async def run(self):
        team = await self.create_team()
        console = await Console(team.run_stream(task=self.task))
        return console

    async def web_run(self):
        team = await self.create_team()
        console = WebUiResponseConsole(team.run_stream(task=self.task))
        return console


if __name__ == "__main__":
    task = "下载电影: Before sunrise"


    async def web_run_main():
        agent = QbittorrentAgent(task)
        console = await agent.web_run()
        async for response in console:
            print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
        print("finished!!!!!!!!!")


    async def console_main():
        agent = QbittorrentAgent(task)
        await agent.run()


    # asyncio.run(web_run_main())
    asyncio.run(console_main())
