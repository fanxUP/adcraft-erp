"""Session and message management for AI Assistant."""

from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai_assistant.models import AiChatSession, AiChatMessage
from app.ai_assistant.config import settings


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id, title=None, context=None):
        session = AiChatSession(
            user_id=user_id, title=title or "新对话",
            current_page=context.get("page") if context else None,
            current_business_type=context.get("business_type") if context else None,
            current_business_id=UUID(context["business_id"]) if context and context.get("business_id") else None,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id):
        return await self.db.get(AiChatSession, session_id)

    async def list_user_sessions(self, user_id, limit=50):
        stmt = (select(AiChatSession).where(AiChatSession.user_id == user_id)
                .order_by(desc(AiChatSession.updated_at)).limit(limit))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_session_context(self, session_id, context):
        session = await self.get_session(session_id)
        if not session:
            return
        session.current_page = context.get("page") or session.current_page
        session.current_business_type = context.get("business_type") or session.current_business_type
        if context.get("business_id"):
            session.current_business_id = UUID(context["business_id"])
        await self.db.commit()

    async def update_session_title(self, session_id, title):
        session = await self.get_session(session_id)
        if session:
            session.title = title
            await self.db.commit()

    async def add_message(self, session_id, role, content=None, user_id=None, metadata_json=None):
        msg = AiChatMessage(
            session_id=session_id, role=role, content=content,
            user_id=user_id, metadata_json=metadata_json or {},
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_session_messages(self, session_id, limit=None):
        stmt = (select(AiChatMessage).where(AiChatMessage.session_id == session_id)
                .order_by(AiChatMessage.created_at))
        if limit:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_history_messages(self, session_id):
        messages = await self.get_session_messages(session_id)
        history = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                history.append({"role": msg.role, "content": msg.content or ""})
        max_msgs = settings.AI_MAX_HISTORY_MESSAGES
        if len(history) > max_msgs:
            history = history[-max_msgs:]
        return history
