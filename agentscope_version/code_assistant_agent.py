import os
from agentscope import msghub
import agentscope
from dotenv import load_dotenv
from agentscope.message import Msg
from loguru import logger
from prompts.search_agent_prompt import SEARCH_AGENT_PROMPT
from prompts.execute_command_prompt import EXECUTOR_PROMPT
from agentscope.agents import ReActAgentV2, UserAgent, DialogAgent, DictDialogAgent, ReActAgent
from agentscope.parsers import MarkdownJsonDictParser
from tools.my_search_tool import tavily_search
from agentscope.service import (ServiceToolkit,
                                execute_python_code,
                                execute_shell_command,
                                create_file,
                                create_directory,
                                list_directory_content,
                                get_current_directory,
                                read_text_file,
                                write_text_file,
                                )

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TAVILY_SEARCH_API_KEY = os.getenv("TAVILY_API_KEY")

agentscope.init(
    model_configs={
        "config_name": "deepseek-chat",
        "model_type": "openai_chat",
        "model_name": "deepseek-chat",
        "api_key": DEEPSEEK_API_KEY,
        "client_args": {
            "base_url": "https://api.deepseek.com/v1"
        }
    },
)

# mcp_server_config = {
#     "mcpServers": {
#         "filesystem": {
#             "command": "npx",
#             "args": [
#                 "-y",
#                 "@modelcontextprotocol/server-filesystem",
#                 "./"
#             ]
#         }
#     }
# }

executor_toolkit = ServiceToolkit()
# executor_toolkit.add_mcp_servers(server_configs=mcp_server_config)
executor_toolkit.add(execute_shell_command)
executor_toolkit.add(execute_python_code)
executor_toolkit.add(create_file)
executor_toolkit.add(create_directory)
executor_toolkit.add(list_directory_content)
executor_toolkit.add(get_current_directory)
executor_toolkit.add(read_text_file)
executor_toolkit.add(write_text_file)

search_toolkit = ServiceToolkit()
search_toolkit.add(tavily_search, api_key=TAVILY_SEARCH_API_KEY)

executor_agent = ReActAgent(name="executor", model_config_name="deepseek-chat",
                            service_toolkit=executor_toolkit,
                            sys_prompt=EXECUTOR_PROMPT)

user_agent = UserAgent(name="thumb", input_hint="用户输入: \n")

search_agent = ReActAgent(
    name="web-search-assistant",
    model_config_name="deepseek-chat",
    service_toolkit=search_toolkit,
    sys_prompt=SEARCH_AGENT_PROMPT,
)

# Workflow: Routing
routing_agent = DictDialogAgent(
    name="Routing",
    model_config_name="deepseek-chat",
    sys_prompt="You're a routing agent. Your target is to route the user query to the right follow-up task",
    max_retries=3
)

# 要求智能体生成包含 `thought`、`speak` 和 `decision` 的结构化输出
route_parse = MarkdownJsonDictParser(
    content_hint={
        "thought": "你的想法",
        "speak": "你要说的话",
        "decision": "你的最终决定，Search Info/Execute Command/User Interrupt/Finish",
    },
    keys_to_metadata="decision",
    required_keys=["thought", "speak", "decision"],
)
routing_agent.set_parser(route_parse)

input_msg = "最近什么电影好看？整理成一个markdown文件"
msg = Msg("user", input_msg, "user")

with msghub(participants=[routing_agent, user_agent, search_agent, executor_agent], announcement=msg) as hub:
    current_step = 0
    max_step = 10
    while current_step < max_step:
        current_step += 1
        logger.info(f"step {current_step}: {max_step}")
        msg = routing_agent()
        if msg.metadata == "User Interrupt":
            logger.info("decide to choose user interrupt agent")
            msg = user_agent(msg)
        if msg.metadata == "Search Info":
            logger.info("decide to choose search info agent")
            msg = search_agent(msg)
        if msg.metadata == "Execute Command":
            logger.info("decide to choose command executor agent")
            msg = executor_agent(msg)
        if msg.metadata == "Finish":
            logger.info("decide to finish task")
            break
