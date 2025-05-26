# MCP (Model Context Protocol) 开发指南

## 1. MCP 概述

MCP（Model Context Protocol）是一个开放协议，用于标准化应用程序如何向LLMs（大型语言模型）提供上下文。它类似于AI应用程序的USB-C端口，提供了一种标准化的方式来连接AI模型与不同的数据源和工具。

### 核心架构

MCP遵循客户端-服务器架构，其中一个宿主应用程序可以连接到多个服务器：

- **MCP Host**：如Claude Desktop、IDE或AI工具等想要通过MCP访问数据的程序
- **MCP Client**：维护与服务器1:1连接的协议客户端
- **MCP Server**：通过标准化的Model Context Protocol暴露特定功能的轻量级程序
- **本地数据源**：MCP服务器可以安全访问的计算机文件、数据库和服务
- **远程服务**：MCP服务器可以连接的通过互联网可用的外部系统（例如，通过API）

## 2. MCP 组件

### 2.1 MCP Host

Host是使用MCP客户端连接到一个或多个MCP服务器的应用程序。Host通常包含一个LLM（大型语言模型），并使用MCP来扩展LLM的能力。

Host的主要职责：
- 初始化与MCP服务器的连接
- 向LLM提供上下文
- 处理LLM生成的工具调用
- 管理与服务器的交互

### 2.2 MCP Client

Client是实现MCP协议客户端部分的组件，负责与MCP服务器通信。

Client的主要职责：
- 建立与服务器的连接
- 发送请求到服务器
- 接收服务器的响应
- 处理协议级别的错误

### 2.3 MCP Server

Server是实现MCP协议服务器部分的组件，提供各种功能如工具、资源和提示。

Server的主要职责：
- 处理来自客户端的请求
- 提供工具和资源
- 执行工具调用
- 返回结果给客户端

## 3. MCP 核心概念

### 3.1 工具 (Tools)

工具是服务器提供的可执行功能，允许LLM执行操作。每个工具都有：
- 名称
- 描述
- 输入模式（JSON Schema）
- 输出类型

### 3.2 资源 (Resources)

资源是服务器提供的数据或内容，可以被LLM访问。资源有：
- URI
- 内容类型
- 内容

### 3.3 提示 (Prompts)

提示是可重用的模板，可以与特定输入一起使用来生成LLM的输入。

### 3.4 采样 (Sampling)

采样允许服务器请求LLM生成内容，使服务器能够利用LLM的能力。

## 4. 实现MCP Host

### 4.1 基本结构

```python
import mcp.host
import mcp.types as types

class MyMCPHost:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.mcp_clients = {}  # 存储与不同服务器的连接
        
    async def connect_to_server(self, server_name, transport):
        """连接到MCP服务器"""
        client = mcp.host.Client(server_name)
        await client.connect(transport)
        self.mcp_clients[server_name] = client
        return client
        
    async def list_tools(self, server_name):
        """列出服务器上可用的工具"""
        client = self.mcp_clients.get(server_name)
        if not client:
            raise ValueError(f"未连接到服务器: {server_name}")
        return await client.list_tools()
        
    async def call_tool(self, server_name, tool_name, arguments):
        """调用服务器上的工具"""
        client = self.mcp_clients.get(server_name)
        if not client:
            raise ValueError(f"未连接到服务器: {server_name}")
        return await client.call_tool(tool_name, arguments)
        
    async def process_llm_response(self, response):
        """处理LLM的响应，执行工具调用"""
        # 解析LLM响应中的工具调用
        tool_calls = extract_tool_calls(response)
        
        results = []
        for call in tool_calls:
            server_name = call.server_name
            tool_name = call.tool_name
            arguments = call.arguments
            
            # 调用工具并获取结果
            result = await self.call_tool(server_name, tool_name, arguments)
            results.append(result)
            
        return results
        
    async def run_conversation(self, user_query):
        """运行一个完整的对话循环"""
        conversation_history = []
        conversation_history.append({"role": "user", "content": user_query})
        
        while True:
            # 获取LLM响应
            llm_response = await self.llm_client.generate(conversation_history)
            conversation_history.append({"role": "assistant", "content": llm_response})
            
            # 检查是否有工具调用
            if has_tool_calls(llm_response):
                # 处理工具调用
                tool_results = await self.process_llm_response(llm_response)
                
                # 将工具结果添加到对话历史
                for result in tool_results:
                    conversation_history.append({"role": "tool", "content": result})
            else:
                # 如果没有工具调用，对话结束
                break
                
        return conversation_history
```

