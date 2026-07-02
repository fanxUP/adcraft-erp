import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, ConversationMember, Message, MessageReadReceipt, UserPresence
from app.models.user import User


class ConversationRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.members))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_user_conversations(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Conversation], int]:
        """获取用户的会话列表"""
        # 子查询：获取用户参与的会话ID
        member_subquery = (
            select(ConversationMember.conversation_id)
            .where(ConversationMember.user_id == user_id)
        )

        # 主查询
        query = (
            select(Conversation)
            .where(Conversation.id.in_(member_subquery))
            .order_by(Conversation.last_message_at.desc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        conversations = list(result.scalars().all())

        # 总数查询
        count_query = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.id.in_(member_subquery))
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        return conversations, total

    async def find_private_conversation(
        self,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID,
    ) -> Optional[Conversation]:
        """查找两个用户之间的私聊会话"""
        # 查找两个用户都是成员的私聊会话
        query = (
            select(Conversation)
            .join(ConversationMember)
            .where(
                Conversation.type == "private",
                ConversationMember.user_id.in_([user1_id, user2_id]),
            )
            .group_by(Conversation.id)
            .having(func.count(ConversationMember.id) == 2)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_last_message(
        self,
        conversation_id: uuid.UUID,
        content: str,
        sender_id: uuid.UUID,
    ) -> None:
        """更新会话的最后消息信息"""
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                last_message_at=func.now(),
                last_message_content=content[:256] if content else "",
                last_message_sender_id=sender_id,
            )
        )


class ConversationMemberRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> ConversationMember:
        """添加成员"""
        member = ConversationMember(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """移除成员"""
        result = await self.db.execute(
            delete(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def get_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ConversationMember]:
        """获取成员信息"""
        result = await self.db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_members(
        self,
        conversation_id: uuid.UUID,
    ) -> list[ConversationMember]:
        """获取所有成员"""
        result = await self.db.execute(
            select(ConversationMember)
            .where(ConversationMember.conversation_id == conversation_id)
            .order_by(ConversationMember.role.desc(), ConversationMember.joined_at)
        )
        return list(result.scalars().all())

    async def update_role(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> bool:
        """更新成员角色"""
        result = await self.db.execute(
            update(ConversationMember)
            .where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
            .values(role=role)
        )
        return result.rowcount > 0

    async def update_last_read(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """更新最后阅读时间"""
        await self.db.execute(
            update(ConversationMember)
            .where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
            .values(last_read_at=func.now())
        )

    async def is_member(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """检查是否是成员"""
        result = await self.db.execute(
            select(func.count())
            .select_from(ConversationMember)
            .where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        return (result.scalar() or 0) > 0

    async def get_conversation_ids_by_user(
        self,
        user_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """获取用户参与的所有会话ID"""
        result = await self.db.execute(
            select(ConversationMember.conversation_id)
            .where(ConversationMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]


class MessageRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, message: Message) -> Message:
        """创建消息"""
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_by_id(self, message_id: uuid.UUID) -> Optional[Message]:
        """获取消息"""
        result = await self.db.execute(
            select(Message)
            .options(selectinload(Message.sender))
            .where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_messages(
        self,
        conversation_id: uuid.UUID,
        before_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> list[Message]:
        """获取消息列表（游标分页）"""
        query = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
        )

        if before_id:
            # 获取指定消息之前的消息
            before_msg = await self.get_by_id(before_id)
            if before_msg:
                query = query.where(Message.created_at < before_msg.created_at)

        query = query.order_by(Message.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()  # 按时间正序返回
        return messages

    async def get_message_count(
        self,
        conversation_id: uuid.UUID,
    ) -> int:
        """获取消息总数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

    async def count_unread_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        after_time: datetime,
    ) -> int:
        """SQL 级别计算未读消息数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.created_at > after_time,
                Message.deleted_at.is_(None),
            )
        )
        return result.scalar() or 0

    async def search_messages(
        self,
        user_id: uuid.UUID,
        keyword: str,
        conversation_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Message], int]:
        """搜索消息"""
        # 获取用户参与的会话ID
        member_repo = ConversationMemberRepo(self.db)
        conversation_ids = await member_repo.get_conversation_ids_by_user(user_id)

        if not conversation_ids:
            return [], 0

        query = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.content.ilike(f"%{keyword}%"),
                Message.deleted_at.is_(None),
            )
        )

        if conversation_id:
            query = query.where(Message.conversation_id == conversation_id)

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(Message.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        return messages, total

    async def get_recent_shared_cards(
        self,
        user_id: uuid.UUID,
        card_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """获取用户最近分享的业务卡片"""
        member_repo = ConversationMemberRepo(self.db)
        conversation_ids = await member_repo.get_conversation_ids_by_user(user_id)

        if not conversation_ids:
            return []

        query = (
            select(Message)
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.type == "card",
                Message.deleted_at.is_(None),
                Message.extra_data.isnot(None),
            )
        )

        query = query.order_by(Message.created_at.desc()).limit(limit * 3)  # 多取一些用于去重
        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        # Python 层过滤 card_type（JSON 列不支持 .astext）
        if card_type:
            messages = [m for m in messages if (m.extra_data or {}).get("card_type") == card_type]

        # 按 card_id 去重，保留最新的
        seen = set()
        cards = []
        for msg in messages:
            extra = msg.extra_data or {}
            card_id = extra.get("card_id")
            if card_id and card_id not in seen:
                seen.add(card_id)
                cards.append({
                    "id": card_id,
                    "card_type": extra.get("card_type", ""),
                    "title": extra.get("title", ""),
                    "subtitle": extra.get("subtitle", ""),
                    "status": extra.get("status"),
                    "amount": extra.get("amount"),
                    "shared_at": msg.created_at.isoformat() if msg.created_at else None,
                })
                if len(cards) >= limit:
                    break

        return cards


class MessageReadReceiptRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def mark_read(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MessageReadReceipt:
        """标记消息已读"""
        # 检查是否已存在
        existing = await self.get_receipt(message_id, user_id)
        if existing:
            return existing

        receipt = MessageReadReceipt(
            message_id=message_id,
            user_id=user_id,
        )
        self.db.add(receipt)
        await self.db.flush()
        await self.db.refresh(receipt)
        return receipt

    async def get_receipt(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[MessageReadReceipt]:
        """获取已读回执"""
        result = await self.db.execute(
            select(MessageReadReceipt).where(
                MessageReadReceipt.message_id == message_id,
                MessageReadReceipt.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_read_count(
        self,
        message_id: uuid.UUID,
    ) -> int:
        """获取已读人数"""
        result = await self.db.execute(
            select(func.count())
            .select_from(MessageReadReceipt)
            .where(MessageReadReceipt.message_id == message_id)
        )
        return result.scalar() or 0

    async def batch_mark_read(
        self,
        message_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> int:
        """批量标记已读（使用 INSERT ... ON CONFLICT 避免重复）"""
        if not message_ids:
            return 0

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # 使用 PostgreSQL 的 INSERT ... ON CONFLICT DO NOTHING
        stmt = pg_insert(MessageReadReceipt).values(
            [{"message_id": mid, "user_id": user_id} for mid in message_ids]
        ).on_conflict_do_nothing(
            constraint="uq_message_read_receipt"
        )
        result = await self.db.execute(stmt)
        return result.rowcount


class UserPresenceRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_status(
        self,
        user_id: uuid.UUID,
        status: str,
    ) -> UserPresence:
        """更新在线状态"""
        from datetime import datetime

        result = await self.db.execute(
            select(UserPresence).where(UserPresence.user_id == user_id)
        )
        presence = result.scalar_one_or_none()

        if presence:
            presence.status = status
            presence.last_seen_at = datetime.utcnow()
        else:
            presence = UserPresence(
                user_id=user_id,
                status=status,
                last_seen_at=datetime.utcnow(),
            )
            self.db.add(presence)

        await self.db.flush()
        await self.db.refresh(presence)
        return presence

    async def get_status(
        self,
        user_id: uuid.UUID,
    ) -> Optional[UserPresence]:
        """获取用户在线状态"""
        result = await self.db.execute(
            select(UserPresence).where(UserPresence.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_batch_status(
        self,
        user_ids: list[uuid.UUID],
    ) -> list[UserPresence]:
        """批量获取在线状态"""
        if not user_ids:
            return []
        result = await self.db.execute(
            select(UserPresence).where(UserPresence.user_id.in_(user_ids))
        )
        return list(result.scalars().all())

    async def set_offline(
        self,
        user_id: uuid.UUID,
    ) -> None:
        """设置离线"""
        from datetime import datetime

        await self.db.execute(
            update(UserPresence)
            .where(UserPresence.user_id == user_id)
            .values(status="offline", last_seen_at=datetime.utcnow())
        )
