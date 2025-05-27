from typing import List, Dict, Any, Optional
import logging
import json
import tiktoken

logger = logging.getLogger("context_manager")

class ContextManager:
    def __init__(self, 
                 model_name: str = "gpt-4o",
                 token_limit: int = 128000,
                 token_threshold: float = 0.8,
                 compression_interval: int = 5,
                 openai_client: Any = None,
                 deployment_name: Optional[str] = None):
        """
        初始化上下文管理器
        
        Args:
            model_name: 模型名称，用于确定编码器和token限制
            token_limit: 模型的最大token限制
            token_threshold: 触发压缩的阈值比例（0.0-1.0）
            compression_interval: 每隔多少轮进行一次压缩检查
            openai_client: OpenAI客户端实例
            deployment_name: 部署名称
        """
        self.model_name = model_name
        self.token_limit = token_limit
        self.token_threshold = token_threshold
        self.compression_interval = compression_interval
        self.messages: List[Dict[str, Any]] = []
        self.system_prompt: Optional[Dict[str, Any]] = None
        self.openai_client = openai_client
        self.deployment_name = deployment_name
        
        try:
            self.encoding = self._get_encoding(model_name)
            logger.info(f"成功初始化{model_name}的tokenizer")
        except Exception as e:
            logger.warning(f"初始化{model_name}的tokenizer失败: {str(e)}")
            self.encoding = None

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

    def _get_encoding(self, model_name: str):
        """获取模型对应的编码器"""
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            logger.warning(f"在tiktoken中未找到模型{model_name}，使用cl100k_base编码")
            return tiktoken.get_encoding("cl100k_base")
    
    def _count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """计算消息列表的token数量"""
        if not self.encoding:
            return sum(len(str(m.get("content", ""))) // 4 for m in messages)
        
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # 每条消息的基础token消耗
            
            for key, value in message.items():
                if key == "role":
                    num_tokens += 1
                elif key == "content" and value:
                    num_tokens += len(self.encoding.encode(str(value)))
                elif key == "name" and value:
                    num_tokens += len(self.encoding.encode(str(value))) + 1
                elif key == "tool_calls" and value:
                    num_tokens += len(self.encoding.encode(str(value)))
            
        num_tokens += 3  # 消息列表的基础token消耗
        return num_tokens

    async def add_message(self, message: Dict[str, Any], iteration: int) -> List[Dict[str, Any]]:
        """添加新消息并管理上下文"""
        if not self.messages and message["role"] == "system":
            self.system_prompt = message
            
        self.messages.append(message)
        
        current_tokens = self._count_tokens(self.messages)
        token_threshold = int(self.token_limit * self.token_threshold)
        
        logger.info(f"当前token数: {current_tokens}/{self.token_limit} (阈值: {token_threshold})")
        
        # 只在达到压缩间隔时检查是否需要压缩
        if iteration > 0 and iteration % self.compression_interval == 0:
            if current_tokens > token_threshold:
                logger.info(f"触发压缩，原因: token数量({current_tokens})超过阈值({token_threshold})")
                return await self._compress_context()
            else:
                logger.info(f"达到压缩间隔({self.compression_interval}轮)但token数({current_tokens})未超过阈值({token_threshold})，不进行压缩")
        
        # 如果token数超出限制，强制压缩
        elif current_tokens > token_threshold:
            logger.warning(f"token数量({current_tokens})超出限制({self.token_limit})，强制压缩")
            return await self._compress_context()
        
        return self.messages
    
    async def _compress_context(self) -> List[Dict[str, Any]]:
        """将历史上下文压缩为一条简洁的assistant消息"""
        compressed_context: List[Dict[str, Any]] = []
        if self.system_prompt is not None:
            compressed_context.append(self.system_prompt)

        # 保留最后一条用户消息
        last_user_message = None
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                last_user_message = msg
                break

        # 收集需要压缩的消息
        messages_to_compress = []
        for msg in self.messages:
            if msg == self.system_prompt or msg == last_user_message:
                continue
            messages_to_compress.append(msg)

        if not messages_to_compress:
            return self.messages

        # 计算压缩提示的基础token数
        base_prompt = """请将对话历史压缩为一条全面但简洁的总结，包括：
1. 已经发现的关键信息。
2. 重要的工具调用记录，包括工具名称，调用方式以及精简的调用结果。
3. 当前的推理进展和结论

对话历史："""
        
        base_tokens = len(self.encoding.encode(base_prompt))
        available_tokens = self.token_limit - base_tokens - 1000  # 预留1000个token的余量
        
        # 从后向前截取消息，确保不超出token限制
        selected_messages = []
        current_tokens = 0
        
        for msg in reversed(messages_to_compress):
            msg_tokens = len(self.encoding.encode(json.dumps(msg, ensure_ascii=False)))
            if current_tokens + msg_tokens > available_tokens:
                break
            selected_messages.insert(0, msg)
            current_tokens += msg_tokens

        # 创建压缩提示
        summary_prompt = {
            "role": "user",
            "content": f"{base_prompt}\n{json.dumps(selected_messages, ensure_ascii=False, indent=2)}"
        }

        try:
            response = self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[summary_prompt],
                temperature=0.3
            )
            
            summary = response.model_dump()['choices'][0]['message']['content']

            # 创建压缩后的上下文：system + summary + last_user
            compressed_context.append({
                "role": "assistant",
                "content": f"历史对话总结：\n{summary}"
            })

            if last_user_message:
                compressed_context.append(last_user_message)

            # 更新内部消息列表
            self.messages = compressed_context
            logger.info(f"压缩后的token数: {self._count_tokens(compressed_context)}")
            return compressed_context

        except Exception as e:
            logger.error(f"压缩上下文失败: {str(e)}")
            # 发生错误时，只保留系统消息和最后的用户消息
            fallback_context = []
            if self.system_prompt:
                fallback_context.append(self.system_prompt)
            if last_user_message:
                fallback_context.append(last_user_message)
            
            self.messages = fallback_context
            return fallback_context
    
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