### 4.2 与Azure OpenAI集成

```python
import os
import mcp.host
import mcp.types as types
from azure.openai import AzureOpenAI

class AzureOpenAIMCPHost:
    def __init__(self):
        # 初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.model = os.getenv("AZURE_OPENAI_MODEL")
        self.mcp_clients = {}
        
    # MCP客户端连接和工具调用方法...
    
    async def generate_with_tools(self, messages, tools):
        """使用工具生成响应"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        return response
        
    # 其他方法...
```

## 5. 实现MCP Client

### 5.1 命令行客户端

```python
import argparse
import asyncio
import json
import os
import sys

import mcp.client
from mcp.client.stdio import stdio_client

async def main():
    parser = argparse.ArgumentParser(description="MCP命令行客户端")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 查询命令
    query_parser = subparsers.add_parser("query", help="向MCP Host发送查询")
    query_parser.add_argument("text", help="查询文本")
    
    # 列出工具命令
    list_tools_parser = subparsers.add_parser("list-tools", help="列出可用工具")
    
    # 调用工具命令
    call_tool_parser = subparsers.add_parser("call-tool", help="调用工具")
    call_tool_parser.add_argument("tool_name", help="工具名称")
    call_tool_parser.add_argument("--args", help="JSON格式的参数", default="{}")
    
    args = parser.parse_args()
    
    # 连接到MCP Host
    async with stdio_client() as (read_stream, write_stream):
        client = mcp.client.Client()
        await client.connect(read_stream, write_stream)
        
        if args.command == "query":
            # 发送查询到Host
            response = await client.send_query(args.text)
            print(json.dumps(response, indent=2))
            
        elif args.command == "list-tools":
            # 列出可用工具
            tools = await client.list_tools()
            print(json.dumps(tools, indent=2))
            
        elif args.command == "call-tool":
            # 调用工具
            arguments = json.loads(args.args)
            result = await client.call_tool(args.tool_name, arguments)
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. 完整的MCP Demo

### 6.1 项目结构

```
mcp_demo/
├── host/
│   ├── __init__.py
│   ├── azure_openai_host.py
│   └── mcp_host.py
├── client/
│   ├── __init__.py
│   └── cli_client.py
├── main.py
└── requirements.txt
```

### 6.2 主程序

```python
import asyncio
import os
import sys
from dotenv import load_dotenv

from host.azure_openai_host import AzureOpenAIMCPHost
from mcp.server.stdio import stdio_server

async def main():
    # 加载环境变量
    load_dotenv()
    
    # 创建MCP Host
    host = AzureOpenAIMCPHost()
    
    # 连接到MCP Server
    server_transport = stdio_server()
    server_client = await host.connect_to_server("openapi-mcp-server", server_transport)
    
    # 获取用户查询
    query = sys.argv[1] if len(sys.argv) > 1 else input("请输入您的查询: ")
    
    # 运行对话
    conversation = await host.run_conversation(query)
    
    # 打印结果
    for message in conversation:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            print(f"\n用户: {content}")
        elif role == "assistant":
            print(f"\n助手: {content}")
        elif role == "tool":
            print(f"\n工具结果: {content}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 7. 调试和测试

### 7.1 使用MCP Inspector

MCP Inspector是一个交互式调试工具，可用于测试和检查MCP服务器。

### 7.2 日志记录

在开发过程中，启用详细日志记录以帮助调试：

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_demo")
```

## 8. 最佳实践

1. **错误处理**: 实现健壮的错误处理，特别是在网络通信和工具调用中
2. **超时管理**: 为所有网络请求和工具调用设置适当的超时
3. **安全性**: 确保敏感数据（如API密钥）安全存储
4. **可扩展性**: 设计组件以便轻松添加新的服务器和工具
5. **文档**: 为所有工具和资源提供清晰的文档

## 9. 参考资源

- [MCP官方文档](https://modelcontextprotocol.io/)
- [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP规范](https://modelcontextprotocol.io/specification)
