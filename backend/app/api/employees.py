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
async def list_employees(page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100), keyword=None, department=None, employment_status=None, db=Depends(get_db), current_user=Depends(get_current_user)):
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