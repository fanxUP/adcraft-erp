"""Pending action confirmation service."""

from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import or_, update
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

    async def confirm_action(self, action_id, user_id):
        """Atomically claim an action so concurrent confirmations execute once."""
        now = datetime.utcnow()
        stmt = (
            update(AiPendingAction)
            .where(
                AiPendingAction.id == action_id,
                AiPendingAction.user_id == user_id,
                AiPendingAction.status == "waiting_confirmation",
                or_(
                    AiPendingAction.expires_at.is_(None),
                    AiPendingAction.expires_at >= now,
                ),
            )
            .values(status="confirmed", confirmed_at=now)
            .returning(AiPendingAction)
        )
        action = (await self.db.execute(stmt)).scalar_one_or_none()
        if not action:
            await self.db.execute(
                update(AiPendingAction)
                .where(
                    AiPendingAction.id == action_id,
                    AiPendingAction.user_id == user_id,
                    AiPendingAction.status == "waiting_confirmation",
                    AiPendingAction.expires_at < now,
                )
                .values(status="expired"),
            )
        await self.db.commit()
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
