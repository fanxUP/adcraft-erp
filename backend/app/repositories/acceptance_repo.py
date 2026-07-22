from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, not_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.acceptance import AcceptanceForm, AcceptanceItem, AcceptanceAttachment
from app.models.business_document import BusinessDocument


class AcceptanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, page: int, page_size: int, keyword: str = "",
                       status: str = "", document_id: str = "",
                       # backward compat
                       order_id: str = "") -> tuple[list[AcceptanceForm], int]:
        doc_id = document_id or order_id
        q = select(AcceptanceForm).where(AcceptanceForm.deleted_at.is_(None))
        q = q.options(
            selectinload(AcceptanceForm.document).selectinload(BusinessDocument.customer),
            selectinload(AcceptanceForm.items),
        )
        count_q = select(func.count()).select_from(AcceptanceForm).where(AcceptanceForm.deleted_at.is_(None))

        if keyword:
            pattern = f"%{keyword}%"
            q = q.where(AcceptanceForm.acceptance_no.ilike(pattern))
            count_q = count_q.where(AcceptanceForm.acceptance_no.ilike(pattern))
        if status:
            q = q.where(AcceptanceForm.status == status)
            count_q = count_q.where(AcceptanceForm.status == status)
        if doc_id:
            q = q.where(AcceptanceForm.document_id == UUID(doc_id))
            count_q = count_q.where(AcceptanceForm.document_id == UUID(doc_id))

        total_result = await self.db.execute(count_q)
        total = total_result.scalar()

        q = q.order_by(AcceptanceForm.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        items = list(result.scalars().all())
        return items, total

    async def list_available_quotes(self) -> list[BusinessDocument]:
        """Return quotes not yet linked to any acceptance (exclude cancelled/converted)."""
        ac_sub = select(AcceptanceForm.document_id).where(
            AcceptanceForm.deleted_at.is_(None),
            AcceptanceForm.document_id.isnot(None),
        )
        result = await self.db.execute(
            select(BusinessDocument)
            .where(
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.doc_type == "quote",
                BusinessDocument.status.notin_(["cancelled", "converted"]),
                not_(BusinessDocument.id.in_(ac_sub)),
            )
            .order_by(BusinessDocument.created_at.desc())
            .limit(500)
        )
        return list(result.scalars().all())

    async def list_available_orders(self) -> list[BusinessDocument]:
        """Return orders not yet linked to any acceptance (exclude cancelled)."""
        ac_sub = select(AcceptanceForm.document_id).where(
            AcceptanceForm.deleted_at.is_(None),
            AcceptanceForm.document_id.isnot(None),
        )
        result = await self.db.execute(
            select(BusinessDocument)
            .options(selectinload(BusinessDocument.customer))
            .where(
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.doc_type == "order",
                BusinessDocument.status != "cancelled",
                not_(BusinessDocument.id.in_(ac_sub)),
            )
            .order_by(BusinessDocument.created_at.desc())
            .limit(500)
        )
        return list(result.scalars().all())

    async def get_by_id(self, acceptance_id: UUID) -> AcceptanceForm | None:
        q = (
            select(AcceptanceForm)
            .where(AcceptanceForm.id == acceptance_id, AcceptanceForm.deleted_at.is_(None))
            .options(
                selectinload(AcceptanceForm.items),
                selectinload(AcceptanceForm.attachments),
                selectinload(AcceptanceForm.document).selectinload(BusinessDocument.customer),
                selectinload(AcceptanceForm.our_acceptor),
            )
        )
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> AcceptanceForm:
        items_data = data.pop("items", [])
        form = AcceptanceForm(**data)
        self.db.add(form)
        await self.db.flush()

        for item_data in items_data:
            item = AcceptanceItem(acceptance_id=form.id, **item_data)
            self.db.add(item)

        await self.db.flush()
        return await self.get_by_id(form.id)

    async def update(self, form: AcceptanceForm, data: dict) -> AcceptanceForm:
        items_data = data.pop("items", None)

        for key, value in data.items():
            if hasattr(form, key):
                setattr(form, key, value)

        if items_data is not None:
            for item in form.items:
                await self.db.delete(item)
            await self.db.flush()
            for item_data in items_data:
                item = AcceptanceItem(acceptance_id=form.id, **item_data)
                self.db.add(item)

        await self.db.flush()
        return await self.get_by_id(form.id)

    async def soft_delete(self, form: AcceptanceForm) -> None:
        form.deleted_at = datetime.now()
        await self.db.flush()

    async def count_by_document(self, document_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(AcceptanceForm)
            .where(AcceptanceForm.document_id == document_id, AcceptanceForm.deleted_at.is_(None))
        )
        return result.scalar()

    async def get_item_by_id(self, item_id: UUID) -> AcceptanceItem | None:
        result = await self.db.execute(
            select(AcceptanceItem).where(AcceptanceItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def update_item_status(self, item: AcceptanceItem, status: str, remark: str | None = None) -> None:
        item.item_status = status
        if remark is not None:
            item.remark = remark
        await self.db.flush()

    async def add_attachment(self, acceptance_id: UUID, filename: str, filepath: str,
                             filesize: int | None, upload_by: UUID | None) -> AcceptanceAttachment:
        att = AcceptanceAttachment(
            acceptance_id=acceptance_id,
            filename=filename,
            filepath=filepath,
            filesize=filesize,
            upload_by=upload_by,
        )
        self.db.add(att)
        await self.db.flush()
        return att

    async def get_attachment_by_id(self, att_id: UUID) -> AcceptanceAttachment | None:
        result = await self.db.execute(
            select(AcceptanceAttachment).where(AcceptanceAttachment.id == att_id)
        )
        return result.scalar_one_or_none()

    async def delete_attachment(self, att: AcceptanceAttachment) -> None:
        await self.db.delete(att)
        await self.db.flush()
