from typing import List, Dict, Any, Optional, Union
import json
import logging

logger = logging.getLogger("context_manager")

class ContextManager:
    def __init__(self, 
                 max_messages: int = 10,
                 compression_interval: int = 5,
                 openai_client: Any = None,
                 deployment_name: Optional[str] = None):
        self.max_messages = max_messages
        self.compression_interval = compression_interval
        self.messages: List[Dict[str, Any]] = []
        self.system_prompt: Optional[Dict[str, Any]] = None
        self.openai_client = openai_client
        self.deployment_name = deployment_name
        
    async def add_message(self, message: Dict[str, Any], iteration: int) -> List[Dict[str, Any]]:
        """添加新消息并管理上下文"""
        if not self.messages and message["role"] == "system":
            self.system_prompt = message
            
        self.messages.append(message)
        
        if iteration > 0 and iteration % self.compression_interval == 0:
            return await self._compress_context()
            
        return self._apply_sliding_window()
    
    async def _compress_context(self) -> List[Dict[str, Any]]:
        """压缩当前上下文"""
        summary_prompt = {
            "role": "user",
            "content": "请总结到目前为止的对话要点，包括：1. 用户的主要问题 2. 已经发现的关键信息 3. 当前的推理进展"
        }
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=self.messages + [summary_prompt],
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            compressed_context: List[Dict[str, Any]] = []
            if self.system_prompt is not None:
                compressed_context.append(self.system_prompt)
            
            compressed_context.append({
                "role": "assistant",
                "content": f"Previous Context Summary:\n{summary}"
            })
            
            return compressed_context
        except Exception as e:
            logger.error(f"Context compression failed: {str(e)}")
            return self._apply_sliding_window()
    
    def _apply_sliding_window(self) -> List[Dict[str, Any]]:
        """应用滑动窗口机制"""
        if len(self.messages) <= self.max_messages:
            return self.messages
            
        result: List[Dict[str, Any]] = []
        if self.system_prompt is not None:
            result.append(self.system_prompt)
        
        result.extend(self.messages[-(self.max_messages-1):])
        return result
    
    def format_tool_results(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """格式化工具调用结果"""
        formatted_results = []
        for call in tool_calls:
            formatted_results.append({
                "tool_name": call["tool_name"],
                "key_findings": self._extract_key_info(call["tool_result"])
            })
        return {"results": formatted_results}
    
    def _extract_key_info(self, tool_result: Any) -> str:
        """提取工具调用结果中的关键信息"""
        if isinstance(tool_result, str):
            return tool_result[:200] + "..." if len(tool_result) > 200 else tool_result
        return json.dumps(tool_result, ensure_ascii=False)[:200]
