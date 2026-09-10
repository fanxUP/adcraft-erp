import os
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import (
    PERM_DESIGN_TASK_CHANGE_STATUS,
    PERM_DESIGN_TASK_CREATE,
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_UPDATE,
    PERM_INSTALLATION_TASK_CHANGE_STATUS,
    PERM_INSTALLATION_TASK_CREATE,
    PERM_INSTALLATION_TASK_READ,
    PERM_INSTALLATION_TASK_UPDATE,
    PERM_PRODUCTION_TASK_CHANGE_STATUS,
    PERM_PRODUCTION_TASK_CREATE,
    PERM_PRODUCTION_TASK_READ,
    PERM_PRODUCTION_TASK_UPDATE,
    require_any_permission,
    require_permission,
    require_role,
)
from app.models.user import User
from app.models.task import InstallationTask
from app.schemas.common import success, success_paginated
from app.schemas.task import (
    DesignTaskCreate,
    DesignTaskUpdate,
    InstallationTaskCreate,
    InstallationTaskUpdate,
    ProductionTaskCreate,
    ProductionTaskUpdate,
    TaskStatusChange,
    TaskType,
)
from app.services.task_queue_service import list_task_queue
from app.services.task_service import (
    AttachmentService,
    DesignTaskService,
    InstallationTaskService,
    ProductionTaskService,
    get_task_order_item_options,
)


def _ensure_uuid(s: str):
    return _uuid.UUID(s)


INSTALLATION_PHOTO_MAX_BYTES = 10 * 1024 * 1024
UPLOAD_DIRECTORY_MODE = 0o750
UPLOAD_FILE_MODE = 0o640
_INSTALLATION_PHOTO_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "image/webp": (b"RIFF", ".webp"),
}


def validate_installation_photo(content_type: str | None, contents: bytes) -> tuple[str | None, str | None]:
    """Validate an installation photo and return a safe extension for storage."""
    photo_type = _INSTALLATION_PHOTO_TYPES.get(content_type or "")
    if photo_type is None:
        return "现场照片仅支持 JPG、PNG 或 WEBP 图片", None
    if len(contents) > INSTALLATION_PHOTO_MAX_BYTES:
        return "单张现场照片不能超过 10MB", None

    signature, extension = photo_type
    if content_type == "image/webp":
        is_valid_signature = len(contents) >= 12 and contents.startswith(signature) and contents[8:12] == b"WEBP"
    else:
        is_valid_signature = contents.startswith(signature)
    if not is_valid_signature:
        return "上传的文件不是有效图片，请重新选择", None
    return None, extension


def _user_has_permission(user: User, permission_code: str) -> bool:
    return any(
        permission.code == permission_code
        for role in user.roles
        for permission in role.permissions
    )


# -- Unified project task queue --

queue_router = APIRouter(prefix="/task-queue", tags=["Task Queue"])


@queue_router.get("/")
async def list_project_task_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    stage: str | None = None,
    status: str | None = None,
    order_id: str | None = None,
    order_item_id: str | None = None,
    overdue: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(
        PERM_DESIGN_TASK_READ,
        PERM_PRODUCTION_TASK_READ,
        PERM_INSTALLATION_TASK_READ,
    )),
):
    tasks, total = await list_task_queue(
        db,
        page=page,
        page_size=page_size,
        stage=stage,
        status=status,
        order_id=order_id,
        order_item_id=order_item_id,
        overdue=overdue,
    )
    return success_paginated(tasks, total, page, page_size)


@queue_router.get("/order-item-options")
async def list_task_order_item_options(
    task_type: TaskType = Query(...),
    task_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(
        PERM_DESIGN_TASK_READ,
        PERM_PRODUCTION_TASK_READ,
        PERM_INSTALLATION_TASK_READ,
    )),
):
    """返回任务处理页的订单明细阶段与可选性。"""
    try:
        options = await get_task_order_item_options(
            db,
            task_type,
            _ensure_uuid(task_id),
        )
        return success(options)
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}


# -- Design Tasks --

design_router = APIRouter(prefix="/design-tasks", tags=["Design Tasks"])


