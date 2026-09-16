import uuid as _uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    String,
    and_,
    case,
    cast,
    delete as sa_delete,
    func,
    literal,
    or_,
    select,
)

from app.models.outsource import OutsourceVendor, OutsourceTask, OutsourcePayment


class OutsourceVendorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, vendor_id: UUID) -> OutsourceVendor | None:
        result = await self.db.execute(
            select(OutsourceVendor).where(OutsourceVendor.id == vendor_id, OutsourceVendor.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_vendors(self, skip: int = 0, limit: int = 20, keyword: str | None = None,
                           service_type: str | None = None) -> tuple[list[OutsourceVendor], int]:
        # Legacy 外协商页面 is a compatibility view over the unified master;
        # keep it limited to the external-service supplier type.
        q = select(OutsourceVendor).where(
            OutsourceVendor.deleted_at.is_(None),
            OutsourceVendor.supplier_type == "outsource",
        )
        if keyword:
            q = q.where(OutsourceVendor.name.ilike(f"%{keyword}%"))
        if service_type:
            q = q.where(OutsourceVendor.service_type == service_type)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourceVendor.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OutsourceVendor:
        data.setdefault("id", _uuid.uuid4())
        vendor = OutsourceVendor(**data)
        self.db.add(vendor)
        await self.db.flush()
        return vendor

    async def update(self, vendor: OutsourceVendor, data: dict) -> OutsourceVendor:
        for k, v in data.items():
            if v is not None:
                setattr(vendor, k, v)
        await self.db.flush()
        return vendor

    async def soft_delete(self, vendor: OutsourceVendor) -> None:
        from datetime import datetime
        vendor.deleted_at = datetime.now()
        await self.db.flush()


class OutsourceTaskRepository:
    SOURCE_TASK_TYPES = ("design", "production", "installation")
    RELATED_DOCUMENT_TYPES = ("order", "quote")

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        task_id: UUID,
        *,
        for_update: bool = False,
    ) -> OutsourceTask | None:
        query = select(OutsourceTask).where(
            OutsourceTask.id == task_id,
            OutsourceTask.deleted_at.is_(None),
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    def _task_group_key_expression(cls):
        """Return the database-side, stable identity used by grouped views.

        Valid internal-task links are grouped by their source task. Legacy or
        incomplete links deliberately fall back to a document or a single
        task identity so the UI never silently merges unrelated records.
        """
        has_source = or_(
            OutsourceTask.source_task_type.isnot(None),
            OutsourceTask.source_task_id.isnot(None),
        )
        complete_source = and_(
            OutsourceTask.source_task_type.in_(cls.SOURCE_TASK_TYPES),
            OutsourceTask.source_task_id.isnot(None),
        )
        has_document = or_(
            OutsourceTask.related_doc_type.isnot(None),
            OutsourceTask.related_doc_id.isnot(None),
        )
        complete_document = and_(
            OutsourceTask.related_doc_type.in_(cls.RELATED_DOCUMENT_TYPES),
            OutsourceTask.related_doc_id.isnot(None),
        )
        return case(
            (
                complete_source,
                func.concat(
                    literal("source:"),
                    OutsourceTask.source_task_type,
                    literal(":"),
                    cast(OutsourceTask.source_task_id, String),
                ),
            ),
            (
                and_(~has_source, complete_document),
                func.concat(
                    literal("document:"),
                    OutsourceTask.related_doc_type,
                    literal(":"),
                    cast(OutsourceTask.related_doc_id, String),
                ),
            ),
            (
                has_source,
                func.concat(literal("task:"), cast(OutsourceTask.id, String)),
            ),
            (
                has_document,
                func.concat(literal("task:"), cast(OutsourceTask.id, String)),
            ),
            else_=literal("unlinked"),
        )

    @classmethod
    def _task_group_kind_expression(cls):
        has_source = or_(
            OutsourceTask.source_task_type.isnot(None),
            OutsourceTask.source_task_id.isnot(None),
        )
        complete_source = and_(
            OutsourceTask.source_task_type.in_(cls.SOURCE_TASK_TYPES),
            OutsourceTask.source_task_id.isnot(None),
        )
        has_document = or_(
            OutsourceTask.related_doc_type.isnot(None),
            OutsourceTask.related_doc_id.isnot(None),
        )
        complete_document = and_(
            OutsourceTask.related_doc_type.in_(cls.RELATED_DOCUMENT_TYPES),
            OutsourceTask.related_doc_id.isnot(None),
        )
        return case(
            (complete_source, literal("source_task")),
            (has_source, literal("unresolved_source")),
            (complete_document, literal("related_document")),
            (has_document, literal("unresolved_document")),
            else_=literal("unlinked"),
        )

    @staticmethod
    def _task_conditions(status: str | None = None,
                          vendor_id: UUID | None = None,
                          related_doc_id: UUID | None = None,
                          source_task_type: str | None = None,
                          source_task_id: UUID | None = None,
                          task_type: str | None = None,
                          order_item_id: UUID | None = None):
        conditions = [OutsourceTask.deleted_at.is_(None)]
        if status:
            conditions.append(OutsourceTask.status == status)
        if vendor_id:
            conditions.append(OutsourceTask.vendor_id == vendor_id)
        if related_doc_id:
            conditions.append(OutsourceTask.related_doc_id == related_doc_id)
        if source_task_type:
            conditions.append(OutsourceTask.source_task_type == source_task_type)
        if source_task_id:
            conditions.append(OutsourceTask.source_task_id == source_task_id)
        if task_type:
            conditions.append(OutsourceTask.task_type == task_type)
        if order_item_id:
            conditions.append(OutsourceTask.order_item_id == order_item_id)
        return conditions

    async def list_tasks(self, skip: int = 0, limit: int = 20, status: str | None = None,
                         vendor_id: UUID | None = None, related_doc_id: UUID | None = None,
                         source_task_type: str | None = None, source_task_id: UUID | None = None,
                         task_type: str | None = None,
                         order_item_id: UUID | None = None) -> tuple[list[OutsourceTask], int]:
        q = select(OutsourceTask).where(*self._task_conditions(
            status,
            vendor_id,
            related_doc_id,
            source_task_type,
            source_task_id,
            task_type,
            order_item_id,
        ))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourceTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def list_task_groups(self, skip: int = 0, limit: int = 20, status: str | None = None,
                               vendor_id: UUID | None = None, related_doc_id: UUID | None = None,
                               source_task_type: str | None = None, source_task_id: UUID | None = None,
                               task_type: str | None = None,
                               order_item_id: UUID | None = None) -> tuple[list, int]:
        """Return one aggregate row per stable external-task group."""
        conditions = self._task_conditions(
            status,
            vendor_id,
            related_doc_id,
            source_task_type,
            source_task_id,
            task_type,
            order_item_id,
        )
        group_key = self._task_group_key_expression()
        group_kind = self._task_group_kind_expression()
        not_cancelled = OutsourceTask.status != "cancelled"
        recognized = OutsourceTask.status.in_(("completed", "settled"))
        amount = OutsourceTask.total_amount

        grouped = (
            select(
                group_key.label("group_key"),
                group_kind.label("group_kind"),
                func.count(OutsourceTask.id).label("task_count"),
                func.count(OutsourceTask.id).filter(not_cancelled).label("active_task_count"),
                func.count(OutsourceTask.id).filter(OutsourceTask.status == "pending").label("status_pending_count"),
                func.count(OutsourceTask.id).filter(OutsourceTask.status == "in_progress").label("status_in_progress_count"),
                func.count(OutsourceTask.id).filter(OutsourceTask.status == "completed").label("status_completed_count"),
                func.count(OutsourceTask.id).filter(OutsourceTask.status == "settled").label("status_settled_count"),
                func.count(OutsourceTask.id).filter(OutsourceTask.status == "cancelled").label("status_cancelled_count"),
                func.count(OutsourceTask.id).filter(
                    ~OutsourceTask.status.in_(("pending", "in_progress", "completed", "settled", "cancelled"))
                ).label("status_other_count"),
                func.coalesce(func.sum(case((not_cancelled, amount), else_=0)), 0).label("planned_amount"),
                func.coalesce(func.sum(case((recognized, amount), else_=0)), 0).label("recognized_cost"),
                func.coalesce(func.sum(case((not_cancelled, OutsourceTask.paid_amount), else_=0)), 0).label("paid_amount"),
                func.coalesce(func.sum(case((not_cancelled, OutsourceTask.unpaid_amount), else_=0)), 0).label("unpaid_amount"),
                func.array_agg(func.distinct(OutsourceTask.related_doc_id)).filter(
                    OutsourceTask.related_doc_id.isnot(None)
                ).label("related_doc_ids"),
                func.max(OutsourceTask.created_at).label("latest_created_at"),
            )
            .where(*conditions)
            .group_by(group_key, group_kind)
            .order_by(func.max(OutsourceTask.created_at).desc(), group_key.asc())
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(group_key.label("group_key"))
            .where(*conditions)
            .group_by(group_key)
            .subquery()
        )
        total = (await self.db.execute(
            select(func.count()).select_from(count_query)
        )).scalar() or 0
        result = await self.db.execute(grouped)
        return list(result.all()), total

    async def list_task_group_tasks(self, group_key: str, skip: int = 0, limit: int = 20,
                                    status: str | None = None,
                                    vendor_id: UUID | None = None,
                                    related_doc_id: UUID | None = None,
                                    source_task_type: str | None = None,
                                    source_task_id: UUID | None = None,
                                    task_type: str | None = None,
                                    order_item_id: UUID | None = None) -> tuple[list[OutsourceTask], int]:
        """Return the paginated children for one validated group identity."""
        conditions = self._task_conditions(
            status,
            vendor_id,
            related_doc_id,
            source_task_type,
            source_task_id,
            task_type,
            order_item_id,
        )
        q = select(OutsourceTask).where(
            *conditions,
            self._task_group_key_expression() == group_key,
        )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(OutsourceTask.created_at.desc(), OutsourceTask.id.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OutsourceTask:
        data.setdefault("id", _uuid.uuid4())
        task = OutsourceTask(**data)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update(self, task: OutsourceTask, data: dict) -> OutsourceTask:
        for k, v in data.items():
            # None is meaningful for explicit relationship clearing, e.g.
            # order_item_id=null must remove the item link.
            setattr(task, k, v)
        await self.db.flush()
        return task


    async def soft_delete(self, task: OutsourceTask) -> None:
        from datetime import datetime
        task.deleted_at = datetime.now()
        await self.db.flush()

    async def restore(self, task: OutsourceTask) -> None:
        task.deleted_at = None
        task.status = "cancelled"
        await self.db.flush()

    async def list_deleted_tasks(self, skip: int = 0, limit: int = 20) -> tuple[list[OutsourceTask], int]:
        q = select(OutsourceTask).where(OutsourceTask.deleted_at.isnot(None))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourceTask.deleted_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_deleted_by_id(self, task_id: UUID) -> OutsourceTask | None:
        result = await self.db.execute(
            select(OutsourceTask).where(OutsourceTask.id == task_id, OutsourceTask.deleted_at.isnot(None))
        )
        return result.scalar_one_or_none()


class OutsourcePaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_payments(self, skip: int = 0, limit: int = 20, vendor_id: UUID | None = None,
                            task_id: UUID | None = None) -> tuple[list[OutsourcePayment], int]:
        q = select(OutsourcePayment)
        if vendor_id:
            q = q.where(OutsourcePayment.vendor_id == vendor_id)
        if task_id:
            q = q.where(OutsourcePayment.task_id == task_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(OutsourcePayment.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> OutsourcePayment:
        data.setdefault("id", _uuid.uuid4())
        payment = OutsourcePayment(**data)
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def payment_totals(self, task_id: UUID) -> tuple[int, float]:
        """返回某任务的付款记录数与付款总额。"""
        result = await self.db.execute(
            select(
                func.count(OutsourcePayment.id),
                func.coalesce(func.sum(OutsourcePayment.amount), 0),
            ).where(OutsourcePayment.task_id == task_id)
        )
        count, total = result.one()
        return count, float(total)

    async def delete_by_task(self, task_id: UUID) -> None:
        """硬删除某任务的付款记录（付款表无软删除字段）。"""
        await self.db.execute(
            sa_delete(OutsourcePayment).where(OutsourcePayment.task_id == task_id)
        )
