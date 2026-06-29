from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success, success_paginated, error
from app.services.operation_log_service import OperationLogService

router = APIRouter(prefix="/logs", tags=["Operation Logs"])


@router.get("/")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user_id: str | None = None,
    object_type: str | None = None,
    action: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OperationLogService(db)
    uid = UUID(user_id) if user_id else None
    logs, total = await service.list_logs(
        page=page, page_size=page_size,
        user_id=uid, object_type=object_type,
        action=action, date_from=date_from, date_to=date_to,
    )
    return success_paginated(logs, total, page, page_size)


@router.get("/{log_id}")
async def get_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = OperationLogService(db)
    log = await service.get_log(UUID(log_id))
    if not log:
        return error(40401, "日志不存在")
    return success(log)
