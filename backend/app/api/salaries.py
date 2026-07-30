import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.salary import SalaryRecordCreate, SalaryRecordUpdate
from app.schemas.common import success, success_paginated
from app.services.salary_service import SalaryRecordService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/salaries", tags=["Salaries"])


@router.get("/")
async def list_salaries(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        employee_id: str | None = None, month: str | None = None,
                        payment_status: str | None = None, db=Depends(get_db),
                        current_user=Depends(get_current_user)):
    eid = UUID(employee_id) if employee_id else None
    items, total = await SalaryRecordService(db).list_records(page, page_size, eid, month, payment_status)
    return success_paginated(items, total, page, page_size)


@router.post("/")
async def create_salary(data: SalaryRecordCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await SalaryRecordService(db).create_record(data.model_dump()))


@router.get("/{salary_id}")
async def get_salary(salary_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    s = await SalaryRecordService(db).get_record(UUID(salary_id))
    if not s:
        return {"code": 40401, "message": "工资记录不存在", "data": None}
    return success(s)


@router.put("/{salary_id}")
async def update_salary(salary_id: str, data: SalaryRecordUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRecordService(db).update_record(UUID(salary_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/{salary_id}")
async def delete_salary(salary_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await SalaryRecordService(db).delete_record(UUID(salary_id)):
        return {"code": 40401, "message": "工资记录不存在", "data": None}
    return success(None)
