"""
PymChat LLM工具：发送消息
按照AstrBot官方文档的FunctionTool写法
"""
from typing import Any

from pydantic import Field
from pydantic.dataclasses import dataclass

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class SendPymChatMessageTool(FunctionTool[AstrAgentContext]):
    """
    通过PymChat API发送消息的工具
    """
    plugin_instance: Any = None  # 引用主插件实例

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
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "目标用户名（私聊）或群组ID（群聊）",
                },
                "message": {
                    "type": "string",
                    "description": "要发送的消息内容",
                },
                "message_type": {
                    "type": "string",
                    "enum": ["private", "group"],
                    "description": "消息类型：private=私聊，group=群组，默认为private",
                },
            },
            "required": ["target", "message"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        """
        执行发送消息

        Args:
            context: AstrBot上下文
            **kwargs: 工具参数 (target, message, message_type)

        Returns:
            执行结果
        """
        target = kwargs.get("target")
        message = kwargs.get("message")
        message_type = kwargs.get("message_type", "private")

        if not self.plugin_instance:
            return "错误：插件实例未初始化"

        if not target or not message:
            return "错误：缺少必要参数 target 或 message"

        # 获取当前用户ID并发送消息
        event = context.context.event
        user_id = str(event.sender_id)
        result = await self.plugin_instance.send_message_api_by_user_id(user_id, target, message, message_type)

        if result.get("success"):
            return f"消息已成功发送给 {target}（类型: {message_type}）"
        else:
            return f"发送失败: {result.get('error')}"
