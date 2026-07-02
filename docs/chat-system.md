# 实时通信系统使用说明

## 功能概述

本系统实现了完整的即时通讯功能，包括：

- **私聊**: 一对一实时聊天
- **群聊**: 创建群组、群消息、群公告、群成员管理
- **在线状态**: 用户在线/离线/忙碌状态显示
- **消息已读**: 已读回执、未读计数
- **@提醒**: 在消息中@其他用户
- **文件发送**: 图片、文件发送
- **消息搜索**: 搜索历史消息
- **消息撤回**: 2分钟内可撤回消息

## 技术架构

### 后端

- **WebSocket**: `/ws/chat` 端点，支持实时消息推送
- **数据库**: 新增 5 个表 - `conversations`, `conversation_members`, `messages`, `message_read_receipts`, `user_presence`
- **API**: 完整的 RESTful API，支持会话管理、消息管理、在线状态等

### 前端

- **聊天页面**: `/chat` 路由，左侧会话列表 + 右侧聊天窗口
- **WebSocket**: 实时消息接收、输入状态、在线状态
- **状态管理**: Pinia store 管理聊天状态

## 使用步骤

### 1. 数据库迁移

运行 Alembic 迁移创建新的数据库表：

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### 2. 启动服务

```bash
# 终端 1 - 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 - 前端
cd frontend
node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173
```

### 3. 访问聊天页面

1. 登录系统
2. 点击左侧菜单 "即时通讯" 或顶部导航栏的聊天图标
3. 点击 "+" 按钮创建新会话
4. 选择 "私聊" 或 "群聊"
5. 搜索并选择用户
6. 开始聊天

## API 文档

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/conversations` | 创建会话 |
| GET | `/api/v1/conversations` | 获取会话列表 |
| GET | `/api/v1/conversations/{id}` | 获取会话详情 |
| PUT | `/api/v1/conversations/{id}` | 更新群信息 |
| DELETE | `/api/v1/conversations/{id}` | 删除会话/退出群 |

### 成员管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/conversations/{id}/members` | 添加成员 |
| DELETE | `/api/v1/conversations/{id}/members/{uid}` | 移除成员 |
| PUT | `/api/v1/conversations/{id}/members/{uid}` | 更新成员角色 |
| POST | `/api/v1/conversations/{id}/transfer` | 转让群主 |

### 消息管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/conversations/{id}/messages` | 获取消息列表 |
| POST | `/api/v1/conversations/{id}/messages` | 发送消息 |
| DELETE | `/api/v1/conversations/messages/{id}` | 删除消息 |
| POST | `/api/v1/conversations/messages/{id}/recall` | 撤回消息 |
| GET | `/api/v1/conversations/messages/search` | 搜索消息 |

### 已读回执

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/conversations/{id}/messages/{mid}/read` | 标记消息已读 |
| POST | `/api/v1/conversations/{id}/read-all` | 标记会话所有消息已读 |

### 在线状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/conversations/presence/{uid}` | 获取用户在线状态 |
| PUT | `/api/v1/conversations/presence` | 更新我的在线状态 |
| POST | `/api/v1/conversations/presence/batch` | 批量获取在线状态 |

## WebSocket 协议

### 连接地址

```
ws://localhost:8000/ws/chat?token={JWT_TOKEN}
```

### 客户端 -> 服务端

```json
// 输入状态
{
  "type": "typing",
  "conversation_id": "uuid"
}

// 标记已读
{
  "type": "mark_read",
  "conversation_id": "uuid",
  "message_id": "uuid"
}
```

### 服务端 -> 客户端

```json
// 新消息
{
  "type": "new_message",
  "data": {
    "message": { ... },
    "conversation_id": "uuid"
  }
}

// 用户输入中
{
  "type": "user_typing",
  "data": {
    "conversation_id": "uuid",
    "user_id": "uuid",
    "user_name": "用户名"
  }
}

// 在线状态更新
{
  "type": "presence_update",
  "data": {
    "user_id": "uuid",
    "status": "online|away|busy|offline"
  }
}

// 消息已读
{
  "type": "message_read",
  "data": {
    "conversation_id": "uuid",
    "message_id": "uuid",
    "user_id": "uuid"
  }
}
```

## 权限配置

新增的权限码：

- `chat:read` - 查看聊天
- `chat:create` - 创建会话
- `chat:delete` - 删除会话
- `chat:group:create` - 创建群聊
- `chat:group:manage` - 管理群聊

## 文件结构

```
backend/
├── app/
│   ├── models/chat.py              # 数据库模型
│   ├── schemas/conversation.py     # Pydantic Schema
│   ├── repositories/conversation_repo.py  # 数据访问层
│   ├── services/chat_service.py    # 业务逻辑层
│   └── api/conversations.py        # API 路由
└── alembic/versions/
    └── xxx_add_chat_tables.py      # 数据库迁移

frontend/
├── src/
│   ├── types/chat.ts              # TypeScript 类型
│   ├── api/chat.ts                # API 封装
│   ├── stores/chat.ts             # Pinia 状态管理
│   └── views/chat/
│       ├── ChatLayout.vue         # 聊天主布局
│       └── ChatWindow.vue         # 聊天窗口
```

## 后续优化

1. **Redis Pub/Sub**: 支持多进程 WebSocket 广播
2. **消息漫游**: 跨设备消息同步
3. **文件上传**: 完善文件上传功能
4. **表情包**: 支持表情选择
5. **群公告**: 群公告功能
6. **@提醒通知**: @消息同时发送系统通知
