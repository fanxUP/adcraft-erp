from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.business_document import (
    BusinessDocument,
    BusinessDocumentItem,
    BusinessDocumentStatusLog,
    BusinessDocumentVersion,
)


class BusinessDocumentRepository:
    """统一业务单据仓库 — 提供按 doc_type 筛选的 CRUD。"""

    def __init__(self, db: AsyncSession, doc_type: str | None = None):
        self.db = db
        self.doc_type = doc_type  # 'order', 'quote', or None for both

    # ── 基础查询 ──

    async def get_by_id(self, doc_id: UUID) -> BusinessDocument | None:
        q = select(BusinessDocument).where(
            BusinessDocument.id == doc_id,
            BusinessDocument.deleted_at.is_(None),
        )
        if self.doc_type:
            q = q.where(BusinessDocument.doc_type == self.doc_type)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_deleted_by_id(self, doc_id: UUID) -> BusinessDocument | None:
        q = select(BusinessDocument).where(
            BusinessDocument.id == doc_id,
            BusinessDocument.deleted_at.isnot(None),
        )
        if self.doc_type:
            q = q.where(BusinessDocument.doc_type == self.doc_type)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_all(
        self, skip: int = 0, limit: int = 20,
        status: str | None = None,
        customer_id: UUID | None = None,
        keyword: str | None = None,
        exclude_status: str | None = None,
    ) -> tuple[list[BusinessDocument], int]:
        """列出所有活跃单据，支持 doc_type 过滤。"""
        q = select(BusinessDocument).where(BusinessDocument.deleted_at.is_(None))
        if self.doc_type:
            q = q.where(BusinessDocument.doc_type == self.doc_type)
        if status:
            q = q.where(BusinessDocument.status == status)
        if exclude_status:
            q = q.where(BusinessDocument.status != exclude_status)
        if customer_id:
            q = q.where(BusinessDocument.customer_id == customer_id)
        if keyword:
            q = q.where(
                BusinessDocument.doc_no.ilike(f"%{keyword}%")
                | BusinessDocument.project_name.ilike(f"%{keyword}%")
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(BusinessDocument.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def list_deleted(
        self, skip: int = 0, limit: int = 20, keyword: str | None = None
    ) -> tuple[list[BusinessDocument], int]:
        q = select(BusinessDocument).where(BusinessDocument.deleted_at.isnot(None))
        if self.doc_type:
            q = q.where(BusinessDocument.doc_type == self.doc_type)
        if keyword:
            q = q.where(
                BusinessDocument.doc_no.ilike(f"%{keyword}%")
                | BusinessDocument.project_name.ilike(f"%{keyword}%")
            )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(BusinessDocument.deleted_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    # ── CRUD ──

    async def create(self, data: dict) -> BusinessDocument:
        items_data = data.pop("items", [])
        doc = BusinessDocument(**data)
        self.db.add(doc)
        await self.db.flush()

        for idx, item in enumerate(items_data):
            item.setdefault("sort_order", idx)
            item["document_id"] = doc.id
            self.db.add(BusinessDocumentItem(**item))
        if items_data:
            await self.db.flush()

        return doc

    async def update(self, doc: BusinessDocument, data: dict) -> BusinessDocument:
        items_data = data.pop("items", None)
        for k, v in data.items():
            if v is not None:
                setattr(doc, k, v)

        if items_data is not None:
            # Replace all items
            existing = (await self.db.execute(
                select(BusinessDocumentItem).where(
                    BusinessDocumentItem.document_id == doc.id
                )
            )).scalars().all()
            for old in existing:
                await self.db.delete(old)
            for idx, item in enumerate(items_data):
                item.setdefault("sort_order", idx)
                item["document_id"] = doc.id
                self.db.add(BusinessDocumentItem(**item))

        await self.db.flush()
        return doc

    async def soft_delete(self, doc: BusinessDocument) -> None:
        doc.deleted_at = datetime.now()
        await self.db.flush()

    async def restore(self, doc: BusinessDocument) -> None:
        doc.deleted_at = None
        doc.status = "cancelled"  # 恢复的订单默认为已取消
        await self.db.flush()

    # ── 明细 ──

    async def get_items(self, doc_id: UUID) -> list[BusinessDocumentItem]:
        result = await self.db.execute(
            select(BusinessDocumentItem)
            .where(BusinessDocumentItem.document_id == doc_id)
            .order_by(BusinessDocumentItem.sort_order)
        )
        return list(result.scalars().all())

    async def add_items(self, doc_id: UUID, items_data: list[dict]) -> list[BusinessDocumentItem]:
        items = []
        for item in items_data:
            item["document_id"] = doc_id
            obj = BusinessDocumentItem(**item)
            self.db.add(obj)
            items.append(obj)
            await self.db.flush()
        return items

    async def update_item(self, item: BusinessDocumentItem, data: dict) -> BusinessDocumentItem:
        for k, v in data.items():
            if v is not None:
                setattr(item, k, v)
        await self.db.flush()
        return item

    async def delete_item(self, item: BusinessDocumentItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    # ── 状态日志 ──

    async def get_status_logs(self, doc_id: UUID) -> list[BusinessDocumentStatusLog]:
        result = await self.db.execute(
            select(BusinessDocumentStatusLog)
            .where(BusinessDocumentStatusLog.document_id == doc_id)
            .order_by(BusinessDocumentStatusLog.operated_at.desc())
        )
        return list(result.scalars().all())

    async def create_status_log(
        self, doc_id: UUID, from_status: str | None, to_status: str,
        reason: str | None, operated_by: UUID | None,
    ) -> BusinessDocumentStatusLog:
        log = BusinessDocumentStatusLog(
            document_id=doc_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            operated_by=operated_by,
            operated_at=datetime.now(),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    # ── 版本 ──

    async def get_next_version_no(self, doc_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(BusinessDocumentVersion.version_no), 0))
            .where(BusinessDocumentVersion.document_id == doc_id)
        )
        return result.scalar() + 1

    async def create_version(
        self, doc_id: UUID, version_no: int, snapshot: dict, created_by: UUID | None
    ) -> BusinessDocumentVersion:
        ver = BusinessDocumentVersion(
            document_id=doc_id,
            version_no=version_no,
            snapshot=snapshot,
            created_by=created_by,
        )
        self.db.add(ver)
        await self.db.flush()
        return ver

    # ── 转换 ──

    async def convert_doc_type(self, doc: BusinessDocument, new_type: str, new_doc_no: str) -> BusinessDocument:
        """切换 doc_type + 重新编号。ID 不变，所有 FK 自动跟随。"""
        doc.doc_type = new_type
        doc.doc_no = new_doc_no
        await self.db.flush()
        return doc
