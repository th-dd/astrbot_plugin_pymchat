"""
PymChat LLM工具：发送消息
"""
from typing import Any
from dataclasses import dataclass

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent


@dataclass
class SendPymChatMessageTool(FunctionTool):
    """
    通过PymChat API发送消息的工具
    """
    plugin_instance: Any  # 引用主插件实例
    
    name: str = "send_pymchat_message"
    description: str = """
    通过PymChat跨平台聊天系统发送消息给指定用户或群组。
    
    适用场景：
    - 需要通过PymChat与其他人进行一对一私聊
    - 需要在PymChat群组中发送消息
    - 作为中继器转发消息到PymChat平台
    
    参数说明：
    - target: 目标用户名或群组ID
    - message: 要发送的消息内容（纯文本）
    - message_type: 消息类型，"private"表示私聊，"group"表示群组消息，默认为私聊
    """
    
    parameters: dict = None
    
    def __post_init__(self):
        self.parameters = {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "目标用户名（私聊）或群组ID（群聊）"
                },
                "message": {
                    "type": "string",
                    "description": "要发送的消息内容"
                },
                "message_type": {
                    "type": "string",
                    "enum": ["private", "group"],
                    "description": "消息类型：private=私聊，group=群组，默认为private",
                    "default": "private"
                }
            },
            "required": ["target", "message"]
        }
    
    async def execute(self, event: AstrMessageEvent, target: str, message: str, message_type: str = "private") -> str:
        """
        执行发送消息
        
        Args:
            event: AstrBot事件对象
            target: 目标用户/群组
            message: 消息内容
            message_type: 消息类型
            
        Returns:
            执行结果的文本描述
        """
        if not self.plugin_instance:
            return "错误：插件实例未初始化"
        
        result = await self.plugin_instance.send_message(target, message, message_type)
        
        if result.get("success"):
            return f"✓ 消息已成功发送给 {target}（类型: {message_type}）"
        else:
            return f"✗ 发送失败: {result.get('error')}"
