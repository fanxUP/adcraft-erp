import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
        latest = rules[0]  # ordered by effective_date desc
        return self._to_dict(latest)

    async def create_rule(self, data):
        if isinstance(data.get("employee_id"), str):
            data["employee_id"] = UUID(data["employee_id"])
        return self._to_dict(await self.repo.create(data))

    async def update_rule(self, rid: UUID, data):
        r = await self.repo.get_by_id(rid)
        if not r:
            raise ValueError("工资规则不存在")
        return self._to_dict(await self.repo.update(r, data))

    async def delete_rule(self, rid: UUID):
        r = await self.repo.get_by_id(rid)
        if not r:
            return False
        await self.repo.delete(r)
        return True

    def _to_dict(self, r):
        return {
            "id": str(r.id),
            "employee_id": str(r.employee_id),
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "base_salary": float(r.base_salary) if r.base_salary else 0,
            "overtime_rate": float(r.overtime_rate) if r.overtime_rate else None,
            "bonus_standard": float(r.bonus_standard) if r.bonus_standard else None,
            "commission_rate": float(r.commission_rate) if r.commission_rate else None,
            "subsidy_standard": float(r.subsidy_standard) if r.subsidy_standard else None,
            "attendance_bonus": float(r.attendance_bonus) if r.attendance_bonus else None,
            "social_insurance": float(r.social_insurance) if r.social_insurance else None,
            "housing_fund": float(r.housing_fund) if r.housing_fund else None,
            "deduction_standard": float(r.deduction_standard) if r.deduction_standard else None,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
