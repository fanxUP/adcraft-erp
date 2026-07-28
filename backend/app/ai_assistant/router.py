"""AI Assistant API routes."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success, error
from app.ai_assistant.config import settings
from app.ai_assistant.schemas import AiChatRequest
from app.ai_assistant.service import AiAssistantService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


@router.post("/chat")
async def chat(data: AiChatRequest, request: Request, db: AsyncSession = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    """Send a chat message to the AI assistant."""
    if not settings.AI_ASSISTANT_ENABLED:
        return error(400, "AI Assistant 未启用")
    service = AiAssistantService(db)
    result = await service.chat(
        user=current_user, message=data.message, session_id=data.session_id,
        context=data.context.model_dump(exclude_none=True) if data.context else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"))
    response = {"session_id": result["session_id"], "message_id": result["message_id"],
                "reply": result["reply"], "tool_calls": result["tool_calls"]}
    if result.get("pending_action"):
        response["pending_action"] = result["pending_action"]
    return success(response)



@router.post("/chat/stream")

async def chat_stream(data: AiChatRequest, request: Request, db: AsyncSession = Depends(get_db),

                      current_user: User = Depends(get_current_user)):

    """SSE streaming chat endpoint."""

    if not settings.AI_ASSISTANT_ENABLED:

        from fastapi.responses import JSONResponse

        return JSONResponse({"code": 400, "message": "AI Assistant 未启用"})



    from fastapi.responses import StreamingResponse

    service = AiAssistantService(db)



    async def event_generator():

        async for event in service.orchestrator.stream_process_message(

            user=current_user, message=data.message, session_id=data.session_id,

            context=data.context.model_dump(exclude_none=True) if data.context else None,

            ip_address=request.client.host if request.client else None,

            user_agent=request.headers.get("user-agent"),

        ):

            import json as _json

            yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"



    return StreamingResponse(

        event_generator(),

        media_type="text/event-stream",

        headers={

            "Cache-Control": "no-cache",

            "Connection": "keep-alive",

            "X-Accel-Buffering": "no",

        },

    )


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    service = AiAssistantService(db)
    return success(await service.get_sessions(current_user.id))


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    try:
        sid = UUID(session_id)
    except ValueError:
        return error(400, "无效的会话ID")
    service = AiAssistantService(db)
    messages = await service.get_session_messages(sid, current_user.id)
    if messages is None:
        return error(404, "会话不存在")
    return success(messages)


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: str, request: Request, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    try:
        aid = UUID(action_id)
    except ValueError:
        return error(400, "无效的操作ID")
    service = AiAssistantService(db)
    result = await service.confirm_action(aid, user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"))
    if result.get("status") == "failed":
        return error(400, result.get("error_message", "操作失败"))
    # After executing the action, continue the conversation so the AI
    # can inform the user of the result (e.g. "报价单已创建成功")
    if result.get("status") == "success":
        followup = await service.followup_after_confirm(aid, user=current_user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            execution_result=result)
        if followup:
            result["reply"] = followup.get("reply", "")
            result["followup_message_id"] = followup.get("message_id", "")
    return success(result)


@router.post("/actions/{action_id}/cancel")
async def cancel_action(action_id: str, request: Request, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    try:
        aid = UUID(action_id)
    except ValueError:
        return error(400, "无效的操作ID")
    service = AiAssistantService(db)
    result = await service.cancel_action(aid, current_user)
    if result.get("status") == "failed":
        return error(400, result.get("error_message", "取消失败"))
    return success(result)


@router.get("/tool-call-logs")
async def get_tool_call_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                             db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    service = AiAssistantService(db)
    return success(await service.get_tool_call_logs(current_user.id, page, page_size))


@router.get("/audit-logs")
async def get_audit_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                         db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    is_admin = any(role.name == "admin" for role in current_user.roles)
    if not is_admin:
        return error(403, "权限不足: 需要管理员角色")
    service = AiAssistantService(db)
    return success(await service.get_audit_logs(page, page_size))
