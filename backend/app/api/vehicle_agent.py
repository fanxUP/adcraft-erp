"""Vehicle Agent API — message analysis and draft management."""

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission, PERM_VEHICLE_READ, PERM_VEHICLE_UPDATE
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.services.vehicle_agent_service import VehicleAgentService

router = APIRouter(prefix="/vehicle-agent", tags=["Vehicle Agent"])


@router.post("/messages/analyze")
async def analyze_message(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):
    """Analyze a message and create a draft.

    Body:
    - content: str (required) — message text
    - platform: str — message source platform
    - conversation_id: str — conversation ID
    - message_id: str — message ID
    - sender_name: str — sender name
    - sender_id: str — sender ID
    """
    content = body.get("content", "").strip()
    if not content:
        raise ValueError("消息内容不能为空")

    service = VehicleAgentService(db, current_user)
    draft = await service.analyze_message(
        content=content,
        platform=body.get("platform", "manual"),
        conversation_id=body.get("conversation_id"),
        message_id=body.get("message_id"),
        sender_name=body.get("sender_name"),
        sender_id=body.get("sender_id"),
    )
    return success(draft)


@router.get("/drafts")
async def list_drafts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    intent: str | None = None,
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):
    """List agent drafts with filters."""
    service = VehicleAgentService(db, current_user)
    items, total = await service.list_drafts(
        page=page, page_size=page_size,
        status=status, intent=intent, platform=platform,
    )
    return success_paginated(items, total, page, page_size)


@router.get("/drafts/{draft_id}")
async def get_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_READ)),
):
    """Get a single draft."""
    service = VehicleAgentService(db, current_user)
    draft = await service.get_draft(draft_id)
    if not draft:
        raise ValueError("草稿不存在")
    return success(draft)


@router.post("/drafts/{draft_id}/confirm")
async def confirm_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    """Confirm a draft and create the corresponding record."""
    service = VehicleAgentService(db, current_user)
    draft = await service.confirm_draft(draft_id, confirmed_by=current_user.id)
    return success(draft)


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(
    draft_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_VEHICLE_UPDATE)),
):
    """Reject a draft.

    Body:
    - reject_reason: str (optional) — reason for rejection
    """
    service = VehicleAgentService(db, current_user)
    draft = await service.reject_draft(draft_id, reject_reason=body.get("reject_reason"))
    return success(draft)
