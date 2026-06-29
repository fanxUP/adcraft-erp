from datetime import datetime, date
import uuid as _uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.quote import Quote, QuoteItem, QuoteVersion


class QuoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, quote_id: UUID) -> Quote | None:
        result = await self.db.execute(
            select(Quote).where(Quote.id == quote_id, Quote.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_quotes(self, skip: int = 0, limit: int = 20,
                          status: str | None = None, customer_id: UUID | None = None,
                          keyword: str | None = None,
                          date_from: date | None = None, date_to: date | None = None) -> tuple[list[Quote], int]:
        q = select(Quote).where(Quote.deleted_at.is_(None))
        if status:
            q = q.where(Quote.status == status)
        if customer_id:
            q = q.where(Quote.customer_id == customer_id)
        if keyword:
            q = q.where(
                Quote.quote_no.ilike(f"%{keyword}%") | Quote.project_name.ilike(f"%{keyword}%")
            )
        if date_from:
            q = q.where(Quote.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            q = q.where(Quote.created_at <= datetime.combine(date_to, datetime.max.time()))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Quote.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> Quote:
        items_data = data.pop("items", [])
        # Pre-assign ID so it's available for item foreign keys
        data.setdefault("id", _uuid.uuid4())
        quote = Quote(**data)
        self.db.add(quote)
        for idx, item_data in enumerate(items_data):
            item_data.pop("sort_order", None)  # repo handles ordering
            item = QuoteItem(quote_id=quote.id, sort_order=idx, **item_data)
            self.db.add(item)
        await self.db.flush()
        return quote

    async def update(self, quote: Quote, data: dict) -> Quote:
        for k, v in data.items():
            if v is not None:
                setattr(quote, k, v)
        await self.db.flush()
        return quote

    async def soft_delete(self, quote: Quote) -> Quote:
        from datetime import datetime, timezone
        quote.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return quote

    async def get_items(self, quote_id: UUID) -> list[QuoteItem]:
        result = await self.db.execute(
            select(QuoteItem).where(QuoteItem.quote_id == quote_id).order_by(QuoteItem.sort_order)
        )
        return list(result.scalars().all())

    async def get_item(self, item_id: UUID) -> QuoteItem | None:
        result = await self.db.execute(select(QuoteItem).where(QuoteItem.id == item_id))
        return result.scalar_one_or_none()

    async def create_item(self, quote_id: UUID, data: dict) -> QuoteItem:
        item = QuoteItem(quote_id=quote_id, **data)
        self.db.add(item)
        await self.db.flush()
        return item

    async def update_item(self, item: QuoteItem, data: dict) -> QuoteItem:
        for k, v in data.items():
            if v is not None:
                setattr(item, k, v)
        await self.db.flush()
        return item

    async def delete_item(self, item: QuoteItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def get_next_version_no(self, quote_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(QuoteVersion.version_no)).where(QuoteVersion.quote_id == quote_id)
        )
        max_ver = result.scalar()
        return (max_ver or 0) + 1

    async def create_version(self, quote_id: UUID, version_no: int, snapshot: dict, created_by: UUID | None = None) -> QuoteVersion:
        ver = QuoteVersion(quote_id=quote_id, version_no=version_no, snapshot=snapshot, created_by=created_by)
        self.db.add(ver)
        await self.db.flush()
        return ver
