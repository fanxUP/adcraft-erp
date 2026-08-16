"""Apply HR module (Employee + Attendance) after deploy resets git-tracked files"""
import pathlib, os, sys

BACKEND = pathlib.Path("/opt/adcraft/backend")
FRONTEND = pathlib.Path("/opt/adcraft/frontend")

def write(path: str, content: str):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip())
    print(f"  CREATED {p.name}")

def patch(path: str, old: str, new: str):
    p = pathlib.Path(path)
    c = p.read_text()
    if old in c:
        c = c.replace(old, new)
        p.write_text(c)
        print(f"  PATCHED {p.name}")
    elif new in c:
        print(f"  OK {p.name} (already patched)")
    else:
        print(f"  WARN {p.name} (pattern not found)")

# ============================================================
# A. Backend - Employee module (model, schema, repo, service, router)
# ============================================================
print("=== A. Employee Module ===")

write(BACKEND / "app/models/employee.py", '''
import uuid
from datetime import date
from sqlalchemy import Boolean, Date, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, SoftDeleteMixin

class Employee(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    department: Mapped[str | None] = mapped_column(String(32), nullable=True)
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resignation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(String(16), default="active")
    id_card: Mapped[str | None] = mapped_column(String(32), nullable=True)
    education: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skills: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    base_salary: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
''')

# Schema
write(BACKEND / "app/schemas/employee.py", '''
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class EmployeeCreate(BaseModel):
    name: str; phone: Optional[str] = None; gender: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: str = "active"; id_card: Optional[str] = None; education: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None; base_salary: Optional[float] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: bool = True

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None; phone: Optional[str] = None; gender: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: Optional[str] = None; id_card: Optional[str] = None; education: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None; base_salary: Optional[float] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: Optional[bool] = None

class EmployeeResponse(BaseModel):
    id: str; employee_no: str; name: str; phone: Optional[str] = None; gender: Optional[str] = None
    birth_date: Optional[date] = None; department: Optional[str] = None; position: Optional[str] = None
    employment_type: Optional[str] = None; hire_date: Optional[date] = None; resignation_date: Optional[date] = None
    employment_status: str; id_card: Optional[str] = None; education: Optional[str] = None
    emergency_contact: Optional[str] = None; emergency_phone: Optional[str] = None
    skills: Optional[list[str]] = None; base_salary: Optional[float] = None
    bank_name: Optional[str] = None; bank_account: Optional[str] = None; address: Optional[str] = None
    user_id: Optional[str] = None; remark: Optional[str] = None; is_active: bool
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
''')

# Repo
write(BACKEND / "app/repositories/employee_repo.py", '''
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.employee import Employee

class EmployeeRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def get_by_id(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()
    async def list(self, skip=0, limit=20, keyword=None, department=None, employment_status=None):
        q = select(Employee).where(Employee.deleted_at.is_(None))
        if keyword: p = f"%{keyword}%"; q = q.where(or_(Employee.employee_no.ilike(p), Employee.name.ilike(p), Employee.phone.ilike(p)))
        if department: q = q.where(Employee.department == department)
        if employment_status: q = q.where(Employee.employment_status == employment_status)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(q.order_by(Employee.employee_no.asc()).offset(skip).limit(limit))
        return list(r.scalars().all()), t
    async def create(self, data): e = Employee(**data); self.db.add(e); await self.db.flush(); return e
    async def update(self, e, data):
        for k, v in data.items():
            if v is not None: setattr(e, k, v)
        await self.db.flush(); return e
    async def soft_delete(self, e): e.deleted_at = datetime.now(); await self.db.flush()
''')

# Service
write(BACKEND / "app/services/employee_service.py", '''
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
''')

