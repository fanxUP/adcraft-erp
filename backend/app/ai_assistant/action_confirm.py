"""Pending action confirmation service."""

from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai_assistant.models import AiPendingAction
from app.ai_assistant.config import settings


class ActionConfirmService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pending_action(self, session_id, user_id, action_type, tool_name, tool_args, preview_data):
        expires_at = datetime.utcnow() + timedelta(minutes=settings.AI_PENDING_ACTION_EXPIRE_MINUTES)
        action = AiPendingAction(
            session_id=session_id, user_id=user_id, action_type=action_type,
            tool_name=tool_name, tool_args=tool_args, preview_data=preview_data,
            status="waiting_confirmation", expires_at=expires_at,
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def get_pending_action(self, action_id):
        return await self.db.get(AiPendingAction, action_id)

    async def confirm_action(self, action_id):
        action = await self.get_pending_action(action_id)
        if not action or action.status != "waiting_confirmation":
            return None
        if action.expires_at and action.expires_at < datetime.utcnow():
            action.status = "expired"
            await self.db.commit()
            return None
        action.status = "confirmed"
        action.confirmed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def cancel_action(self, action_id):
        action = await self.get_pending_action(action_id)
        if not action or action.status != "waiting_confirmation":
            return None
        action.status = "cancelled"
        action.cancelled_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def mark_executed(self, action_id, error_message=None):
        action = await self.get_pending_action(action_id)
        if not action:
            return
        action.status = "executed" if not error_message else "failed"
        action.executed_at = datetime.utcnow()
        action.error_message = error_message
        await self.db.commit()
