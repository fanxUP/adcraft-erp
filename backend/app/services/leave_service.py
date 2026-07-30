import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.leave_repo import LeaveRequestRepository
from app.models.employee import Employee

logger = logging.getLogger(__name__)


class LeaveRequestService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LeaveRequestRepository(db)

    async def _load_employee(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()

    async def list_requests(self, page=1, page_size=20, employee_id=None, status=None, leave_type=None):
        skip = (page - 1) * page_size
        items, total = await self.repo.list(skip, page_size, employee_id, status, leave_type)
        result = []
        for l in items:
            d = self._d(l)
            emp = await self._load_employee(l.employee_id)
            if emp:
                d["employee_no"] = emp.employee_no
                d["employee_name"] = emp.name
            result.append(d)
        return result, total

    async def get_request(self, lid: UUID):
        l = await self.repo.get_by_id(lid)
        if not l:
            return None
        d = self._d(l)
        emp = await self._load_employee(l.employee_id)
        if emp:
            d["employee_no"] = emp.employee_no
            d["employee_name"] = emp.name
        return d

    async def create_request(self, data):
        if isinstance(data.get("employee_id"), str):
            data["employee_id"] = UUID(data["employee_id"])
        data.setdefault("status", "pending")
        return self._d(await self.repo.create(data))

    async def update_request(self, lid: UUID, data):
        l = await self.repo.get_by_id(lid)
        if not l:
            raise ValueError("请假申请不存在")
        return self._d(await self.repo.update(l, data))

    async def approve_request(self, lid: UUID, status: str, operated_by: UUID, remark: str | None = None):
        l = await self.repo.get_by_id(lid)
        if not l:
            raise ValueError("请假申请不存在")
        if l.status != "pending":
            raise ValueError(f"当前状态为 {l.status}，无法审批")
        l.status = status
        l.approved_by = operated_by
        l.approved_at = datetime.now(timezone.utc)
        if remark:
            l.remark = remark
        await self.db.flush()
        return self._d(l)

    async def delete_request(self, lid: UUID):
        l = await self.repo.get_by_id(lid)
        if not l:
            return False
        await self.repo.delete(l)
        return True

    def _d(self, l):
        return {
            "id": str(l.id),
            "employee_id": str(l.employee_id),
            "leave_type": l.leave_type,
            "start_date": l.start_date.isoformat() if l.start_date else None,
            "end_date": l.end_date.isoformat() if l.end_date else None,
            "duration_days": float(l.duration_days) if l.duration_days else 0,
            "reason": l.reason,
            "status": l.status,
            "approved_by": str(l.approved_by) if l.approved_by else None,
            "approved_at": l.approved_at.isoformat() if l.approved_at else None,
            "remark": l.remark,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "updated_at": l.updated_at.isoformat() if l.updated_at else None,
        }