# Router
write(BACKEND / "app/api/employees.py", '''
import logging, os, uuid as _uuid
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db; from app.core.deps import get_current_user
from app.core.permissions import require_role; from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.schemas.common import success, success_paginated
from app.services.employee_service import EmployeeService
from app.services.task_service import AttachmentService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("/")
async def list_employees(page=Query(1,ge=1), page_size=Query(20,ge=1,le=100), keyword=None, department=None, employment_status=None, db=Depends(get_db), current_user=Depends(get_current_user)):
    s = EmployeeService(db); items, total = await s.list_employees(page, page_size, keyword, department, employment_status)
    return success_paginated(items, total, page, page_size)

@router.post("/")
async def create_employee(data: EmployeeCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await EmployeeService(db).create_employee(data.model_dump()))

@router.get("/{employee_id}")
async def get_employee(employee_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    emp = await EmployeeService(db).get_employee(UUID(employee_id))
    if not emp: return {"code": 40401, "message": "员工不存在", "data": None}
    return success(emp)

@router.put("/{employee_id}")
async def update_employee(employee_id: str, data: EmployeeUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try: return success(await EmployeeService(db).update_employee(UUID(employee_id), data.model_dump(exclude_none=True)))
    except ValueError as e: return {"code": 40401, "message": str(e), "data": None}

@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, db=Depends(get_db), current_user=Depends(require_role("admin"))):
    if not await EmployeeService(db).delete_employee(UUID(employee_id)): return {"code": 40401, "message": "员工不存在", "data": None}
    return success(None)

@router.get("/{employee_id}/attachments")
async def list_attachments(employee_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await AttachmentService(db).list_attachments("employee", UUID(employee_id)))

@router.post("/{employee_id}/attachments")
async def upload_attachment(employee_id: str, file: UploadFile = File(...), category: str|None=None, remark: str|None=None, db=Depends(get_db), current_user=Depends(get_current_user)):
    upload_dir=settings.LOCAL_UPLOAD_DIR; date_dir=datetime.now(timezone.utc).strftime("%Y%m"); dest_dir=f"{upload_dir}/{date_dir}"
    os.makedirs(dest_dir, exist_ok=True)
    ext = file.filename.rsplit(".",1)[1] if file.filename and "." in file.filename else ""
    fn = f"{_uuid.uuid4().hex}.{ext}"; fp = f"{dest_dir}/{fn}"
    c = await file.read()
    with open(fp,"wb") as f: f.write(c)
    att = await AttachmentService(db).add_attachment("employee", UUID(employee_id),
        {"filename": file.filename or fn, "file_path": f"{date_dir}/{fn}", "file_size": len(c), "file_type": file.content_type, "category": category, "remark": remark}, uploaded_by=current_user.id)
    return success(att)

@router.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await AttachmentService(db).delete_attachment(UUID(attachment_id)): return {"code": 40401, "message": "附件不存在", "data": None}
    return success(None)
''')

# generate_employee_no in number_generator
ng_path = BACKEND / "app/services/number_generator.py"
ng = ng_path.read_text()
if "generate_employee_no" not in ng:
    with open(ng_path, "a") as f: f.write("\n\nasync def generate_employee_no(db):\n    return await _generate_no(db, \"EMP\")\n")
    print("  PATCHED number_generator.py (added generate_employee_no)")
else:
    print("  OK number_generator.py")

# ============================================================
# B. Backend - Attendance module (model, schema, repo, service, router)
# ============================================================
print("\n=== B. Attendance Module ===")

write(BACKEND / "app/models/attendance.py", '''
import uuid
from datetime import date, datetime, time
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class AttendanceRule(Base, TimestampMixin):
    __tablename__ = "attendance_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    department: Mapped[str | None] = mapped_column(String(32), nullable=True)
    check_in_time: Mapped[time] = mapped_column(Time, nullable=False)
    check_out_time: Mapped[time] = mapped_column(Time, nullable=False)
    work_days: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    late_threshold: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_threshold: Mapped[int] = mapped_column(Integer, default=0)
    overtime_rate: Mapped[float | None] = mapped_column(Numeric(3, 1), default=1.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_status: Mapped[str] = mapped_column(String(16), default="normal")
    check_out_status: Mapped[str] = mapped_column(String(16), default="normal")
    source: Mapped[str] = mapped_column(String(16), default="manual")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
''')

