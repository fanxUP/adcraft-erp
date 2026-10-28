import logging
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import PERM_SYSTEM_SUPER_ADMIN, require_permission, require_any_permission, user_has_permission
from app.models.user import User
from app.schemas.attendance import AttendanceRuleCreate, AttendanceRuleUpdate, AttendanceRecordCreate, AttendanceRecordUpdate
from app.schemas.common import success, success_paginated
from app.services.attendance_service import AttendanceRuleService, AttendanceRecordService
from app.services.employee_service import EmployeeService

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)


@router.get("/rules")
async def list_rules(db=Depends(get_db), current_user=Depends(require_permission('attendance:read'))):
    return success(await AttendanceRuleService(db).list_rules())


@router.post("/rules")
async def create_rule(data: AttendanceRuleCreate, db=Depends(get_db), current_user=Depends(require_permission('attendance:manage'))):
    return success(await AttendanceRuleService(db).create_rule(data.model_dump()))


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, data: AttendanceRuleUpdate, db=Depends(get_db), current_user=Depends(require_permission('attendance:manage'))):
    try:
        return success(await AttendanceRuleService(db).update_rule(UUID(rule_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        await db.rollback()
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db=Depends(get_db), current_user=Depends(require_permission('attendance:manage'))):
    if not await AttendanceRuleService(db).delete_rule(UUID(rule_id)):
        return {"code": 40401, "message": "考勤规则不存在", "data": None}
    return success(None)


@router.get("/records")
async def list_records(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=1000),
                       employee_id: str | None = None, date_from: date | None = None,
                       date_to: date | None = None, db=Depends(get_db),
                       current_user=Depends(require_permission('attendance:read'))):
    emp_id = UUID(employee_id) if employee_id else None
    items, total = await AttendanceRecordService(db).list_records(page, page_size, emp_id, date_from, date_to)
    return success_paginated(items, total, page, page_size)


@router.post("/records")
async def create_record(data: AttendanceRecordCreate, db=Depends(get_db), current_user=Depends(require_permission('attendance:manage'))):
    try:
        return success(await AttendanceRecordService(db).create_record(data.model_dump()))
    except ValueError as e:
        await db.rollback()
        return {"code": 40001, "message": str(e), "data": None}


@router.put("/records/{record_id}")
async def update_record(record_id: str, data: AttendanceRecordUpdate, db=Depends(get_db), current_user=Depends(require_permission('attendance:manage'))):
    try:
        return success(await AttendanceRecordService(db).update_record(UUID(record_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        await db.rollback()
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/records/{record_id}")
async def delete_record(record_id: str, db=Depends(get_db), current_user=Depends(require_permission('attendance:manage'))):
    if not await AttendanceRecordService(db).delete_record(UUID(record_id)):
        return {"code": 40401, "message": "打卡记录不存在", "data": None}
    return success(None)


@router.get("/employees")
async def list_employees(db=Depends(get_db), current_user=Depends(require_any_permission("attendance:read", "leave:read", "salary:read", "employee:read"))):
    items, _ = await EmployeeService(db).list_employees(1, 1000, status="active")
    return success([{k: item.get(k) for k in ("id", "employee_no", "name", "department")} for item in items])

@router.get("/monthly")
async def attendance_monthly(month: str, db=Depends(get_db), current_user=Depends(require_permission("attendance:read"))):
    from app.services.attendance_summary_service import AttendanceSummaryService
    try:
        return success(await AttendanceSummaryService(db).monthly(month))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}
