import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, ConversationMember, Message
from app.models.user import User
from app.repositories.conversation_repo import (
    ConversationRepo,
    ConversationMemberRepo,
    MessageRepo,
    MessageReadReceiptRepo,
    UserPresenceRepo,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationMemberResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    UserPresenceResponse,
)

logger = logging.getLogger(__name__)

# WebSocket connection manager for chat: user_id -> set of WebSocket connections
_chat_ws_connections: dict[uuid.UUID, set] = {}


def register_chat_ws(user_id: uuid.UUID, ws) -> None:
    """Register a WebSocket connection for chat."""
    if user_id not in _chat_ws_connections:
        _chat_ws_connections[user_id] = set()
    _chat_ws_connections[user_id].add(ws)


def unregister_chat_ws(user_id: uuid.UUID, ws) -> None:
    """Unregister a WebSocket connection for chat."""
    if user_id in _chat_ws_connections:
        _chat_ws_connections[user_id].discard(ws)
        if not _chat_ws_connections[user_id]:
            del _chat_ws_connections[user_id]


async def broadcast_to_user(user_id: uuid.UUID, data: dict) -> None:
    """Send a message to all WebSocket connections of a specific user."""
    if user_id not in _chat_ws_connections:
        return
    message = json.dumps(data, default=str)
    dead = set()
    for ws in _chat_ws_connections[user_id]:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _chat_ws_connections[user_id].discard(ws)
    if not _chat_ws_connections.get(user_id):
        _chat_ws_connections.pop(user_id, None)


