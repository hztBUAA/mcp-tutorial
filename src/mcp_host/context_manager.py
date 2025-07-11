from typing import List, Dict, Any, Optional, Union
import json
import logging

logger = logging.getLogger("context_manager")

class ContextManager:
    def __init__(self, 
                 max_messages: int = 20,
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
            "tool_calls" in messages[start_idx] and
            messages[start_idx]["tool_calls"] is not None):
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
        """压缩当前上下文，保持tool相关消息的完整性和时序性"""
        compressed_context: List[Dict[str, Any]] = []
        if self.system_prompt is not None:
            compressed_context.append(self.system_prompt)

        # 按时序将消息分组，确保tool calls和responses的完整性
        message_groups = []
        idx = 0
        while idx < len(self.messages):
            if self.messages[idx]["role"] in ["user", "assistant"]:
                end_idx, group = self._get_message_group(self.messages, idx)
                message_groups.append(group)
                idx = end_idx
            else:
                idx += 1

        # 为每组消息创建总结提示
        for group in message_groups:
            if len(group) == 1 and group[0]["role"] == "user":
                # 用户消息保持原样
                compressed_context.extend(group)
                continue

            # 准备总结提示
            if any(msg["role"] == "tool" for msg in group):
                # 处理包含tool调用的消息组
                assistant_msg = next(msg for msg in group if msg["role"] == "assistant")
                tool_calls = assistant_msg.get("tool_calls", [])
                
                summary_prompt = {
                    "role": "user",
                    "content": f"""请总结这组工具调用相关的消息，包括：
1. Assistant的意图和推理
2. 工具调用的关键结果
3. 保持工具调用ID和关键参数的完整性

原始消息：
{json.dumps(group, ensure_ascii=False, indent=2)}
"""
                }
            else:
                # 处理普通的assistant消息
                summary_prompt = {
                    "role": "user",
                    "content": f"""请总结这组消息的要点，包括：
1. Assistant的推理过程
2. 关键发现和结论

原始消息：
{json.dumps(group, ensure_ascii=False, indent=2)}
"""
                }

            try:
                response = self.openai_client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[summary_prompt],
                    temperature=0.3
                )
                
                summary = response.choices[0].message.content

                if any(msg["role"] == "tool" for msg in group):
                    # 对于工具调用消息组，保持结构但压缩内容
                    assistant_msg = next(msg for msg in group if msg["role"] == "assistant")
                    compressed_assistant = {
                        "role": "assistant",
                        "content": summary,
                        "tool_calls": tool_calls if tool_calls is not None else []
                    }
                    compressed_context.append(compressed_assistant)

                    # 为每个tool调用添加压缩后的响应
                    for tool_msg in group:
                        if tool_msg["role"] == "tool":
                            compressed_tool = {
                                "role": "tool",
                                "tool_call_id": tool_msg["tool_call_id"],
                                "name": tool_msg["name"],
                                "content": f"Summarized result: {summary}"
                            }
                            compressed_context.append(compressed_tool)
                else:
                    # 对于普通消息组，直接添加总结
                    compressed_context.append({
                        "role": "assistant",
                        "content": summary
                    })

            except Exception as e:
                logger.error(f"Failed to compress message group: {str(e)}")
                # 发生错误时保留原始消息组
                compressed_context.extend(group)

        return compressed_context
    
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
