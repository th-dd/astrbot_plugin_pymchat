# astrbot_plugin_pymchat

AstrBot插件：集成PymChat跨平台聊天API

## 功能特性

- 中文指令：`pc登录`、`pc发消息`、`pc状态`、`pc登出`
- LLM工具调用：支持通过AI直接调用发送PymChat消息
- 多用户支持：每个用户独立登录，数据持久化
- 安全登录：群内触发获取token，私聊完成验证

## 安装

在AstrBot插件管理页面添加仓库：

```
https://github.com/th-dd/astrbot_plugin_pymchat
```

或手动克隆到插件目录后重载插件

## 配置

在AstrBot配置文件中添加（可选）：

```yaml
plugins:
  - name: astrbot_plugin_pymchat
    config:
      api_url: "https://chat.qplm.xyz/api/"
```

## 使用方法

### 指令方式

**私聊直接登录：**
```
pc登录 用户名 密码
```

**群内安全登录：**
1. 群内发送 `pc登录` → 获取token
2. 私聊发送 `【token】用户名 密码` → 完成验证

**发送消息：**
```
pc发消息 目标用户 消息内容
pc发消息 群名称 group 消息内容  # 群组消息
```

**其他指令：**
```
pc状态  # 查看登录状态
pc登出  # 退出登录
```

### LLM工具方式

你可以让AI助手帮你发送消息，例如：

"帮我给xxx发送一条消息：你好呀"

## 数据存储

用户登录数据保存在：

```
data/plugin_data/astrbot_plugin_pymchat/pymchat_users.json
```

## API说明

- API地址：https://chat.qplm.xyz/api/messages.php
- 认证方式：API Key（有效期30天）

## 作者

叹号大帝

## 支持

如有问题请联系作者或提交Issue。
