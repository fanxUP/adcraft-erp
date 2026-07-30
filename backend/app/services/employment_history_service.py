import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.employment_history_repo import EmploymentHistoryRepository
from app.models.employee import Employee

logger = logging.getLogger(__name__)


class EmploymentHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EmploymentHistoryRepository(db)

    async def _load_employee(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()

    async def list_histories(self, page=1, page_size=20, employee_id=None, change_type=None):
        skip = (page - 1) * page_size
        items, total = await self.repo.list(skip, page_size, employee_id, change_type)
        result = []
        for h in items:
            d = self._d(h)
            emp = await self._load_employee(h.employee_id)
            if emp:
                d["employee_no"] = emp.employee_no
                d["employee_name"] = emp.name
            result.append(d)
        return result, total

    async def get_history(self, hid: UUID):
        h = await self.repo.get_by_id(hid)
        if not h:
            return None
        d = self._d(h)
        emp = await self._load_employee(h.employee_id)
        if emp:
            d["employee_no"] = emp.employee_no
            d["employee_name"] = emp.name
        return d

    async def create_history(self, data):
        if isinstance(data.get("employee_id"), str):
            data["employee_id"] = UUID(data["employee_id"])
        return self._d(await self.repo.create(data))

    async def update_history(self, hid: UUID, data):
        h = await self.repo.get_by_id(hid)
        if not h:
            raise ValueError("履历记录不存在")
        return self._d(await self.repo.update(h, data))

    async def delete_history(self, hid: UUID):
        h = await self.repo.get_by_id(hid)
        if not h:
            return False
        await self.repo.delete(h)
        return True

    def _d(self, h):
        return {
            "id": str(h.id),
            "employee_id": str(h.employee_id),
            "change_date": h.change_date.isoformat() if h.change_date else None,
            "change_type": h.change_type,
            "previous_department": h.previous_department,
            "new_department": h.new_department,
            "previous_position": h.previous_position,
            "new_position": h.new_position,
            "reason": h.reason,
            "remark": h.remark,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
