from datetime import datetime
from uuid import UUID
from sqlalchemy import select, func, text

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_document import BusinessDocument
from app.domain.workflows import (
    DESIGN_TASK_WORKFLOW,
    INSTALLATION_TASK_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    allowed_targets,
)
from app.schemas.attachment import AttachmentResponse
from app.schemas.task import DesignTaskResponse, ProductionTaskResponse, InstallationTaskResponse

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
    return AttachmentResponse.model_validate(att).model_dump(mode="json")


async def _enrich_task_order(db, task_dict: dict) -> dict:
    """Query order by document_id and add order_no, customer_name, department, total_amount."""
    doc_id = task_dict.get("document_id") or task_dict.get("order_id")
    if not doc_id:
        return task_dict
    row = (await db.execute(
        text("SELECT doc_no, customer_name, department, total_amount FROM business_documents WHERE id = :id"),
        {"id": doc_id},
    )).fetchone()
    if row:
        task_dict["order_no"] = row[0]
        task_dict["customer_name"] = row[1]
        task_dict["department"] = row[2]
        task_dict["total_amount"] = float(row[3]) if row[3] is not None else None
        task_dict["source"] = "订单"
    # Resolve assigned_to user name
    assigned_to = task_dict.get("assigned_to")
    if assigned_to:
        user_row = (await db.execute(
            text("SELECT real_name FROM users WHERE id = :id"),
            {"id": str(assigned_to)},
        )).fetchone()
        if user_row:
            task_dict["assigned_to_name"] = user_row[0]
    return task_dict


async def _refresh_task_for_response(db: AsyncSession, task) -> None:
    """显式加载异步 ORM 字段，避免响应序列化触发隐式数据库 IO。"""
    await db.refresh(task)
    await db.refresh(task, ["attachments"])


async def _prepare_task_create_data(
    db: AsyncSession,
    data: dict,
    *,
    allowed_order_statuses: tuple[str, ...],
    task_label: str,
) -> dict:
    """校验父订单并把前端兼容字段转换为任务模型字段。"""
    normalized = dict(data)
    raw_order_id = normalized.pop("order_id", None) or normalized.get(
        "document_id"
    )
    if not raw_order_id:
        raise ValueError("请选择关联订单")
    order_id = (
        raw_order_id
        if isinstance(raw_order_id, UUID)
        else UUID(str(raw_order_id))
    )
    order = await db.get(BusinessDocument, order_id)
    if (
        not order
        or order.doc_type != "order"
        or order.deleted_at is not None
    ):
        raise ValueError("关联订单不存在或已取消")
    if order.status not in allowed_order_statuses:
        allowed_text = "、".join(allowed_order_statuses)
        raise ValueError(
            f"订单当前状态不能创建{task_label}任务，允许状态：{allowed_text}"
        )
    if not order.customer_id:
        raise ValueError("订单未关联正式客户，请先完善客户资料")

    normalized["document_id"] = order_id
    normalized["customer_id"] = order.customer_id
    normalized["project_name"] = (
        (normalized.get("project_name") or "").strip()
        or order.project_name
    )
    for field in ("assigned_to", "material_id", "process_id"):
        if field not in normalized:
            continue
        value = normalized[field]
        normalized[field] = (
            UUID(str(value))
            if value and not isinstance(value, UUID)
            else value or None
        )
    if normalized.get("scheduled_at") and isinstance(
        normalized["scheduled_at"],
        str,
    ):
        normalized["scheduled_at"] = datetime.fromisoformat(
            normalized["scheduled_at"]
        )
    return normalized


async def _attach_outsource_flags(db: AsyncSession, task_type: str, task_dicts: list[dict]) -> list[dict]:
    """为任务列表批量补 is_outsourced：存在未删除的关联外协任务即 True。"""
    from app.models.outsource import OutsourceTask
    ids = [d.get("id") for d in task_dicts if d.get("id")]
    linked: set[str] = set()
    if ids:
        result = await db.execute(
            select(OutsourceTask.source_task_id).where(
                OutsourceTask.source_task_type == task_type,
                OutsourceTask.source_task_id.in_([UUID(i) for i in ids]),
                OutsourceTask.deleted_at.is_(None),
            )
        )
        linked = {str(x) for x in result.scalars().all()}
    for d in task_dicts:
        d["is_outsourced"] = str(d.get("id")) in linked
    return task_dicts


