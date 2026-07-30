import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.attendance_repo import AttendanceRuleRepository, AttendanceRecordRepository
logger = logging.getLogger(__name__)

class AttendanceRuleService:
    def __init__(self, db: AsyncSession): self.db = db; self.repo = AttendanceRuleRepository(db)
    async def list_rules(self): return [self._d(r) for r in (await self.repo.list())]
    async def get_rule(self, rid): r = await self.repo.get_by_id(rid); return self._d(r) if r else None
    async def create_rule(self, d): return self._d(await self.repo.create(d))
    async def update_rule(self, rid, d):
        r = await self.repo.get_by_id(rid)
        if not r: raise ValueError("考勤规则不存在")
        return self._d(await self.repo.update(r, d))
    async def delete_rule(self, rid):
        r = await self.repo.get_by_id(rid)
        if not r: return False
        await self.repo.delete(r); return True
    def _d(self, r): return {"id": str(r.id), "name": r.name, "department": r.department,
        "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
        "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
        "work_days": r.work_days if isinstance(r.work_days, list) else [],
        "late_threshold": r.late_threshold, "early_leave_threshold": r.early_leave_threshold,
        "overtime_rate": float(r.overtime_rate) if r.overtime_rate else None,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None}

class AttendanceRecordService:
    def __init__(self, db: AsyncSession): self.db = db; self.repo = AttendanceRecordRepository(db)
    async def list_records(self, page=1, page_size=20, employee_id=None, date_from=None, date_to=None):
        skip = (page-1)*page_size
        records, total = await self.repo.list(skip, page_size, employee_id, date_from, date_to)
        return [self._d(r) for r in records], total
    async def get_record(self, rid): r = await self.repo.get_by_id(rid); return self._d(r) if r else None
    async def create_record(self, d): return self._d(await self.repo.create(d))
    async def update_record(self, rid, d):
        r = await self.repo.get_by_id(rid)
        if not r: raise ValueError("打卡记录不存在")
        return self._d(await self.repo.update(r, d))
    async def delete_record(self, rid):
        r = await self.repo.get_by_id(rid)
        if not r: return False
        await self.repo.delete(r); return True
    def _d(self, r): return {"id": str(r.id), "employee_id": str(r.employee_id),
        "date": r.date.isoformat() if r.date else None,
        "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
        "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
        "check_in_status": r.check_in_status, "check_out_status": r.check_out_status,
        "source": r.source, "remark": r.remark,
        "overtime_hours": float(r.overtime_hours) if r.overtime_hours else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None}