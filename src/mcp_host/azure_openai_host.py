import os
import asyncio
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple, Union, Literal, cast
import mcp.types as types
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from openai import AzureOpenAI
from mcp_host.mock_openai import MockAzureOpenAI
from mcp_host.prompts import SYSTEM_PROMPT
from mcp_host.context_manager import ContextManager
from datetime import datetime
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("azure_openai_mcp_host")

# 根据环境变量选择实现
if os.getenv('MOCK', '').lower() == 'true':
    OpenAIClient = MockAzureOpenAI
else:
    OpenAIClient = AzureOpenAI

class AzureOpenAIMCPHost:
    """
    MCP Host implementation using Azure OpenAI API.
    This class handles the integration between Azure OpenAI and MCP protocol.
    """
    
    def __init__(self):
        """Initialize the Azure OpenAI MCP Host with environment variables."""
        self.client = OpenAIClient(
            api_key=os.getenv("AZURE_OPENAI_API_KEY", "mock-key"),  # mock 模式下使用默认值
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "https://mock-endpoint.openai.azure.com")
        )
        self.model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self.mcp_session: Optional[ClientSession] = None
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", "10"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.transport_type: Literal["stdio", "sse"] = cast(
            Literal["stdio", "sse"], 
            os.getenv("MCP_TRANSPORT", "sse").lower()
        )
        self.tools: List[Union[types.Tool, types.Resource]] = []
        
        self.context_manager = ContextManager(
            max_messages=10,
            compression_interval=5,
            openai_client=self.client,
            deployment_name=self.deployment_name
        )
        
    async def connect_to_server(self, server_command: Optional[List[str]] = None, 
                               server_url: Optional[str] = None,
                               transport_type: Optional[Literal["stdio", "sse"]] = None) -> None:
        """
        Connect to MCP server using the specified transport.
        
        Args:
            server_command: Command to start the MCP server (for stdio transport)
            server_url: URL of the MCP server (for SSE transport)
            transport_type: Transport type to use ("stdio" or "sse")
        """
        used_transport_type = cast(Literal["stdio", "sse"], transport_type or self.transport_type)
        
        try:
            if used_transport_type == "stdio":
                if not server_command:
                    raise ValueError("server_command is required for stdio transport")
                    
                logger.info(f"Connecting to MCP server with stdio transport, command: {' '.join(server_command)}")
                async with stdio_client(server_command) as streams:
                    read_stream, write_stream = streams
                    async with ClientSession(read_stream, write_stream) as session:
                        self.mcp_session = session
                        result = await self.mcp_session.list_tools()
                        self.tools = result.tools
                        
                        
            elif used_transport_type == "sse":
                if not server_url:
                    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
                
                if not server_url.endswith("/sse"):
                    server_url = urllib.parse.urljoin(server_url, "/sse")
                    
                logger.info(f"Connecting to MCP server with SSE transport, URL: {server_url}")
                
                # 保存上下文管理器引用
                self._streams_context = sse_client(server_url)
                streams = await self._streams_context.__aenter__()
                
                # 保存会话上下文管理器引用
                self._session_context = ClientSession(*streams)
                self.mcp_session = await self._session_context.__aenter__()
                
                await self.mcp_session.initialize()
                result = await self.mcp_session.list_tools()
                self.tools = result.tools
                
                logger.info("Successfully connected to MCP server")
                logger.info(f"Retrieved {len(self.tools)} tools")
            
            else:
                raise ValueError(f"Unsupported transport type: {used_transport_type}")
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            # 确保清理资源
            await self.disconnect()
            raise
        
    async def _convert_mcp_tools_to_openai_format(self) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to OpenAI tool format.
        
        Returns:
            List of tools in OpenAI format
        """
        openai_tools = []
        
        for tool in self.tools:
            if isinstance(tool, types.Resource):
                continue
                
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            if tool.inputSchema:
                if "properties" in tool.inputSchema:
                    openai_tool["function"]["parameters"]["properties"] = tool.inputSchema["properties"]
                if "required" in tool.inputSchema:
                    openai_tool["function"]["parameters"]["required"] = tool.inputSchema["required"]
            
            openai_tools.append(openai_tool)
            
        return openai_tools
        
    async def _call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            tool_args: Arguments to pass to the tool
            
        Returns:
            Tool response
        """
        if not self.mcp_session:
            raise RuntimeError("Not connected to MCP server")
            
        logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
        
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            error_msg = f"Tool {tool_name} not found"
            logger.error(error_msg)
            return {"error": error_msg}
            
        try:
            logger.info(f"Found tool: {tool.name}, preparing to call...")
            result = await self.mcp_session.call_tool(tool_name, tool_args)
            
            # 处理 CallToolResult
            if isinstance(result, types.CallToolResult):
                # 将内容转换为可序列化的格式
                serializable_content = []
                for content in result.content:
                    if isinstance(content, types.TextContent):
                        serializable_content.append({
                            "type": "text",
                            "text": content.text
                        })
                    # 可以根据需要添加其他类型的处理（ImageContent, EmbeddedResource等）
                
                logger.info(f"Tool {tool_name} returned: {serializable_content}")
                return {
                    "content": serializable_content,
                    "isError": result.isError
                }
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
                return {"error": f"Unexpected result type: {type(result)}"}
            
        except Exception as e:
            error_msg = f"Error calling tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Error type: {type(e)}")
            logger.error("Error details:", exc_info=True)
            return {"error": error_msg}
    
    def _create_response_entry(self, iteration: int, assistant_message) -> Dict[str, Any]:
        """创建响应条目"""
        return {
            "iteration": iteration,
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": None,
            "is_final": False
        }

    async def _handle_tool_calls(self, tool_calls, response_entry) -> List[Dict[str, Any]]:
        """处理工具调用"""
        tool_results = []
        response_entry["tool_calls"] = []
        
        for tool_call in tool_calls:
            function_call = tool_call.function
            tool_args = json.loads(function_call.arguments)
            tool_result = await self._call_tool(function_call.name, tool_args)
            
            response_entry["tool_calls"].append({
                "tool_name": function_call.name,
                "tool_args": tool_args,
                "tool_result": tool_result
            })
            
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_call.name,
                "content": json.dumps(tool_result)
            })
        
        return tool_results

    def _create_reflection_prompt(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建反思提示"""
        tool_observations = [
            f"Tool '{result['name']}' returned: {result['content']}"
            for result in tool_results
        ]
        
        return {
            "role": "user",
            "content": (
                "Based on the tool results:\n" + 
                "\n".join(tool_observations) + "\n\n" +
                "Please analyze these results and decide:\n" +
                "1. What have we learned?\n" +
                "2. Do we need more information?\n" +
                "3. Are we ready for a Final Answer?\n"
            )
        }
        
    async def process_query(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Process user query with iterative tool calling.
        
        Args:
            user_query: User query to process
            
        Returns:
            List of responses including model outputs and tool calls
        """
        logger.info(f"Processing query: {user_query}")
        
        openai_tools = await self._convert_mcp_tools_to_openai_format()
        
        messages = await self.context_manager.add_message(
            {"role": "system", "content": SYSTEM_PROMPT},
            iteration=0
        )
        
        messages = await self.context_manager.add_message(
            {"role": "user", "content": f"Query: {user_query}\n\nLet's approach this step-by-step:"},
            iteration=0
        )
        
        all_responses = []
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Iteration {iteration}/{self.max_iterations}")
            
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto",
                    temperature=self.temperature
                )
                
                assistant_message = response.choices[0].message
                content = assistant_message.content
                
                # 创建当前迭代的响应条目
                response_entry = {
                    "iteration": iteration,
                    "role": "assistant",
                    "content": content,
                    "tool_calls": None,
                    "is_final": False
                }

                messages = await self.context_manager.add_message(
                    assistant_message.model_dump(),
                    iteration
                )
                
                # 检查是否达到最终答案 - 添加 None 检查
                if content is not None and "Final Answer:" in content:
                    response_entry["is_final"] = True
                    all_responses.append(response_entry)
                    break
                
                # 处理工具调用
                if assistant_message.tool_calls:
                    response_entry["tool_calls"] = []
                    tool_observations = []
                    
                    # 执行每个工具调用并收集结果
                    for tool_call in assistant_message.tool_calls:
                        function_call = tool_call.function
                        tool_args = json.loads(function_call.arguments)
                        tool_result = await self._call_tool(function_call.name, tool_args)
                        
                        response_entry["tool_calls"].append({
                            "tool_name": function_call.name,
                            "tool_args": tool_args,
                            "tool_result": tool_result
                        })
                        
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_call.name,
                            "content": json.dumps(tool_result)
                        }
                        
                        messages = await self.context_manager.add_message(
                            tool_message,
                            iteration
                        )
                        
                        tool_observations.append(f"Tool '{function_call.name}' returned: {json.dumps(tool_result)}")
                    
                    # 添加反思提示作为用户消息
                    reflection_prompt = {
                        "role": "user",
                        "content": (
                            "Based on the tool results:\n" + 
                            "\n".join(tool_observations) + "\n\n" +
                            "Please analyze these results and decide:\n" +
                            "1. What have we learned?\n" +
                            "2. Do we need more information?\n" +
                            "3. Are we ready for a Final Answer?\n"
                        )
                    }
                    
                    messages = await self.context_manager.add_message(
                        reflection_prompt,
                        iteration
                    )
                    
                else:
                    # 如果没有工具调用且没有最终答案，添加提示继续思考
                    if "Final Answer:" not in content:
                        continue_prompt = {
                            "role": "user",
                            "content": (
                                "You haven't used any tools or provided a Final Answer. "
                                "Please either use tools to gather more information or "
                                "provide a Final Answer if you have enough information."
                            )
                        }
                        
                        messages = await self.context_manager.add_message(
                            continue_prompt,
                            iteration
                        )
                
                all_responses.append(response_entry)
                
            except Exception as e:
                error_msg = f"Error in iteration {iteration}: {str(e)}"
                logger.error(error_msg)
                all_responses.append({
                    "iteration": iteration,
                    "error": error_msg
                })
                break
                
        try:
            # 获取中国时间
            china_tz = pytz.timezone('Asia/Shanghai')
            current_time = datetime.now(china_tz)
            timestamp = current_time.strftime('%Y_%m_%d_%H_%M')
            
            # 创建 outputs 目录（如果不存在）
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件名
            output_filename = f"{timestamp}_result_mcp_demo_using_reAct.txt"
            output_path = os.path.join(output_dir, output_filename)
            
            # 写入结果
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Query: {user_query}\n")
                f.write("=" * 80 + "\n\n")
                
                for response in all_responses:
                    f.write(f"--- Iteration {response['iteration']} ---\n")
                    
                    # 写入助手响应
                    if 'content' in response:
                        f.write(f"Assistant: {response['content']}\n")
                    
                    # 写入工具调用结果（如果有）
                    if response.get('tool_calls'):
                        f.write("\nTool Calls:\n")
                        for tool_call in response['tool_calls']:
                            f.write(f"\nTool: {tool_call['tool_name']}\n")
                            f.write(f"Arguments: {json.dumps(tool_call['tool_args'], indent=2, ensure_ascii=False)}\n")
                            f.write(f"Result: {json.dumps(tool_call['tool_result'], indent=2, ensure_ascii=False)}\n")
                    
                    # 写入错误信息（如果有）
                    if 'error' in response:
                        f.write(f"\nERROR: {response['error']}\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
                
                # 写入总结信息
                f.write(f"\nTotal iterations: {len(all_responses)}\n")
                f.write(f"Timestamp: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
            
            logger.info(f"Results written to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error writing results to file: {str(e)}")
        
        return all_responses
        
    async def disconnect(self) -> None:
        """清理连接资源"""
        try:
            if hasattr(self, '_session_context') and self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if hasattr(self, '_streams_context') and self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
        finally:
            self.mcp_session = None
            self.tools = []
