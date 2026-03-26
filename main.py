"""
PymChat插件主文件
支持LLM工具调用和指令发送PymChat消息
"""
import httpx
from typing import Optional, Dict, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .tools.send import SendPymChatMessageTool


@register("pymchat", "叹号大帝", "集成PymChat跨平台聊天API，支持LLM工具调用和指令发送消息", "1.0.0")
class PymChatPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://chat.qplm.xyz/api/messages.php"
        self.api_key: Optional[str] = None
        self.pending_login: Dict[str, Dict[str, Any]] = {}  # token -> {user_id, username}
        self._load_config()

    def _load_config(self):
        """加载配置"""
        config = self.context.get_plugin_config()
        if config:
            self.api_url = config.get("api_url", self.api_url)
            self.api_key = config.get("api_key")

    async def initialize(self):
        """插件初始化"""
        self.context.add_llm_tools(SendPymChatMessageTool(plugin_instance=self))
        logger.info("PymChat插件已加载")

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """登录PymChat获取API Key"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "action": "login",
                        "username": username,
                        "password": password,
                    },
                )
                data = response.json()

                if data.get("success") or data.get("code") == 0:
                    api_key = data.get("api_key") or data.get("key") or data.get("token")
                    if api_key:
                        self.api_key = api_key
                        return {"success": True, "api_key": api_key}

                return {"success": False, "error": data.get("message", "登录失败")}

        except Exception as e:
            logger.error(f"PymChat登录异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_message(self, target: str, message: str, message_type: str = "private") -> Dict[str, Any]:
        """发送消息到PymChat"""
        if not self.api_key:
            return {"success": False, "error": "未登录，请先使用 /pc_login 或配置API Key"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "api_key": self.api_key,
                        "action": "send_message",
                        "target": target,
                        "message": message,
                        "type": message_type,
                    },
                )
                data = response.json()

                if data.get("success") or data.get("code") == 0:
                    return {"success": True}

                return {"success": False, "error": data.get("message", "发送失败")}

        except Exception as e:
            logger.error(f"PymChat发送消息异常: {e}")
            return {"success": False, "error": str(e)}

    @filter.command("pc_login")
    async def cmd_login(self, event: AstrMessageEvent):
        """
        第一步：在群内触发登录，返回提示让用户私聊发送密码
        """
        user_id = str(event.sender_id)

        # 检查是否为群聊消息
        is_group = hasattr(event, "is_group_message") and event.is_group_message

        if is_group:
            # 群内触发，生成临时标记并提示私聊
            import secrets
            token = secrets.token_hex(16)
            self.pending_login[token] = {"user_id": user_id}

            yield event.plain_result(
                f"PymChat登录已触发\n"
                f"请私聊机器人发送：\n"
                f"【{token}】你的用户名 你的密码\n\n"
                f"示例：{token} zhangsan 123456"
            )
        else:
            # 私聊直接处理
            message_str = event.message_str.strip()
            parts = message_str.split(maxsplit=1)

            if len(parts) < 2:
                yield event.plain_result(
                    "PymChat登录\n\n"
                    "格式：你的用户名 你的密码\n"
                    "示例：zhangsan 123456"
                )
                return

            username, password = parts[0], parts[1]
            result = await self.login(username, password)

            if result.get("success"):
                yield event.plain_result("登录成功！API Key已保存（有效期30天）")
            else:
                yield event.plain_result(f"登录失败: {result.get('error')}")

    @filter.command("pc_login_verify")
    async def cmd_login_verify(self, event: AstrMessageEvent):
        """
        第二步：私聊发送 token 用户名 密码 完成登录
        """
        user_id = str(event.sender_id)

        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=2)

        if len(parts) < 3:
            yield event.plain_result(
                "格式：token 用户名 密码\n"
                "示例：abc123... zhangsan 123456"
            )
            return

        token, username, password = parts[0], parts[1], parts[2]

        # 验证token
        pending = self.pending_login.get(token)
        if not pending:
            yield event.plain_result("Token无效或已过期，请先在群内发送 /pc_login 获取新token")
            return

        # 删除pending记录
        del self.pending_login[token]

        # 执行登录
        result = await self.login(username, password)

        if result.get("success"):
            yield event.plain_result("登录成功！API Key已保存（有效期30天）")
        else:
            yield event.plain_result(f"登录失败: {result.get('error')}")

    @filter.command("pc_send")
    async def cmd_send(self, event: AstrMessageEvent):
        """发送消息到PymChat"""
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=2)

        if len(parts) < 2:
            yield event.plain_result(
                "格式：目标用户 消息\n"
                "示例：/pc_send 张三 你好\n\n"
                "或指定类型：目标 private/group 消息"
            )
            return

        target = parts[0]

        if len(parts) == 3:
            msg_type = parts[1]
            message = parts[2]
        else:
            msg_type = "private"
            message = parts[1]

        result = await self.send_message(target, message, msg_type)

        if result.get("success"):
            yield event.plain_result(f"消息已发送给 {target}")
        else:
            yield event.plain_result(f"发送失败: {result.get('error')}")

    @filter.command("pc_status")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看PymChat连接状态"""
        if self.api_key:
            status = "已登录"
        else:
            status = "未登录"

        yield event.plain_result(
            f"PymChat 状态：{status}\n"
            f"API地址：{self.api_url}"
        )

    async def terminate(self):
        """插件卸载"""
        logger.info("PymChat插件已卸载")
