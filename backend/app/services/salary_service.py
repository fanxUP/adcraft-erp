import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.salary_repo import SalaryRecordRepository
from app.models.employee import Employee
from sqlalchemy import select

logger = logging.getLogger(__name__)


class SalaryRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SalaryRecordRepository(db)

    async def _load_employee(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()

    async def list_records(self, page=1, page_size=20, employee_id=None, month=None, payment_status=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list(skip, page_size, employee_id, month, payment_status)
        result = []
        for r in records:
            d = self._d(r)
            emp = await self._load_employee(r.employee_id)
            if emp:
                d["employee_no"] = emp.employee_no
                d["employee_name"] = emp.name
            result.append(d)
        return result, total

    async def get_record(self, sid: UUID):
        r = await self.repo.get_by_id(sid)
        if not r:
            return None
        d = self._d(r)
        emp = await self._load_employee(r.employee_id)
        if emp:
            d["employee_no"] = emp.employee_no
            d["employee_name"] = emp.name
        return d

    async def create_record(self, data):
        if isinstance(data.get("employee_id"), str):
            data["employee_id"] = UUID(data["employee_id"])
        return self._d(await self.repo.create(data))

    async def update_record(self, sid: UUID, data):
        r = await self.repo.get_by_id(sid)
        if not r:
            raise ValueError("工资记录不存在")
        return self._d(await self.repo.update(r, data))

    async def delete_record(self, sid: UUID):
        r = await self.repo.get_by_id(sid)
        if not r:
            return False
        await self.repo.delete(r)
        return True

    async def batch_create(self, month: str, employee_ids: list[UUID], base_salary_map: dict):
        """批量生成指定月份的工资记录"""
        created = []
        for eid in employee_ids:
            bs = base_salary_map.get(str(eid), 0)
            data = {
                "employee_id": eid,
                "month": month,
                "base_salary": bs,
                "net_salary": bs,
                "payment_status": "pending",
            }
            created.append(self._d(await self.repo.create(data)))
        return created

    def _d(self, r):
        return {
            "id": str(r.id),
            "employee_id": str(r.employee_id),
            "month": r.month,
            "base_salary": float(r.base_salary) if r.base_salary else 0,
            "overtime_pay": float(r.overtime_pay) if r.overtime_pay else None,
            "bonus": float(r.bonus) if r.bonus else None,
            "commission": float(r.commission) if r.commission else None,
            "subsidy": float(r.subsidy) if r.subsidy else None,
            "deduction": float(r.deduction) if r.deduction else None,
            "net_salary": float(r.net_salary) if r.net_salary else 0,
            "payment_status": r.payment_status,
            "paid_at": r.paid_at.isoformat() if r.paid_at else None,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
