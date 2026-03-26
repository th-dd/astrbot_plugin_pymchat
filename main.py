"""
PymChat插件主文件
支持LLM工具调用和指令发送PymChat消息
"""
import httpx
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain

from .tools.send import SendPymChatMessageTool


@register("pymchat", "叹号大帝", "集成PymChat跨平台聊天API，支持LLM工具调用和指令发送消息", "1.0.0")
class PymChatPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://chat.qplm.xyz/api/messages.php"
        self.api_key: Optional[str] = None
        self._load_config()
        
    def _load_config(self):
        """加载配置"""
        config = self.context.get_plugin_config()
        if config:
            self.api_url = config.get("api_url", self.api_url)
            self.api_key = config.get("api_key")
            username = config.get("username")
            password = config.get("password")
            if username and password and not self.api_key:
                # 尝试自动登录获取API Key
                import asyncio
                asyncio.create_task(self._auto_login(username, password))
    
    async def _auto_login(self, username: str, password: str):
        """自动登录获取API Key"""
        try:
            result = await self.login(username, password)
            if result.get("success"):
                self.api_key = result.get("api_key")
                logger.info(f"PymChat: 自动登录成功，API Key已获取")
        except Exception as e:
            logger.error(f"PymChat: 自动登录失败: {e}")
    
    async def initialize(self):
        """插件初始化"""
        # 注册LLM工具
        self.context.add_llm_tools(SendPymChatMessageTool(self))
        logger.info("PymChat插件已加载")
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        登录PymChat获取API Key
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            包含api_key的字典
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 登录接口 - 根据PymChat API文档
                response = await client.post(
                    self.api_url,
                    json={
                        "action": "login",
                        "username": username,
                        "password": password
                    }
                )
                data = response.json()
                
                if data.get("success") or data.get("code") == 0:
                    api_key = data.get("api_key") or data.get("key") or data.get("token")
                    if api_key:
                        self.api_key = api_key
                        logger.info(f"PymChat登录成功")
                        return {"success": True, "api_key": api_key}
                
                return {"success": False, "error": data.get("message", "登录失败")}
                
        except Exception as e:
            logger.error(f"PymChat登录异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_message(self, target: str, message: str, message_type: str = "private") -> Dict[str, Any]:
        """
        发送消息到PymChat
        
        Args:
            target: 目标用户/群组
            message: 消息内容
            message_type: 消息类型 private/group
            
        Returns:
            发送结果
        """
        if not self.api_key:
            return {"success": False, "error": "未登录，请先使用 /pymchat_login 或配置API Key"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "api_key": self.api_key,
                        "action": "send_message",
                        "target": target,
                        "message": message,
                        "type": message_type
                    }
                )
                data = response.json()
                
                if data.get("success") or data.get("code") == 0:
                    return {"success": True, "message": "发送成功"}
                
                return {"success": False, "error": data.get("message", "发送失败")}
                
        except Exception as e:
            logger.error(f"PymChat发送消息异常: {e}")
            return {"success": False, "error": str(e)}
    
    @filter.command("pymchat_login")
    async def cmd_login(self, event: AstrMessageEvent):
        """登录PymChat获取API Key"""
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        
        if len(parts) < 2:
            yield event.plain_result("用法: /pymchat_login <用户名> <密码>")
            return
        
        username, password = parts[0], parts[1]
        
        result = await self.login(username, password)
        
        if result.get("success"):
            yield event.plain_result(f"✓ 登录成功！API Key已保存（有效期30天）")
        else:
            yield event.plain_result(f"✗ 登录失败: {result.get('error')}")
    
    @filter.command("pymchat_send")
    async def cmd_send(self, event: AstrMessageEvent):
        """发送消息到PymChat"""
        message_str = event.message_str.strip()
        
        # 格式: <目标> <消息> 或 <目标> <类型> <消息>
        parts = message_str.split(maxsplit=2)
        
        if len(parts) < 2:
            yield event.plain_result("用法: /pymchat_send <目标用户> <消息内容>\n或: /pymchat_send <目标用户> <private|group> <消息内容>")
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
            yield event.plain_result(f"✓ 消息已发送给 {target}")
        else:
            yield event.plain_result(f"✗ 发送失败: {result.get('error')}")
    
    @filter.command("pymchat_status")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看PymChat连接状态"""
        if self.api_key:
            status = "已登录 ✓"
            # 尝试获取用户信息
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        self.api_url,
                        json={"api_key": self.api_key, "action": "get_user_info"}
                    )
                    data = response.json()
                    if data.get("username"):
                        status = f"已登录: {data.get('username')} ✓"
            except:
                pass
        else:
            status = "未登录 ✗"
        
        yield event.plain_result(f"PymChat 状态: {status}\nAPI地址: {self.api_url}")
    
    async def terminate(self):
        """插件卸载"""
        logger.info("PymChat插件已卸载")