write(BACKEND / "app/schemas/attendance.py", '''
from pydantic import BaseModel
from datetime import date, datetime, time
from typing import Optional

class AttendanceRuleCreate(BaseModel):
    name: str; department: Optional[str] = None; check_in_time: time; check_out_time: time
    work_days: Optional[list[str]] = None; late_threshold: int = 0; early_leave_threshold: int = 0
    overtime_rate: float = 1.5; is_active: bool = True

class AttendanceRuleUpdate(BaseModel):
    name: Optional[str] = None; department: Optional[str] = None; check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None; work_days: Optional[list[str]] = None
    late_threshold: Optional[int] = None; early_leave_threshold: Optional[int] = None
    overtime_rate: Optional[float] = None; is_active: Optional[bool] = None

class AttendanceRuleResponse(BaseModel):
    id: str; name: str; department: Optional[str] = None; check_in_time: str; check_out_time: str
    work_days: Optional[list] = None; late_threshold: int = 0; early_leave_threshold: int = 0
    overtime_rate: Optional[float] = None; is_active: bool; created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None; model_config = {"from_attributes": True}

class AttendanceRecordCreate(BaseModel):
    employee_id: str; date: date; check_in_time: Optional[datetime] = None; check_out_time: Optional[datetime] = None
    check_in_status: str = "normal"; check_out_status: str = "normal"; source: str = "manual_input"
    remark: Optional[str] = None

class AttendanceRecordUpdate(BaseModel):
    check_in_time: Optional[datetime] = None; check_out_time: Optional[datetime] = None
    check_in_status: Optional[str] = None; check_out_status: Optional[str] = None
    remark: Optional[str] = None

class AttendanceRecordResponse(BaseModel):
    id: str; employee_id: str; date: date; check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None; check_in_status: str; check_out_status: str
    source: str; remark: Optional[str] = None; created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None; model_config = {"from_attributes": True}
''')

write(BACKEND / "app/repositories/attendance_repo.py", '''
from uuid import UUID; from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession; from sqlalchemy import select, func
from app.models.attendance import AttendanceRule, AttendanceRecord

class AttendanceRuleRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def list(self): r = await self.db.execute(select(AttendanceRule).order_by(AttendanceRule.name.asc())); return list(r.scalars().all())
    async def get_by_id(self, rid): r = await self.db.execute(select(AttendanceRule).where(AttendanceRule.id == rid)); return r.scalar_one_or_none()
    async def create(self, d): o = AttendanceRule(**d); self.db.add(o); await self.db.flush(); return o
    async def update(self, o, d):
        for k,v in d.items():
            if v is not None: setattr(o,k,v)
        await self.db.flush(); return o
    async def delete(self, o): await self.db.delete(o); await self.db.flush()

class AttendanceRecordRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def list(self, skip=0, limit=20, employee_id=None, date_from=None, date_to=None):
        q = select(AttendanceRecord)
        if employee_id: q = q.where(AttendanceRecord.employee_id == employee_id)
        if date_from: q = q.where(AttendanceRecord.date >= date_from)
        if date_to: q = q.where(AttendanceRecord.date <= date_to)
        t = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        r = await self.db.execute(q.order_by(AttendanceRecord.date.desc()).offset(skip).limit(limit))
        return list(r.scalars().all()), t
    async def get_by_id(self, rid): r = await self.db.execute(select(AttendanceRecord).where(AttendanceRecord.id == rid)); return r.scalar_one_or_none()
    async def create(self, d): o = AttendanceRecord(**d); self.db.add(o); await self.db.flush(); return o
    async def update(self, o, d):
        for k,v in d.items():
            if v is not None: setattr(o,k,v)
        await self.db.flush(); return o
    async def delete(self, o): await self.db.delete(o); await self.db.flush()
''')

write(BACKEND / "app/services/attendance_service.py", '''
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
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None}
''')

