"""
PymChat插件主文件
支持LLM工具调用和中文指令发送PymChat消息
支持多用户登录
"""
import httpx
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .tools.send import SendPymChatMessageTool


@dataclass
class PymChatUser:
    """PymChat用户"""
    user_id: str
    username: str
    api_key: str


@register("astrbot_plugin_pymchat", "叹号大帝", "集成PymChat跨平台聊天API，支持LLM工具调用和中文指令发送消息", "1.0.0")
class PymChatPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context, config)
        self.api_url = "https://chat.qplm.xyz/api/messages.php"
        self.pending_login: Dict[str, Dict[str, Any]] = {}  # token -> {user_id}
        self.users: Dict[str, PymChatUser] = {}  # user_id -> PymChatUser
        # 使用get_astrbot_data_path获取数据目录
        self.data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "astrbot_plugin_pymchat"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "pymchat_users.json"
        self._load_config(config)
        self._load_users()

    def _load_config(self, config: AstrBotConfig | None):
        """加载配置"""
        if config:
            self.api_url = config.get("api_url", self.api_url)

    def _load_users(self):
        """加载已保存的用户数据"""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, user_data in data.items():
                        self.users[user_id] = PymChatUser(
                            user_id=user_id,
                            username=user_data["username"],
                            api_key=user_data["api_key"]
                        )
                logger.info(f"PymChat: 已加载 {len(self.users)} 个用户")
        except Exception as e:
            logger.error(f"PymChat: 加载用户数据失败: {e}")

    def _save_users(self):
        """保存用户数据"""
        try:
            data = {
                user_id: {
                    "username": user.username,
                    "api_key": user.api_key
                }
                for user_id, user in self.users.items()
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"PymChat: 保存用户数据失败: {e}")

    def _get_user(self, event: AstrMessageEvent) -> Optional[PymChatUser]:
        """获取当前用户"""
        user_id = str(event.sender_id)
        return self.users.get(user_id)

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
                        return {"success": True, "api_key": api_key, "username": username}

                return {"success": False, "error": data.get("message", "登录失败")}

        except Exception as e:
            logger.error(f"PymChat登录异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_message_api(self, user: PymChatUser, target: str, message: str, message_type: str = "private") -> Dict[str, Any]:
        """使用指定用户的API Key发送消息"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "api_key": user.api_key,
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

    @filter.command("pc登录")
    async def cmd_login(self, event: AstrMessageEvent):
        """
        登录PymChat
        """
        user_id = str(event.sender_id)
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)

        # 检查是否为群聊
        is_group = hasattr(event, "group_id") and event.group_id

        if is_group and len(parts) == 0:
            # 群内无参数触发，生成token
            import secrets
            token = secrets.token_hex(16)
            self.pending_login[token] = {"user_id": user_id}

            yield event.plain_result(
                "PymChat登录已触发\n"
                "请私聊机器人发送：\n"
                f"【{token}】用户名 密码\n\n"
                "示例：abc123... zhangsan 123456"
            )
        elif is_group and len(parts) >= 1:
            # 群内带token，验证并登录
            token = parts[0]
            pending = self.pending_login.get(token)

            if not pending:
                yield event.plain_result("Token无效或已过期，请先发送 pc登录 获取新token")
                return

            del self.pending_login[token]

            yield event.plain_result(
                "Token验证通过\n"
                "请私聊机器人完成最终登录：\n"
                "用户名 密码"
            )
        else:
            # 私聊直接处理
            if len(parts) < 2:
                yield event.plain_result(
                    "PymChat登录\n\n"
                    "格式：用户名 密码\n"
                    "示例：zhangsan 123456"
                )
                return

            username, password = parts[0], parts[1]
            result = await self.login(username, password)

            if result.get("success"):
                user = PymChatUser(
                    user_id=user_id,
                    username=result["username"],
                    api_key=result["api_key"]
                )
                self.users[user_id] = user
                self._save_users()
                yield event.plain_result(
                    f"登录成功！\n"
                    f"用户：{result['username']}\n"
                    f"API Key已保存（有效期30天）"
                )
            else:
                yield event.plain_result(f"登录失败: {result.get('error')}")

    @filter.command("pc发消息")
    async def cmd_send(self, event: AstrMessageEvent):
        """发送消息到PymChat"""
        user_id = str(event.sender_id)
        user = self.users.get(user_id)

        if not user:
            yield event.plain_result(
                "您还未登录PymChat\n"
                "请先发送：pc登录 用户名 密码"
            )
            return

        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=2)

        if len(parts) < 2:
            yield event.plain_result(
                "PymChat发消息\n\n"
                "格式：目标 消息\n"
                "示例：pc发消息 张三 你好\n\n"
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

        result = await self.send_message_api(user, target, message, msg_type)

        if result.get("success"):
            yield event.plain_result(f"消息已发送给 {target}")
        else:
            yield event.plain_result(f"发送失败: {result.get('error')}")

    @filter.command("pc状态")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看PymChat连接状态"""
        user_id = str(event.sender_id)
        user = self.users.get(user_id)

        if user:
            status = f"已登录：{user.username}"
        else:
            status = "未登录"

        yield event.plain_result(
            f"PymChat 状态\n"
            f"登录状态：{status}\n"
            f"API地址：{self.api_url}\n\n"
            f"指令帮助：\n"
            f"  pc登录 - 登录账号\n"
            f"  pc发消息 - 发送消息\n"
            f"  pc状态 - 查看状态\n"
            f"  pc登出 - 退出登录"
        )

    @filter.command("pc登出")
    async def cmd_logout(self, event: AstrMessageEvent):
        """退出登录"""
        user_id = str(event.sender_id)

        if user_id in self.users:
            username = self.users[user_id].username
            del self.users[user_id]
            self._save_users()
            yield event.plain_result(f"已退出登录（{username}）")
        else:
            yield event.plain_result("您还未登录")

    async def terminate(self):
        """插件卸载"""
        self._save_users()
        logger.info("PymChat插件已卸载")