async def _clear_outsource_source_refs(db: AsyncSession, task_type: str, task_ids: list[UUID]) -> None:
    """删除任务后清空外协任务对来源任务的悬空引用（source_task_id 无外键）。"""
    if not task_ids:
        return
    from sqlalchemy import update as sa_update
    from app.models.outsource import OutsourceTask
    await db.execute(
        sa_update(OutsourceTask)
        .where(
            OutsourceTask.source_task_type == task_type,
            OutsourceTask.source_task_id.in_(task_ids),
        )
        .values(source_task_type=None, source_task_id=None)
    )


class DesignTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DesignTaskRepository(db)

    async def _to_dict(self, task) -> dict:
        d = DesignTaskResponse.model_validate(task).model_dump(mode="json")
        d["order_id"] = d["document_id"]  # backward-compat alias
        d = await _enrich_task_order(self.db, d)
        return d

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None,
                         outsourced: bool | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.repo.list_tasks(skip=skip, limit=page_size, status=status, order_id=order_id, assigned_to=assigned_to, outsourced=outsourced)
        result = [await self._to_dict(t) for t in tasks]
        return await _attach_outsource_flags(self.db, "design", result), total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        return await self._to_dict(task) if task else None

    async def create_task(self, data: dict) -> dict:
        data = await _prepare_task_create_data(
            self.db,
            data,
            allowed_order_statuses=("confirmed", "designing"),
            task_label="设计",
        )
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
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

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
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def change_status(self, task_id: UUID, to_status: str, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("设计任务不存在")

        valid = allowed_targets(DESIGN_TASK_WORKFLOW, task.status)
        if to_status not in valid:
            raise ValueError(f"不允许从 {task.status} 流转到 {to_status}")

        task.status = to_status
        if to_status == "confirmed":
            task.completed_at = datetime.now()
        await self.db.flush()
        # Auto-advance order when all design tasks completed
        if to_status == "confirmed" and task.document_id:
            from sqlalchemy import func
            from app.models.business_document import BusinessDocument
            from app.models.task import DesignTask, ProductionTask
            from app.services.number_generator import generate_production_no
            from app.services.business_document_service import BusinessDocumentService

            remaining = (await self.db.execute(
                select(func.count()).select_from(DesignTask).where(
                    DesignTask.document_id == task.document_id,
                    DesignTask.status.not_in(["completed", "cancelled", "confirmed"])
                )
            )).scalar()
            if remaining == 0:
                order = await self.db.get(BusinessDocument, task.document_id)
                if order and order.status == "designing":
                    existing_pt = (await self.db.execute(
                        select(ProductionTask).where(ProductionTask.document_id == task.document_id)
                    )).scalar_one_or_none()
                    if not existing_pt:
                        pt = ProductionTask(
                            production_no=await generate_production_no(self.db),
                            document_id=task.document_id,
                            customer_id=order.customer_id,
                            project_name=order.project_name,
                            status="pending",
                            quantity=1,
                        )
                        self.db.add(pt)
                    order.status = "in_production"
                    order_svc = BusinessDocumentService(self.db, doc_type="order")
                    await order_svc.repo.create_status_log(task.document_id, "designing", "in_production",
                        "设计任务全部完成，系统自动推进", operated_by)
                    await self.db.flush()
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def delete_task(self, task_id: UUID) -> None:
        """管理员删除设计任务，回退订单到确认状态。"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("设计任务不存在")

        doc_id = task.document_id
        design_ids = [task_id]
        prod_ids: list[UUID] = []
        inst_ids: list[UUID] = []
        # Hard delete the task
        await self.db.delete(task)

        # Revert order to confirmed (pre-design state)
        if doc_id:
            from app.models.business_document import BusinessDocument
            from app.models.task import ProductionTask, InstallationTask
            from app.services.business_document_service import BusinessDocumentService

            order = await self.db.get(BusinessDocument, doc_id)
            if order and order.doc_type == "order" and order.status in ("designing", "in_production", "in_installation"):
                # Cancel downstream auto-created tasks
                for model_cls in (ProductionTask, InstallationTask):
                    result = await self.db.execute(
                        select(model_cls).where(model_cls.document_id == doc_id)
                    )
                    for t in result.scalars().all():
                        if model_cls is ProductionTask:
                            prod_ids.append(t.id)
                        else:
                            inst_ids.append(t.id)
                        await self.db.delete(t)

                # Soft-delete acceptance if exists
                from app.models.acceptance import AcceptanceForm
                ac_result = await self.db.execute(
                    select(AcceptanceForm).where(
                        AcceptanceForm.document_id == doc_id,
                        AcceptanceForm.deleted_at.is_(None),
                    )
                )
                for form in ac_result.scalars().all():
                    form.deleted_at = datetime.now()

                # Revert order
                old_status = order.status
                order.status = "pending_confirm"
                order_svc = BusinessDocumentService(self.db, doc_type="order")
                await order_svc.repo.create_status_log(doc_id, old_status, "confirmed",
                    "设计任务已被管理员删除，系统自动回退到待确认", None)

        # 清空外协任务对已删任务的悬空来源引用
        await _clear_outsource_source_refs(self.db, "design", design_ids)
        await _clear_outsource_source_refs(self.db, "production", prod_ids)
        await _clear_outsource_source_refs(self.db, "installation", inst_ids)
        await self.db.flush()

class ProductionTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductionTaskRepository(db)

    async def _to_dict(self, task) -> dict:
        d = ProductionTaskResponse.model_validate(task).model_dump(mode="json")
        d["order_id"] = d["document_id"]  # backward-compat alias
        d = await _enrich_task_order(self.db, d)
        return d

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None,
                         outsourced: bool | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.repo.list_tasks(skip=skip, limit=page_size, status=status, order_id=order_id, assigned_to=assigned_to, outsourced=outsourced)
        result = [await self._to_dict(t) for t in tasks]
        return await _attach_outsource_flags(self.db, "production", result), total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        return await self._to_dict(task) if task else None

    async def create_task(self, data: dict) -> dict:
        data = await _prepare_task_create_data(
            self.db,
            data,
            allowed_order_statuses=("in_production",),
            task_label="制作",
        )
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
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

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
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def change_status(self, task_id: UUID, to_status: str, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("制作任务不存在")

        valid = allowed_targets(PRODUCTION_TASK_WORKFLOW, task.status)
        if to_status not in valid:
            raise ValueError(f"不允许从 {task.status} 流转到 {to_status}")

        task.status = to_status
        if to_status == "completed":
            task.completed_at = datetime.now()
        await self.db.flush()
        # Auto-advance order when all production tasks completed
        if to_status == "completed" and task.document_id:
            from sqlalchemy import func
            from app.models.business_document import BusinessDocument
            from app.models.task import ProductionTask, InstallationTask
            from app.services.number_generator import generate_installation_no
            from app.services.business_document_service import BusinessDocumentService

            remaining = (await self.db.execute(
                select(func.count()).select_from(ProductionTask).where(
                    ProductionTask.document_id == task.document_id,
                    ProductionTask.status.not_in(["completed", "cancelled"])
                )
            )).scalar()
            if remaining == 0:
                order = await self.db.get(BusinessDocument, task.document_id)
                if order and order.status == "in_production":
                    existing_it = (await self.db.execute(
                        select(InstallationTask).where(InstallationTask.document_id == task.document_id)
                    )).scalar_one_or_none()
                    if not existing_it:
                        it = InstallationTask(
                            installation_no=await generate_installation_no(self.db),
                            document_id=task.document_id,
                            customer_id=order.customer_id,
                            project_name=order.project_name,
                            status="pending",
                        )
                        self.db.add(it)
                    order.status = "in_installation"
                    order_svc = BusinessDocumentService(self.db, doc_type="order")
                    await order_svc.repo.create_status_log(task.document_id, "in_production", "in_installation",
                        "制作任务全部完成，系统自动推进", operated_by)
                    await self.db.flush()
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def delete_task(self, task_id: UUID) -> None:
        """管理员删除制作任务，回退订单到设计中状态。"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("制作任务不存在")

        doc_id = task.document_id
        prod_ids = [task_id]
        inst_ids: list[UUID] = []
        await self.db.delete(task)

        if doc_id:
            from app.models.business_document import BusinessDocument
            from app.models.task import InstallationTask
            from app.services.business_document_service import BusinessDocumentService

            order = await self.db.get(BusinessDocument, doc_id)
            if order and order.doc_type == "order" and order.status in ("in_production", "in_installation"):
                # Cancel downstream installation task
                result = await self.db.execute(
                    select(InstallationTask).where(InstallationTask.document_id == doc_id)
                )
                for t in result.scalars().all():
                    inst_ids.append(t.id)
                    await self.db.delete(t)

                # Soft-delete acceptance if exists
                from app.models.acceptance import AcceptanceForm
                ac_result = await self.db.execute(
                    select(AcceptanceForm).where(
                        AcceptanceForm.document_id == doc_id,
                        AcceptanceForm.deleted_at.is_(None),
                    )
                )
                for form in ac_result.scalars().all():
                    form.deleted_at = datetime.now()

                old_status = order.status
                order_svc = BusinessDocumentService(self.db, doc_type="order")
                # 回退到设计中；若无设计任务则补建一个，保证看板设计栏有任务可跳转
                await order_svc._auto_create_design_task(order)
                order.status = "designing"
                await order_svc.repo.create_status_log(doc_id, old_status, "designing",
                    "制作任务已被管理员删除，系统自动回退", None)

        # 清空外协任务对已删任务的悬空来源引用
        await _clear_outsource_source_refs(self.db, "production", prod_ids)
        await _clear_outsource_source_refs(self.db, "installation", inst_ids)
        await self.db.flush()

class InstallationTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InstallationTaskRepository(db)

    async def _to_dict(self, task) -> dict:
        d = InstallationTaskResponse.model_validate(task).model_dump(mode="json")
        d["order_id"] = d["document_id"]  # backward-compat alias
        d = await _enrich_task_order(self.db, d)
        return d

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         order_id: str | None = None, assigned_to: str | None = None,
                         outsourced: bool | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.repo.list_tasks(skip=skip, limit=page_size, status=status, order_id=order_id, assigned_to=assigned_to, outsourced=outsourced)
        result = [await self._to_dict(t) for t in tasks]
        return await _attach_outsource_flags(self.db, "installation", result), total

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.repo.get_by_id(task_id)
        return await self._to_dict(task) if task else None

    async def create_task(self, data: dict) -> dict:
        data = await _prepare_task_create_data(
            self.db,
            data,
            allowed_order_statuses=("in_installation",),
            task_label="安装",
        )
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
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

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
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def change_status(self, task_id: UUID, to_status: str, operated_by: UUID | None = None) -> dict:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("安装任务不存在")

        valid = allowed_targets(INSTALLATION_TASK_WORKFLOW, task.status)
        if to_status not in valid:
            raise ValueError(f"不允许从 {task.status} 流转到 {to_status}")

        task.status = to_status
        if to_status == "completed":
            task.completed_at = datetime.now()
        await self.db.flush()
        # Auto-advance order when all installation tasks completed
        if to_status == "completed" and task.document_id:
            from sqlalchemy import func
            from app.models.task import InstallationTask
            from app.models.business_document import BusinessDocument
            from app.services.business_document_service import BusinessDocumentService

            remaining = (await self.db.execute(
                select(func.count()).select_from(InstallationTask).where(
                    InstallationTask.document_id == task.document_id,
                    InstallationTask.status.not_in(["completed", "cancelled"])
                )
            )).scalar()
            if remaining == 0:
                order = await self.db.get(BusinessDocument, task.document_id)
                if order and order.status == "in_installation":
                    order_svc = BusinessDocumentService(self.db, doc_type="order")
                    try:
                        await order_svc.change_status(
                            task.document_id, "completed",
                            "安装任务全部完成，系统自动推进", operated_by)
                    except ValueError:
                        pass
        await _refresh_task_for_response(self.db, task)
        return await self._to_dict(task)

    async def delete_task(self, task_id: UUID) -> None:
        """管理员删除安装任务，回退订单到生产中状态。"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError("安装任务不存在")

        doc_id = task.document_id
        inst_ids = [task_id]
        await self.db.delete(task)

        if doc_id:
            from app.models.business_document import BusinessDocument
            from app.services.business_document_service import BusinessDocumentService

            order = await self.db.get(BusinessDocument, doc_id)
            if order and order.doc_type == "order" and order.status == "in_installation":
                # Soft-delete acceptance if exists
                from app.models.acceptance import AcceptanceForm
                ac_result = await self.db.execute(
                    select(AcceptanceForm).where(
                        AcceptanceForm.document_id == doc_id,
                        AcceptanceForm.deleted_at.is_(None),
                    )
                )
                for form in ac_result.scalars().all():
                    form.deleted_at = datetime.now()

                old_status = order.status
                order_svc = BusinessDocumentService(self.db, doc_type="order")
                # 回退到制作中；若无制作任务则补建一个，保证看板制作栏有任务可跳转
                await order_svc._auto_create_production_task(order)
                order.status = "in_production"
                await order_svc.repo.create_status_log(doc_id, old_status, "in_production",
                    "安装任务已被管理员删除，系统自动回退", None)

        # 清空外协任务对已删任务的悬空来源引用
        await _clear_outsource_source_refs(self.db, "installation", inst_ids)
        await self.db.flush()

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
