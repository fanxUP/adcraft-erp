"""AI Assistant main service."""

from uuid import UUID
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.ai_assistant.orchestrator import AiOrchestrator
from app.ai_assistant.memory_service import MemoryService
from app.ai_assistant.action_confirm import ActionConfirmService
from app.ai_assistant.tool_executor import ToolExecutor
from app.ai_assistant.audit_logger import AuditLogger


class AiAssistantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.orchestrator = AiOrchestrator(db)
        self.memory_service = MemoryService(db)
        self.action_confirm_service = ActionConfirmService(db)
        self.tool_executor = ToolExecutor(db)
        self.audit_logger = AuditLogger(db)

    async def chat(self, user, message, session_id=None, context=None, ip_address=None, user_agent=None):
        sid = UUID(session_id) if session_id else None
        return await self.orchestrator.process_message(
            user=user, message=message, session_id=sid, context=context,
            ip_address=ip_address, user_agent=user_agent)

    async def get_sessions(self, user_id):
        sessions = await self.memory_service.list_user_sessions(user_id)
        return [
            {"id": str(s.id), "title": s.title, "current_page": s.current_page,
             "current_business_type": s.current_business_type,
             "current_business_id": str(s.current_business_id) if s.current_business_id else None,
             "created_at": s.created_at.isoformat() if s.created_at else None,
             "updated_at": s.updated_at.isoformat() if s.updated_at else None}
            for s in sessions
        ]

    async def get_session_messages(self, session_id, user_id):
        session = await self.memory_service.get_session(session_id)
        if not session or session.user_id != user_id:
            return None
        messages = await self.memory_service.get_session_messages(session_id)
        return [
            {"id": str(m.id), "session_id": str(m.session_id), "role": m.role,
             "content": m.content, "metadata_json": m.metadata_json,
             "created_at": m.created_at.isoformat() if m.created_at else None}
            for m in messages
        ]

    async def confirm_action(self, action_id, user, ip_address=None, user_agent=None):
        return await self.tool_executor.execute_confirmed_action(
            action_id=action_id, user=user, ip_address=ip_address, user_agent=user_agent)

    async def followup_after_confirm(self, action_id, user, ip_address=None, user_agent=None, execution_result=None):
        """After a confirmed action is executed, continue the conversation so the AI can reply."""
        pending = await self.action_confirm_service.get_pending_action(action_id)
        if not pending or not pending.session_id:
            return None
        # Save the execution result as a tool message for AI context
        import json
        result_summary = execution_result or {}
        # Remove large fields from context to keep tokens manageable
        if "items" in result_summary:
            result_summary = {k: v for k, v in result_summary.items() if k != "items"}
        if "preview_data" in result_summary:
            del result_summary["preview_data"]
        tool_content = json.dumps(result_summary, ensure_ascii=False)
        await self.memory_service.add_message(pending.session_id, "tool", tool_content,
            metadata_json={"tool_name": pending.tool_name, "status": "executed"})
        # Now call the AI to generate a response
        result = await self.orchestrator.process_message(
            user=user, message="[System: The confirmed action has been executed. Please inform the user of the result in Chinese.]",
            session_id=pending.session_id, context=None,
            ip_address=ip_address, user_agent=user_agent)
        return result

    async def cancel_action(self, action_id, user):
        pending = await self.action_confirm_service.get_pending_action(action_id)
        if not pending or pending.user_id != user.id:
            return {"status": "failed", "error_message": "操作不存在"}
        await self.action_confirm_service.cancel_action(action_id)
        return {"status": "success", "message": "操作已取消"}

    async def get_tool_call_logs(self, user_id, page=1, page_size=20):
        from app.ai_assistant.models import AiToolCallLog
        stmt = (select(AiToolCallLog).where(AiToolCallLog.user_id == user_id)
                .order_by(desc(AiToolCallLog.created_at))
                .offset((page - 1) * page_size).limit(page_size))
        result = await self.db.execute(stmt)
        logs = list(result.scalars().all())
        count_stmt = select(func.count()).select_from(AiToolCallLog).where(AiToolCallLog.user_id == user_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        return {"items": [{"id": str(l.id), "session_id": str(l.session_id) if l.session_id else None,
                           "tool_name": l.tool_name, "tool_args": l.tool_args,
                           "tool_result": l.tool_result, "risk_level": l.risk_level,
                           "status": l.status, "error_message": l.error_message,
                           "created_at": l.created_at.isoformat() if l.created_at else None} for l in logs],
                "total": total, "page": page, "page_size": page_size}

    async def get_audit_logs(self, page=1, page_size=20):
        from app.ai_assistant.models import AiOperationAuditLog
        stmt = (select(AiOperationAuditLog).order_by(desc(AiOperationAuditLog.created_at))
                .offset((page - 1) * page_size).limit(page_size))
        result = await self.db.execute(stmt)
        logs = list(result.scalars().all())
        count_stmt = select(func.count()).select_from(AiOperationAuditLog)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        return {"items": [{"id": str(l.id), "user_id": str(l.user_id),
                           "session_id": str(l.session_id) if l.session_id else None,
                           "action_type": l.action_type, "business_type": l.business_type,
                           "business_id": str(l.business_id) if l.business_id else None,
                           "risk_level": l.risk_level,
                           "created_at": l.created_at.isoformat() if l.created_at else None} for l in logs],
                "total": total, "page": page, "page_size": page_size}