write(BACKEND / "app/api/attendance.py", '''
import logging
from datetime import date; from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db; from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.attendance import AttendanceRuleCreate, AttendanceRuleUpdate, AttendanceRecordCreate, AttendanceRecordUpdate
from app.schemas.common import success, success_paginated
from app.services.attendance_service import AttendanceRuleService, AttendanceRecordService
from app.services.employee_service import EmployeeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/rules") async def list_rules(db=Depends(get_db), current_user=Depends(get_current_user)): return success(await AttendanceRuleService(db).list_rules())
@router.post("/rules") async def create_rule(data: AttendanceRuleCreate, db=Depends(get_db), current_user=Depends(get_current_user)): return success(await AttendanceRuleService(db).create_rule(data.model_dump()))
@router.put("/rules/{rule_id}") async def update_rule(rule_id: str, data: AttendanceRuleUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try: return success(await AttendanceRuleService(db).update_rule(UUID(rule_id), data.model_dump(exclude_none=True)))
    except ValueError as e: return {"code": 40401, "message": str(e), "data": None}
@router.delete("/rules/{rule_id}") async def delete_rule(rule_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await AttendanceRuleService(db).delete_rule(UUID(rule_id)): return {"code": 40401, "message": "考勤规则不存在", "data": None}
    return success(None)

@router.get("/records") async def list_records(page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100), employee_id: str|None=None, date_from: date|None=None, date_to: date|None=None, db=Depends(get_db), current_user=Depends(get_current_user)):
    emp_id = UUID(employee_id) if employee_id else None
    items, total = await AttendanceRecordService(db).list_records(page, page_size, emp_id, date_from, date_to)
    return success_paginated(items, total, page, page_size)
@router.post("/records") async def create_record(data: AttendanceRecordCreate, db=Depends(get_db), current_user=Depends(get_current_user)): return success(await AttendanceRecordService(db).create_record(data.model_dump()))
@router.put("/records/{record_id}") async def update_record(record_id: str, data: AttendanceRecordUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try: return success(await AttendanceRecordService(db).update_record(UUID(record_id), data.model_dump(exclude_none=True)))
    except ValueError as e: return {"code": 40401, "message": str(e), "data": None}
@router.delete("/records/{record_id}") async def delete_record(record_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    if not await AttendanceRecordService(db).delete_record(UUID(record_id)): return {"code": 40401, "message": "打卡记录不存在", "data": None}
    return success(None)
@router.get("/employees") async def list_employees(db=Depends(get_db), current_user=Depends(get_current_user)):
    items, _ = await EmployeeService(db).list_employees(1, 1000, employment_status="active"); return success(items)
''')

# ============================================================
# C. Patch main.py - add employees and attendance
# ============================================================
print("\n=== C. main.py ===")
mp = BACKEND / "app/main.py"
c = mp.read_text()

# Check if already patched
if "employees" in c and "attendance" in c:
    print("  OK main.py (already patched)")
else:
    # Add to import line
    need_import = "employees, attendance" if "employees" not in c and "attendance" not in c else ("attendance" if "attendance" not in c else "employees")
    old_import = "from app.api import auth, users, customers, products, quotes, orders, tasks, payments, reports, outsource, inventory, operation_logs, backup, admin, notifications, conversations, acceptances, contracts, framework_contracts, vehicles, vehicle_agent, vehicle_dashboard, aerial, ai_execute, ai_models, ai_providers, ai_prompts, ai_requests, ai_routes"
    new_import = old_import + ", employees, attendance"

    safe_old = old_import.replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)")
    import subprocess
    subprocess.run(["sed", "-i", f"s|^{old_import}$|{new_import}|", str(mp)], check=True)
    
    # Add router registrations after framework_contracts
    subprocess.run(["sed", "-i", "/^app.include_router(framework_contracts.router/a app.include_router(employees.router, prefix=\\\"/api/v1\\\")\\napp.include_router(attendance.router, prefix=\\\"/api/v1\\\")", str(mp)], check=True)
    print("  PATCHED main.py")

# ============================================================
# D. Frontend - API file + Vue pages
# ============================================================
print("\n=== D. Frontend ===")

