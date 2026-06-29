from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.repositories.inventory_repo import InventoryRepository
from app.models.inventory import InventoryItem


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InventoryRepository(db)

    async def list_items(self, page: int, page_size: int, keyword: str | None = None,
                         category: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        items, total = await self.repo.list_items(skip, page_size, keyword, category)
        return [self._item_to_dict(i) for i in items], total

    async def get_item(self, item_id: UUID) -> dict | None:
        item = await self.repo.get_by_id(item_id)
        if not item:
            return None
        return self._item_to_dict(item)

    async def create_item(self, data: dict) -> dict:
        item = await self.repo.create(data)
        return self._item_to_dict(item)

    async def update_item(self, item_id: UUID, data: dict) -> dict:
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("库存物料不存在")
        item = await self.repo.update(item, data)
        return self._item_to_dict(item)

    async def list_records(self, page: int, page_size: int, item_id: UUID | None = None,
                           record_type: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        records, total = await self.repo.list_records(skip, page_size, item_id, record_type)
        result = []
        for r in records:
            item_name = await self._item_name(r.item_id)
            result.append(self._record_to_dict(r, item_name))
        return result, total

    async def stock_in(self, data: dict) -> dict:
        """入库"""
        item_id = UUID(data["item_id"])
        qty = Decimal(str(data["quantity"]))
        unit_cost = Decimal(str(data.get("unit_cost", 0)))
        total_cost = qty * unit_cost

        record_data = {
            "item_id": item_id, "record_type": "in",
            "quantity": float(qty), "unit_cost": float(unit_cost),
            "total_cost": float(total_cost),
            "order_id": UUID(data["order_id"]) if data.get("order_id") else None,
            "remark": data.get("remark"),
            "operated_at": datetime.now(timezone.utc),
        }
        record = await self.repo.create_record(record_data)

        # Update item quantity and cost
        item = await self.repo.get_by_id(item_id)
        if item:
            new_qty = Decimal(str(item.quantity)) + qty
            item.quantity = float(new_qty)
            item.unit_cost = float(unit_cost)  # simple weighted cost per latest batch
            await self.db.flush()

        item_name = await self._item_name(item_id)
        return self._record_to_dict(record, item_name)

    async def stock_out(self, data: dict) -> dict:
        """出库"""
        item_id = UUID(data["item_id"])
        qty = Decimal(str(data["quantity"]))

        item = await self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("库存物料不存在")
        if Decimal(str(item.quantity)) < qty:
            raise ValueError("库存不足")

        unit_cost = Decimal(str(item.unit_cost))
        total_cost = qty * unit_cost

        record_data = {
            "item_id": item_id, "record_type": "out",
            "quantity": float(qty), "unit_cost": float(unit_cost),
            "total_cost": float(total_cost),
            "order_id": UUID(data["order_id"]) if data.get("order_id") else None,
            "remark": data.get("remark"),
            "operated_at": datetime.now(timezone.utc),
        }
        record = await self.repo.create_record(record_data)

        item.quantity = float(Decimal(str(item.quantity)) - qty)
        await self.db.flush()

        item_name = await self._item_name(item_id)
        return self._record_to_dict(record, item_name)

    async def _item_name(self, item_id: UUID) -> str | None:
        result = await self.db.execute(select(InventoryItem.material_name).where(InventoryItem.id == item_id))
        return result.scalar_one_or_none()

    def _item_to_dict(self, i) -> dict:
        return {
            "id": str(i.id), "material_name": i.material_name,
            "material_unit": i.material_unit,
            "category": i.category, "spec": i.spec,
            "quantity": float(i.quantity),
            "min_quantity": float(i.min_quantity),
            "unit_cost": float(i.unit_cost),
            "remark": i.remark,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }

    def _record_to_dict(self, r, item_name: str | None = None) -> dict:
        return {
            "id": str(r.id), "item_id": str(r.item_id),
            "item_name": item_name, "record_type": r.record_type,
            "quantity": float(r.quantity),
            "unit_cost": float(r.unit_cost),
            "total_cost": float(r.total_cost),
            "order_id": str(r.order_id) if r.order_id else None,
            "remark": r.remark,
            "operated_at": r.operated_at.isoformat() if r.operated_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
