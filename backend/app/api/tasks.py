import os
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.file_security import confined_path, safe_upload_name
from app.core.permissions import (
    PERM_DESIGN_TASK_CHANGE_STATUS,
    PERM_DESIGN_TASK_CREATE,
    PERM_DESIGN_TASK_ASSIGN,
    PERM_DESIGN_TASK_DELETE,
    PERM_DESIGN_TASK_LIST,
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_UPDATE,
    PERM_INSTALLATION_TASK_CHANGE_STATUS,
    PERM_INSTALLATION_TASK_CREATE,
    PERM_INSTALLATION_TASK_ASSIGN,
    PERM_INSTALLATION_TASK_DELETE,
    PERM_INSTALLATION_TASK_LIST,
    PERM_INSTALLATION_TASK_READ,
    PERM_INSTALLATION_TASK_UPDATE,
    PERM_ORDER_READ,
    PERM_PRODUCTION_TASK_CHANGE_STATUS,
    PERM_PRODUCTION_TASK_CREATE,
    PERM_PRODUCTION_TASK_ASSIGN,
    PERM_PRODUCTION_TASK_DELETE,
    PERM_PRODUCTION_TASK_LIST,
    PERM_PRODUCTION_TASK_READ,
    PERM_PRODUCTION_TASK_UPDATE,
    PERM_TASK_COMPLETION_READ,
    PERM_TASK_QUEUE_READ,
    require_permission,
    user_has_permission as _user_has_permission,
)
from app.models.user import User
from app.models.task import Attachment, DesignTask, InstallationTask, ProductionTask
from app.schemas.common import success, success_paginated
from app.schemas.task import (
    DesignTaskCreate,
    DesignTaskUpdate,
    InstallationTaskCreate,
    InstallationTaskUpdate,
    ProductionTaskCreate,
    ProductionTaskUpdate,
    TaskAssigneeUpdate,
    TaskItemAssigneeUpdate,
    TaskStatusChange,
    TaskType,
)
from app.services.task_queue_service import list_task_queue
from app.services.completed_project_board_service import (
    CompletedProjectBoardService,
    CompletedProjectNotFound,
)
from app.services.task_service import (
    DesignTaskService,
    InstallationTaskService,
    ProductionTaskService,
    get_task_order_item_options,
)
from app.services.order_task_assignment_service import list_task_assignee_options, get_visible_task
from app.services.operation_log_service import ACTION_CREATE, OBJ_ORDER, log_operation
from app.services.order_task_attachment_service import (
    OrderTaskAttachmentService,
    serialize_order_task_attachment,
)


def _ensure_uuid(s: str):
    return _uuid.UUID(s)


INSTALLATION_PHOTO_MAX_BYTES = 10 * 1024 * 1024
INSTALLATION_VIDEO_MAX_BYTES = 45 * 1024 * 1024
TASK_ATTACHMENT_IMAGE_MAX_BYTES = 10 * 1024 * 1024
TASK_ATTACHMENT_FILE_MAX_BYTES = 45 * 1024 * 1024
_INSTALLATION_PHOTO_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "image/webp": (b"RIFF", ".webp"),
}
_INSTALLATION_VIDEO_TYPES = {
    "video/mp4": (".mp4", "ftyp"),
    "video/quicktime": (".mov", "ftyp"),
    "video/webm": (".webm", "ebml"),
}