write(FRONTEND / "src/api/attendance.ts", '''
import { get, post, put, del } from "./index"
import type { PaginatedData, SuccessResponse } from "@/types/api"

export interface AttendanceRuleItem {
  id: string; name: string; department?: string | null; check_in_time: string; check_out_time: string
  work_days?: string[]; late_threshold: number; early_leave_threshold: number; overtime_rate?: number | null
  is_active: boolean; created_at?: string | null; updated_at?: string | null
}
export interface AttendanceRecordItem {
  id: string; employee_id: string; date: string; check_in_time?: string | null; check_out_time?: string | null
  check_in_status: string; check_out_status: string; source: string; remark?: string | null; created_at?: string | null; updated_at?: string | null
}
export interface EmployeeOption { id: string; employee_no: string; name: string; department?: string | null }

export function getAttendanceRules() { return get<AttendanceRuleItem[]>("/attendance/rules") }
export function createAttendanceRule(data: Partial<AttendanceRuleItem>) { return post<AttendanceRuleItem>("/attendance/rules", data) }
export function updateAttendanceRule(id: string, data: Partial<AttendanceRuleItem>) { return put<AttendanceRuleItem>("/attendance/rules/" + id, data) }
export function deleteAttendanceRule(id: string) { return del<SuccessResponse>("/attendance/rules/" + id) }
export function getAttendanceRecords(params: { page?: number; page_size?: number; employee_id?: string; date_from?: string; date_to?: string }) { return get<PaginatedData<AttendanceRecordItem>>("/attendance/records", { params }) }
export function createAttendanceRecord(data: { employee_id: string; date: string; check_in_time?: string | null; check_out_time?: string | null; check_in_status?: string; check_out_status?: string; remark?: string | null }) { return post<AttendanceRecordItem>("/attendance/records", data) }
export function updateAttendanceRecord(id: string, data: any) { return put<AttendanceRecordItem>("/attendance/records/" + id, data) }
export function deleteAttendanceRecord(id: string) { return del<SuccessResponse>("/attendance/records/" + id) }
export function getAttendanceEmployees() { return get<EmployeeOption[]>("/attendance/employees") }
''')

# Vue pages
vue_dir = FRONTEND / "src/views/attendance"
vue_dir.mkdir(parents=True, exist_ok=True)

# AttendanceRuleList.vue
write(vue_dir / "AttendanceRuleList.vue", '''
<template>
  <div class="page">
    <div class="page-header"><h2>考勤规则</h2>
      <el-button type="danger" @click="openCreate">新建规则</el-button>
    </div>
    <el-table :data="rules" v-loading="loading" stripe>
      <el-table-column prop="name" label="规则名称" width="160" />
      <el-table-column label="适用部门" width="120"><template #default="{ row }">{{ row.department || "全局" }}</template></el-table-column>
      <el-table-column prop="check_in_time" label="上班时间" width="100" />
      <el-table-column prop="check_out_time" label="下班时间" width="100" />
      <el-table-column prop="late_threshold" label="迟到阈值" width="100" />
      <el-table-column prop="overtime_rate" label="加班费率" width="100" />
      <el-table-column label="启用" width="80"><template #default="{ row }"><el-tag :type="row.is_active?'success':'info'" size="small">{{ row.is_active?"是":"否" }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="showDialog" :title="isEditing?'编辑规则':'新建规则'" width="500px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="规则名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="适用部门"><el-select v-model="form.department" placeholder="留空=全局" clearable style="width:100%">
          <el-option label="设计部" value="design" /><el-option label="生产部" value="production" />
          <el-option label="安装部" value="installation" /><el-option label="销售部" value="sales" />
          <el-option label="财务部" value="finance" /><el-option label="行政部" value="admin" />
        </el-select></el-form-item>
        <el-form-item label="上班时间" required><el-time-picker v-model="form.check_in_time" format="HH:mm" value-format="HH:mm" style="width:100%" /></el-form-item>
        <el-form-item label="下班时间" required><el-time-picker v-model="form.check_out_time" format="HH:mm" value-format="HH:mm" style="width:100%" /></el-form-item>
        <el-form-item label="迟到阈值(分钟)"><el-input-number v-model="form.late_threshold" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="加班费率"><el-input-number v-model="form.overtime_rate" :min="1" :max="3" :step="0.1" style="width:100%" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getAttendanceRules, createAttendanceRule, updateAttendanceRule, deleteAttendanceRule, type AttendanceRuleItem } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"
const rules = ref<AttendanceRuleItem[]>([]); const loading = ref(false)
const showDialog = ref(false); const isEditing = ref(false); const saving = ref(false)
const form = ref<any>({name:"", check_in_time:"09:00", check_out_time:"18:00", department:"", late_threshold:0, early_leave_threshold:0, overtime_rate:1.5, is_active:true})
async function fetchData() { loading.value=true; try { rules.value = (await getAttendanceRules()) || [] } finally { loading.value=false } }
function openCreate() { isEditing.value=false; form.value={name:"", check_in_time:"09:00", check_out_time:"18:00", department:"", late_threshold:0, early_leave_threshold:0, overtime_rate:1.5, is_active:true}; showDialog.value=true }
function openEdit(r: AttendanceRuleItem) { isEditing.value=true; form.value={...r}; showDialog.value=true }
async function handleSave() { saving.value=true; try { isEditing.value ? await updateAttendanceRule(form.value.id, form.value) : await createAttendanceRule(form.value); ElMessage.success(isEditing.value?"已更新":"已创建"); showDialog.value=false; await fetchData() } finally { saving.value=false } }
async function handleDelete(r: AttendanceRuleItem) { await ElMessageBox.confirm("确定删除？","提示",{type:"warning"}); await deleteAttendanceRule(r.id); ElMessage.success("已删除"); await fetchData() }
onMounted(fetchData)
</script>
''')

