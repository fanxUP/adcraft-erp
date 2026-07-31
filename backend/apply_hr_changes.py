"""Apply HR module changes after deploy (files modified by deploy's git reset)"""
import pathlib

BACKEND = pathlib.Path("/opt/adcraft/backend")
FRONTEND = pathlib.Path("/opt/adcraft/frontend")

# ============================================================
# 1. Create new backend files
# ============================================================
print("=== 创建后端新文件 ===")

# models/attendance.py
(BACKEND / "app/models/attendance.py").write_text('''
import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AttendanceRule(Base, TimestampMixin):
    __tablename__ = "attendance_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="规则名称")
    department: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="适用部门")
    check_in_time: Mapped[time] = mapped_column(Time, nullable=False, comment="上班时间")
    check_out_time: Mapped[time] = mapped_column(Time, nullable=False, comment="下班时间")
    work_days: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="工作日配置")
    late_threshold: Mapped[int] = mapped_column(Integer, default=0, comment="迟到阈值(分钟)")
    early_leave_threshold: Mapped[int] = mapped_column(Integer, default=0, comment="早退阈值(分钟)")
    overtime_rate: Mapped[float | None] = mapped_column(Numeric(3, 1), default=1.5, comment="加班费率")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, comment="员工ID")
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="日期")
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="签到时间")
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="签退时间")
    check_in_status: Mapped[str] = mapped_column(String(16), default="normal", comment="签到状态")
    check_out_status: Mapped[str] = mapped_column(String(16), default="normal", comment="签退状态")
    source: Mapped[str] = mapped_column(String(16), default="manual", comment="来源")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
'''.strip())

# schemas/attendance.py
(BACKEND / "app/schemas/attendance.py").write_text('''
from pydantic import BaseModel
from datetime import date, datetime, time
from typing import Optional


class AttendanceRuleCreate(BaseModel):
    name: str
    department: Optional[str] = None
    check_in_time: time
    check_out_time: time
    work_days: Optional[list[str]] = None
    late_threshold: int = 0
    early_leave_threshold: int = 0
    overtime_rate: float = 1.5
    is_active: bool = True


class AttendanceRuleUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None
    work_days: Optional[list[str]] = None
    late_threshold: Optional[int] = None
    early_leave_threshold: Optional[int] = None
    overtime_rate: Optional[float] = None
    is_active: Optional[bool] = None


class AttendanceRuleResponse(BaseModel):
    id: str
    name: str
    department: Optional[str] = None
    check_in_time: str
    check_out_time: str
    work_days: Optional[list] = None
    late_threshold: int = 0
    early_leave_threshold: int = 0
    overtime_rate: Optional[float] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class AttendanceRecordCreate(BaseModel):
    employee_id: str
    date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    check_in_status: str = "normal"
    check_out_status: str = "normal"
    source: str = "manual_input"
    remark: Optional[str] = None


class AttendanceRecordUpdate(BaseModel):
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    check_in_status: Optional[str] = None
    check_out_status: Optional[str] = None
    remark: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    id: str
    employee_id: str
    date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    check_in_status: str
    check_out_status: str
    source: str
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
'''.strip())

# repositories/attendance_repo.py
(BACKEND / "app/repositories/attendance_repo.py").write_text('''
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.attendance import AttendanceRule, AttendanceRecord


class AttendanceRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self) -> list[AttendanceRule]:
        result = await self.db.execute(select(AttendanceRule).order_by(AttendanceRule.name.asc()))
        return list(result.scalars().all())

    async def get_by_id(self, rule_id: UUID) -> AttendanceRule | None:
        result = await self.db.execute(select(AttendanceRule).where(AttendanceRule.id == rule_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> AttendanceRule:
        obj = AttendanceRule(**data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, rule: AttendanceRule, data: dict) -> AttendanceRule:
        for k, v in data.items():
            if v is not None:
                setattr(rule, k, v)
        await self.db.flush()
        return rule

    async def delete(self, rule: AttendanceRule) -> None:
        await self.db.delete(rule)
        await self.db.flush()


class AttendanceRecordRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, skip=0, limit=20, employee_id=None, date_from=None, date_to=None):
        q = select(AttendanceRecord)
        if employee_id:
            q = q.where(AttendanceRecord.employee_id == employee_id)
        if date_from:
            q = q.where(AttendanceRecord.date >= date_from)
        if date_to:
            q = q.where(AttendanceRecord.date <= date_to)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(AttendanceRecord.date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, record_id: UUID) -> AttendanceRecord | None:
        result = await self.db.execute(select(AttendanceRecord).where(AttendanceRecord.id == record_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> AttendanceRecord:
        obj = AttendanceRecord(**data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def update(self, record: AttendanceRecord, data: dict) -> AttendanceRecord:
        for k, v in data.items():
            if v is not None:
                setattr(record, k, v)
        await self.db.flush()
        return record

    async def delete(self, record: AttendanceRecord) -> None:
        await self.db.delete(record)
        await self.db.flush()
'''.strip())

