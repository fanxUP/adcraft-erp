import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from app.models.salary import SalaryRecord
from app.services.attendance_summary_service import business_today
from app.repositories.salary_rule_repo import SalaryRuleRepository
from app.models.employee import Employee

logger = logging.getLogger(__name__)


class SalaryRuleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SalaryRuleRepository(db)

    async def _load_employee(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()

    async def list_rules(self, page=1, page_size=20, employee_id=None):
        skip = (page - 1) * page_size
        eid = UUID(employee_id) if employee_id else None
        rules, total = await self.repo.list(skip, page_size, eid)
        result = []
        for r in rules:
            d = self._to_dict(r)
            emp = await self._load_employee(r.employee_id)
            if emp:
                d["employee_no"] = emp.employee_no
                d["employee_name"] = emp.name
            result.append(d)
        return result, total

    async def get_rule(self, rid: UUID):
        r = await self.repo.get_by_id(rid)
        if not r:
            return None
        d = self._to_dict(r)
        emp = await self._load_employee(r.employee_id)
        if emp:
            d["employee_no"] = emp.employee_no
            d["employee_name"] = emp.name
        return d

    async def get_employee_rule(self, employee_id: UUID):
        """Get the latest active rule for an employee"""
        rules = await self.repo.get_by_employee(employee_id)
        if not rules:
            return None
        latest = next((r for r in rules if r.effective_date <= business_today()), None)
        if latest is None:
            return None
        return self._to_dict(latest)

    async def create_rule(self, data):
        if isinstance(data.get("employee_id"), str):
            data["employee_id"] = UUID(data["employee_id"])
        if not await self._load_employee(data["employee_id"]):
            raise ValueError("员工不存在")
        existing = await self.repo.get_by_employee(data["employee_id"])
        if any(r.effective_date == data["effective_date"] for r in existing):
            raise ValueError("该生效日期已有工资标准，请选择新的生效日期创建版本")
        # A partial batch adjustment inherits unspecified values from the prior version.
        prior = next((r for r in existing if r.effective_date < data["effective_date"]), None)
        if prior:
            for field in ("base_salary", "social_insurance"):
                data.setdefault(field, getattr(prior, field))
        return self._to_dict(await self.repo.create(data))

    async def _assert_unused(self, rule):
        used = await self.db.scalar(select(func.count()).select_from(SalaryRecord).where(
            SalaryRecord.employee_id == rule.employee_id,
            SalaryRecord.month >= rule.effective_date.strftime("%Y-%m")))
        if used:
            raise ValueError("该工资标准已有核算记录，请用新的生效日期新增版本，保留历史")

    async def update_rule(self, rid: UUID, data):
        r = await self.repo.get_by_id(rid)
        if not r:
            raise ValueError("工资规则不存在")
        await self._assert_unused(r)
        if data.get("effective_date", r.effective_date) != r.effective_date:
            return await self.create_rule({"employee_id": r.employee_id, "base_salary": r.base_salary, "social_insurance": r.social_insurance, **data})
        return self._to_dict(await self.repo.update(r, data))

    async def delete_rule(self, rid: UUID):
        r = await self.repo.get_by_id(rid)
        if not r:
            return False
        await self._assert_unused(r)
        await self.repo.delete(r)
        return True

    def _to_dict(self, r):
        return {
            "id": str(r.id),
            "employee_id": str(r.employee_id),
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "base_salary": float(r.base_salary) if r.base_salary else 0,
            "social_insurance": float(r.social_insurance) if r.social_insurance is not None else None,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
