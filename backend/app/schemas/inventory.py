from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InventoryItemCreate(BaseModel):
    material_id: str | None = None
    material_name: str = Field(..., max_length=255)
    material_unit: str | None = None
    category: str | None = None
    spec: str | None = None
    quantity: Decimal = Decimal("0")
    min_quantity: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    remark: str | None = None


class InventoryItemUpdate(BaseModel):
    material_name: str | None = None
    material_unit: str | None = None
    category: str | None = None
    spec: str | None = None
    min_quantity: Decimal | None = None
    unit_cost: Decimal | None = None
    remark: str | None = None


class InventoryItemResponse(BaseModel):
    id: str
    material_name: str
    material_unit: str | None = None
    category: str | None = None
    spec: str | None = None
    quantity: float
    min_quantity: float
    unit_cost: float
    remark: str | None = None
    created_at: str | None = None


class StockRecordCreate(BaseModel):
    item_id: str = Field(...)
    record_type: str = Field(...)  # in, out
    quantity: Decimal = Field(...)
    unit_cost: Decimal = Decimal("0")
    document_id: str | None = None
    order_id: str | None = None  # 向后兼容，映射到 document_id
    remark: str | None = None


class StockRecordResponse(BaseModel):
    id: str
    item_id: str
    item_name: str | None = None
    record_type: str
    quantity: float
    unit_cost: float
    total_cost: float
    document_id: str | None = None
    order_id: str | None = None  # 向后兼容
    remark: str | None = None
    operated_at: str | None = None
    created_at: str | None = None
