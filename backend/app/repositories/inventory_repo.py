import uuid as _uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.inventory import InventoryItem, StockRecord


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_items(self, skip: int = 0, limit: int = 20,
                         keyword: str | None = None, category: str | None = None) -> tuple[list[InventoryItem], int]:
        q = select(InventoryItem)
        if keyword:
            q = q.where(InventoryItem.material_name.ilike(f"%{keyword}%"))
        if category:
            q = q.where(InventoryItem.category == category)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(InventoryItem.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, item_id: UUID) -> InventoryItem | None:
        result = await self.db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> InventoryItem:
        data.setdefault("id", _uuid.uuid4())
        item = InventoryItem(**data)
        self.db.add(item)
        await self.db.flush()
        return item

    async def update(self, item: InventoryItem, data: dict) -> InventoryItem:
        for k, v in data.items():
            if v is not None:
                setattr(item, k, v)
        await self.db.flush()
        return item

    async def list_records(self, skip: int = 0, limit: int = 20,
                           item_id: UUID | None = None, record_type: str | None = None) -> tuple[list[StockRecord], int]:
        q = select(StockRecord)
        if item_id:
            q = q.where(StockRecord.item_id == item_id)
        if record_type:
            q = q.where(StockRecord.record_type == record_type)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(StockRecord.operated_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_record(self, data: dict) -> StockRecord:
        data.setdefault("id", _uuid.uuid4())
        record = StockRecord(**data)
        self.db.add(record)
        await self.db.flush()
        return record
