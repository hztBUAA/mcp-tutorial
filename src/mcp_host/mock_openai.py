"""
Mock implementation of Azure OpenAI client for testing purposes.
This allows us to test the MCP host and client without requiring actual Azure OpenAI credentials.
"""

import json
import logging
from typing import List, Dict, Any, Optional, cast

logger = logging.getLogger("mock_openai")

class MockMessage:
    """Mock implementation of OpenAI message."""
    
    def __init__(self, content: Optional[str] = None, tool_calls: Optional[List["MockToolCall"]] = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.id = "mock-message-id"
        
    def model_dump(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        result = {"role": "assistant"}
        if self.content:
            result["content"] = self.content
        if self.tool_calls:
            serialized_tool_calls = []
            for tc in self.tool_calls:
                serialized_tool_calls.append({
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    },
                    "type": "function"
                })
            result["tool_calls"] = serialized_tool_calls
        return result

class MockToolCall:
    """Mock implementation of OpenAI tool call."""
    
    def __init__(self, name: str, arguments: Dict[str, Any]):
        self.id = f"mock-tool-call-{name}"
        self.function = MockFunctionCall(name, arguments)

class MockFunctionCall:
    """Mock implementation of OpenAI function call."""
    
    def __init__(self, name: str, arguments: Dict[str, Any]):
        self.name = name
        self.arguments = json.dumps(arguments)

class MockChoice:
    """Mock implementation of OpenAI choice."""
    
    def __init__(self, message: MockMessage):
        self.message = message

class MockResponse:
    """Mock implementation of OpenAI response."""
    
    def __init__(self, choices: List[MockChoice]):
        self.choices = choices

class MockChatCompletions:
    """Mock implementation of OpenAI chat completions."""
    
    def __init__(self):
        self.call_count = 0
        
    def create(self, **kwargs) -> MockResponse:
        """Create a mock chat completion."""
        self.call_count += 1
        
        if self.call_count == 1:
            # 第一次调用：搜索论文
            tool_call = MockToolCall(
                name="search-papers-normal",
                arguments={
                    "authors": "machine learning",
                    "start_time": "2020",
                    "end_time": "2023",
                    "page": 1,
                    "size": 5
                }
            )
            message = MockMessage(
                content=None,
                tool_calls=[tool_call]
            )
            return MockResponse([MockChoice(message)])
            
        elif self.call_count == 2:
            # 第二次调用：分析结果
            message = MockMessage(
                content="""基于搜索结果，我找到了几篇关于量子计算的重要论文。让我为您总结一下。

Final Answer: 我找到了以下关于量子计算的最新研究：
1. "量子计算：现状与未来" (2023)
2. "量子算法的最新进展" (2023)
3. "量子优越性的实验验证" (2022)

这些论文涵盖了量子计算的最新发展，包括算法优化、硬件实现和应用案例。"""
            )
            return MockResponse([MockChoice(message)])
        
        else:
            # 默认响应
            message = MockMessage(
                content="我已经完成了搜索和分析。\n\nFinal Answer: 这是一个模拟响应。"
            )
            return MockResponse([MockChoice(message)])

class MockAzureOpenAI:
    """Mock implementation of Azure OpenAI client."""
    
    def __init__(self, **kwargs):
        """Initialize the mock client."""
        self.api_key = kwargs.get("api_key", "mock-api-key")
        self.api_version = kwargs.get("api_version", "2024-02-01")
        self.azure_endpoint = kwargs.get("azure_endpoint", "https://mock-endpoint.openai.azure.com")
        self.chat = type('MockChat', (), {'completions': MockChatCompletions()})()
