import os
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.schemas.task import (
    DesignTaskCreate, DesignTaskUpdate,
    ProductionTaskCreate, ProductionTaskUpdate,
    InstallationTaskCreate, InstallationTaskUpdate,
    TaskStatusChange,
)
from app.services.task_service import (
    DesignTaskService,
    ProductionTaskService,
    InstallationTaskService,
    AttachmentService,
)


def _ensure_uuid(s: str):
    return _uuid.UUID(s)


# -- Design Tasks --

design_router = APIRouter(prefix="/design-tasks", tags=["Design Tasks"])


@design_router.get("/")
async def list_design_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    order_id: str | None = None,
    assigned_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DesignTaskService(db)
    tasks, total = await service.list_tasks(page, page_size, status, order_id, assigned_to)
    return success_paginated(tasks, total, page, page_size)


@design_router.post("/")
async def create_design_task(
    data: DesignTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DesignTaskService(db)
    task = await service.create_task(data.model_dump())
    return success(task)


@design_router.get("/{task_id}")
async def get_design_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    service = DesignTaskService(db)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_none=True))
    return success(task)


@design_router.post("/{task_id}/change-status")
async def change_design_task_status(
    task_id: str,
    data: TaskStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DesignTaskService(db)
    task = await service.change_status(_ensure_uuid(task_id), data.to_status, current_user.id)
    return success(task)


# -- Production Tasks --

prod_router = APIRouter(prefix="/production-tasks", tags=["Production Tasks"])


@prod_router.get("/")
async def list_production_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    order_id: str | None = None,
    assigned_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductionTaskService(db)
    tasks, total = await service.list_tasks(page, page_size, status, order_id, assigned_to)
    return success_paginated(tasks, total, page, page_size)


@prod_router.post("/")
async def create_production_task(
    data: ProductionTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductionTaskService(db)
    task = await service.create_task(data.model_dump())
    return success(task)


@prod_router.get("/{task_id}")
async def get_production_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    service = ProductionTaskService(db)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_none=True))
    return success(task)


@prod_router.post("/{task_id}/change-status")
async def change_production_task_status(
    task_id: str,
    data: TaskStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductionTaskService(db)
    task = await service.change_status(_ensure_uuid(task_id), data.to_status, current_user.id)
    return success(task)


# -- Installation Tasks --

inst_router = APIRouter(prefix="/installation-tasks", tags=["Installation Tasks"])


@inst_router.get("/")
async def list_installation_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    order_id: str | None = None,
    assigned_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InstallationTaskService(db)
    tasks, total = await service.list_tasks(page, page_size, status, order_id, assigned_to)
    return success_paginated(tasks, total, page, page_size)


@inst_router.post("/")
async def create_installation_task(
    data: InstallationTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InstallationTaskService(db)
    task = await service.create_task(data.model_dump())
    return success(task)


@inst_router.get("/{task_id}")
async def get_installation_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    service = InstallationTaskService(db)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_none=True))
    return success(task)


@inst_router.post("/{task_id}/change-status")
async def change_installation_task_status(
    task_id: str,
    data: TaskStatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InstallationTaskService(db)
    task = await service.change_status(_ensure_uuid(task_id), data.to_status, current_user.id)
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
    current_user: User = Depends(get_current_user),
):
    service = AttachmentService(db)
    ok = await service.delete_attachment(_ensure_uuid(attachment_id))
    if not ok:
        return {"code": 40401, "message": "附件不存在", "data": None}
    return success(None)
