import logging, os, uuid as _uuid
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, File, Query, UploadFile, HTTPException
from app.models.employee import Employee
from app.models.task import Attachment
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db; from app.core.deps import get_current_user
from app.core.permissions import PERM_SYSTEM_SUPER_ADMIN, require_permission, require_any_permission, require_all_permissions, user_has_permission; from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeUserBindingRequest
from app.schemas.common import success, success_paginated
from app.services.employee_service import EmployeeService
from app.services.task_service import AttachmentService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)

PRIVATE_FIELDS = {"id_card", "license_no", "license_type", "license_expire_date", "id_card_front_url", "id_card_back_url", "bank_name", "bank_account", "address", "birth_date", "emergency_contact", "emergency_phone"}


def employee_visible(item, user):
    return item if user_has_permission(user, "employee:private") else {k: v for k, v in item.items() if k not in PRIVATE_FIELDS}


def employee_write(data, user):
    if not user_has_permission(user, "employee:private"):
        data = {k: v for k, v in data.items() if k not in PRIVATE_FIELDS}
    if not user_has_permission(user, "system:super_admin") and (data.get("role_ids") or data.get("initial_password") or data.get("user_id")):
        from fastapi import HTTPException
        raise HTTPException(403, "角色、账号绑定和密码由系统管理员管理")
    return data


async def check_employee_target(employee_id, db, user):
    if user_has_permission(user, "system:super_admin"):
        return
    employee = await db.get(Employee, UUID(str(employee_id)))
    if employee and employee.user and user_has_permission(employee.user, "system:super_admin"):
        raise HTTPException(403, "系统管理员的员工档案和账号状态只能由系统管理员维护")


def checked_image(content):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    raise HTTPException(400, "证件照片仅支持 PNG、JPEG 或 WebP 图片")


@router.get("/")
async def list_employees(page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100), keyword=None, department=None, employment_status=None, db=Depends(get_db), current_user=Depends(require_permission('employee:read'))):
    s = EmployeeService(db); items, total = await s.list_employees(page, page_size, keyword, department, employment_status)
    return success_paginated([employee_visible(item, current_user) for item in items], total, page, page_size)

@router.post("/")
async def create_employee(data: EmployeeCreate, db=Depends(get_db), current_user=Depends(require_permission('employee:manage'))):
    return success(employee_visible(await EmployeeService(db).create_employee(employee_write(data.model_dump(), current_user)), current_user))

@router.get("/account-options")
async def list_account_options(employee_id: UUID | None = Query(None), db=Depends(get_db), current_user=Depends(require_permission('system:super_admin'))):
    return success(await EmployeeService(db).list_account_options(employee_id))

@router.post("/upload")
async def upload_employee_image(file: UploadFile = File(...), db=Depends(get_db), current_user=Depends(require_all_permissions('employee:manage', 'employee:private'))):
    """上传人员图片（身份证正反面等），返回 /uploads/ 相对 URL"""
    upload_dir = settings.LOCAL_UPLOAD_DIR
    date_dir = datetime.now(timezone.utc).strftime("%Y%m")
    dest_dir = f"{upload_dir}/{date_dir}"
    os.makedirs(dest_dir, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[1] if file.filename and "." in file.filename else ""
    fn = f"{_uuid.uuid4().hex}.{ext}"
    fp = f"{dest_dir}/{fn}"
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "证件照片不能超过10MB")
    image_ext = checked_image(content)
    fn = f"{_uuid.uuid4().hex}.{image_ext}"
    fp = f"{dest_dir}/{fn}"
    with open(fp, "wb") as f:
        f.write(content)
    from app.services.file_access_service import register_upload
    await register_upload(db, fp, current_user, "employee:private")
    return success({"file_url": f"/uploads/{date_dir}/{fn}", "file_name": file.filename or fn, "file_size": len(content)})

