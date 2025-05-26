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
        
    def _get_message_group(self, messages: List[Dict[str, Any]], start_idx: int) -> tuple[int, List[Dict[str, Any]]]:
        """获取一个完整的消息组（包括相关的tool calls和responses）"""
        group = [messages[start_idx]]
        end_idx = start_idx + 1
        
        # 如果是assistant消息且包含tool_calls
        if (messages[start_idx]["role"] == "assistant" and 
            "tool_calls" in messages[start_idx]):
            tool_call_count = len(messages[start_idx]["tool_calls"])
            # 收集所有相关的tool响应
            while (end_idx < len(messages) and 
                   messages[end_idx]["role"] == "tool" and 
                   len(group) <= tool_call_count + 1):
                group.append(messages[end_idx])
                end_idx += 1
        
        return end_idx, group

    async def add_message(self, message: Dict[str, Any], iteration: int) -> List[Dict[str, Any]]:
        """添加新消息并管理上下文"""
        if not self.messages and message["role"] == "system":
            self.system_prompt = message
            
        self.messages.append(message)
        
        if iteration > 0 and iteration % self.compression_interval == 0:
            return await self._compress_context()
            
        return self._apply_sliding_window()
    
    async def _compress_context(self) -> List[Dict[str, Any]]:
        """压缩当前上下文，保持tool相关消息的完整性"""
        # 提取需要总结的消息（排除tool相关消息）
        messages_to_summarize = []
        idx = 0
        while idx < len(self.messages):
            if self.messages[idx]["role"] in ["user", "assistant"]:
                end_idx, group = self._get_message_group(self.messages, idx)
                if not any(msg["role"] == "tool" for msg in group):
                    messages_to_summarize.extend(group)
                idx = end_idx
            else:
                idx += 1

        summary_prompt = {
            "role": "user",
            "content": "请总结到目前为止的对话要点，包括：1. 用户的主要问题 2. 已经发现的关键信息 3. 当前的推理进展"
        }
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages_to_summarize + [summary_prompt],
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
            
            # 保留最近的tool相关消息组
            recent_messages = self._apply_sliding_window()
            tool_related_messages = []
            
            idx = 0
            while idx < len(recent_messages):
                if recent_messages[idx]["role"] in ["user", "assistant"]:
                    end_idx, group = self._get_message_group(recent_messages, idx)
                    if any(msg["role"] == "tool" for msg in group):
                        tool_related_messages.extend(group)
                    idx = end_idx
                else:
                    idx += 1
            
            compressed_context.extend(tool_related_messages)
            return compressed_context
            
        except Exception as e:
            logger.error(f"Context compression failed: {str(e)}")
            return self._apply_sliding_window()
    
    def _apply_sliding_window(self) -> List[Dict[str, Any]]:
        """应用滑动窗口机制，保持消息组的完整性"""
        if len(self.messages) <= self.max_messages:
            return self.messages
            
        result: List[Dict[str, Any]] = []
        if self.system_prompt is not None:
            result.append(self.system_prompt)
        
        # 从后向前构建完整的消息组
        remaining_slots = self.max_messages - len(result)
        current_messages = []
        idx = len(self.messages) - 1
        
        while idx >= 0 and len(current_messages) < remaining_slots:
            start_idx = idx
            while start_idx >= 0:
                if self.messages[start_idx]["role"] in ["user", "assistant"]:
                    break
                start_idx -= 1
            
            if start_idx < 0:
                break
                
            _, group = self._get_message_group(self.messages, start_idx)
            if len(current_messages) + len(group) > remaining_slots:
                break
                
            current_messages = group + current_messages
            idx = start_idx - 1
            
        result.extend(current_messages)
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
