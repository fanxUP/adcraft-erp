"""Order-scoped access to design, production, and installation materials.

The existing task attachment API is intentionally task-permission scoped.  An
order detail page has a different boundary: a user who can view the order can
manage the materials belonging to that order, without receiving permissions
to list or mutate an entire task queue.  Every method below re-checks the
order -> task -> attachment relationship in the database.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.file_security import confined_path, safe_upload_name
from app.models.business_document import BusinessDocument
from app.models.task import Attachment, DesignTask, InstallationTask, ProductionTask
from app.models.user import User
from app.services.operation_log_service import (
    ACTION_CREATE,
    ACTION_DELETE,
    OBJ_DESIGN_TASK,
    OBJ_INSTALLATION_TASK,
    OBJ_PRODUCTION_TASK,
    log_operation,
)


_TASK_CONFIG = {
    "design": {
        "related_type": "design_task",
        "model": DesignTask,
        "number_field": "design_no",
        "label": "设计任务：任务附件",
        "task_label": "设计任务",
        "object_type": OBJ_DESIGN_TASK,
        "accept": (
            "image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,"
            "application/pdf,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.dwg,.dxf,.zip,.rar,.7z"
        ),
    },
    "production": {
        "related_type": "production_task",
        "model": ProductionTask,
        "number_field": "production_no",
        "label": "制作任务：任务附件",
        "task_label": "制作任务",
        "object_type": OBJ_PRODUCTION_TASK,
        "accept": (
            "image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,"
            "application/pdf,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.dwg,.dxf,.zip,.rar,.7z"
        ),
    },
    "installation": {
        "related_type": "installation_task",
        "model": InstallationTask,
        "number_field": "installation_no",
        "label": "安装任务：现场照片与视频",
        "task_label": "安装任务",
        "object_type": OBJ_INSTALLATION_TASK,
        "accept": "image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime",
    },
}

_STATUS_LABELS = {
    "pending": "待分配",
    "assigned": "已分配",
    "designing": "设计中",
    "pending_review": "待确认",
    "revision": "需修改",
    "confirmed": "已完成",
    "in_progress": "制作中",
    "rework": "返工中",
    "pending_acceptance": "待验收",
    "completed": "已完成",
    "cancelled": "已取消",
    "canceled": "已取消",
}
_CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
_ORDER_TASK_RELATED_TYPES = tuple(config["related_type"] for config in _TASK_CONFIG.values())


def _task_config(task_type: str) -> dict:
    config = _TASK_CONFIG.get(task_type)
    if config is None:
        raise ValueError("资料所属任务类型无效")
    return config


def _iso(value) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def serialize_order_task_attachment(
    attachment: Attachment,
    *,
    uploaded_by_name: str | None = None,
) -> dict:
    """Expose attachment metadata without exposing the server storage path."""

    return {
        "id": str(attachment.id),
        "related_type": attachment.related_type,
        "related_id": str(attachment.related_id),
        "filename": attachment.filename,
        "file_size": attachment.file_size,
        "file_type": attachment.file_type,
        "category": attachment.category,
        "uploaded_by": str(attachment.uploaded_by) if attachment.uploaded_by else None,
        "uploaded_by_name": uploaded_by_name,
        "remark": attachment.remark,
        "created_at": _iso(attachment.created_at),
    }


class OrderTaskAttachmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_order(self, order_id: UUID) -> BusinessDocument:
        result = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id == order_id,
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise ValueError("订单不存在")
        return order

    async def _get_task(self, order_id: UUID, task_type: str, task_id: UUID):
        config = _task_config(task_type)
        result = await self.db.execute(
            select(config["model"]).where(
                config["model"].id == task_id,
                config["model"].document_id == order_id,
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise ValueError("任务不存在或不属于该订单")
        return task, config

    @staticmethod
    def _attachment_rows_query(attachment_id: UUID, order_id: UUID):
        """Build an exact order-scoped attachment lookup.

        Attachment.related_id is polymorphic and therefore cannot use one
        foreign key.  The stage-specific subqueries make the ownership check
        explicit and prevent an attachment ID from another order being used
        through a guessed URL.
        """

        design_ids = select(DesignTask.id).where(DesignTask.document_id == order_id)
        production_ids = select(ProductionTask.id).where(ProductionTask.document_id == order_id)
        installation_ids = select(InstallationTask.id).where(InstallationTask.document_id == order_id)
        belongs_to_order = or_(
            and_(Attachment.related_type == "design_task", Attachment.related_id.in_(design_ids)),
            and_(Attachment.related_type == "production_task", Attachment.related_id.in_(production_ids)),
            and_(Attachment.related_type == "installation_task", Attachment.related_id.in_(installation_ids)),
        )
        return select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.related_type.in_(_ORDER_TASK_RELATED_TYPES),
            belongs_to_order,
        )

    async def _get_order_attachment(self, order_id: UUID, attachment_id: UUID) -> Attachment:
        await self._get_order(order_id)
        result = await self.db.execute(self._attachment_rows_query(attachment_id, order_id))
        attachment = result.scalar_one_or_none()
        if attachment is None:
            raise ValueError("附件不存在或不属于该订单")
        return attachment

    async def list_for_order(self, order_id: UUID) -> dict:
        await self._get_order(order_id)
        groups: list[dict] = []

        for task_type, config in _TASK_CONFIG.items():
            task_result = await self.db.execute(
                select(config["model"])
                .where(config["model"].document_id == order_id)
                .order_by(config["model"].created_at.asc())
            )
            tasks = []
            for task in task_result.scalars().all():
                attachment_result = await self.db.execute(
                    select(Attachment, User.real_name, User.username)
                    .outerjoin(User, User.id == Attachment.uploaded_by)
                    .where(
                        Attachment.related_type == config["related_type"],
                        Attachment.related_id == task.id,
                    )
                    .order_by(Attachment.created_at.desc())
                )
                attachments = []
                for attachment, real_name, username in attachment_result.all():
                    attachments.append(
                        serialize_order_task_attachment(
                            attachment,
                            uploaded_by_name=real_name or username,
                        )
                    )

                status = getattr(task, "status", "pending") or "pending"
                tasks.append(
                    {
                        "task_id": str(task.id),
                        "task_no": getattr(task, config["number_field"], None),
                        "status": status,
                        "status_label": _STATUS_LABELS.get(status, status),
                        "completed_at": _iso(getattr(task, "completed_at", None)),
                        "upload_allowed": status not in _CANCELLED_STATUSES,
                        "read_only_reason": "已取消的任务只能查看资料" if status in _CANCELLED_STATUSES else None,
                        "attachments": attachments,
                    }
                )

            groups.append(
                {
                    "task_type": task_type,
                    "label": config["label"],
                    "task_label": config["task_label"],
                    "accept": config["accept"],
                    "tasks": tasks,
                    "task_count": len(tasks),
                    "attachment_count": sum(len(task["attachments"]) for task in tasks),
                }
            )

        return {"order_id": str(order_id), "groups": groups}

    async def upload(
        self,
        order_id: UUID,
        task_type: str,
        task_id: UUID,
        file,
        uploaded_by: UUID,
        uploaded_by_name: str | None = None,
    ) -> dict:
        await self._get_order(order_id)
        task, config = await self._get_task(order_id, task_type, task_id)
        if (getattr(task, "status", None) or "pending") in _CANCELLED_STATUSES:
            raise ValueError("已取消的任务不能上传资料")

        contents = await file.read()
        # Keep the existing, magic-byte-aware policy as the single validation
        # source for both the task pages and this order-scoped entry point.
        from app.api.tasks import validate_installation_media, validate_task_attachment

        if task_type == "installation":
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
            raise ValueError(message)

        date_dir = datetime.now(timezone.utc).strftime("%Y%m")
        dest_dir = Path(settings.LOCAL_UPLOAD_DIR) / date_dir
        dest_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
        os.chmod(dest_dir, 0o750)
        unique_name = f"{uuid4().hex}{safe_extension or ''}"
        stored_path = dest_dir / unique_name
        relative_path = f"{date_dir}/{unique_name}"

        _, display_name = safe_upload_name(file.filename, "attachment")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            with stored_path.open("wb") as output:
                output.write(contents)
            os.chmod(stored_path, 0o640)

            attachment = Attachment(
                related_type=config["related_type"],
                related_id=task_id,
                filename=display_name or unique_name,
                file_path=relative_path,
                file_size=len(contents),
                file_type=file.content_type,
                category=category,
                uploaded_by=uploaded_by,
                created_at=now,
                updated_at=now,
            )
            self.db.add(attachment)
            await self.db.flush()
            await log_operation(
                self.db,
                uploaded_by,
                uploaded_by_name,
                config["object_type"],
                task_id,
                ACTION_CREATE,
                after_data={
                    "attachment_id": str(attachment.id),
                    "order_id": str(order_id),
                    "filename": attachment.filename,
                    "file_size": attachment.file_size,
                    "file_type": attachment.file_type,
                    "category": attachment.category,
                },
            )
        except Exception:
            if stored_path.is_file():
                stored_path.unlink()
            raise

        return serialize_order_task_attachment(
            attachment,
            uploaded_by_name=uploaded_by_name,
        )

    async def get_file(self, order_id: UUID, attachment_id: UUID) -> tuple[Attachment, str]:
        attachment = await self._get_order_attachment(order_id, attachment_id)
        stored_path = confined_path(settings.LOCAL_UPLOAD_DIR, attachment.file_path)
        if not os.path.isfile(stored_path):
            raise ValueError("附件文件不存在")
        return attachment, stored_path

    async def delete(
        self,
        order_id: UUID,
        attachment_id: UUID,
        operated_by: UUID,
        operated_by_name: str | None = None,
    ) -> tuple[dict, str]:
        attachment = await self._get_order_attachment(order_id, attachment_id)
        before = serialize_order_task_attachment(attachment)
        stored_path = attachment.file_path
        object_type = {
            "design_task": OBJ_DESIGN_TASK,
            "production_task": OBJ_PRODUCTION_TASK,
            "installation_task": OBJ_INSTALLATION_TASK,
        }[attachment.related_type]
        task_id = attachment.related_id

        await self.db.delete(attachment)
        await self.db.flush()
        await log_operation(
            self.db,
            operated_by,
            operated_by_name,
            object_type,
            task_id,
            ACTION_DELETE,
            before_data={
                **before,
                "order_id": str(order_id),
            },
        )
        return before, stored_path