@router.get("/{employee_id}/handover")
async def employee_handover(employee_id: UUID, db=Depends(get_db), current_user=Depends(require_permission("employee:manage"))):
    return success(await EmployeeService(db).handover(employee_id, include_salary=user_has_permission(current_user, "salary:read")))

@router.get("/{employee_id}")
async def get_employee(employee_id: str, db=Depends(get_db), current_user=Depends(require_permission('employee:read'))):
    emp = await EmployeeService(db).get_employee(UUID(employee_id))
    if not emp: return {"code": 40401, "message": "员工不存在", "data": None}
    return success(employee_visible(emp, current_user))

@router.put("/{employee_id}/account")
async def bind_employee_account(employee_id: str, data: EmployeeUserBindingRequest, db=Depends(get_db), current_user=Depends(require_permission('system:super_admin'))):
    return success(await EmployeeService(db).bind_user(UUID(employee_id), data.user_id))

@router.put("/{employee_id}")
async def update_employee(employee_id: str, data: EmployeeUpdate, db=Depends(get_db), current_user=Depends(require_permission('employee:manage'))):
    await check_employee_target(employee_id, db, current_user)
    try: return success(employee_visible(await EmployeeService(db).update_employee(UUID(employee_id), employee_write(data.model_dump(exclude_none=True), current_user)), current_user))
    except ValueError as e: return {"code": 40401, "message": str(e), "data": None}

@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, db=Depends(get_db), current_user=Depends(require_permission('employee:manage'))):
    await check_employee_target(employee_id, db, current_user)
    if not await EmployeeService(db).delete_employee(UUID(employee_id)): return {"code": 40401, "message": "员工不存在", "data": None}
    return success(None)

@router.get("/{employee_id}/attachments")
async def list_attachments(employee_id: str, db=Depends(get_db), current_user=Depends(require_permission('employee:private'))):
    return success(await AttachmentService(db).list_attachments("employee", UUID(employee_id)))

@router.post("/{employee_id}/attachments")
async def upload_attachment(employee_id: str, file: UploadFile = File(...), category: str|None=None, remark: str|None=None, db=Depends(get_db), current_user=Depends(require_all_permissions('employee:manage', 'employee:private'))):
    upload_dir=settings.LOCAL_UPLOAD_DIR; date_dir=datetime.now(timezone.utc).strftime("%Y%m"); dest_dir=f"{upload_dir}/{date_dir}"
    os.makedirs(dest_dir, exist_ok=True)
    ext = file.filename.rsplit(".",1)[1] if file.filename and "." in file.filename else ""
    fn = f"{_uuid.uuid4().hex}.{ext}"; fp = f"{dest_dir}/{fn}"
    if ext.lower() not in {"pdf", "jpg", "jpeg", "png", "webp", "doc", "docx", "xls", "xlsx", "txt"}:
        raise HTTPException(400, "不支持此附件格式，请使用常用文档或图片格式")
    c = await file.read(20 * 1024 * 1024 + 1)
    if len(c) > 20 * 1024 * 1024:
        raise HTTPException(400, "附件不能超过20MB")
    from app.core.file_security import validate_attachment_content
    validate_attachment_content(file.filename, c)
    with open(fp,"wb") as f: f.write(c)
    att = await AttachmentService(db).add_attachment("employee", UUID(employee_id),
        {"filename": file.filename or fn, "file_path": f"{date_dir}/{fn}", "file_size": len(c), "file_type": file.content_type, "category": category, "remark": remark}, uploaded_by=current_user.id)
    return success(att)

@router.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str, db=Depends(get_db), current_user=Depends(require_all_permissions('employee:manage', 'employee:private'))):
    attachment = await db.get(Attachment, UUID(attachment_id))
    if attachment and attachment.related_type != "employee":
        raise HTTPException(403, "只能删除员工档案附件")
    if not await AttachmentService(db).delete_attachment(UUID(attachment_id)): return {"code": 40401, "message": "附件不存在", "data": None}
    return success(None)
