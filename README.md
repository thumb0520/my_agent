# My Agent

这是一个基于 AutoGen 和 AgentScope 框架的智能代理项目，提供了两种不同版本的实现。

## 项目结构

```
my_agent/
├── agentscope_version/           # AgentScope 框架实现
│   ├── my_assistant_agent.py    # 主应用入口
│   ├── prompts/                 # agent 提示词
│   └── tools/                   # 内置工具
│
├── autogen_version/             # AutoGen 框架实现
│   ├── agents/                  # 主应用入口
│   │   └── qbittorrent_agent.py
│   ├── config/                  # 项目配置
│   ├── deepseek_adapter/        # DS 接口适配
│   ├── prompts/                 # agent 提示词
│   ├── tools/                   # 内置工具
│   ├── stop_condition/          # 自定义停止条件
│   └── requirements.txt         # 依赖
│
└── mcp_server/                  # MCP 服务实现
    ├── config/                  # mcp server 启动配置
    ├── qbittorrent/             # bt 下载相关 mcp server
    ├── rarbg/                   # rarbg 搜索核心
    ├── web_search/             # 网络搜索 mcp server
    └── requirements.txt         # 依赖
```

## 环境要求

- Python 3.10+
- Conda 或 pip

## 安装步骤

1. 克隆项目：

```bash
git clone git@github.com:thumb0520/my_agent.git
cd my_agent
```

2. 创建并激活虚拟环境（推荐）：

使用 Conda：

```bash
# 创建新的 conda 环境
conda create -n autogen python=3.12

# 激活环境
conda activate autogen
```

3. 安装依赖：

```bash
cd autogen_version
pip install -r requirements.txt
```

4. 配置环境变量：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填入必要的 API 密钥：

- DEEPSEEK_API_KEY：DeepSeek API 密钥
- TAVILY_API_KEY：Tavily 搜索 API 密钥

## 使用说明

### 启动 MCP SSE Server

1. 创建并激活虚拟环境：

```bash
cd mcp_server
# 创建新的 conda 环境
conda create -n mcp_server python=3.12
conda activate mcp_server
pip install -r requirements.txt
```

2. 启动mcp servers

```bash
python main.py
```

### AutoGen 版本

```bash
cd autogen_version
python main.py
```

### AgentScope 版本

```bash
cd agentscope_version
python my_assistant_agent.py
```

## MCP 服务能力说明

### qbittorrent_mcp_server

- [x] 添加磁力链接 🧲 到 qbittorrent 下载列表
- [ ] 查询下载列表
- [ ] 删除没有速度的种子

### magnet_search_mcp_server 基于[rarbgcli](https://github.com/FarisHijazi/rarbgcli)改造

- [x] 从 rarbg 搜索磁力链接 🧲
- [x] 自动选择文件大小最大的种子

### web_search_mcp_server

- [x] 联网搜索功能
- [x] 支持多搜索引擎集成
- [x] 提供搜索结果摘要
- [x] 支持实时网络信息获取

## 依赖说明

主要依赖包括：

### AutoGen 版本依赖

- autogen-agentchat==0.6.1
- autogen-core==0.6.1
- autogen-ext==0.6.1
- openai==1.86.0
- pydantic==2.11.5
- fastmcp==2.8.0
- mcp==1.9.3

### MCP 服务依赖

- fastmcp==2.8.0
- mcp==1.9.3
- qbittorrent-api==2025.5.0
- beautifulsoup4==4.13.4
- requests==2.32.4
- wget==3.2

完整依赖列表请参考各目录下的 `requirements.txt` 文件。

## 注意事项

1. 确保已正确配置所有必要的 API 密钥
2. 建议在虚拟环境中运行项目
3. 使用前请确保所有依赖已正确安装
4. MCP 服务需要单独启动才能使用相关功能

## TODO

- [x] autogen 适配 deepseek 结构化输出 api
- [x] autogen version 接入 mcp server
- [x] autogen version 增加网页流式返回输出
- [ ] 添加字幕搜索mcp server
- [ ] 添加刮削mcp server
- [ ] autogen deepseek 结构化输出接口自动添加实体类型描述至 system prompt
- [ ] autogen 写一个复杂图结构的 agent 应用
- [ ] 添加页面交互，提交下载任务

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交 Pull Request 或创建 Issue 来改进项目。在提交代码前，请确保：

1. 代码符合项目的编码规范
2. 添加必要的测试用例
3. 更新相关文档
4. 提交信息清晰明了

对于重大更改，请先开 Issue 讨论您想要更改的内容。