_TASK_ATTACHMENT_RULES = {
    ".jpg": {"extension": ".jpg", "category": "image", "mime_types": {"image/jpeg"}},
    ".jpeg": {"extension": ".jpg", "category": "image", "mime_types": {"image/jpeg"}},
    ".png": {"extension": ".png", "category": "image", "mime_types": {"image/png"}},
    ".webp": {"extension": ".webp", "category": "image", "mime_types": {"image/webp"}},
    ".mp4": {"extension": ".mp4", "category": "video", "mime_types": {"video/mp4"}},
    ".webm": {"extension": ".webm", "category": "video", "mime_types": {"video/webm"}},
    ".mov": {"extension": ".mov", "category": "video", "mime_types": {"video/quicktime"}},
    ".pdf": {"extension": ".pdf", "category": "pdf", "mime_types": {"application/pdf"}},
    ".doc": {"extension": ".doc", "category": "document", "mime_types": {"application/msword"}, "signature": "ole"},
    ".docx": {
        "extension": ".docx",
        "category": "document",
        "mime_types": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        "signature": "zip",
    },
    ".xls": {"extension": ".xls", "category": "document", "mime_types": {"application/vnd.ms-excel"}, "signature": "ole"},
    ".xlsx": {
        "extension": ".xlsx",
        "category": "document",
        "mime_types": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        "signature": "zip",
    },
    ".dwg": {
        "extension": ".dwg",
        "category": "cad",
        "mime_types": {"application/acad", "application/x-acad", "image/vnd.dwg", "application/octet-stream"},
        "signature": "dwg",
    },
    ".dxf": {
        "extension": ".dxf",
        "category": "cad",
        "mime_types": {"application/dxf", "image/vnd.dxf", "text/plain", "application/octet-stream"},
        "signature": "dxf",
    },
    ".zip": {
        "extension": ".zip",
        "category": "archive",
        "mime_types": {"application/zip", "application/x-zip-compressed", "application/octet-stream"},
        "signature": "zip",
    },
    ".rar": {
        "extension": ".rar",
        "category": "archive",
        "mime_types": {"application/vnd.rar", "application/x-rar-compressed", "application/octet-stream"},
        "signature": "rar",
    },
    ".7z": {
        "extension": ".7z",
        "category": "archive",
        "mime_types": {"application/x-7z-compressed", "application/octet-stream"},
        "signature": "7z",
    },
}
_TASK_ATTACHMENT_IMAGE_SIGNATURES = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
}
_TASK_ATTACHMENT_WEBP_SIGNATURE = b"RIFF"
_TASK_ATTACHMENT_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_TASK_ATTACHMENT_TASK_MODELS = {
    "design_task": DesignTask,
    "production_task": ProductionTask,
    "installation_task": InstallationTask,
}
_TASK_ATTACHMENT_PERMISSIONS = {
    "design_task": PERM_DESIGN_TASK_UPDATE,
    "production_task": PERM_PRODUCTION_TASK_UPDATE,
    "installation_task": PERM_INSTALLATION_TASK_UPDATE,
}