# AttendanceRecordList.vue
write(vue_dir / "AttendanceRecordList.vue", '''
<template>
  <div class="page">
    <div class="page-header"><h2>打卡记录</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <el-select v-model="fEmp" placeholder="员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-date-picker v-model="fDate" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" @change="fetchData" />
        <el-button type="danger" @click="openCreate">录入打卡</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column label="员工" width="140"><template #default="{ row }">{{ empName(row.employee_id) }}</template></el-table-column>
      <el-table-column prop="check_in_time" label="签到时间" width="170"><template #default="{ row }">{{ fmtDT(row.check_in_time) }}</template></el-table-column>
      <el-table-column label="签到" width="80"><template #default="{ row }"><el-tag :type="tagType(row.check_in_status)" size="small">{{ label(row.check_in_status) }}</el-tag></template></el-table-column>
      <el-table-column prop="check_out_time" label="签退时间" width="170"><template #default="{ row }">{{ fmtDT(row.check_out_time) }}</template></el-table-column>
      <el-table-column label="签退" width="80"><template #default="{ row }"><el-tag :type="tagType(row.check_out_status)" size="small">{{ label(row.check_out_status) }}</el-tag></template></el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }"><el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button><el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10,20,50]" :total="total" layout="total,sizes,prev,pager,next" style="margin-top:16px" @change="fetchData" />
    <el-dialog v-model="showDialog" :title="isEditing?'编辑打卡':'录入打卡'" width="500px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="员工" v-if="!isEditing" required><el-select v-model="form.employee_id" placeholder="选择员工" filterable style="width:100%"><el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" /></el-select></el-form-item>
        <el-form-item label="日期" required><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="签到时间"><el-date-picker v-model="form.check_in_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" /></el-form-item>
        <el-form-item label="签到状态"><el-select v-model="form.check_in_status" style="width:100%"><el-option label="正常" value="normal" /><el-option label="迟到" value="late" /><el-option label="缺卡" value="missed" /></el-select></el-form-item>
        <el-form-item label="签退时间"><el-date-picker v-model="form.check_out_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" /></el-form-item>
        <el-form-item label="签退状态"><el-select v-model="form.check_out_status" style="width:100%"><el-option label="正常" value="normal" /><el-option label="早退" value="early" /><el-option label="缺卡" value="missed" /></el-select></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getAttendanceRecords, createAttendanceRecord, updateAttendanceRecord, deleteAttendanceRecord, getAttendanceEmployees, type AttendanceRecordItem, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"
const list = ref<AttendanceRecordItem[]>([]); const employees = ref<EmployeeOption[]>([]); const loading = ref(false)
const page = ref(1); const pageSize = ref(20); const total = ref(0); const fEmp = ref(""); const fDate = ref<string[]>([])
const showDialog = ref(false); const isEditing = ref(false); const saving = ref(false); const editId = ref("")
const form = ref<any>({employee_id:"",date:"",check_in_time:null,check_out_time:null,check_in_status:"normal",check_out_status:"normal",remark:""})
const empName = (id:string) => employees.value.find(e=>e.id===id)?.name||id
const label = (s:string) => ({normal:"正常",late:"迟到",early:"早退",missed:"缺卡"})[s]||s
const tagType = (s:string) => ({normal:"success",late:"warning",early:"warning",missed:"danger"})[s]||"info"
const fmtDT = (dt:string|null) => dt ? dt.replace("T"," ").substring(0,19) : "-"
async function fetchData() {
  loading.value=true; try { const p:any={page:page.value,page_size:pageSize.value}
    if(fEmp.value) p.employee_id=fEmp.value; if(fDate.value?.length===2) { p.date_from=fDate.value[0]; p.date_to=fDate.value[1] }
    const r = await getAttendanceRecords(p); list.value=r?.items||[]; total.value=r?.total||0 } finally { loading.value=false } }
async function loadEmps() { employees.value = (await getAttendanceEmployees()) || [] }
function openCreate() { isEditing.value=false; editId.value=""; form.value={employee_id:"",date:"",check_in_time:null,check_out_time:null,check_in_status:"normal",check_out_status:"normal",remark:""}; showDialog.value=true }
function openEdit(r: AttendanceRecordItem) { isEditing.value=true; editId.value=r.id; form.value={...r}; showDialog.value=true }
async function handleSave() {
  saving.value=true; try { isEditing.value?await updateAttendanceRecord(editId.value,form.value):await createAttendanceRecord(form.value); ElMessage.success(isEditing.value?"已更新":"已创建"); showDialog.value=false; await fetchData() } finally { saving.value=false } }
async function handleDelete(r: AttendanceRecordItem) { await ElMessageBox.confirm("确定删除？","提示",{type:"warning"}); await deleteAttendanceRecord(r.id); ElMessage.success("已删除"); await fetchData() }
onMounted(()=>{fetchData();loadEmps()})
</script>
''')

