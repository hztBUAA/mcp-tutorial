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
import re

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
                
                # 使用辅助方法创建响应条目
                response_entry = self._create_response_entry(iteration, assistant_message)

                messages = await self.context_manager.add_message(
                    assistant_message.model_dump(),
                    iteration
                )
                
                # 检查是否达到最终答案
                if content is not None and "Final Answer:" in content:
                    # 首先检查所有必要章节是否完整
                    sections_complete = all(
                        self._is_section_complete(content, section)
                        for section in ['what_learned', 'need_more', 'ready_final']
                    )
                    
                    # 然后检查是否需要更多分析
                    needs_more_analysis = self._check_needs_more_analysis(content)
                    
                    if sections_complete and not needs_more_analysis:
                        response_entry["is_final"] = True
                        all_responses.append(response_entry)
                        break
                    else:
                        messages = await self.context_manager.add_message(
                            self._create_continue_analysis_prompt(),
                            iteration
                        )
                
                # 处理工具调用
                if assistant_message.tool_calls:
                    response_entry["tool_calls"] = []
                    tool_results = []
                    
                    # 执行每个工具调用并收集结果
                    for tool_call in assistant_message.tool_calls:
                        tool_result = await self._process_tool_call(tool_call, response_entry)
                        tool_results.append(tool_result)
                        
                        messages = await self.context_manager.add_message(
                            tool_result,
                            iteration
                        )
                    
                    # 使用辅助方法创建反思提示
                    reflection_prompt = self._create_reflection_prompt(tool_results)
                    messages = await self.context_manager.add_message(
                        reflection_prompt,
                        iteration
                    )
                    
                else:
                    # 如果没有工具调用且没有最终答案
                    if "Final Answer:" not in content:
                        messages = await self.context_manager.add_message(
                            self._create_continue_prompt(),
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
            
        await self._write_results_to_file(user_query, all_responses)
        return all_responses

    # 新增的辅助方法
    def _check_needs_more_analysis(self, content: str) -> bool:
        """
        检查是否需要更多分析，采用多重判断策略：
        1. 结构化分析：检查是否包含特定的章节标记
        2. 关键词分析：多语言关键词匹配
        3. 上下文分析：检查是否有明确的后续计划或待办事项
        """
        # 1. 结构化分析
        has_final_section = bool(re.search(r'(Final Answer|最终答案|最后答案|总结|Summary)[:：]', content))
        if not has_final_section:
            return True
        
        # 2. 多语言关键词匹配
        need_more_patterns = [
            # 英文关键词
            r'need.+more',
            r'further.+(?:analysis|information|data)',
            r'additional.+(?:analysis|information|data)',
            r'not.+(?:ready|complete|enough)',
            # 中文关键词
            r'需要.+(?:更多|进一步|补充)',
            r'还.+(?:不够|不完整)',
            r'继续.+(?:分析|研究)',
            r'深入.+(?:分析|研究)',
            # 计划相关关键词
            r'next.+step',
            r'plan.+to',
            r'下一步',
            r'接下来',
            r'计划'
        ]
        
        # 3. 上下文分析
        context_patterns = [
            # 检查是否存在明确的后续计划或列表
            r'^\s*\d+\.',  # 数字列表
            r'^\s*[•\-\*]',  # 项目符号列表
            # 检查是否有明确的待办事项
            r'todo',
            r'plan',
            r'next',
            r'待办',
            r'计划',
            # 检查是否提到需要获取更多信息
            r'获取',
            r'collect',
            r'gather',
            r'analyze',
            r'研究',
            r'分析'
        ]
        
        # 将内容按行分割进行分析
        lines = content.lower().split('\n')
        
        # 在最后N行中检查是否有继续分析的迹象
        last_n_lines = lines[-5:]  # 检查最后5行
        last_section = '\n'.join(last_n_lines)
        
        # 检查是否存在需要更多分析的模式
        for pattern in need_more_patterns:
            if re.search(pattern, content.lower()):
                return True
            
        # 在最后部分检查是否有上下文模式
        for pattern in context_patterns:
            if re.search(pattern, last_section):
                return True
            
        # 检查是否包含问题或疑问句
        if re.search(r'[?？]', last_section):
            return True
        
        # 检查是否包含明确的结束语
        conclusion_patterns = [
            r'(conclusion|结论|总结)[:：].*(?:完整|complete|done|finished)',
            r'(no.+(?:further|more|additional)|不需要.+更多)',
            r'(ready|准备好).+(?:final|conclude|总结)',
        ]
        
        has_conclusion = any(re.search(pattern, content.lower()) for pattern in conclusion_patterns)
        if has_conclusion:
            return False
        
        # 默认需要更多分析
        # 这是一个保守的策略，除非明确表示完成，否则继续分析
        return True

    def _is_section_complete(self, content: str, section_name: str) -> bool:
        """
        检查特定章节是否完整
        """
        # 通用的章节标记模式
        section_patterns = {
            'what_learned': [
                r'(?:what.+learned|学到.+什么|总结发现)',
                r'(?:findings|发现|结果)'
            ],
            'need_more': [
                r'(?:need.+more|是否需要.+信息|是否需要.+分析)',
                r'(?:additional|更多|补充)'
            ],
            'ready_final': [
                r'(?:ready.+final|准备.+最终|可以.+总结)',
                r'(?:conclude|总结|结论)'
            ]
        }
        
        if section_name not in section_patterns:
            return False
        
        patterns = section_patterns[section_name]
        section_exists = any(re.search(pattern, content.lower()) for pattern in patterns)
        
        if not section_exists:
            return False
        
        # 检查章节内容是否为空或过短
        section_content = re.split(r'\n+(?=\w)', content.lower())
        relevant_sections = [s for s in section_content if any(re.search(pattern, s) for pattern in patterns)]
        
        if not relevant_sections:
            return False
        
        # 检查章节内容是否包含实质性信息
        section_text = relevant_sections[0]
        # 排除只有标题的情况
        if len(section_text.split('\n')) <= 1:
            return False
        
        return True

    def _create_continue_analysis_prompt(self) -> Dict[str, Any]:
        """创建继续分析提示"""
        return {
            "role": "user",
            "content": (
                "I notice that we still need more information or analysis. "
                "Please continue with the necessary tool calls or analysis "
                "before providing the final answer."
            )
        }

    def _create_continue_prompt(self) -> Dict[str, Any]:
        """创建继续思考提示"""
        return {
            "role": "user",
            "content": (
                "You haven't used any tools or provided a Final Answer. "
                "Please either use tools to gather more information or "
                "provide a Final Answer if you have enough information."
            )
        }

    async def _process_tool_call(self, tool_call, response_entry: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个工具调用"""
        function_call = tool_call.function
        tool_args = json.loads(function_call.arguments)
        tool_result = await self._call_tool(function_call.name, tool_args)
        
        response_entry["tool_calls"].append({
            "tool_name": function_call.name,
            "tool_args": tool_args,
            "tool_result": tool_result
        })
        
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": function_call.name,
            "content": json.dumps(tool_result)
        }

    async def _write_results_to_file(self, user_query: str, all_responses: List[Dict[str, Any]]):
        """将结果写入文件"""
        try:
            china_tz = pytz.timezone('Asia/Shanghai')
            current_time = datetime.now(china_tz)
            timestamp = current_time.strftime('%Y_%m_%d_%H_%M')
            
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            output_filename = f"{timestamp}_result_mcp_demo_using_reAct.txt"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Query: {user_query}\n")
                f.write("=" * 80 + "\n\n")
                
                for response in all_responses:
                    f.write(f"--- Iteration {response['iteration']} ---\n")
                    
                    if 'content' in response:
                        f.write(f"Assistant: \n\n{response['content']}\n\n")
                    
                    if response.get('tool_calls'):
                        f.write("\nTool Calls:\n")
                        for tool_call in response['tool_calls']:
                            f.write(f"\nTool: {tool_call['tool_name']}\n")
                            f.write(f"Arguments: {json.dumps(tool_call['tool_args'], indent=2, ensure_ascii=False)}\n")
                            f.write(f"Result: {json.dumps(tool_call['tool_result'], indent=2, ensure_ascii=False)}\n")
                    
                    if 'error' in response:
                        f.write(f"\nERROR: {response['error']}\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
                
                f.write(f"\nTotal iterations: {len(all_responses)}\n")
                f.write(f"Timestamp: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
            
            logger.info(f"Results written to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error writing results to file: {str(e)}")
        
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