class AttachmentService:
    """Compatibility writer for the legacy ``/attachments/upload`` adapter.

    The old route still receives a task id from older clients, but it writes
    the same order-owned row as the canonical order endpoint.  Keeping this
    small compatibility surface also lets older integrations finish their
    release window without restoring task-owned persistence.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_attachment(
        self,
        related_type: str,
        related_id,
        data: dict,
        uploaded_by=None,
        uploaded_by_name: str | None = None,
    ) -> dict:
        del related_type
        values = dict(data)
        entry_task_id = values.pop("entry_task_id", None)
        order_id = values.get("order_id") or related_id
        values.update(
            {
                "related_type": "order_stage",
                "related_id": order_id,
                "order_id": order_id,
            }
        )
        attachment = Attachment(
            **values,
            uploaded_by=uploaded_by,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(attachment)
        await self.db.flush()
        await log_operation(
            self.db,
            uploaded_by,
            uploaded_by_name,
            OBJ_ORDER,
            order_id,
            ACTION_CREATE,
            after_data={
                "attachment_id": str(attachment.id),
                "stage": values.get("stage"),
                "entry_task_id": str(entry_task_id) if entry_task_id else None,
                "filename": attachment.filename,
                "file_size": attachment.file_size,
                "file_type": attachment.file_type,
                "category": attachment.category,
            },
        )
        return serialize_order_task_attachment(
            attachment,
            uploaded_by_name=uploaded_by_name,
        )


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


def validate_installation_media(
    content_type: str | None, contents: bytes
) -> tuple[str | None, str | None, str | None]:
    """Validate an installation image or video and return its safe category/extension."""
    if content_type in _INSTALLATION_PHOTO_TYPES:
        message, extension = validate_installation_photo(content_type, contents)
        return message, extension, None if message else "photo"

    video_type = _INSTALLATION_VIDEO_TYPES.get(content_type or "")
    if video_type is None:
        return "现场媒体仅支持 JPG、PNG、WEBP、MP4、WEBM 或 MOV 文件", None, None
    if len(contents) > INSTALLATION_VIDEO_MAX_BYTES:
        return "单个现场视频不能超过 45MB", None, None

    extension, signature = video_type
    if signature == "ftyp":
        is_valid_signature = len(contents) >= 12 and contents[4:8] == b"ftyp"
    else:
        is_valid_signature = contents.startswith(b"\x1a\x45\xdf\xa3")
    if not is_valid_signature:
        return "上传的文件不是有效视频，请重新选择", None, None
    return None, extension, "video"


def validate_task_attachment(
    filename: str | None, content_type: str | None, contents: bytes
) -> tuple[str | None, str | None, str | None]:
    """Validate a design/production task attachment and return safe metadata."""
    extension = Path(filename or "").suffix.lower()
    rule = _TASK_ATTACHMENT_RULES.get(extension)
    if rule is None:
        return "任务附件仅支持 JPG、PNG、WEBP、视频、PDF、Word、Excel、CAD 或压缩包", None, None

    category = rule["category"]
    max_bytes = TASK_ATTACHMENT_IMAGE_MAX_BYTES if category == "image" else TASK_ATTACHMENT_FILE_MAX_BYTES
    if len(contents) > max_bytes:
        limit_label = "10MB" if category == "image" else "45MB"
        return f"{('图片' if category == 'image' else '附件')}不能超过 {limit_label}", None, None

    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    allowed_types = rule["mime_types"]
    if normalized_type and normalized_type not in allowed_types and normalized_type != "application/octet-stream":
        return "文件类型与扩展名不匹配，请重新选择", None, None

    signature = rule.get("signature")
    is_valid_signature = True
    if category == "image":
        if extension == ".webp":
            is_valid_signature = len(contents) >= 12 and contents.startswith(_TASK_ATTACHMENT_WEBP_SIGNATURE) and contents[8:12] == b"WEBP"
        else:
            is_valid_signature = contents.startswith(_TASK_ATTACHMENT_IMAGE_SIGNATURES[extension])
    elif category == "video":
        if extension == ".webm":
            is_valid_signature = contents.startswith(b"\x1a\x45\xdf\xa3")
        else:
            is_valid_signature = len(contents) >= 12 and contents[4:8] == b"ftyp"
    elif extension == ".pdf":
        is_valid_signature = contents.startswith(b"%PDF-")
    elif signature == "ole":
        is_valid_signature = contents.startswith(_TASK_ATTACHMENT_OLE_SIGNATURE)
    elif signature == "zip":
        is_valid_signature = contents.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
    elif signature == "rar":
        is_valid_signature = contents.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"))
    elif signature == "7z":
        is_valid_signature = contents.startswith(b"7z\xbc\xaf\x27\x1c")
    elif signature == "dwg":
        is_valid_signature = contents.startswith(b"AC10")
    elif signature == "dxf":
        is_valid_signature = bool(contents.strip())

    if not is_valid_signature:
        label = "图片" if category == "image" else "视频" if category == "video" else "文件"
        return f"上传的文件不是有效{label}，请重新选择", None, None
    return None, rule["extension"], category


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
    current_user: User = Depends(require_permission(PERM_TASK_QUEUE_READ)),
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
        viewer=current_user,
    )
    return success_paginated(tasks, total, page, page_size)


@queue_router.get("/completed-projects")
async def list_completed_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=200),
    stage: TaskType | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_TASK_COMPLETION_READ)),
):
    """Return the current viewer's authorized completed project cards."""
    service = CompletedProjectBoardService(db, current_user)
    projects, total = await service.get_projects(
        page=page,
        page_size=page_size,
        stage=stage,
    )
    return success_paginated(projects, total, page, page_size)