@design_router.get("/")
async def list_design_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    order_id: str | None = None,
    order_item_id: str | None = None,
    assigned_to: str | None = None,
    outsourced: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_READ)),
):
    service = DesignTaskService(db)
    tasks, total = await service.list_tasks(
        page, page_size, status, order_id, assigned_to, outsourced, order_item_id
    )
    return success_paginated(tasks, total, page, page_size)


@design_router.post("/")
async def create_design_task(
    data: DesignTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_CREATE)),
):
    service = DesignTaskService(db)
    task = await service.create_task(data.model_dump(exclude_none=True), current_user.id)
    return success(task)


@design_router.get("/{task_id}")
async def get_design_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_READ)),
):
    service = DesignTaskService(db)
    task = await service.get_task(_ensure_uuid(task_id))
    if not task:
        return {"code": 40401, "message": "设计任务不存在", "data": None}
    return success(task)


@design_router.put("/{task_id}")
async def update_design_task(
    task_id: str,
    data: DesignTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_UPDATE)),
):
    service = DesignTaskService(db)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_unset=True), current_user.id)
    return success(task)


@design_router.delete("/{task_id}")
async def delete_design_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = DesignTaskService(db)
    try:
        await service.delete_task(_ensure_uuid(task_id))
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@design_router.post("/{task_id}/change-status")
async def change_design_task_status(
    task_id: str,
    data: TaskStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_CHANGE_STATUS)),
):
    service = DesignTaskService(db)
    task = await service.change_status(
        _ensure_uuid(task_id), data.to_status, current_user.id, data.reason, data.order_item_ids
    )
    return success(task)


# -- Production Tasks --

prod_router = APIRouter(prefix="/production-tasks", tags=["Production Tasks"])


@prod_router.get("/")
async def list_production_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    order_id: str | None = None,
    order_item_id: str | None = None,
    assigned_to: str | None = None,
    outsourced: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_READ)),
):
    service = ProductionTaskService(db)
    tasks, total = await service.list_tasks(
        page, page_size, status, order_id, assigned_to, outsourced, order_item_id
    )
    return success_paginated(tasks, total, page, page_size)


@prod_router.post("/")
async def create_production_task(
    data: ProductionTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_CREATE)),
):
    service = ProductionTaskService(db)
    task = await service.create_task(data.model_dump(exclude_none=True), current_user.id)
    return success(task)


@prod_router.get("/{task_id}")
async def get_production_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_READ)),
):
    service = ProductionTaskService(db)
    task = await service.get_task(_ensure_uuid(task_id))
    if not task:
        return {"code": 40401, "message": "制作任务不存在", "data": None}
    return success(task)


@prod_router.put("/{task_id}")
async def update_production_task(
    task_id: str,
    data: ProductionTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_UPDATE)),
):
    service = ProductionTaskService(db)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_unset=True), current_user.id)
    return success(task)


@prod_router.delete("/{task_id}")
async def delete_production_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = ProductionTaskService(db)
    try:
        await service.delete_task(_ensure_uuid(task_id))
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@prod_router.post("/{task_id}/change-status")
async def change_production_task_status(
    task_id: str,
    data: TaskStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_CHANGE_STATUS)),
):
    service = ProductionTaskService(db)
    task = await service.change_status(
        _ensure_uuid(task_id), data.to_status, current_user.id, data.reason, data.order_item_ids
    )
    return success(task)


# -- Installation Tasks --

inst_router = APIRouter(prefix="/installation-tasks", tags=["Installation Tasks"])


@inst_router.get("/")
async def list_installation_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    order_id: str | None = None,
    order_item_id: str | None = None,
    assigned_to: str | None = None,
    outsourced: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_READ)),
):
    service = InstallationTaskService(db)
    tasks, total = await service.list_tasks(
        page, page_size, status, order_id, assigned_to, outsourced, order_item_id
    )
    return success_paginated(tasks, total, page, page_size)


@inst_router.post("/")
async def create_installation_task(
    data: InstallationTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_CREATE)),
):
    service = InstallationTaskService(db)
    task = await service.create_task(data.model_dump(exclude_none=True), current_user.id)
    return success(task)


@inst_router.get("/{task_id}")
async def get_installation_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_READ)),
):
    service = InstallationTaskService(db)
    task = await service.get_task(_ensure_uuid(task_id))
    if not task:
        return {"code": 40401, "message": "安装任务不存在", "data": None}
    return success(task)


