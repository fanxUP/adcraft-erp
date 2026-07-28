"""API endpoints for AI request logs and usage tracking."""
import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_role
from app.models.user import User
from app.repositories.ai_request_repo import AIRequestRepository
from app.schemas.common import success, success_paginated
from app.services.ai_request_service import AIRequestService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Requests"])


def _get_service(db: AsyncSession = Depends(get_db)) -> AIRequestService:
    return AIRequestService(AIRequestRepository(db))


@router.get("/ai/requests/")
async def list_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    task_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    provider_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_role("admin")),
    service: AIRequestService = Depends(_get_service),
):
    """List AI request logs with filters."""
    data = await service.list_requests(
        tenant_id="00000000-0000-0000-0000-000000000001",
        page=page,
        page_size=page_size,
        task_code=task_code,
        status=status,
        provider_id=provider_id,
        start_date=start_date,
        end_date=end_date,
    )
    return success_paginated(data["items"], data["total"], data["page"], data["page_size"])


@router.get("/ai/usage/summary")
async def get_usage_summary(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    task_code: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    service: AIRequestService = Depends(_get_service),
):
    """Get AI usage summary for a date range."""
    result = await service.get_usage_summary(
        tenant_id="00000000-0000-0000-0000-000000000001",
        start_date=start_date,
        end_date=end_date,
        task_code=task_code,
    )
    return success(result)
