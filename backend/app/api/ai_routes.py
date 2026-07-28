"""API endpoints for AI Task Route management."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.repositories.ai_task_route_repo import AITaskRouteRepository
from app.schemas.ai_task_route import TaskRouteCreate, TaskRouteUpdate
from app.schemas.common import success, success_paginated, error
from app.services.ai_task_route_service import AITaskRouteService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Task Routes"])


def _get_service(db: AsyncSession = Depends(get_db)) -> AITaskRouteService:
    return AITaskRouteService(AITaskRouteRepository(db))


@router.get("/ai/routes/")
async def list_routes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    enabled_only: bool = Query(False),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    service: AITaskRouteService = Depends(_get_service),
):
    """List task routes with pagination and search."""
    data = await service.list_routes(
        tenant_id="00000000-0000-0000-0000-000000000001",
        page=page,
        page_size=page_size,
        enabled_only=enabled_only,
        search=search,
    )
    return success_paginated(data["items"], data["total"], data["page"], data["page_size"])


@router.post("/ai/routes/")
async def create_route(
    data: TaskRouteCreate,
    current_user: User = Depends(require_role("admin")),
    service: AITaskRouteService = Depends(_get_service),
):
    """Create a new task route."""
    try:
        route = await service.create_route(
            tenant_id="00000000-0000-0000-0000-000000000001",
            data=data.model_dump(),
            created_by=current_user.id,
        )
        return success(route)
    except Exception as e:
        if "uq_task_route_per_tenant" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"任务代码 '{data.task_code}' 已存在")
        raise HTTPException(status_code=500, detail=f"创建路由失败: {str(e)}")


@router.get("/ai/routes/{route_id}")
async def get_route(
    route_id: UUID,
    current_user: User = Depends(require_role("admin")),
    service: AITaskRouteService = Depends(_get_service),
):
    """Get a single task route by ID."""
    route = await service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="任务路由不存在")
    return success(route)


@router.patch("/ai/routes/{route_id}")
async def update_route(
    route_id: UUID,
    data: TaskRouteUpdate,
    current_user: User = Depends(require_role("admin")),
    service: AITaskRouteService = Depends(_get_service),
):
    """Update a task route."""
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        return success({"updated": False, "message": "没有需要更新的字段"})
    route = await service.update_route(route_id, payload)
    if not route:
        raise HTTPException(status_code=404, detail="任务路由不存在")
    return success(route)


@router.delete("/ai/routes/{route_id}")
async def delete_route(
    route_id: UUID,
    current_user: User = Depends(require_role("admin")),
    service: AITaskRouteService = Depends(_get_service),
):
    """Delete a task route."""
    deleted = await service.delete_route(route_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="任务路由不存在")
    return success({"deleted": True})