@inst_router.put("/{task_id}")
async def update_installation_task(
    task_id: str,
    data: InstallationTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_UPDATE)),
):
    service = InstallationTaskService(db)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_unset=True), current_user.id)
    return success(task)


@inst_router.delete("/{task_id}")
async def delete_installation_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = InstallationTaskService(db)
    try:
        await service.delete_task(_ensure_uuid(task_id))
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@inst_router.post("/{task_id}/change-status")
async def change_installation_task_status(
    task_id: str,
    data: TaskStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_CHANGE_STATUS)),
):
    service = InstallationTaskService(db)
    task = await service.change_status(
        _ensure_uuid(task_id), data.to_status, current_user.id, data.reason, data.order_item_ids
    )
    return success(task)


# -- Attachments --

att_router = APIRouter(prefix="/attachments", tags=["Attachments"])


@att_router.post("/upload")
async def upload_attachment(
    related_type: str = Query(...),
    related_id: str = Query(...),
    category: str | None = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exact_permission = {
        "design_task": PERM_DESIGN_TASK_UPDATE,
        "production_task": PERM_PRODUCTION_TASK_UPDATE,
        "installation_task": PERM_INSTALLATION_TASK_UPDATE,
    }.get(related_type)
    has_permission = (
        _user_has_permission(current_user, exact_permission)
        if exact_permission
        else any(
            _user_has_permission(current_user, permission)
            for permission in (
                PERM_DESIGN_TASK_UPDATE,
                PERM_PRODUCTION_TASK_UPDATE,
                PERM_INSTALLATION_TASK_UPDATE,
            )
        )
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="没有该附件关联对象的上传权限")

    upload_dir = settings.LOCAL_UPLOAD_DIR
    date_dir = datetime.now(timezone.utc).strftime("%Y%m")
    dest_dir = os.path.join(upload_dir, date_dir)

    safe_extension: str | None = None
    if related_type == "installation_task":
        try:
            installation_task_id = _ensure_uuid(related_id)
        except ValueError:
            return {"code": 40001, "message": "安装任务编号无效", "data": None}
        installation_task = await db.get(InstallationTask, installation_task_id)
        if installation_task is None:
            return {"code": 40401, "message": "安装任务不存在", "data": None}
    contents = await file.read()
    if related_type == "installation_task":
        message, safe_extension = validate_installation_photo(file.content_type, contents)
        if message:
            return {"code": 40001, "message": message, "data": None}

    # Nginx serves /uploads/ from the same filesystem as the backend.  The
    # production service uses a restrictive umask, so relying on the default
    # modes would create 700 directories and 600 files that Nginx cannot read.
    # Set the modes explicitly and keep the upload owner as the backend user.
    os.makedirs(dest_dir, mode=UPLOAD_DIRECTORY_MODE, exist_ok=True)
    os.chmod(dest_dir, UPLOAD_DIRECTORY_MODE)
    ext = safe_extension or ""
    if safe_extension is None and file.filename and "." in file.filename:
        candidate = file.filename.rsplit(".", 1)[1].lower()
        if candidate.isalnum() and len(candidate) <= 10:
            ext = candidate
    unique_name = f"{_uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(dest_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)
    os.chmod(file_path, UPLOAD_FILE_MODE)

    service = AttachmentService(db)
    att = await service.add_attachment(
        related_type=related_type,
        related_id=_ensure_uuid(related_id),
        data={
            "filename": file.filename or unique_name,
            "file_path": f"{date_dir}/{unique_name}",
            "file_size": len(contents),
            "file_type": file.content_type,
            "category": "photo" if related_type == "installation_task" else category,
        },
        uploaded_by=current_user.id,
    )
    return success(att)


@att_router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(
        PERM_DESIGN_TASK_UPDATE,
        PERM_PRODUCTION_TASK_UPDATE,
        PERM_INSTALLATION_TASK_UPDATE,
    )),
):
    service = AttachmentService(db)
    ok = await service.delete_attachment(_ensure_uuid(attachment_id))
    if not ok:
        return {"code": 40401, "message": "附件不存在", "data": None}
    return success(None)
