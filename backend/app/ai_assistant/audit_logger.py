"""Audit logging for AI operations."""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai_assistant.models import AiToolCallLog, AiOperationAuditLog


class AuditLogger:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_tool_call(self, session_id, message_id, user_id, tool_name, tool_args,
                            risk_level=None, status="pending", tool_result=None, error_message=None):
        log = AiToolCallLog(
            session_id=session_id, message_id=message_id, user_id=user_id,
            tool_name=tool_name, tool_args=tool_args, risk_level=risk_level,
            status=status, tool_result=tool_result, error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def update_tool_call_status(self, log_id, status, tool_result=None, error_message=None):
        log = await self.db.get(AiToolCallLog, log_id)
        if log:
            log.status = status
            if tool_result is not None:
                log.tool_result = tool_result
            if error_message is not None:
                log.error_message = error_message
            if status in ("success", "failed"):
                log.finished_at = datetime.utcnow()
            await self.db.commit()

    async def log_audit(self, user_id, session_id, action_type, business_type=None,
                        business_id=None, before_data=None, after_data=None,
                        risk_level=None, ip_address=None, user_agent=None):
        audit = AiOperationAuditLog(
            user_id=user_id, session_id=session_id, action_type=action_type,
            business_type=business_type, business_id=business_id,
            before_data=before_data, after_data=after_data, risk_level=risk_level,
            ip_address=ip_address, user_agent=user_agent,
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit
