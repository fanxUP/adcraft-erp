import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.employee_repo import EmployeeRepository
from app.services.number_generator import generate_employee_no

logger = logging.getLogger(__name__)

class EmployeeService:
    def __init__(self, db: AsyncSession): self.db = db; self.repo = EmployeeRepository(db)
    async def list_employees(self, page=1, page_size=20, keyword=None, dept=None, status=None):
        skip = (page-1)*page_size
        emps, total = await self.repo.list(skip, page_size, keyword, dept, status)
        return [self._d(e) for e in emps], total
    async def get_employee(self, eid): e = await self.repo.get_by_id(eid); return self._d(e) if e else None
    async def create_employee(self, data):
        if not data.get("employee_no"):
            data["employee_no"] = await generate_employee_no(self.db)
        return self._d(await self.repo.create(data))
    async def update_employee(self, eid, data):
        e = await self.repo.get_by_id(eid)
        if not e: raise ValueError("员工不存在")
        return self._d(await self.repo.update(e, data))
    async def delete_employee(self, eid):
        e = await self.repo.get_by_id(eid)
        if not e: return False
        await self.repo.soft_delete(e); return True
    def _d(self, e):
        return {"id": str(e.id), "employee_no": e.employee_no, "name": e.name, "phone": e.phone,
            "gender": e.gender, "birth_date": e.birth_date.isoformat() if e.birth_date else None,
            "department": e.department, "position": e.position,
            "employment_type": e.employment_type, "employment_status": e.employment_status,
            "hire_date": e.hire_date.isoformat() if e.hire_date else None,
            "resignation_date": e.resignation_date.isoformat() if e.resignation_date else None,
            "id_card": e.id_card, "education": e.education,
            "emergency_contact": e.emergency_contact, "emergency_phone": e.emergency_phone,
            "skills": e.skills if isinstance(e.skills, list) else [],
            "base_salary": float(e.base_salary) if e.base_salary else None,
            "bank_name": e.bank_name, "bank_account": e.bank_account, "address": e.address,
            "user_id": str(e.user_id) if e.user_id else None,
            "remark": e.remark, "is_active": e.is_active,
            "created_at": e.created_at.isoformat() if e.created_at else None}