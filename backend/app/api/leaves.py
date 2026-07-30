import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.leave import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestApprove
from app.schemas.common import success, success_paginated
from app.services.leave_service import LeaveRequestService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaves", tags=["Leaves"])


@router.get("/")
async def list_leaves(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                      employee_id: str | None = None, status: str | None = None,
                      leave_type: str | None = None, db=Depends(get_db),
                      current_user=Depends(get_current_user)):
    eid = UUID(employee_id) if employee_id else None
    items, total = await LeaveRequestService(db).list_requests(page, page_size, eid, status, leave_type)
    return success_paginated(items, total, page, page_size)


@router.post("/")
async def create_leave(data: LeaveRequestCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await LeaveRequestService(db).create_request(data.model_dump()))


@router.get("/{leave_id}")
async def get_leave(leave_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    l = await LeaveRequestService(db).get_request(UUID(leave_id))
    if not l:
        return {"code": 40401, "message": "请假申请不存在", "data": None}
    return success(l)


@router.put("/{leave_id}")
async def update_leave(leave_id: str, data: LeaveRequestUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await LeaveRequestService(db).update_request(UUID(leave_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.post("/{leave_id}/approve")
async def approve_leave(leave_id: str, data: LeaveRequestApprove, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await LeaveRequestService(db).approve_request(
            UUID(leave_id), data.status, current_user.id, data.remark
        ))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.delete("/{leave_id}")
async def delete_leave(leave_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await LeaveRequestService(db).delete_request(UUID(leave_id)):
        return {"code": 40401, "message": "请假申请不存在", "data": None}
    return success(None)
