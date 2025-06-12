# My Agent

这是一个基于 AutoGen 和 AgentScope 框架的智能代理项目，提供了两种不同版本的实现。

## 项目结构

```
my_agent
├─ agentscope_version 
│  ├─ my_assistant_agent.py 主应用入口
│  ├─ prompts agent提示词
│  └─ tools 内置工具
├─ autogen_version
│  ├─ agents 主应用入口
│  │  └─ qbittorrent_agent.py 
│  ├─ config 项目配置
│  ├─ deepseek_adapter DS接口适配
│  ├─ prompts agent提示词
│  ├─ tools 内置工具
│  ├─ stop_condition 自定义停止条件
│  └─ requirements.txt 依赖
└─ mcp_server
   ├─ config mcp server启动配置
   ├─ qbittorrent bt下载相关mcp server
   ├─ rarbg rarbg搜索核心
   ├─ web_search 网络搜索mcp server
   └─ requirements.txt 依赖
```

## 环境要求

- Python 3.10+
- Conda 或 pip

## 安装步骤

1. 克隆项目：

```bash
git clone https://github.com/yourusername/my_agent.git
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
pip install -r autogen_version/requirements.txt
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
    - 已集成 MCP 服务

2. AgentScope 版本 (`agentscope_version/`)
    - 基于 AgentScope 框架的智能代理实现
    - 包含自定义工具和提示词模板
    - 支持运行记录和示例代码

## 使用说明

### 启动 MCP SSE Server

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

## MCP 服务能力说明

### qbittorrent_mcp_server

- 提供从 rarbg 搜索磁力链接 🧲
- 添加磁力链接 🧲 到 qbittorrent 下载列表
- 支持下载进度监控
- 支持下载任务管理

### web_search_mcp_server

- 联网搜索功能
- 支持多搜索引擎集成
- 提供搜索结果摘要
- 支持实时网络信息获取

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
4. MCP 服务需要单独启动才能使用相关功能

## TODO

- [x] autogen 适配 deepseek 结构化输出 api
- [ ] autogen deepseek 结构化输出接口自动添加实体类型描述至 system prompt
- [ ] autogen 写一个复杂图结构的 agent 应用
- [x] autogen version 接入 mcp server

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交 Pull Request 或创建 Issue 来改进项目。在提交代码前，请确保：

1. 代码符合项目的编码规范
2. 添加必要的测试用例
3. 更新相关文档
4. 提交信息清晰明了

对于重大更改，请先开 Issue 讨论您想要更改的内容。
