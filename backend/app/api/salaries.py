import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.salary import SalaryRecordCreate, SalaryRecordUpdate, SalaryGenerateRequest
from app.schemas.common import success, success_paginated
from app.services.salary_service import SalaryRecordService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/salaries", tags=["Salaries"])


# ── 工资网格（考勤式）：指标列 + 公式 + 单元格 ─────────────────────────────

class SalaryItemCreate(BaseModel):
    key: str
    label: str
    formula: str
    sort_order: int = 0


class SalaryItemUpdate(BaseModel):
    label: str | None = None
    formula: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class SalaryGridCell(BaseModel):
    employee_id: str
    item_key: str
    value: float | None = None


class SalaryGridPayment(BaseModel):
    employee_id: str
    payment_status: str


class SalaryGridComputeRequest(BaseModel):
    month: str
    employee_ids: list[str] | None = None


class SalaryGridSaveRequest(BaseModel):
    month: str
    cells: list[SalaryGridCell] | None = None
    payments: list[SalaryGridPayment] | None = None


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


@router.post("/generate")
async def generate_salaries(data: SalaryGenerateRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    """按工资规则自动生成指定月份的工资记录（全部在职，或指定的员工子集）。"""
    eids = [UUID(e) for e in data.employee_ids] if data.employee_ids else None
    return success(await SalaryRecordService(db).generate_month(data.month, eids))


@router.get("/report")
async def salary_report(month: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    """仿 Excel「工资计算明细表」的月度工资报表。"""
    try:
        return success(await SalaryRecordService(db).report_month(month))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.get("/items")
async def salary_items(db=Depends(get_db), current_user=Depends(get_current_user)):
    """工资指标列列表（含停用，按 sort_order 排序）。"""
    return success(await SalaryRecordService(db).list_items())


@router.post("/items")
async def create_salary_item(data: SalaryItemCreate, db=Depends(get_db),
                             current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRecordService(db).create_item(data.model_dump()))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.put("/items/{item_id}")
async def update_salary_item(item_id: str, data: SalaryItemUpdate, db=Depends(get_db),
                             current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRecordService(db).update_item(
            UUID(item_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.delete("/items/{item_id}")
async def delete_salary_item(item_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        await SalaryRecordService(db).delete_item(UUID(item_id))
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.get("/grid")
async def salary_grid(month: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    """工资网格：指标列 + 全部在职员工行 + 单元格值 + 支付状态。"""
    try:
        return success(await SalaryRecordService(db).get_grid(month))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.post("/grid/compute")
async def salary_grid_compute(data: SalaryGridComputeRequest, db=Depends(get_db),
                              current_user=Depends(get_current_user)):
    """按指标公式计算当月（全部或指定员工）工资网格值并落库。"""
    eids = [UUID(e) for e in data.employee_ids] if data.employee_ids else None
    try:
        return success(await SalaryRecordService(db).compute_month(data.month, eids))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.post("/grid/save")
async def salary_grid_save(data: SalaryGridSaveRequest, db=Depends(get_db),
                           current_user=Depends(get_current_user)):
    """保存网格手工修改的单元格与支付状态。"""
    try:
        cells = [c.model_dump() for c in (data.cells or [])]
        payments = [p.model_dump() for p in (data.payments or [])]
        return success(await SalaryRecordService(db).save_cells(data.month, cells, payments))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


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