async def broadcast_to_conversation(
    conversation_id: uuid.UUID,
    data: dict,
    exclude_user_id: Optional[uuid.UUID] = None,
) -> None:
    """Send a message to all members of a conversation."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        member_repo = ConversationMemberRepo(db)
        members = await member_repo.get_members(conversation_id)
        for member in members:
            if member.user_id != exclude_user_id:
                await broadcast_to_user(member.user_id, data)


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepo(db)
        self.member_repo = ConversationMemberRepo(db)
        self.message_repo = MessageRepo(db)
        self.read_receipt_repo = MessageReadReceiptRepo(db)
        self.presence_repo = UserPresenceRepo(db)

    # ============ 会话管理 ============

    async def create_conversation(
        self,
        data: ConversationCreate,
        creator_id: uuid.UUID,
    ) -> ConversationResponse:
        """创建会话（私聊/群聊）"""
        if data.type == "private":
            # 私聊：检查是否已存在
            if len(data.member_ids) != 1:
                raise ValueError("私聊只能包含一个对方用户")

            other_user_id = data.member_ids[0]
            existing = await self.conversation_repo.find_private_conversation(
                creator_id, other_user_id
            )
            if existing:
                return await self._to_conversation_response(existing, creator_id)

            # 创建新的私聊会话
            conversation = Conversation(type="private")
            conversation = await self.conversation_repo.create(conversation)

            # 添加双方为成员
            await self.member_repo.add_member(conversation.id, creator_id, "member")
            await self.member_repo.add_member(conversation.id, other_user_id, "member")

        elif data.type == "group":
            # 群聊
            if not data.name:
                raise ValueError("群聊必须指定名称")

            conversation = Conversation(
                type="group",
                name=data.name,
                owner_id=creator_id,
            )
            conversation = await self.conversation_repo.create(conversation)

            # 添加创建者为群主
            await self.member_repo.add_member(conversation.id, creator_id, "owner")

            # 添加其他成员
            for member_id in data.member_ids:
                if member_id != creator_id:
                    await self.member_repo.add_member(conversation.id, member_id, "member")
        else:
            raise ValueError(f"不支持的会话类型: {data.type}")

        await self.db.commit()
        return await self._to_conversation_response(conversation, creator_id)

    async def get_or_create_private_conversation(
        self,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID,
    ) -> ConversationResponse:
        """获取或创建私聊会话（懒加载模式）"""
        # 先查找已存在的私聊
        existing = await self.conversation_repo.find_private_conversation(user1_id, user2_id)
        if existing:
            return await self._to_conversation_response(existing, user1_id)

        # 创建新的私聊会话
        conversation = Conversation(type="private")
        conversation = await self.conversation_repo.create(conversation)
        await self.member_repo.add_member(conversation.id, user1_id, "member")
        await self.member_repo.add_member(conversation.id, user2_id, "member")
        await self.db.commit()
        return await self._to_conversation_response(conversation, user1_id)

    async def get_conversations(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ConversationResponse]:
        """获取用户的会话列表"""
        conversations, _ = await self.conversation_repo.get_user_conversations(
            user_id, page, page_size
        )

        result = []
        for conv in conversations:
            resp = await self._to_conversation_response(conv, user_id)
            result.append(resp)

        return result

    async def get_conversation_detail(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ConversationDetailResponse]:
        """获取会话详情"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None

        # 检查是否是成员
        is_member = await self.member_repo.is_member(conversation_id, user_id)
        if not is_member:
            return None

        # 获取成员列表
        members = await self.member_repo.get_members(conversation_id)
        member_responses = []
        for member in members:
            user = member.user
            presence = await self.presence_repo.get_status(member.user_id)
            member_responses.append(ConversationMemberResponse(
                id=member.id,
                user_id=member.user_id,
                user_name=user.real_name or user.username if user else None,
                role=member.role,
                nickname=member.nickname,
                muted=member.muted,
                joined_at=member.joined_at,
                last_read_at=member.last_read_at,
                is_online=presence.status == "online" if presence else False,
            ))

        # 基础响应
        resp = await self._to_conversation_response(conversation, user_id)
        return ConversationDetailResponse(
            **resp.model_dump(),
            members=member_responses,
        )

    async def update_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        avatar: Optional[str] = None,
    ) -> Optional[ConversationResponse]:
        """更新群信息"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return None

        # 检查权限（只有群主和管理员可以修改）
        member = await self.member_repo.get_member(conversation_id, user_id)
        if not member or member.role not in ("owner", "admin"):
            raise ValueError("没有权限修改群信息")

        if name is not None:
            conversation.name = name
        if avatar is not None:
            conversation.avatar = avatar

        await self.db.commit()
        return await self._to_conversation_response(conversation, user_id)

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """删除会话/退出群"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return False

        if conversation.type == "private":
            # 私聊：直接删除会话
            await self.db.delete(conversation)
        else:
            # 群聊：检查是否是群主
            if conversation.owner_id == user_id:
                # 群主删除群
                await self.db.delete(conversation)
            else:
                # 普通成员退出群
                await self.member_repo.remove_member(conversation_id, user_id)

        await self.db.commit()
        return True

    # ============ 成员管理 ============

    async def add_members(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        user_ids: list[uuid.UUID],
    ) -> bool:
        """添加成员"""
        # 检查权限
        member = await self.member_repo.get_member(conversation_id, user_id)
        if not member or member.role not in ("owner", "admin"):
            raise ValueError("没有权限添加成员")

        # 添加成员
        for uid in user_ids:
            existing = await self.member_repo.get_member(conversation_id, uid)
            if not existing:
                await self.member_repo.add_member(conversation_id, uid, "member")

        await self.db.commit()
        return True

    async def remove_member(
        self,
        conversation_id: uuid.UUID,
        operator_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """移除成员"""
        # 检查权限
        operator = await self.member_repo.get_member(conversation_id, operator_id)
        if not operator or operator.role not in ("owner", "admin"):
            raise ValueError("没有权限移除成员")

        # 不能移除自己
        if operator_id == user_id:
            raise ValueError("不能移除自己")

        # 不能移除群主
        target = await self.member_repo.get_member(conversation_id, user_id)
        if target and target.role == "owner":
            raise ValueError("不能移除群主")

        await self.member_repo.remove_member(conversation_id, user_id)
        await self.db.commit()
        return True

    async def update_member_role(
        self,
        conversation_id: uuid.UUID,
        operator_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> bool:
        """更新成员角色"""
        # 检查权限（只有群主可以修改角色）
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation or conversation.owner_id != operator_id:
            raise ValueError("只有群主可以修改成员角色")

        await self.member_repo.update_role(conversation_id, user_id, role)
        await self.db.commit()
        return True

    async def transfer_owner(
        self,
        conversation_id: uuid.UUID,
        current_owner_id: uuid.UUID,
        new_owner_id: uuid.UUID,
    ) -> bool:
        """转让群主"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation or conversation.owner_id != current_owner_id:
            raise ValueError("只有群主可以转让群主")

        # 更新群主
        conversation.owner_id = new_owner_id

        # 更新角色
        await self.member_repo.update_role(conversation_id, current_owner_id, "admin")
        await self.member_repo.update_role(conversation_id, new_owner_id, "owner")

        await self.db.commit()
        return True

    # ============ 消息管理 ============

    async def send_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        data: MessageCreate,
    ) -> MessageResponse:
        """发送消息"""
        # 检查是否是成员
        is_member = await self.member_repo.is_member(conversation_id, sender_id)
        if not is_member:
            raise ValueError("不是会话成员")

        # 创建消息
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            type=data.type,
            content=data.content,
            reply_to_id=data.reply_to_id,
            mentions=data.mentions,
            extra_data=data.extra_data,
        )
        message = await self.message_repo.create(message)

        # 更新会话的最后消息
        await self.conversation_repo.update_last_message(
            conversation_id, data.content, sender_id
        )

        # 更新发送者的最后阅读时间
        await self.member_repo.update_last_read(conversation_id, sender_id)

        # 构建响应（必须在 commit 前，否则事务已关闭无法查询）
        response = await self._to_message_response(message, sender_id)

        await self.db.commit()
        return response

    async def get_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        before_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> MessageListResponse:
        """获取消息列表"""
        # 检查是否是成员
        is_member = await self.member_repo.is_member(conversation_id, user_id)
        if not is_member:
            raise ValueError("不是会话成员")

        messages = await self.message_repo.get_messages(
            conversation_id, before_id, limit
        )
        total = await self.message_repo.get_message_count(conversation_id)

        result = []
        for msg in messages:
            resp = await self._to_message_response(msg, user_id)
            result.append(resp)

        return MessageListResponse(
            items=result,
            total=total,
            has_more=len(messages) == limit,
        )

    async def delete_message(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """删除消息（软删除）"""
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            return False

        # 只能删除自己的消息
        if message.sender_id != user_id:
            raise ValueError("只能删除自己的消息")

        message.deleted_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def recall_message(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """撤回消息（2分钟内）"""
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            return False

        # 只能撤回自己的消息
        if message.sender_id != user_id:
            raise ValueError("只能撤回自己的消息")

        # 检查时间限制（2分钟）
        time_diff = datetime.utcnow() - message.created_at
        if time_diff.total_seconds() > 120:
            raise ValueError("只能撤回2分钟内的消息")

        # 标记为已撤回
        message.type = "recalled"
        message.content = "消息已撤回"
        await self.db.commit()
        return True

    async def search_messages(
        self,
        user_id: uuid.UUID,
        keyword: str,
        conversation_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MessageResponse], int]:
        """搜索消息"""
        messages, total = await self.message_repo.search_messages(
            user_id, keyword, conversation_id, page, page_size
        )

        result = []
        for msg in messages:
            resp = await self._to_message_response(msg, user_id)
            result.append(resp)

        return result, total

    # ============ 已读回执 ============

    async def mark_read(
        self,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """标记消息已读"""
        # 检查是否是成员
        is_member = await self.member_repo.is_member(conversation_id, user_id)
        if not is_member:
            return False

        await self.read_receipt_repo.mark_read(message_id, user_id)
        await self.member_repo.update_last_read(conversation_id, user_id)
        await self.db.commit()
        return True

    async def mark_conversation_read(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        """标记会话所有消息已读"""
        # 检查是否是成员
        is_member = await self.member_repo.is_member(conversation_id, user_id)
        if not is_member:
            return 0

        # 获取未读消息
        messages = await self.message_repo.get_messages(conversation_id, limit=1000)
        unread_ids = [msg.id for msg in messages if msg.sender_id != user_id]

        count = await self.read_receipt_repo.batch_mark_read(unread_ids, user_id)
        await self.member_repo.update_last_read(conversation_id, user_id)
        await self.db.commit()
        return count

    # ============ 在线状态 ============

    async def update_presence(
        self,
        user_id: uuid.UUID,
        status: str,
    ) -> UserPresenceResponse:
        """更新在线状态"""
        presence = await self.presence_repo.update_status(user_id, status)
        await self.db.commit()
        return UserPresenceResponse(
            user_id=presence.user_id,
            status=presence.status,
            last_seen_at=presence.last_seen_at,
        )

    async def get_presence(
        self,
        user_id: uuid.UUID,
    ) -> Optional[UserPresenceResponse]:
        """获取用户在线状态"""
        presence = await self.presence_repo.get_status(user_id)
        if not presence:
            return UserPresenceResponse(
                user_id=user_id,
                status="offline",
                last_seen_at=None,
            )
        return UserPresenceResponse(
            user_id=presence.user_id,
            status=presence.status,
            last_seen_at=presence.last_seen_at,
        )

    async def get_batch_presence(
        self,
        user_ids: list[uuid.UUID],
    ) -> list[UserPresenceResponse]:
        """批量获取在线状态"""
        presences = await self.presence_repo.get_batch_status(user_ids)
        presence_map = {p.user_id: p for p in presences}

        result = []
        for user_id in user_ids:
            presence = presence_map.get(user_id)
            if presence:
                result.append(UserPresenceResponse(
                    user_id=presence.user_id,
                    status=presence.status,
                    last_seen_at=presence.last_seen_at,
                ))
            else:
                result.append(UserPresenceResponse(
                    user_id=user_id,
                    status="offline",
                    last_seen_at=None,
                ))

        return result

    # ============ 辅助方法 ============

    async def _to_conversation_response(
        self,
        conversation: Conversation,
        user_id: uuid.UUID,
    ) -> ConversationResponse:
        """转换为会话响应"""
        # 获取未读数（使用 SQL 级别计算）
        unread_count = await self._get_unread_count(conversation.id, user_id)

        # 获取成员数
        members = await self.member_repo.get_members(conversation.id)
        member_count = len(members)

        # 获取最后消息发送者名称
        last_message_sender_name = None
        if conversation.last_message_sender_id:
            sender = await self.db.get(User, conversation.last_message_sender_id)
            if sender:
                last_message_sender_name = sender.real_name or sender.username

        # 对于私聊，获取对方名称
        name = conversation.name
        avatar = conversation.avatar
        if conversation.type == "private":
            for member in members:
                if member.user_id != user_id:
                    user = member.user
                    if user:
                        name = user.real_name or user.username
                    break

        return ConversationResponse(
            id=conversation.id,
            type=conversation.type,
            name=name,
            avatar=avatar,
            owner_id=conversation.owner_id,
            last_message_at=conversation.last_message_at,
            last_message_content=conversation.last_message_content,
            last_message_sender_id=conversation.last_message_sender_id,
            last_message_sender_name=last_message_sender_name,
            unread_count=unread_count,
            member_count=member_count,
            created_at=conversation.created_at,
        )

    async def _to_message_response(
        self,
        message: Message,
        user_id: uuid.UUID,
    ) -> MessageResponse:
        """转换为消息响应"""
        # 获取发送者信息
        sender = message.sender
        sender_name = sender.real_name or sender.username if sender else None

        # 获取回复消息信息
        reply_to_content = None
        reply_to_sender_name = None
        if message.reply_to_id:
            reply_msg = await self.message_repo.get_by_id(message.reply_to_id)
            if reply_msg:
                reply_to_content = reply_msg.content[:100] if reply_msg.content else None
                if reply_msg.sender:
                    reply_to_sender_name = reply_msg.sender.real_name or reply_msg.sender.username

        # 获取已读数
        read_count = await self.read_receipt_repo.get_read_count(message.id)

        # 检查当前用户是否已读
        is_read = False
        if message.sender_id != user_id:
            receipt = await self.read_receipt_repo.get_receipt(message.id, user_id)
            is_read = receipt is not None

        return MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_name=sender_name,
            type=message.type,
            content=message.content,
            reply_to_id=message.reply_to_id,
            reply_to_content=reply_to_content,
            reply_to_sender_name=reply_to_sender_name,
            mentions=message.mentions,
            extra_data=message.extra_data,
            is_read=is_read,
            read_by_count=read_count,
            created_at=message.created_at,
        )

    async def _get_unread_count(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        """获取未读消息数（使用 SQL 级别计算）"""
        member = await self.member_repo.get_member(conversation_id, user_id)
        if not member or not member.last_read_at:
            # 从未读过，返回所有消息数
            return await self.message_repo.get_message_count(conversation_id)

        # 使用 SQL 级别计算未读数
        return await self.message_repo.count_unread_messages(
            conversation_id, user_id, member.last_read_at
        )
