from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ============ 会话相关 Schema ============

class ConversationCreate(BaseModel):
    """创建会话请求"""
    type: str  # 'private' | 'group'
    name: Optional[str] = None  # 群聊名称（群聊必填）
    member_ids: list[UUID]  # 成员ID列表（私聊传1个，群聊传多个）


class ConversationUpdate(BaseModel):
    """更新群信息请求"""
    name: Optional[str] = None
    avatar: Optional[str] = None


class ConversationMemberResponse(BaseModel):
    """会话成员响应"""
    id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    role: str
    nickname: Optional[str] = None
    muted: bool
    joined_at: datetime
    last_read_at: Optional[datetime] = None
    is_online: bool = False

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """会话响应"""
    id: UUID
    type: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    owner_id: Optional[UUID] = None
    last_message_at: Optional[datetime] = None
    last_message_content: Optional[str] = None
    last_message_sender_id: Optional[UUID] = None
    last_message_sender_name: Optional[str] = None
    unread_count: int = 0
    member_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    """会话详情响应（包含成员列表）"""
    members: list[ConversationMemberResponse] = []


class AddMembersRequest(BaseModel):
    """添加成员请求"""
    user_ids: list[UUID]


class UpdateMemberRoleRequest(BaseModel):
    """更新成员角色请求"""
    role: str  # 'admin' | 'member'


# ============ 消息相关 Schema ============

class MessageCreate(BaseModel):
    """发送消息请求"""
    content: str
    type: str = "text"  # 'text'|'image'|'file'
    reply_to_id: Optional[UUID] = None
    mentions: Optional[list[UUID]] = None
    extra_data: Optional[dict] = None


class MessageResponse(BaseModel):
    """消息响应"""
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None
    type: str
    content: str
    reply_to_id: Optional[UUID] = None
    reply_to_content: Optional[str] = None
    reply_to_sender_name: Optional[str] = None
    mentions: Optional[list[UUID]] = None
    extra_data: Optional[dict] = None
    is_read: bool = False
    read_by_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """消息列表响应"""
    items: list[MessageResponse]
    total: int
    has_more: bool


# ============ 在线状态相关 Schema ============

class UserPresenceResponse(BaseModel):
    """用户在线状态响应"""
    user_id: UUID
    status: str  # 'online'|'away'|'busy'|'offline'
    last_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UpdatePresenceRequest(BaseModel):
    """更新在线状态请求"""
    status: str  # 'online'|'away'|'busy'


class BatchPresenceRequest(BaseModel):
    """批量查询在线状态请求"""
    user_ids: list[UUID]


# ============ WebSocket 消息协议 ============

class WsSendMessage(BaseModel):
    """WebSocket 发送消息"""
    type: str = "send_message"
    conversation_id: UUID
    content: str
    msg_type: str = "text"
    reply_to_id: Optional[UUID] = None
    mentions: Optional[list[UUID]] = None
    temp_id: str  # 客户端临时ID


class WsTyping(BaseModel):
    """WebSocket 输入中"""
    type: str = "typing"
    conversation_id: UUID


class WsMarkRead(BaseModel):
    """WebSocket 标记已读"""
    type: str = "mark_read"
    conversation_id: UUID
    message_id: UUID


class WsNewMessage(BaseModel):
    """WebSocket 新消息推送"""
    type: str = "new_message"
    message: MessageResponse
    conversation: ConversationResponse


class WsUserTyping(BaseModel):
    """WebSocket 用户输入中"""
    type: str = "user_typing"
    conversation_id: UUID
    user_id: UUID
    user_name: str


class WsPresenceUpdate(BaseModel):
    """WebSocket 在线状态更新"""
    type: str = "presence_update"
    user_id: UUID
    status: str


class WsMessageRead(BaseModel):
    """WebSocket 消息已读"""
    type: str = "message_read"
    conversation_id: UUID
    message_id: UUID
    user_id: UUID
