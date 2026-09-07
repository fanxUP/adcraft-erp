import os
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
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
from app.schemas.common import success, success_paginated
from app.schemas.task import (
    DesignTaskCreate, DesignTaskUpdate,
    ProductionTaskCreate, ProductionTaskUpdate,
    InstallationTaskCreate, InstallationTaskUpdate,
    TaskStatusChange, TaskType,
)
from app.services.task_service import (
    DesignTaskService,
    ProductionTaskService,
    InstallationTaskService,
    AttachmentService,
    get_task_order_item_options,
)
from app.services.task_queue_service import list_task_queue
from app.services.task_history_service import list_task_history, task_exists


def _ensure_uuid(s: str):
    return _uuid.UUID(s)


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


# -- Task change history --

history_router = APIRouter(prefix="/task-history", tags=["Task History"])
HISTORY_READ_PERMISSIONS = {
    "design": PERM_DESIGN_TASK_READ,
    "production": PERM_PRODUCTION_TASK_READ,
    "installation": PERM_INSTALLATION_TASK_READ,
}


@history_router.get("/")
async def get_task_history(
    task_type: str = Query(...),
    task_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(
        PERM_DESIGN_TASK_READ,
        PERM_PRODUCTION_TASK_READ,
        PERM_INSTALLATION_TASK_READ,
    )),
):
    required_permission = HISTORY_READ_PERMISSIONS.get(task_type)
    if not required_permission:
        return {"code": 40001, "message": f"不支持的任务类型: {task_type}", "data": None}
    granted_permissions = {
        permission.code
        for role in current_user.roles
        for permission in role.permissions
    }
    if required_permission not in granted_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要「{required_permission}」权限",
        )
    try:
        task_uuid = _ensure_uuid(task_id)
        exists = await task_exists(db, task_type, task_uuid)
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}
    if not exists:
        return {"code": 40401, "message": "任务不存在", "data": None}

    items, total = await list_task_history(
        db,
        task_type,
        task_uuid,
        page=page,
        page_size=page_size,
    )
    return success_paginated(items, total, page, page_size)


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
    task = await service.create_task(data.model_dump(), current_user.id)
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
    task = await service.create_task(data.model_dump(), current_user.id)
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
    task = await service.create_task(data.model_dump(), current_user.id)
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
    current_user: User = Depends(require_any_permission(
        PERM_DESIGN_TASK_UPDATE,
        PERM_PRODUCTION_TASK_UPDATE,
        PERM_INSTALLATION_TASK_UPDATE,
    )),
):
    upload_dir = settings.LOCAL_UPLOAD_DIR
    date_dir = datetime.now(timezone.utc).strftime("%Y%m")
    dest_dir = os.path.join(upload_dir, date_dir)
    os.makedirs(dest_dir, exist_ok=True)

    ext = ""
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[1]
    unique_name = f"{_uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(dest_dir, unique_name)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    service = AttachmentService(db)
    att = await service.add_attachment(
        related_type=related_type,
        related_id=_ensure_uuid(related_id),
        data={
            "filename": file.filename or unique_name,
            "file_path": f"{date_dir}/{unique_name}",
            "file_size": len(contents),
            "file_type": file.content_type,
            "category": category,
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