@queue_router.get("/completed-projects/{project_id}")
async def get_completed_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_TASK_COMPLETION_READ)),
):
    """Return a read-only, permission-trimmed completed project detail."""
    service = CompletedProjectBoardService(db, current_user)
    try:
        project = await service.get_project(_ensure_uuid(project_id))
    except CompletedProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return success(project)


@queue_router.get("/order-item-options")
async def list_task_order_item_options(
    task_type: TaskType = Query(...),
    task_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_TASK_QUEUE_READ)),
):
    """返回任务处理页的订单明细阶段与可选性。"""
    if not _user_has_permission(current_user, _TASK_READ_PERMISSIONS[task_type]):
        raise HTTPException(
            status_code=403,
            detail=f"当前账号没有{_TASK_LABELS[task_type]}任务详情查看权限",
        )
    try:
        options = await get_task_order_item_options(
            db,
            task_type,
            _ensure_uuid(task_id),
            viewer=current_user,
        )
        return success(options)
    except ValueError as exc:
        return {"code": 40001, "message": str(exc), "data": None}


_TASK_ASSIGN_PERMISSIONS = {
    "design": PERM_DESIGN_TASK_ASSIGN,
    "production": PERM_PRODUCTION_TASK_ASSIGN,
    "installation": PERM_INSTALLATION_TASK_ASSIGN,
}

_TASK_READ_PERMISSIONS = {
    "design": PERM_DESIGN_TASK_READ,
    "production": PERM_PRODUCTION_TASK_READ,
    "installation": PERM_INSTALLATION_TASK_READ,
}

_TASK_LABELS = {
    "design": "设计",
    "production": "制作",
    "installation": "安装",
}


