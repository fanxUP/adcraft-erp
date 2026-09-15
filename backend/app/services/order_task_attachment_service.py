"""Canonical order-owned materials for the design/production/install stages.

The order owns these three collections. A task detail page may provide a task
id as an access context, but a task is never required to create, read, or
delete an order-stage attachment and is never used as the attachment owner.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.file_security import confined_path, safe_upload_name
from app.core.permissions import (
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_UPDATE,
    PERM_INSTALLATION_TASK_READ,
    PERM_INSTALLATION_TASK_UPDATE,
    PERM_ORDER_READ,
    PERM_PRODUCTION_TASK_READ,
    PERM_PRODUCTION_TASK_UPDATE,
    PERM_TASK_COMPLETION_READ,
    PERM_TASK_COMPLETION_VIEW_ALL,
    user_has_permission,
)
from app.models.business_document import BusinessDocument, BusinessDocumentItem
from app.models.task import Attachment, DesignTask, InstallationTask, ProductionTask
from app.models.task_item_status_log import TaskItemStatusLog
from app.models.user import User
from app.services.operation_log_service import ACTION_CREATE, ACTION_DELETE, OBJ_ORDER, log_operation
from app.services.order_task_assignment_service import get_visible_task


STAGE_CONFIG = {
    "design": {
        "related_type": "design_task",
        "model": DesignTask,
        "number_field": "design_no",
        "label": "设计任务：任务附件",
        "task_label": "设计任务",
        "read_permission": PERM_DESIGN_TASK_READ,
        "write_permission": PERM_DESIGN_TASK_UPDATE,
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
        "read_permission": PERM_PRODUCTION_TASK_READ,
        "write_permission": PERM_PRODUCTION_TASK_UPDATE,
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
        "read_permission": PERM_INSTALLATION_TASK_READ,
        "write_permission": PERM_INSTALLATION_TASK_UPDATE,
        "accept": "image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime",
    },
}
STAGES = tuple(STAGE_CONFIG)

# Compatibility name used by older code and tests. New code should use
# STAGE_CONFIG and stage instead of task_type.
_TASK_CONFIG = STAGE_CONFIG


class OrderTaskAttachmentPermissionError(PermissionError):
    """The entry point has no permission for the requested order/stage."""


def _stage_config(stage: str) -> dict:
    config = STAGE_CONFIG.get(stage)
    if config is None:
        raise ValueError("资料阶段无效，只支持设计、制作、安装")
    return config


def _iso(value) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def serialize_order_task_attachment(
    attachment: Attachment,
    *,
    uploaded_by_name: str | None = None,
    order_item_name: str | None = None,
    order_item_sort_order: int | None = None,
    order_item_label: str | None = None,
) -> dict:
    """Expose metadata only; never expose the server storage path."""

    order_id = getattr(attachment, "order_id", None)
    order_item_id = getattr(attachment, "order_item_id", None)
    return {
        "id": str(attachment.id),
        "related_type": attachment.related_type,
        "related_id": str(attachment.related_id),
        "order_id": str(order_id) if order_id else None,
        "order_item_id": str(order_item_id) if order_item_id else None,
        "order_item_name": order_item_name,
        "order_item_sort_order": order_item_sort_order,
        "order_item_label": order_item_label or order_item_name,
        "stage": getattr(attachment, "stage", None),
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

    @staticmethod
    def _has_permission(viewer: User | None, permission: str) -> bool:
        return viewer is None or user_has_permission(viewer, permission)

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

    async def _get_task(
        self,
        order_id: UUID,
        stage: str,
        task_id: UUID,
        viewer: User | None = None,
    ):
        config = _stage_config(stage)
        if viewer is None:
            result = await self.db.execute(
                select(config["model"]).where(
                    config["model"].id == task_id,
                    config["model"].document_id == order_id,
                )
            )
            task = result.scalar_one_or_none()
        else:
            task = await get_visible_task(self.db, config["model"], task_id, viewer)
            if task is not None and task.document_id != order_id:
                task = None
        if task is None:
            raise ValueError("任务不存在或不属于该订单")
        return task

    async def _can_view_completed_project(
        self,
        order: BusinessDocument,
        stage: str,
        viewer: User,
    ) -> bool:
        """Allow the completed-project entry without inventing a task owner.

        Completion pages can be reached by employees who have completion-read
        permission but not order-read permission.  Their access is still
        scoped to a completed order where they have a completion event; the
        attachment itself remains owned by ``order_id + stage``.
        """
        if order.status != "completed" or not self._has_permission(
            viewer,
            PERM_TASK_COMPLETION_READ,
        ):
            return False
        if self._has_permission(viewer, PERM_TASK_COMPLETION_VIEW_ALL):
            return True

        completed_statuses = {
            "design": ("confirmed", "completed"),
            "production": ("completed",),
            "installation": ("completed",),
        }[stage]
        result = await self.db.execute(
            select(TaskItemStatusLog.id)
            .where(
                TaskItemStatusLog.document_id == order.id,
                TaskItemStatusLog.task_type == stage,
                TaskItemStatusLog.to_status.in_(completed_statuses),
                TaskItemStatusLog.assignee_user_id == viewer.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _authorize(
        self,
        order_id: UUID,
        stage: str,
        viewer: User | None,
        *,
        operation: str,
        task_id: UUID | None = None,
        order: BusinessDocument | None = None,
        required_permission: str | None = None,
    ) -> BusinessDocument:
        config = _stage_config(stage)
        order_access = self._has_permission(viewer, PERM_ORDER_READ)

        if not order_access:
            required = required_permission or (
                config["read_permission"] if operation == "read" else config["write_permission"]
            )
            if not self._has_permission(viewer, required):
                action = "查看" if operation == "read" else "操作"
                raise OrderTaskAttachmentPermissionError(
                    f"当前账号没有{config['task_label']}资料{action}权限"
                )

        # Check the caller's capability before looking up the order. This keeps
        # a task-only account from learning whether an arbitrary order id is
        # real when it does not even have the requested stage permission.
        order = order or await self._get_order(order_id)
        if not order_access:
            if task_id is None and not (
                operation == "read"
                and viewer is not None
                and await self._can_view_completed_project(order, stage, viewer)
            ):
                raise OrderTaskAttachmentPermissionError(
                    "任务资料入口缺少任务上下文，请从对应任务详情进入"
                )

        if task_id is not None:
            # An order reader can use a task id only as a consistency check;
            # task visibility still applies to task-only entry points.
            await self._get_task(
                order_id,
                stage,
                task_id,
                viewer=None if order_access else viewer,
            )
        return order

    async def _attachment_rows(
        self,
        order_id: UUID,
        stage: str | None = None,
    ) -> list[tuple[Attachment, str | None, str | None]]:
        conditions = [Attachment.order_id == order_id]
        if stage is not None:
            config = _stage_config(stage)
            conditions.extend(
                (
                    Attachment.stage == stage,
                    Attachment.related_type.in_(("order_stage", config["related_type"])),
                )
            )
        else:
            conditions.append(
                Attachment.related_type.in_(
                    ("order_stage",) + tuple(config["related_type"] for config in STAGE_CONFIG.values())
                )
            )
        result = await self.db.execute(
            select(Attachment, User.real_name, User.username)
            .outerjoin(User, User.id == Attachment.uploaded_by)
            .where(and_(*conditions))
            .order_by(Attachment.created_at.desc(), Attachment.id.desc())
        )
        return list(result.all())

    async def _attachment_item_metadata(
        self,
        attachments: list[Attachment],
        order_id: UUID,
    ) -> dict[UUID, tuple[str | None, int | None]]:
        item_ids = {
            item_id
            for attachment in attachments
            if (item_id := getattr(attachment, "order_item_id", None)) is not None
        }
        if not item_ids:
            return {}

        result = await self.db.execute(
            select(
                BusinessDocumentItem.id,
                BusinessDocumentItem.item_name,
                BusinessDocumentItem.sort_order,
            ).where(
                BusinessDocumentItem.id.in_(item_ids),
                BusinessDocumentItem.document_id == order_id,
            )
        )
        metadata: dict[UUID, tuple[str | None, int | None]] = {}
        for row in result.all():
            item_id = row[0]
            metadata[item_id] = (row[1], row[2])
        return metadata

    async def list_for_order(
        self,
        order_id: UUID,
        *,
        stage: str | None = None,
        task_id: UUID | None = None,
        viewer: User | None = None,
    ) -> dict:
        if task_id is not None and stage is None:
            raise ValueError("任务资料阶段不能为空")
        if (
            task_id is None
            and stage is None
            and not self._has_permission(viewer, PERM_ORDER_READ)
        ):
            raise OrderTaskAttachmentPermissionError("请从完成项目详情按阶段查看资料")

        requested_stages = [stage] if stage is not None else list(STAGES)
        await self._authorize(
            order_id,
            requested_stages[0],
            viewer,
            operation="read",
            task_id=task_id,
        )

        groups: list[dict] = []
        order_access = self._has_permission(viewer, PERM_ORDER_READ)
        for current_stage in requested_stages:
            config = _stage_config(current_stage)
            rows = await self._attachment_rows(order_id, current_stage)
            row_attachments = [row[0] for row in rows]
            item_metadata = await self._attachment_item_metadata(row_attachments, order_id)
            attachments = [
                serialize_order_task_attachment(
                    attachment,
                    uploaded_by_name=real_name or username,
                    order_item_name=item_metadata.get(
                        getattr(attachment, "order_item_id", None),
                        (None, None),
                    )[0],
                    order_item_sort_order=item_metadata.get(
                        getattr(attachment, "order_item_id", None),
                        (None, None),
                    )[1],
                )
                for attachment, real_name, username in rows
            ]
            can_manage_stage = order_access or self._has_permission(
                viewer,
                config["write_permission"],
            )
            groups.append(
                {
                    "stage": current_stage,
                    "task_type": current_stage,  # compatibility alias
                    "label": config["label"],
                    "task_label": config["task_label"],
                    "accept": config["accept"],
                    "task_count": 0,
                    "attachment_count": len(attachments),
                    "can_upload": can_manage_stage,
                    "can_delete": can_manage_stage,
                    "attachments": attachments,
                    "tasks": [],  # compatibility shape; no task ownership
                }
            )
        return {"order_id": str(order_id), "groups": groups}

    async def upload(
        self,
        order_id: UUID,
        task_type: str,
        task_id: UUID | None,
        file,
        uploaded_by: UUID,
        uploaded_by_name: str | None = None,
        *,
        viewer: User | None = None,
        order_item_id: UUID | None = None,
    ) -> dict:
        """Create an order-stage attachment; ``task_id`` is optional context."""

        _stage_config(task_type)
        await self._authorize(
            order_id,
            task_type,
            viewer,
            operation="write",
            task_id=task_id,
        )

        contents, safe_extension, category = await self._validate_file(task_type, file)
        payload, _ = await self._store_attachment(
            order_id,
            task_type,
            task_id,
            file,
            contents,
            safe_extension,
            category,
            uploaded_by,
            uploaded_by_name,
            order_item_id=order_item_id,
        )
        return payload

    async def _validate_file(self, task_type: str, file) -> tuple[bytes, str | None, str | None]:
        # Reuse the established magic-byte and extension policy so the order
        # entry and task-entry adapters cannot drift apart.
        from app.api.tasks import validate_installation_media, validate_task_attachment

        contents = await file.read()

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
        return contents, safe_extension, category

    async def _store_attachment(
        self,
        order_id: UUID,
        task_type: str,
        task_id: UUID | None,
        file,
        contents: bytes,
        safe_extension: str | None,
        category: str | None,
        uploaded_by: UUID,
        uploaded_by_name: str | None,
        *,
        order_item_id: UUID | None = None,
    ) -> tuple[dict, str]:

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
                related_type="order_stage",
                related_id=order_id,
                order_id=order_id,
                order_item_id=order_item_id,
                stage=task_type,
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
                OBJ_ORDER,
                order_id,
                ACTION_CREATE,
                after_data={
                    "attachment_id": str(attachment.id),
                    "stage": task_type,
                    "order_item_id": str(order_item_id) if order_item_id else None,
                    "entry_task_id": str(task_id) if task_id else None,
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
        ), str(stored_path)

    async def upload_many_for_item(
        self,
        order_id: UUID,
        stage: str,
        task_id: UUID,
        order_item_id: UUID | str,
        files: list,
        uploaded_by: UUID,
        uploaded_by_name: str | None = None,
        *,
        viewer: User | None = None,
        authorization_permission: str | None = None,
    ) -> tuple[list[dict], list[str]]:
        """Upload completion materials and bind every file to one item.

        The caller owns the surrounding transaction.  Physical files are
        removed if any file in the batch fails so a failed completion cannot
        leave orphaned files on disk.
        """

        _stage_config(stage)
        order = await self._authorize(
            order_id,
            stage,
            viewer,
            operation="write",
            task_id=task_id,
            required_permission=authorization_permission,
        )
        try:
            item_uuid = UUID(str(order_item_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("订单明细编号无效") from exc

        item = await self.db.get(BusinessDocumentItem, item_uuid)
        if (
            item is None
            or item.document_id != order.id
            or getattr(item, "lifecycle_status", "active") != "active"
        ):
            raise ValueError("订单明细不存在或已失效")
        if not files:
            raise ValueError("请至少选择一个资料")

        payloads: list[dict] = []
        stored_paths: list[str] = []
        try:
            for file in files:
                contents, safe_extension, category = await self._validate_file(stage, file)
                payload, stored_path = await self._store_attachment(
                    order_id,
                    stage,
                    task_id,
                    file,
                    contents,
                    safe_extension,
                    category,
                    uploaded_by,
                    uploaded_by_name,
                    order_item_id=item_uuid,
                )
                payloads.append(payload)
                stored_paths.append(stored_path)
        except Exception:
            for stored_path in stored_paths:
                path = Path(stored_path)
                if path.is_file():
                    path.unlink()
            raise
        return payloads, stored_paths

    async def _get_order_attachment(
        self,
        order_id: UUID,
        attachment_id: UUID,
        *,
        stage: str | None = None,
    ) -> Attachment:
        conditions = [
            Attachment.id == attachment_id,
            Attachment.order_id == order_id,
        ]
        if stage is not None:
            config = _stage_config(stage)
            conditions.extend(
                (
                    Attachment.stage == stage,
                    Attachment.related_type.in_(("order_stage", config["related_type"])),
                )
            )
        else:
            conditions.append(
                Attachment.related_type.in_(
                    ("order_stage",) + tuple(config["related_type"] for config in STAGE_CONFIG.values())
                )
            )
        result = await self.db.execute(select(Attachment).where(and_(*conditions)))
        attachment = result.scalar_one_or_none()
        if attachment is None:
            raise ValueError("附件不存在或不属于该订单")
        return attachment

    async def get_file(
        self,
        order_id: UUID,
        attachment_id: UUID,
        *,
        stage: str | None = None,
        task_id: UUID | None = None,
        viewer: User | None = None,
    ) -> tuple[Attachment, str]:
        if task_id is not None and stage is None:
            raise ValueError("任务资料阶段不能为空")
        if stage is None:
            if not self._has_permission(viewer, PERM_ORDER_READ):
                raise OrderTaskAttachmentPermissionError("请从对应任务详情进入订单阶段资料")
            await self._get_order(order_id)
        else:
            await self._authorize(
                order_id,
                stage,
                viewer,
                operation="read",
                task_id=task_id,
            )
        attachment = await self._get_order_attachment(
            order_id,
            attachment_id,
            stage=stage,
        )
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
        *,
        stage: str | None = None,
        task_id: UUID | None = None,
        viewer: User | None = None,
    ) -> tuple[dict, str]:
        if task_id is not None and stage is None:
            raise ValueError("任务资料阶段不能为空")
        if stage is None:
            if not self._has_permission(viewer, PERM_ORDER_READ):
                raise OrderTaskAttachmentPermissionError("请从对应任务详情进入订单阶段资料")
            await self._get_order(order_id)
        else:
            await self._authorize(
                order_id,
                stage,
                viewer,
                operation="write",
                task_id=task_id,
            )
        attachment = await self._get_order_attachment(
            order_id,
            attachment_id,
            stage=stage,
        )
        before = serialize_order_task_attachment(attachment)
        relative_path = attachment.file_path
        await self.db.delete(attachment)
        await self.db.flush()
        await log_operation(
            self.db,
            operated_by,
            operated_by_name,
            OBJ_ORDER,
            order_id,
            ACTION_DELETE,
            before_data={
                **before,
                "entry_task_id": str(task_id) if task_id else None,
            },
        )
        return before, relative_path
