"""Tool executor — execute tools with permission checks and logging."""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.ai_assistant.tool_registry import ToolRegistry
from app.ai_assistant.permission_guard import PermissionGuard
from app.ai_assistant.audit_logger import AuditLogger
from app.ai_assistant.action_confirm import ActionConfirmService
from app.ai_assistant.config import settings
from app.ai_assistant.tools import register_all_tools


class ToolExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = ToolRegistry()
        self.permission_guard = PermissionGuard(db)
        self.audit_logger = AuditLogger(db)
        self.action_confirm = ActionConfirmService(db)
        register_all_tools()

    async def execute_tool(self, tool_name, args, user, session_id=None,
                           message_id=None, ip_address=None, user_agent=None):
        tool_def = self.registry.get(tool_name)
        if not tool_def:
            return {"status": "failed", "error_message": f"未知工具: {tool_name}"}

        # 1. Permission check
        try:
            await self.permission_guard.assert_permission(user, tool_def)
        except Exception as e:
            await self.audit_logger.log_tool_call(
                session_id=session_id, message_id=message_id, user_id=user.id,
                tool_name=tool_name, tool_args=args,
                risk_level=tool_def.risk_level, status="blocked", error_message=str(e))
            return {"status": "blocked", "error_message": str(e)}

        # 2. Risk level checks
        if tool_def.risk_level == "level_4":
            err = "高风险操作不允许AI执行"
            await self.audit_logger.log_tool_call(session_id=session_id, message_id=message_id, user_id=user.id,
                tool_name=tool_name, tool_args=args, risk_level=tool_def.risk_level, status="blocked", error_message=err)
            return {"status": "blocked", "error_message": err}

        if tool_def.risk_level == "level_3" and not settings.AI_ALLOW_WRITE_ACTIONS:
            err = "AI写入操作已被系统禁用"
            await self.audit_logger.log_tool_call(session_id=session_id, message_id=message_id, user_id=user.id,
                tool_name=tool_name, tool_args=args, risk_level=tool_def.risk_level, status="blocked", error_message=err)
            return {"status": "blocked", "error_message": err}

        # 3. Log tool call start
        log_entry = await self.audit_logger.log_tool_call(
            session_id=session_id, message_id=message_id, user_id=user.id,
            tool_name=tool_name, tool_args=args, risk_level=tool_def.risk_level, status="running")

        try:
            if not tool_def.handler:
                raise ValueError(f"工具 {tool_name} 未注册处理函数")

            if (
                tool_def.requires_confirmation
                and settings.AI_REQUIRE_CONFIRMATION
            ):
                if not tool_def.preview_handler:
                    raise ValueError(f"工具 {tool_name} 未配置安全预览处理函数")
                result = await tool_def.preview_handler(
                    db=self.db,
                    user=user,
                    **args,
                )
            else:
                result = await tool_def.handler(db=self.db, user=user, **args)

            if tool_def.risk_level == "level_1":
                await self.audit_logger.update_tool_call_status(log_entry.id, "success", tool_result={"data": result})
                return {"status": "success", "result": result}

            elif tool_def.risk_level in ("level_2", "level_3"):
                if tool_def.requires_confirmation and settings.AI_REQUIRE_CONFIRMATION:
                    preview_data = result if isinstance(result, dict) else {"data": result}
                    pending = await self.action_confirm.create_pending_action(
                        session_id=session_id or UUID(int=0), user_id=user.id,
                        action_type=tool_name, tool_name=tool_name,
                        tool_args=args, preview_data=preview_data)
                    await self.audit_logger.update_tool_call_status(
                        log_entry.id, "waiting_confirmation",
                        tool_result={"preview": result, "pending_action_id": str(pending.id)})
                    return {"status": "waiting_confirmation", "result": result,
                            "pending_action_id": str(pending.id), "preview_data": preview_data}
                else:
                    await self.audit_logger.update_tool_call_status(log_entry.id, "success", tool_result={"data": result})
                    return {"status": "success", "result": result, "is_preview": True}
            else:
                await self.audit_logger.update_tool_call_status(log_entry.id, "success", tool_result={"data": result})
                return {"status": "success", "result": result}

        except Exception as e:
            await self.audit_logger.update_tool_call_status(log_entry.id, "failed", error_message=str(e))
            return {"status": "failed", "error_message": str(e)}

    async def execute_confirmed_action(self, action_id, user, ip_address=None, user_agent=None):
        pending = await self.action_confirm.get_pending_action(action_id)
        if (
            not pending
            or pending.user_id != user.id
            or pending.status != "waiting_confirmation"
        ):
            return {"status": "failed", "error_message": "操作不存在或已过期"}

        tool_def = self.registry.get(pending.tool_name)
        if not tool_def or not tool_def.handler:
            return {"status": "failed", "error_message": f"未知工具: {pending.tool_name}"}

        try:
            await self.permission_guard.assert_permission(user, tool_def)
        except Exception as e:
            return {"status": "blocked", "error_message": str(e)}

        if tool_def.risk_level == "level_4":
            return {"status": "blocked", "error_message": "高风险操作不允许AI执行"}
        if tool_def.risk_level == "level_3" and not settings.AI_ALLOW_WRITE_ACTIONS:
            return {"status": "blocked", "error_message": "AI写入操作已被系统禁用"}

        pending = await self.action_confirm.confirm_action(action_id, user.id)
        if not pending:
            return {"status": "failed", "error_message": "操作不存在或已过期"}

        try:
            result = await tool_def.handler(db=self.db, user=user, **pending.tool_args)
            await self.action_confirm.mark_executed(action_id)
            await self.audit_logger.log_audit(
                user_id=user.id, session_id=pending.session_id, action_type=pending.action_type,
                business_type=(
                    pending.tool_args.get("business_type")
                    or pending.preview_data.get("business_type")
                ),
                business_id=(
                    pending.tool_args.get("business_id")
                    or pending.tool_args.get("order_id")
                    or pending.tool_args.get("quote_id")
                    or pending.preview_data.get("business_id")
                ),
                before_data=pending.preview_data,
                after_data=result if isinstance(result, dict) else {"data": result},
                risk_level=tool_def.risk_level, ip_address=ip_address, user_agent=user_agent)
            return {"status": "success", "result": result}
        except Exception as e:
            await self.action_confirm.mark_executed(action_id, error_message=str(e))
            return {"status": "failed", "error_message": str(e)}
