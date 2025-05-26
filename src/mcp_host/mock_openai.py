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
            message = MockMessage(content=None, tool_calls=[tool_call])
            return MockResponse([MockChoice(message)])
            
        else:
            message = MockMessage(
                content="Based on my search, I found several papers about machine learning published between 2020 and 2023. These papers cover various topics including deep learning, reinforcement learning, and natural language processing."
            )
            return MockResponse([MockChoice(message)])

class MockAzureOpenAI:
    """Mock implementation of Azure OpenAI client."""
    
    def __init__(self, **kwargs):
        """Initialize the mock client."""
        self.api_key = kwargs.get("api_key", "mock-api-key")
        self.api_version = kwargs.get("api_version", "2024-02-01")
        self.api_base = kwargs.get("api_base", "https://mock-endpoint.openai.azure.com")
        self.chat = type('MockChat', (), {'completions': MockChatCompletions()})()