# ============================================================
# E. Patch navigation.ts
# ============================================================
print("\n=== E. Navigation ===")
patch(FRONTEND / "src/config/navigation.ts",
    "children: [\n      { label: '员工管理', path: '/employees' },\n    ],",
    "children: [\n      { label: '员工管理', path: '/employees' },\n      {\n        label: '考勤管理',\n        icon: 'Clock',\n        children: [\n          { label: '打卡记录', path: '/attendance/records' },\n          { label: '考勤规则', path: '/attendance/rules' },\n        ],\n      },\n    ],"
)

# ============================================================
# F. Patch SidebarNavItem.vue - add Clock icon
# ============================================================
print("\n=== F. Sidebar Icon ===")
sidebar = FRONTEND / "src/components/navigation/SidebarNavItem.vue"
c = sidebar.read_text()
if "Clock" not in c:
    c = c.replace("import {\n  Avatar,", "import {\n  Avatar,\n  Clock,")
    c = c.replace("const icons: Record<string, Component> = {\n    Avatar,", "const icons: Record<string, Component> = {\n    Avatar,\n    Clock,")
    sidebar.write_text(c)
    print("  PATCHED SidebarNavItem.vue")
else:
    print("  OK SidebarNavItem.vue")

# ============================================================
# G. Patch router/index.ts
# ============================================================
print("\n=== G. Router ===")
patch(FRONTEND / "src/router/index.ts",
    "{ path: \"employees\", name: \"EmployeeList\", meta: { roles: [\"admin\"] }, component: () => import(\"@/views/employee/EmployeeList.vue\") },",
    "{ path: \"employees\", name: \"EmployeeList\", meta: { roles: [\"admin\"] }, component: () => import(\"@/views/employee/EmployeeList.vue\") },\n      { path: \"attendance/records\", name: \"AttendanceRecordList\", meta: { roles: [\"admin\"] }, component: () => import(\"@/views/attendance/AttendanceRecordList.vue\") },\n      { path: \"attendance/rules\", name: \"AttendanceRuleList\", meta: { roles: [\"admin\"] }, component: () => import(\"@/views/attendance/AttendanceRuleList.vue\") },"
)

# ============================================================
# H. Build frontend
# ============================================================
print("\n=== H. Build Frontend ===")
ret = os.system("cd /opt/adcraft/frontend && npm run build 2>&1 | tail -3")
if ret == 0:
    print("  Frontend build SUCCESS")
else:
    print("  Frontend build FAILED (check errors)")
    sys.exit(1)

print("\n=== ALL DONE ===")