@queue_router.get("/assignee-options")
async def list_task_assignee_options_route(
    task_type: TaskType = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return assignable employees only to users who can assign this stage."""
    permission = _TASK_ASSIGN_PERMISSIONS[task_type]
    if not _user_has_permission(current_user, permission):
        raise HTTPException(status_code=403, detail="没有该阶段的任务分配权限")
    return success(await list_task_assignee_options(db))


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
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_LIST)),
):
    service = DesignTaskService(db, current_user)
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
    service = DesignTaskService(db, current_user)
    task = await service.create_task(data.model_dump(exclude_none=True), current_user.id)
    return success(task)


@design_router.get("/{task_id}")
async def get_design_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_READ)),
):
    service = DesignTaskService(db, current_user)
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
    service = DesignTaskService(db, current_user)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_unset=True), current_user.id)
    return success(task)


@design_router.put("/{task_id}/assignee")
async def assign_design_task(
    task_id: str,
    data: TaskAssigneeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_ASSIGN)),
):
    raise ValueError("整张设计任务负责人已停用，请在订单上设置可见员工，或在任务处理卡中改派订单明细")


@design_router.put("/{task_id}/order-item-assignees")
async def reassign_design_task_items(
    task_id: str,
    data: TaskItemAssigneeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_ASSIGN)),
):
    service = DesignTaskService(db, current_user)
    task = await service.reassign_items(
        _ensure_uuid(task_id),
        data.order_item_ids,
        data.assignee_user_id,
        current_user.id,
    )
    return success(task)


@design_router.delete("/{task_id}")
async def delete_design_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DESIGN_TASK_DELETE)),
):
    service = DesignTaskService(db, current_user)
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
    service = DesignTaskService(db, current_user)
    task = await service.change_status(
        _ensure_uuid(task_id),
        data.to_status,
        current_user.id,
        data.reason,
        data.order_item_ids,
        assigned_to=data.assigned_to,
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
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_LIST)),
):
    service = ProductionTaskService(db, current_user)
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
    service = ProductionTaskService(db, current_user)
    task = await service.create_task(data.model_dump(exclude_none=True), current_user.id)
    return success(task)


@prod_router.get("/{task_id}")
async def get_production_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_READ)),
):
    service = ProductionTaskService(db, current_user)
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
    service = ProductionTaskService(db, current_user)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_unset=True), current_user.id)
    return success(task)


@prod_router.put("/{task_id}/assignee")
async def assign_production_task(
    task_id: str,
    data: TaskAssigneeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_ASSIGN)),
):
    raise ValueError("整张制作任务负责人已停用，请在订单上设置可见员工，或在任务处理卡中改派订单明细")


@prod_router.put("/{task_id}/order-item-assignees")
async def reassign_production_task_items(
    task_id: str,
    data: TaskItemAssigneeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_ASSIGN)),
):
    service = ProductionTaskService(db, current_user)
    task = await service.reassign_items(
        _ensure_uuid(task_id),
        data.order_item_ids,
        data.assignee_user_id,
        current_user.id,
    )
    return success(task)


@prod_router.delete("/{task_id}")
async def delete_production_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_PRODUCTION_TASK_DELETE)),
):
    service = ProductionTaskService(db, current_user)
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
    service = ProductionTaskService(db, current_user)
    task = await service.change_status(
        _ensure_uuid(task_id),
        data.to_status,
        current_user.id,
        data.reason,
        data.order_item_ids,
        assigned_to=data.assigned_to,
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
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_LIST)),
):
    service = InstallationTaskService(db, current_user)
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
    service = InstallationTaskService(db, current_user)
    task = await service.create_task(data.model_dump(exclude_none=True), current_user.id)
    return success(task)


@inst_router.get("/{task_id}")
async def get_installation_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_READ)),
):
    service = InstallationTaskService(db, current_user)
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
    service = InstallationTaskService(db, current_user)
    task = await service.update_task(_ensure_uuid(task_id), data.model_dump(exclude_unset=True), current_user.id)
    return success(task)


@inst_router.put("/{task_id}/assignee")
async def assign_installation_task(
    task_id: str,
    data: TaskAssigneeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_ASSIGN)),
):
    raise ValueError("整张安装任务负责人已停用，请在订单上设置可见员工，或在任务处理卡中改派订单明细")


@inst_router.put("/{task_id}/order-item-assignees")
async def reassign_installation_task_items(
    task_id: str,
    data: TaskItemAssigneeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_ASSIGN)),
):
    service = InstallationTaskService(db, current_user)
    task = await service.reassign_items(
        _ensure_uuid(task_id),
        data.order_item_ids,
        data.assignee_user_id,
        current_user.id,
    )
    return success(task)


@inst_router.delete("/{task_id}")
async def delete_installation_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_INSTALLATION_TASK_DELETE)),
):
    service = InstallationTaskService(db, current_user)
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
    service = InstallationTaskService(db, current_user)
    task = await service.change_status(
        _ensure_uuid(task_id),
        data.to_status,
        current_user.id,
        data.reason,
        data.order_item_ids,
        assigned_to=data.assigned_to,
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
    task_model = _TASK_ATTACHMENT_TASK_MODELS.get(related_type)
    stage = {
        "design_task": "design",
        "production_task": "production",
        "installation_task": "installation",
    }.get(related_type)
    if stage is None or task_model is None:
        return {"code": 40001, "message": "附件关联任务类型无效", "data": None}
    exact_permission = _TASK_ATTACHMENT_PERMISSIONS[related_type]
    if not _user_has_permission(current_user, exact_permission):
        raise HTTPException(status_code=403, detail="没有该附件关联对象的上传权限")

    try:
        related_uuid = _ensure_uuid(related_id)
    except ValueError:
        return {"code": 40001, "message": "任务编号无效", "data": None}
    task = await get_visible_task(db, task_model, related_uuid, current_user)
    if task is None:
        return {"code": 40401, "message": "关联任务不存在或当前账号无权查看", "data": None}
    order_id = getattr(task, "document_id", None) or related_uuid
    uploader_name = getattr(current_user, "real_name", None) or getattr(
        current_user,
        "username",
        None,
    )
    contents = await file.read()
    if stage == "installation":
        message, safe_extension, category = validate_installation_media(
            file.content_type,
            contents,
        )
    else:
        message, safe_extension, category = validate_task_attachment(
            file.filename,
            file.content_type,
            contents,
        )
    if message:
        return {"code": 40001, "message": message, "data": None}

    date_dir = datetime.now(timezone.utc).strftime("%Y%m")
    dest_dir = Path(settings.LOCAL_UPLOAD_DIR) / date_dir
    dest_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
    os.chmod(dest_dir, 0o750)
    unique_name = f"{uuid4().hex}{safe_extension or ''}"
    stored_path = dest_dir / unique_name
    relative_path = f"{date_dir}/{unique_name}"
    _, display_name = safe_upload_name(file.filename, "attachment")

    try:
        with stored_path.open("wb") as output:
            output.write(contents)
        os.chmod(stored_path, 0o640)
        att = await AttachmentService(db).add_attachment(
            "order_stage",
            order_id,
            data={
                "order_id": order_id,
                "stage": stage,
                "filename": display_name or unique_name,
                "file_path": relative_path,
                "file_size": len(contents),
                "file_type": file.content_type,
                "category": category,
                "entry_task_id": related_uuid,
            },
            uploaded_by=current_user.id,
            uploaded_by_name=uploader_name,
        )
        return success(att)
    except PermissionError as exc:
        if stored_path.is_file():
            stored_path.unlink()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        if stored_path.is_file():
            stored_path.unlink()
        await db.rollback()
        return {"code": 40001, "message": str(exc), "data": None}
    except Exception:
        if stored_path.is_file():
            stored_path.unlink()
        raise


@att_router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        attachment_uuid = _ensure_uuid(attachment_id)
    except ValueError:
        return {"code": 40001, "message": "附件编号无效", "data": None}
    attachment = await db.get(Attachment, attachment_uuid)
    if attachment is None:
        return {"code": 40401, "message": "附件不存在", "data": None}
    service = OrderTaskAttachmentService(db)
    if attachment.related_type == "order_stage":
        if not _user_has_permission(current_user, PERM_ORDER_READ):
            raise HTTPException(
                status_code=403,
                detail="该订单资料已统一由订单资料接口管理，请从订单或对应任务详情进入",
            )
        order_id = attachment.order_id
        stage = attachment.stage
        task_id = None
    else:
        stage = {
            "design_task": "design",
            "production_task": "production",
            "installation_task": "installation",
        }.get(attachment.related_type)
        task_model = _TASK_ATTACHMENT_TASK_MODELS.get(attachment.related_type)
        if stage is None or task_model is None:
            return {"code": 40001, "message": "附件关联任务类型无效", "data": None}
        permission = _TASK_ATTACHMENT_PERMISSIONS[attachment.related_type]
        if not _user_has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail="没有该附件关联对象的删除权限")
        related_id = getattr(attachment, "related_id", None)
        if related_id is None:
            return {"code": 40401, "message": "附件归属信息不存在", "data": None}
        visible_task = await get_visible_task(
            db, task_model, related_id, current_user
        )
        if visible_task is None:
            return {"code": 40401, "message": "附件关联任务不存在或当前账号无权查看", "data": None}
        order_id = visible_task.document_id
        task_id = related_id

    if not order_id or not stage:
        return {"code": 40401, "message": "附件归属信息不存在", "data": None}
    try:
        _, relative_path = await service.delete(
            order_id,
            attachment_uuid,
            current_user.id,
            current_user.real_name or current_user.username,
            stage=stage,
            task_id=task_id,
            viewer=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        return {"code": 40401, "message": str(exc), "data": None}
    try:
        stored_path = confined_path(settings.LOCAL_UPLOAD_DIR, relative_path)
        if os.path.isfile(stored_path):
            os.remove(stored_path)
    except HTTPException:
        # The database record is already removed; do not expose a server path.
        pass
    return success(None)
