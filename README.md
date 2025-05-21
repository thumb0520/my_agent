# My Agent

这是一个基于 AutoGen 和 AgentScope 框架的智能代理项目，提供了两种不同版本的实现。

## 项目结构

```
.
├── autogen_version/          # AutoGen 框架实现版本
│   ├── tools/               # 自定义工具
│   ├── prompts/             # 提示词模板
│   ├── stop_condition/      # 停止条件
│   └── example/             # 示例代码
├── agentscope_version/      # AgentScope 框架实现版本
│   ├── tools/               # 自定义工具
│   ├── prompts/             # 提示词模板
│   └── example/             # 示例代码
├── requirements.txt         # 项目依赖
├── .env.example            # 环境变量示例
└── clear.sh                # 清理脚本
```

## 环境要求

- Python 3.10+
- Conda 或 pip

## 安装步骤

1. 克隆项目：
```bash
git clone [repository-url]
cd my_agent
```

2. 创建并激活虚拟环境（推荐）：

使用 Conda：
```bash
# 创建新的 conda 环境
conda create -n my_agent python=3.10

# 激活环境
conda activate my_agent
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
```bash
cp .env.example .env
```
然后编辑 `.env` 文件，填入必要的 API 密钥：
- DEEPSEEK_API_KEY：DeepSeek API 密钥
- TAVILY_API_KEY：Tavily 搜索 API 密钥

## 主要功能

项目提供了两个版本的实现：

1. AutoGen 版本 (`autogen_version/`)
   - 基于 AutoGen 框架的智能代理实现
   - 包含自定义工具和提示词模板
   - 支持多种停止条件

2. AgentScope 版本 (`agentscope_version/`)
   - 基于 AgentScope 框架的智能代理实现
   - 包含自定义工具和提示词模板
   - 支持运行记录和示例代码

## 使用说明
### 启动mcp sse server
```bash
cd agentscope_version/mcp_tools
mcp run main.py -t sse
```

### AutoGen 版本

```bash
cd autogen_version
python my_autogen_assistant_agent.py
```

### AgentScope 版本

```bash
cd agentscope_version
python my_assistant_agent.py
```

## 依赖说明

主要依赖包括：
- agentscope==0.1.4
- autogen-agentchat==0.4.9.3
- autogen-core==0.4.9.3
- autogen-ext==0.4.9.3
- autogenstudio==0.4.2.1
- fastapi==0.115.12
- flask==3.0.0
- openai==1.78.1
- pydantic==2.11.4

完整依赖列表请参考 `requirements.txt`。

## 注意事项

1. 确保已正确配置所有必要的 API 密钥
2. 建议在虚拟环境中运行项目
3. 使用前请确保所有依赖已正确安装

## TODO 
- autogen适配deepseek 结构化输出api
## 许可证

[添加许可证信息]

## 贡献指南

[添加贡献指南]
