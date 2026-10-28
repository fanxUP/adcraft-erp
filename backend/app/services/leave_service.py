import logging
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.leave_repo import LeaveRequestRepository
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.services.attendance_summary_service import AttendanceSummaryService, WEEKDAYS, employed_on
from datetime import timedelta
from app.models.attendance import AttendanceRule

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
        data["status"] = "pending"
        await self._validate(data)
        return self._d(await self.repo.create(data))

    async def update_request(self, lid: UUID, data):
        l = await self.repo.get_by_id(lid)
        if not l:
            raise ValueError("请假申请不存在")
        if l.status != "pending":
            raise ValueError("仅待审批请假可编辑；已审批记录请先撤销后重新申请")
        if "status" in data:
            raise ValueError("请使用审批或撤销操作变更请假状态")
        await self._validate({**{k: getattr(l, k) for k in ("employee_id", "start_date", "end_date", "duration_days")}, **data}, lid)
        return self._d(await self.repo.update(l, data))

    async def approve_request(self, lid: UUID, status: str, operated_by: UUID, remark: str | None = None):
        l = await self.repo.get_by_id(lid)
        if not l:
            raise ValueError("请假申请不存在")
        if status not in {"approved", "rejected", "cancelled"}:
            raise ValueError("无效的审批状态")
        if (status == "cancelled" and l.status not in {"pending", "approved"}) or (status != "cancelled" and l.status != "pending"):
            raise ValueError(f"当前状态为 {l.status}，无法执行该操作")
        if status == "approved":
            await self._validate({k: getattr(l, k) for k in ("employee_id", "start_date", "end_date", "duration_days")}, lid)
        if status == "cancelled" and (not remark or not remark.strip()):
            raise ValueError("请填写撤销原因")
        l.status = status
        if status == "cancelled":
            l.cancelled_by = operated_by
            l.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
            l.cancellation_reason = remark.strip()
        else:
            l.approved_by = operated_by
            l.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if remark:
                l.remark = remark
        await self.db.flush()
        await self.db.refresh(l)
        return self._d(l)

    async def delete_request(self, lid: UUID):
        l = await self.repo.get_by_id(lid)
        if not l:
            return False
        if l.status != "pending":
            raise ValueError("已审批请假保留历史，可撤销但不能删除")
        await self.repo.delete(l)
        return True

    async def _validate(self, data, exclude_id=None):
        employee_id = data["employee_id"]
        emp = await self.db.scalar(select(Employee).where(Employee.id == employee_id).with_for_update(of=Employee))
        if emp is None:
            raise ValueError("员工不存在")
        start, end = data["start_date"], data["end_date"]
        duration = float(data["duration_days"])
        if end < start or duration <= 0:
            raise ValueError("请假结束日期不能早于开始日期，天数必须大于0")
        if not employed_on(emp, start) or not employed_on(emp, end):
            raise ValueError("请假日期应在员工任职期间")
        q = select(LeaveRequest.id).where(LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["pending", "approved"]), LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start)
        if exclude_id:
            q = q.where(LeaveRequest.id != exclude_id)
        if await self.db.scalar(q):
            raise ValueError("与已有待审批或已批准请假日期重叠")
        rules = (await self.db.execute(select(AttendanceRule).where(AttendanceRule.is_active.is_(True))
            .order_by(AttendanceRule.updated_at.desc(), AttendanceRule.id))).scalars().all()
        rule = next((r for r in rules if r.department and r.department == emp.department), None)
        rule = rule or next((r for r in rules if not r.department), None)
        weekdays = set(rule.work_days if rule and rule.work_days is not None else WEEKDAYS[:5])
        count = sum(1 for offset in range((end-start).days+1) if WEEKDAYS[(start+timedelta(days=offset)).weekday()] in weekdays)
        if not ((duration == 0.5 and start == end and count == 1) or duration == count and count > 0):
            raise ValueError(f"按当前考勤规则，本次应为 {count} 个工作日；半天请假请单独选择同一天并填写0.5")

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
            "cancellation_reason": l.cancellation_reason,
            "cancelled_at": l.cancelled_at.isoformat() if l.cancelled_at else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "updated_at": l.updated_at.isoformat() if l.updated_at else None,
        }
