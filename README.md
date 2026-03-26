# astrbot_plugin_pymchat

AstrBot插件：集成PymChat跨平台聊天API

## 功能特性

- LLM工具调用：支持通过AI直接调用发送PymChat消息
- 指令发送：使用`/pymchat_send`指令发送消息
- 登录管理：支持配置API密钥

## 安装

1. 在AstrBot插件管理页面添加仓库：
   `https://github.com/th-dd/astrbot_plugin_pymchat`

2. 或手动克隆到插件目录后重载插件

## 配置

在AstrBot配置文件中添加：

```yaml
plugins:
  - name: pymchat
    config:
      api_url: "https://chat.qplm.xyz/api/"
      api_key: "你的API密钥"  # 可选，首次使用会自动登录获取
      username: "你的用户名"  # 用于登录获取API Key
      password: "你的密码"    # 用于登录获取API Key
```

## 使用方法

### 指令方式

```
/pymchat_login <用户名> <密码>
/pymchat_send <目标用户> <消息内容>
/pymchat_send <目标用户> <private|group> <消息内容>
/pymchat_status
```

### LLM工具方式

你可以让AI助手帮你发送消息，例如：

"帮我给xxx发送一条消息：你好呀"

## API说明

- API地址：https://chat.qplm.xyz/api/messages.php
- 认证方式：API Key（有效期30天）

## 作者

叹号大帝

## 支持

如有问题请联系作者或提交Issue。
