import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.employment_history import EmploymentHistoryCreate, EmploymentHistoryUpdate
from app.schemas.common import success, success_paginated
from app.services.employment_history_service import EmploymentHistoryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employment-histories", tags=["EmploymentHistories"])


@router.get("/")
async def list_histories(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                         employee_id: str | None = None, change_type: str | None = None,
                         db=Depends(get_db), current_user=Depends(get_current_user)):
    eid = UUID(employee_id) if employee_id else None
    items, total = await EmploymentHistoryService(db).list_histories(page, page_size, eid, change_type)
    return success_paginated(items, total, page, page_size)


@router.post("/")
async def create_history(data: EmploymentHistoryCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await EmploymentHistoryService(db).create_history(data.model_dump()))


@router.get("/{history_id}")
async def get_history(history_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    h = await EmploymentHistoryService(db).get_history(UUID(history_id))
    if not h:
        return {"code": 40401, "message": "履历记录不存在", "data": None}
    return success(h)


@router.put("/{history_id}")
async def update_history(history_id: str, data: EmploymentHistoryUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await EmploymentHistoryService(db).update_history(UUID(history_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/{history_id}")
async def delete_history(history_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await EmploymentHistoryService(db).delete_history(UUID(history_id)):
        return {"code": 40401, "message": "履历记录不存在", "data": None}
    return success(None)
