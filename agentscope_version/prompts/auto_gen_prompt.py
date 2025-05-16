import os

from agentscope.prompt import ChineseSystemPromptGenerator
import agentscope
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")

model_config = {
    "config_name": "deepseek-chat",
    "model_type": "openai_chat",
    "model_name": "deepseek-chat",
    "api_key": API_KEY,
    "client_args": {
        "base_url": "https://api.deepseek.com/v1"
    }
}

agentscope.init(
    model_configs=model_config,
)

prompt_generator = ChineseSystemPromptGenerator(
    model_config_name="deepseek-chat"
)

generated_system_prompt = prompt_generator.generate(
    user_input="为执行操作agent编写系统提示,该agent主要功能有execute_shell_command，execute_python_code，create_file，create_directory，list_directory_content，get_current_directory，read_text_file，write_text_file",
)

print(generated_system_prompt)
