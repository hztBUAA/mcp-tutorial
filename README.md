# MCP端到端教程 | 从开发者角度来理解它

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/hztBUAA/mcp-tutorial/actions)
[![Documentation](https://img.shields.io/badge/Docs-Latest-blue.svg)](https://github.com/hztBUAA/mcp-tutorial/blob/master/MCP_GUIDE.md)
[![Issues](https://img.shields.io/github/issues/hztBUAA/mcp-tutorial.svg)](https://github.com/hztBUAA/mcp-tutorial/issues)

## 📖 项目简介

本项目实现了一个基于 **MCP (Model Context Protocol)** 协议的完整项目，包含客户端和服务端的端到端实现。将 **Bohrium OpenAPI** 封装为标准化的工具集，使大型语言模型能够自然地调用这些 API 能力。MCP 协议是一种专为大模型设计的上下文增强协议，通过标准化的工具发现和调用机制，显著提升了大模型的外部工具使用能力。

✨ **核心特性** ✨
- 将 HTTP API 转换为大模型可直接调用的工具
- 支持 SSE 和 stdio 两种传输层实现
- 提供标准化的工具发现和调用机制
- 实现 ReAct 推理框架进行迭代思考

---

## 🚀 核心组件

本项目包含三个核心组件，共同构成完整的 MCP 生态系统：

- **MCP Server** (`src/openapi_mcp_server/`)：
  - 协议的服务端实现，封装 Bohrium OpenAPI 为标准化工具
  - 提供了丰富的学术工具集，包括：
    - 论文搜索（普通版、加强版、Pro版）
    - 学者信息查询
    - 知识库管理
  - 需要 Bohrium OpenAPI 密钥进行认证
  - 支持 SSE 传输方式

- **MCP Host** (`src/mcp_host/`)：
  - 集成了 MCP Client 与 LLM 的桥接层
  - 内部包含：
    - MCP Client：与 Server 建立 1:1 连接，处理会话请求和响应
    - LLM 集成：支持 Azure OpenAI 或 Mock 实现
  - 支持两种运行模式：
    1. Mock 模式：使用内置的模拟响应，适合开发测试
    2. Azure OpenAI 模式：连接真实的 GPT 模型，用于生产环境
  - 实现了 ReAct 推理框架，能够迭代调用工具解决复杂问题

- **命令行工具** (`src/cli/`)：
  - 作为用户交互的入口
  - 实例化并管理 MCP Host
  - 提供命令行界面，支持：
    - 单次查询模式
    - 交互式会话模式
  - 负责结果的格式化展示

这三个组件的工作流程：
1. MCP Server 启动并暴露标准化的工具接口
2. MCP Host 中的 Client 与 Server 建立连接，获取可用工具列表
3. 命令行工具接收用户输入，传递给 Host 处理
4. Host 使用 LLM 分析请求，通过内部的 Client 调用 Server 提供的工具
5. 结果通过命令行界面返回给用户

---

---

## ⚙️ 系统要求

- **Python**：3.11 或更高版本

- **Bohrium OpenAPI 密钥**（必需）：
  1. 访问 [Bohrium 官网](https://bohrium.com)
  2. 注册并登录账户
  3. 进入"个人设置" > "API 密钥"
  4. 创建新的访问密钥
  > ⚠️ 注意：无论是开发测试还是生产环境，都需要配置 Bohrium API 密钥来启动MCP Server。 后续会开发server的mock版本。

- **Azure OpenAI API 密钥**（可选）：
  - 开发测试环境：
    - 可以使用 Mock 模式，无需 Azure OpenAI API 密钥
  
  - 生产环境：
    1. 访问 [Azure Portal](https://portal.azure.com)
    2. 创建 Azure OpenAI 服务实例
    3. 在"密钥和终结点"获取 API 密钥和终结点

- **Python 依赖**：所有依赖在 `pyproject.toml` 中管理，按照安装步骤操作即可

---

## 🛠️ 安装步骤

> 💡 快速开始提示：
> - 必须配置 Bohrium API 密钥以使用 MCP Server
> - 可以使用 Mock 模式（无需 Azure OpenAI 密钥）快速开始
> - 生产环境建议使用 Azure OpenAI 模式获得更好的效果

1. **克隆仓库**：
   ```bash
   git clone https://github.com/hztBUAA/mcp-tutorial.git
   cd mcp-tutorial
   ```

2. **创建虚拟环境**：
   ```bash
   # 推荐使用 conda（需要 Python >= 3.11）
   conda create -n mcp_env python=3.11 -y
   conda activate mcp_env

   # 或使用 venv
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate   # Windows
   ```

3. **安装项目**：
   ```bash
   # 普通用户安装
   pip install .
   
   # 开发者安装（源码可编辑模式）
   pip install -e .

   # 如果需要开发环境（包含 jupyter 支持等）
   pip install -e ".[dev]"

   # 如果需要测试工具
   pip install -e ".[test]"
   ```

   > 💡 说明：
   > - 普通用户使用 `pip install .` 即可，这会根据项目根目录的pyproject.toml文件安装一个稳定版本
   > - 开发者使用 `-e` 参数安装，这样修改源码后不需要重新安装
   > - 所有依赖都在 `pyproject.toml` 中管理，无需手动安装其他依赖

4. **环境配置**：
   ```bash
   # 创建 .env 文件
   cp .env.example .env
   ```

   选择以下配置方式之一：

   A. 使用 Mock 模式（快速上手）：
   ```bash
   # 在 .env 中设置
   MOCK=True
   ```
   这种模式不需要 API 密钥，而是使用本项目开发的模拟Openai类，适合快速体验和开发测试。

   B. 生产环境：
   ```bash
   # Azure OpenAI 配置
   MOCK=False  # 或删除此行
   AZURE_OPENAI_API_KEY=your_api_key
   AZURE_OPENAI_ENDPOINT=your_endpoint
   ```

   > 💡 提示：
   > - 开发和测试时推荐使用 Mock 模式，无需配置 API 密钥
   > - Mock 模式提供模拟响应，可以帮助您快速理解系统工作方式
   > - 生产环境请使用实际的 Azure OpenAI 配置

5. **验证安装**：
   ```bash
   # 测试导入是否正常
   python -c "from openapi_mcp_server import __version__; print(__version__)"
   python -c "from cli import __version__; print(__version__)"
   python -c "from mcp_host import __version__; print(__version__)"
   ```

## 常见问题

1. 如果遇到 "ModuleNotFoundError" 错误：
   - 检查是否在用正确的conda环境，因为新开的终端会重置为base的conda环境，需要重新`conda activate mcp_env`。
   - 这说明包或其依赖没有正确安装
   - 确保执行了 `pip install .` 命令（普通用户）或 `pip install -e .`（开发者）
   - 检查 Python 版本是否 >= 3.11

2. 如果遇到依赖冲突：
   ```bash
   # 清理环境
   pip uninstall -y -r <(pip freeze)
   # 重新安装
   pip install .  # 普通用户
   # 或
   pip install -e .  # 开发者
   ```


---

## 🚀 使用方法

### 启动 MCP 服务器

```bash
# 使用默认配置启动服务器
python start_server.py

```

### 使用 MCP 客户端

#### 单次查询模式
```bash
# 使用 SSE 传输（默认）
python mcp_demo.py "查找关于量子计算的最新论文"

# 使用 stdio 传输  未测试，由于服务器目前仅支持sse
# MCP_TRANSPORT=stdio python mcp_demo.py "查找关于量子计算的最新论文"
```

#### 交互式模式

```bash
# 启动交互式会话
python mcp_demo.py --interactive
```

---

## 📊 示例运行

以下是使用 MCP 系统进行论文搜索的实际运行示例，展示了系统如何使用 ReAct 风格进行推理：

### 查询示例：查找机器学习相关论文

**用户查询**：`Find papers about machine learning`

**系统思考过程**：

![image](https://github.com/user-attachments/assets/0d91fd8b-2335-4d74-93ad-b76e6cc815a3)


系统首先分析查询，确定需要使用增强型论文搜索工具，并构建适当的查询参数。

**工具调用与结果**：

![image](https://github.com/user-attachments/assets/19bc495c-65f3-4bae-a6e3-2f7ff23dd6e0)


系统调用 `search_papers_enhanced` 工具，获取相关论文列表，并对结果进行分析，提取关键信息如主题分布、元数据特征和可用性。

**最终回答**：
![image](https://github.com/user-attachments/assets/137a5193-92cc-4732-a921-c64b9462626a)
![image](https://github.com/user-attachments/assets/a62f278c-d921-4a20-a175-8d89591cefa7)


系统生成结构化的最终回答，包括精选的论文列表，每篇论文包含标题、作者、DOI 链接等关键信息，涵盖机器学习的多个方面。

这个示例展示了 MCP 系统如何：
1. 理解用户意图并规划查询策略
2. 调用适当的工具并处理返回结果
3. 分析和综合信息，生成有条理的回答
4. 在整个过程中保持透明的推理链

---

## 🏗️ 代码结构

```
mcp-tutorial/
├── src/
│   ├── mcp_client/         # MCP 客户端实现
│   │   └── cli_client.py   # 命令行客户端
│   ├── mcp_host/           # MCP 主机实现
│   │   ├── azure_openai_host.py  # Azure OpenAI 集成
│   │   └── prompts.py      # 系统提示模板
│   └── openapi_mcp_server/ # MCP 服务器实现
│       ├── server.py       # 核心服务器逻辑
│       ├── scholar/        # 学者 API 模块
│       ├── paper/          # 论文 API 模块
│       └── knowledge/      # 知识库 API 模块
├── mcp_demo.py             # 演示脚本
├── MCP_GUIDE.md            # MCP 开发指南
├── GUIDE.md                # API 模块开发指南
├── requirements.txt        # 项目依赖
└── README.md               # 项目说明
```

---

## 💡 MCP 协议核心概念

### 工具 (Tools)

工具是服务器提供的可执行功能，允许大模型执行操作。每个工具都有：
- 名称（如 `search-papers`）
- 描述（如 "搜索相关论文"）
- 输入模式（JSON Schema 格式）
- 输出类型（文本、图像等）

### 资源 (Resources)

资源是服务器提供的数据或内容，可以被大模型访问。资源有：
- URI（如 `tables://analytics`）
- 内容类型
- 内容

### 提示 (Prompts)

提示是可重用的模板，可以与特定输入一起使用来生成大模型的输入。

---

## 🔄 传输层实现

MCP 协议支持两种主要的传输层实现：

### SSE (Server-Sent Events)

适用于网络环境，通过 HTTP 长连接实现服务器向客户端的单向通信。

```python
# 服务器端
@app.route("/sse")
async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1])

# 客户端
async with sse_client(server_url) as streams:
    async with ClientSession(*streams) as session:
        # 使用 session 进行通信
```

### stdio (标准输入/输出)

适用于本地环境，通过标准输入/输出流进行通信。

```python
# 服务器端
async def main():
    await stdio_server(server)

# 客户端
async with stdio_client(server_command) as streams:
    async with ClientSession(*streams) as session:
        # 使用 session 进行通信
```

---

## 📊 Bohrium OpenAPI 能力

本项目封装了 Bohrium OpenAPI 的多种能力，包括：

### 学者相关 API
- 学者个人信息查询
- 学者合作作者关系
- 学者论文列表
- 关注与订阅列表

### 论文搜索引擎
- 普通版搜索
- 加强版搜索
- 语料 Pro 版本

### 解析与识别
- PDF 文件解析
- 图片识别
- 格式化输出

### 任务管理
- 任务创建与提交
- 任务状态查询
- 任务组管理

...and so on~
---

## 🔍 REST API vs MCP：为什么需要 MCP？

### REST API 的局限

REST API 在传统 Web 应用中表现出色，但在大模型应用场景中存在一些局限：

1. **缺乏自描述能力**：REST API 通常需要额外的文档来描述其功能和参数
2. **缺乏标准化的发现机制**：客户端难以自动发现可用的 API 端点
3. **不适合复杂交互**：无法自然地支持多轮对话和上下文保持

### MCP 的优势

MCP 协议专为大模型设计，具有以下优势：

1. **标准化的工具发现**：大模型可以自动发现可用的工具和资源
2. **自描述的输入模式**：工具定义包含完整的参数描述和类型信息
3. **统一的内容表示**：标准化的响应格式便于大模型处理
4. **适合大模型交互**：设计理念与大模型的工具调用机制天然契合

---

## 🔮 未来改进方向

1. **更多 API和TOOL模块支持**：扩展对更多 Bohrium OpenAPI 模块和工具的支持，包括RAG、Websearch以及CodeExecute等等
2. **多模型支持**：扩展对更多大模型的支持（如 Claude、GLM 等）
3. **安全增强**：实现更完善的认证和授权机制
4. **监控与日志**：添加详细的监控和日志记录功能
---

## 📚 参考资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [OpenAI Function Calling 文档](https://platform.openai.com/docs/guides/function-calling)
- [MCP 协议讨论](https://github.com/orgs/modelcontextprotocol/discussions/209)
- [OpenAI Tools & Remote MCP 指南](https://platform.openai.com/docs/guides/tools-remote-mcp)
- [MCP vs REST 讨论](https://zhuanlan.zhihu.com/p/29001189476)

---

## 🤝 如何贡献

欢迎任何形式的贡献！请：
1. 通过 [Issues](https://github.com/hztBUAA/mcp-tutorial/issues) 报告问题或建议
2. 通过 [Pull Requests](https://github.com/hztBUAA/mcp-tutorial/pulls) 提交改进

---

## 📄 许可证

本项目采用 [MIT 许可证](https://opensource.org/licenses/MIT) 开源。
