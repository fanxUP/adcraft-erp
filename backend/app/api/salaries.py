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
    is_manual: bool = False
    group1: str | None = None
    group2: str | None = None


class SalaryItemUpdate(BaseModel):
    label: str | None = None
    formula: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    is_manual: bool | None = None
    group1: str | None = None
    group2: str | None = None


class SalaryParamCreate(BaseModel):
    key: str
    label: str
    sort_order: int = 0


class SalaryParamUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None


class SalaryParamValueIn(BaseModel):
    key: str
    value: float | None = None


class SalaryParamSaveRequest(BaseModel):
    month: str
    values: list[SalaryParamValueIn] = []


class SalaryGridCell(BaseModel):
    employee_id: str
    item_key: str
    value: float | None = None


class SalaryGridPayment(BaseModel):
    employee_id: str
    payment_status: str


class SalaryGridRemark(BaseModel):
    employee_id: str
    remark: str | None = None


class SalaryGridComputeRequest(BaseModel):
    month: str
    employee_ids: list[str] | None = None


class SalaryGridSaveRequest(BaseModel):
    month: str
    cells: list[SalaryGridCell] | None = None
    payments: list[SalaryGridPayment] | None = None
    remarks: list[SalaryGridRemark] | None = None


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
    """保存网格手工修改的单元格、支付状态与备注。"""
    try:
        cells = [c.model_dump() for c in (data.cells or [])]
        payments = [p.model_dump() for p in (data.payments or [])]
        remarks = [r.model_dump() for r in (data.remarks or [])]
        return success(await SalaryRecordService(db).save_cells(data.month, cells, payments, remarks))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


# ── 工资参数（每月手工填一个值，公式可引用）───────────────────────────────

@router.get("/params")
async def salary_params(month: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    """参数定义 + 当月取值。"""
    try:
        return success(await SalaryRecordService(db).list_params(month))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.post("/params")
async def create_salary_param(data: SalaryParamCreate, db=Depends(get_db),
                              current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRecordService(db).create_param(data.model_dump()))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.post("/params/save")
async def save_salary_params(data: SalaryParamSaveRequest, db=Depends(get_db),
                             current_user=Depends(get_current_user)):
    """保存某月参数取值（value=None 表示清空该月取值）。"""
    try:
        return success(await SalaryRecordService(db).save_param_values(
            data.month, [v.model_dump() for v in data.values]))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.put("/params/{param_id}")
async def update_salary_param(param_id: str, data: SalaryParamUpdate, db=Depends(get_db),
                              current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRecordService(db).update_param(
            UUID(param_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.delete("/params/{param_id}")
async def delete_salary_param(param_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        await SalaryRecordService(db).delete_param(UUID(param_id))
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


# ── 工资指标设置模板（命名保存的指标快照，一键应用）────────────────────────

class SalaryTemplateItem(BaseModel):
    key: str
    label: str = ""
    formula: str = "0"
    sort_order: int = 0
    is_active: bool = True
    is_manual: bool = False
    group1: str | None = None
    group2: str | None = None


class SalaryTemplateCreate(BaseModel):
    name: str
    items: list[SalaryTemplateItem]


class SalaryTemplateUpdate(BaseModel):
    name: str | None = None
    items: list[SalaryTemplateItem] | None = None


@router.get("/templates")
async def salary_templates(db=Depends(get_db), current_user=Depends(get_current_user)):
    """指标设置模板列表（id/名称/列数）。"""
    return success(await SalaryRecordService(db).list_templates())


@router.post("/templates")
async def create_salary_template(data: SalaryTemplateCreate, db=Depends(get_db),
                                 current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRecordService(db).create_template(
            data.name, [i.model_dump() for i in data.items]))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.put("/templates/{template_id}")
async def update_salary_template(template_id: str, data: SalaryTemplateUpdate, db=Depends(get_db),
                                 current_user=Depends(get_current_user)):
    try:
        items = [i.model_dump() for i in data.items] if data.items is not None else None
        return success(await SalaryRecordService(db).update_template(
            UUID(template_id), data.name, items))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.delete("/templates/{template_id}")
async def delete_salary_template(template_id: str, db=Depends(get_db),
                                 current_user=Depends(get_current_user)):
    try:
        await SalaryRecordService(db).delete_template(UUID(template_id))
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.post("/templates/{template_id}/apply")
async def apply_salary_template(template_id: str, db=Depends(get_db),
                                current_user=Depends(get_current_user)):
    """应用模板：命中更新、未命中停用（保留数据）、缺的创建，返回应用后的指标列表。"""
    try:
        return success(await SalaryRecordService(db).apply_template(UUID(template_id)))
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