# services/attendance_service.py
(BACKEND / "app/services/attendance_service.py").write_text('''
import logging
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.attendance_repo import AttendanceRuleRepository, AttendanceRecordRepository

logger = logging.getLogger(__name__)


class AttendanceRuleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttendanceRuleRepository(db)

    async def list_rules(self):
        return [self._r2d(r) for r in (await self.repo.list())]

    async def get_rule(self, rule_id: UUID):
        r = await self.repo.get_by_id(rule_id)
        return self._r2d(r) if r else None

    async def create_rule(self, data: dict):
        return self._r2d(await self.repo.create(data))

    async def update_rule(self, rule_id: UUID, data: dict):
        r = await self.repo.get_by_id(rule_id)
        if not r:
            raise ValueError("考勤规则不存在")
        return self._r2d(await self.repo.update(r, data))

    async def delete_rule(self, rule_id: UUID):
        r = await self.repo.get_by_id(rule_id)
        if not r:
            return False
        await self.repo.delete(r)
        return True

    def _r2d(self, r):
        return {
            "id": str(r.id), "name": r.name, "department": r.department,
            "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
            "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
            "work_days": r.work_days if isinstance(r.work_days, list) else [],
            "late_threshold": r.late_threshold, "early_leave_threshold": r.early_leave_threshold,
            "overtime_rate": float(r.overtime_rate) if r.overtime_rate else None,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }


class AttendanceRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttendanceRecordRepository(db)

    async def list_records(self, page=1, page_size=20, employee_id=None, date_from=None, date_to=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list(skip, page_size, employee_id, date_from, date_to)
        return [self._r2d(r) for r in records], total

    async def get_record(self, record_id: UUID):
        r = await self.repo.get_by_id(record_id)
        return self._r2d(r) if r else None

    async def create_record(self, data: dict):
        return self._r2d(await self.repo.create(data))

    async def update_record(self, record_id: UUID, data: dict):
        r = await self.repo.get_by_id(record_id)
        if not r:
            raise ValueError("打卡记录不存在")
        return self._r2d(await self.repo.update(r, data))

    async def delete_record(self, record_id: UUID):
        r = await self.repo.get_by_id(record_id)
        if not r:
            return False
        await self.repo.delete(r)
        return True

    def _r2d(self, r):
        return {
            "id": str(r.id), "employee_id": str(r.employee_id),
            "date": r.date.isoformat() if r.date else None,
            "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
            "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
            "check_in_status": r.check_in_status, "check_out_status": r.check_out_status,
            "source": r.source, "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
'''.strip())

# api/attendance.py
(BACKEND / "app/api/attendance.py").write_text('''
import logging
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.attendance import AttendanceRuleCreate, AttendanceRuleUpdate, AttendanceRecordCreate, AttendanceRecordUpdate
from app.schemas.common import success, success_paginated
from app.services.attendance_service import AttendanceRuleService, AttendanceRecordService
from app.services.employee_service import EmployeeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/rules")
async def list_rules(db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await AttendanceRuleService(db).list_rules())


@router.post("/rules")
async def create_rule(data: AttendanceRuleCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await AttendanceRuleService(db).create_rule(data.model_dump()))


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, data: AttendanceRuleUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await AttendanceRuleService(db).update_rule(UUID(rule_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await AttendanceRuleService(db).delete_rule(UUID(rule_id)):
        return {"code": 40401, "message": "考勤规则不存在", "data": None}
    return success(None)


@router.get("/records")
async def list_records(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                       employee_id: str|None = None, date_from: date|None = None, date_to: date|None = None,
                       db=Depends(get_db), current_user=Depends(get_current_user)):
    emp_id = UUID(employee_id) if employee_id else None
    items, total = await AttendanceRecordService(db).list_records(page, page_size, emp_id, date_from, date_to)
    return success_paginated(items, total, page, page_size)


@router.post("/records")
async def create_record(data: AttendanceRecordCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await AttendanceRecordService(db).create_record(data.model_dump()))


@router.put("/records/{record_id}")
async def update_record(record_id: str, data: AttendanceRecordUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await AttendanceRecordService(db).update_record(UUID(record_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.delete("/records/{record_id}")
async def delete_record(record_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await AttendanceRecordService(db).delete_record(UUID(record_id)):
        return {"code": 40401, "message": "打卡记录不存在", "data": None}
    return success(None)


@router.get("/employees")
async def list_employees(db=Depends(get_db), current_user=Depends(get_current_user)):
    items, _ = await EmployeeService(db).list_employees(1, 1000, employment_status="active")
    return success(items)
'''.strip())


