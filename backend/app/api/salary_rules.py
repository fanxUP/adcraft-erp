import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.salary_rule import SalaryRuleCreate, SalaryRuleUpdate
from app.schemas.common import success, success_paginated
from app.services.salary_rule_service import SalaryRuleService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/salary-rules", tags=["Salary Rules"])


@router.get("/")
async def list_salary_rules(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=1000),
                            employee_id: str | None = None, db=Depends(get_db),
                            current_user=Depends(get_current_user)):
    items, total = await SalaryRuleService(db).list_rules(page, page_size, employee_id)
    return success_paginated(items, total, page, page_size)


@router.get("/employee/{employee_id}")
async def get_employee_rule(employee_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    """获取指定员工的最新工资规则"""
    rule = await SalaryRuleService(db).get_employee_rule(UUID(employee_id))
    if not rule:
        return {"code": 40401, "message": "该员工暂无工资规则", "data": None}
    return success(rule)


@router.post("/")
async def create_salary_rule(data: SalaryRuleCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await SalaryRuleService(db).create_rule(data.model_dump()))


@router.get("/{rule_id}")
async def get_salary_rule(rule_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    r = await SalaryRuleService(db).get_rule(UUID(rule_id))
    if not r:
        return {"code": 40401, "message": "工资规则不存在", "data": None}
    return success(r)


@router.put("/{rule_id}")
async def update_salary_rule(rule_id: str, data: SalaryRuleUpdate, db=Depends(get_db),
                              current_user=Depends(get_current_user)):
    try:
        return success(await SalaryRuleService(db).update_rule(UUID(rule_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/{rule_id}")
async def delete_salary_rule(rule_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await SalaryRuleService(db).delete_rule(UUID(rule_id)):
        return {"code": 40401, "message": "工资规则不存在", "data": None}
    return success(None)
