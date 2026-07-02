from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.task_repo import (
    DesignTaskRepository,
    ProductionTaskRepository,
    InstallationTaskRepository,
    AttachmentRepository,
)
from app.services.number_generator import (
    generate_design_no,
    generate_production_no,
    generate_installation_no,
)


def _attachment_to_dict(att) -> dict:
    return {
        "id": str(att.id),
        "related_type": att.related_type,
        "related_id": str(att.related_id),
        "filename": att.filename,
        "file_path": att.file_path,
        "file_size": att.file_size,
        "file_type": att.file_type,
        "category": att.category,
        "uploaded_by": str(att.uploaded_by) if att.uploaded_by else None,
        "remark": att.remark,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


class DesignTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DesignTaskRepository(db)

    def _to_dict(self, task) -> dict:
        return {
            "id": str(task.id),
            "design_no": task.design_no,
            "order_id": str(task.order_id),
            "customer_id": str(task.customer_id),
            "project_name": task.project_name,
            "status": task.status,
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
            "description": task.description,
            "design_file_url": task.design_file_url,
            "client_comments": task.client_comments,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "attachments": [_attachment_to_dict(a) for a in (task.attachments or [])],
        }

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.repo.list_tasks(skip=skip, limit=page_size, status=status, order_id=order_id, assigned_to=assigned_to)
        return [self._to_dict(t) for t in tasks], total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        return self._to_dict(task) if task else None

    async def create_task(self, data: dict) -> dict:
        data["design_no"] = await generate_design_no(self.db)
        data["status"] = "pending"
        task = await self.repo.create(data)
        # Notify assigned user
        if task.assigned_to:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=task.assigned_to,
                type_="task_assigned",
                title=f"新设计任务: {task.design_no}",
                content=f"您被分配了设计任务 {task.project_name}",
                link=f"/design-tasks/{task.id}",
            )
        return self._to_dict(task)

    async def update_task(self, task_id: UUID, data: dict) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("设计任务不存在")
        old_assigned = task.assigned_to
        task = await self.repo.update(task, data)
        # Notify newly assigned user
        new_assigned = data.get("assigned_to")
        if new_assigned and new_assigned != old_assigned:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=new_assigned,
                type_="task_assigned",
                title=f"设计任务分配: {task.design_no}",
                content=f"您被分配了设计任务 {task.project_name}",
                link=f"/design-tasks/{task.id}",
            )
        return self._to_dict(task)

    async def change_status(self, task_id: UUID, to_status: str, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("设计任务不存在")

        allowed = {
            "pending": ["designing"],
            "designing": ["pending_review", "pending"],
            "pending_review": ["confirmed", "revision"],
            "revision": ["designing", "pending_review"],
            "confirmed": [],
        }
        valid = allowed.get(task.status, [])
        if to_status not in valid:
            raise ValueError(f"不允许从 {task.status} 流转到 {to_status}")

        task.status = to_status
        if to_status == "confirmed":
            task.completed_at = datetime.now()
        await self.db.flush()
        return self._to_dict(task)


class ProductionTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductionTaskRepository(db)

    def _to_dict(self, task) -> dict:
        return {
            "id": str(task.id),
            "production_no": task.production_no,
            "order_id": str(task.order_id),
            "customer_id": str(task.customer_id),
            "project_name": task.project_name,
            "status": task.status,
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
            "material_id": str(task.material_id) if task.material_id else None,
            "process_id": str(task.process_id) if task.process_id else None,
            "length": float(task.length) if task.length else None,
            "width": float(task.width) if task.width else None,
            "height": float(task.height) if task.height else None,
            "quantity": float(task.quantity),
            "qc_result": task.qc_result,
            "rework_reason": task.rework_reason,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "attachments": [_attachment_to_dict(a) for a in (task.attachments or [])],
        }

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.repo.list_tasks(skip=skip, limit=page_size, status=status, order_id=order_id, assigned_to=assigned_to)
        return [self._to_dict(t) for t in tasks], total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        return self._to_dict(task) if task else None

    async def create_task(self, data: dict) -> dict:
        data["production_no"] = await generate_production_no(self.db)
        data["status"] = "pending"
        task = await self.repo.create(data)
        # Notify assigned user
        if task.assigned_to:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=task.assigned_to,
                type_="task_assigned",
                title=f"新制作任务: {task.production_no}",
                content=f"您被分配了制作任务 {task.project_name}",
                link=f"/production-tasks/{task.id}",
            )
        return self._to_dict(task)

    async def update_task(self, task_id: UUID, data: dict) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("制作任务不存在")
        old_assigned = task.assigned_to
        task = await self.repo.update(task, data)
        # Notify newly assigned user
        new_assigned = data.get("assigned_to")
        if new_assigned and new_assigned != old_assigned:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=new_assigned,
                type_="task_assigned",
                title=f"制作任务分配: {task.production_no}",
                content=f"您被分配了制作任务 {task.project_name}",
                link=f"/production-tasks/{task.id}",
            )
        return self._to_dict(task)

    async def change_status(self, task_id: UUID, to_status: str, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("制作任务不存在")

        allowed = {
            "pending": ["queued", "in_progress"],
            "queued": ["in_progress", "pending"],
            "in_progress": ["qc_check", "rework", "completed"],
            "qc_check": ["completed", "rework"],
            "rework": ["in_progress", "qc_check"],
            "completed": [],
        }
        valid = allowed.get(task.status, [])
        if to_status not in valid:
            raise ValueError(f"不允许从 {task.status} 流转到 {to_status}")

        task.status = to_status
        if to_status == "completed":
            task.completed_at = datetime.now()
        await self.db.flush()
        return self._to_dict(task)


class InstallationTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InstallationTaskRepository(db)

    def _to_dict(self, task) -> dict:
        return {
            "id": str(task.id),
            "installation_no": task.installation_no,
            "order_id": str(task.order_id),
            "customer_id": str(task.customer_id),
            "project_name": task.project_name,
            "status": task.status,
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
            "address": task.address,
            "contact_name": task.contact_name,
            "contact_phone": task.contact_phone,
            "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
            "acceptance_result": task.acceptance_result,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "attachments": [_attachment_to_dict(a) for a in (task.attachments or [])],
        }

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.repo.list_tasks(skip=skip, limit=page_size, status=status, order_id=order_id, assigned_to=assigned_to)
        return [self._to_dict(t) for t in tasks], total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        return self._to_dict(task) if task else None

    async def create_task(self, data: dict) -> dict:
        data["installation_no"] = await generate_installation_no(self.db)
        data["status"] = "pending"
        task = await self.repo.create(data)
        # Notify assigned user
        if task.assigned_to:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=task.assigned_to,
                type_="task_assigned",
                title=f"新安装任务: {task.installation_no}",
                content=f"您被分配了安装任务 {task.project_name}",
                link=f"/installation-tasks/{task.id}",
            )
        return self._to_dict(task)

    async def update_task(self, task_id: UUID, data: dict) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("安装任务不存在")
        old_assigned = task.assigned_to
        task = await self.repo.update(task, data)
        # Notify newly assigned user
        new_assigned = data.get("assigned_to")
        if new_assigned and new_assigned != old_assigned:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.create_system_notification(
                user_id=new_assigned,
                type_="task_assigned",
                title=f"安装任务分配: {task.installation_no}",
                content=f"您被分配了安装任务 {task.project_name}",
                link=f"/installation-tasks/{task.id}",
            )
        return self._to_dict(task)

    async def change_status(self, task_id: UUID, to_status: str, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("安装任务不存在")

        allowed = {
            "pending": ["assigned", "in_progress"],
            "assigned": ["in_progress", "pending"],
            "in_progress": ["pending_acceptance", "pending"],
            "pending_acceptance": ["completed", "in_progress"],
            "completed": [],
        }
        valid = allowed.get(task.status, [])
        if to_status not in valid:
            raise ValueError(f"不允许从 {task.status} 流转到 {to_status}")

        task.status = to_status
        if to_status == "completed":
            task.completed_at = datetime.now()
        await self.db.flush()
        return self._to_dict(task)


class AttachmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttachmentRepository(db)

    async def add_attachment(self, related_type: str, related_id: UUID, data: dict, uploaded_by: UUID | None = None) -> dict:
        data["related_type"] = related_type
        data["related_id"] = related_id
        data["uploaded_by"] = uploaded_by
        att = await self.repo.create(data)
        return _attachment_to_dict(att)

    async def list_attachments(self, related_type: str, related_id: UUID) -> list[dict]:
        atts = await self.repo.get_by_task(related_type, related_id)
        return [_attachment_to_dict(a) for a in atts]

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        return await self.repo.delete(attachment_id)