# ============================================================
# 2. Modify main.py to register attendance router
# ============================================================
print("=== 修改 main.py ===")
main_py = BACKEND / "app/main.py"
content = main_py.read_text()

# Add import
if "attendance" not in content:
    content = content.replace(
        "from app.api import auth, users, customers, products, quotes, orders, tasks, payments, reports, outsource, inventory, operation_logs, backup, admin, notifications, conversations, acceptances, contracts, framework_contracts, vehicles, vehicle_agent, vehicle_dashboard, aerial, ai_execute, ai_models, ai_providers, ai_prompts, ai_requests, ai_routes, employees",
        "from app.api import auth, users, customers, products, quotes, orders, tasks, payments, reports, outsource, inventory, operation_logs, backup, admin, notifications, conversations, acceptances, contracts, framework_contracts, vehicles, vehicle_agent, vehicle_dashboard, aerial, ai_execute, ai_models, ai_providers, ai_prompts, ai_requests, ai_routes, employees, attendance"
    )
    # Add router registration
    content = content.replace(
        "app.include_router(employees.router, prefix=\"/api/v1\")",
        "app.include_router(employees.router, prefix=\"/api/v1\")\napp.include_router(attendance.router, prefix=\"/api/v1\")"
    )
    main_py.write_text(content)
    print("  main.py - imported and registered attendance router")
else:
    print("  main.py - already up to date")

# ============================================================
# 3. Create frontend files
# ============================================================
print("=== 创建前端文件 ===")

# api/attendance.ts
api_file = FRONTEND / "src/api/attendance.ts"
api_file.parent.mkdir(parents=True, exist_ok=True)
api_file.write_text('''
import { get, post, put, del } from "./index"
import type { PaginatedData, SuccessResponse } from "@/types/api"

export interface AttendanceRuleItem {
  id: string
  name: string
  department?: string | null
  check_in_time: string
  check_out_time: string
  work_days?: string[]
  late_threshold: number
  early_leave_threshold: number
  overtime_rate?: number | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AttendanceRecordItem {
  id: string
  employee_id: string
  date: string
  check_in_time?: string | null
  check_out_time?: string | null
  check_in_status: string
  check_out_status: string
  source: string
  remark?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface EmployeeOption {
  id: string
  employee_no: string
  name: string
  department?: string | null
}

export function getAttendanceRules() {
  return get<AttendanceRuleItem[]>("/attendance/rules")
}

export function createAttendanceRule(data: Partial<AttendanceRuleItem>) {
  return post<AttendanceRuleItem>("/attendance/rules", data)
}

export function updateAttendanceRule(id: string, data: Partial<AttendanceRuleItem>) {
  return put<AttendanceRuleItem>("/attendance/rules/" + id, data)
}

export function deleteAttendanceRule(id: string) {
  return del<SuccessResponse>("/attendance/rules/" + id)
}

export function getAttendanceRecords(params: {
  page?: number
  page_size?: number
  employee_id?: string
  date_from?: string
  date_to?: string
}) {
  return get<PaginatedData<AttendanceRecordItem>>("/attendance/records", { params })
}

export function createAttendanceRecord(data: {
  employee_id: string
  date: string
  check_in_time?: string | null
  check_out_time?: string | null
  check_in_status?: string
  check_out_status?: string
  remark?: string | null
}) {
  return post<AttendanceRecordItem>("/attendance/records", data)
}

export function updateAttendanceRecord(id: string, data: {
  check_in_time?: string | null
  check_out_time?: string | null
  check_in_status?: string
  check_out_status?: string
  remark?: string | null
}) {
  return put<AttendanceRecordItem>("/attendance/records/" + id, data)
}

export function deleteAttendanceRecord(id: string) {
  return del<SuccessResponse>("/attendance/records/" + id)
}

export function getAttendanceEmployees() {
  return get<EmployeeOption[]>("/attendance/employees")
}
'''.strip())

print("  src/api/attendance.ts - created")

print()
print("=== 全部完成 ===")
