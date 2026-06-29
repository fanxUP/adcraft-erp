from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success, success_paginated, error
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, StockRecordCreate
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/items")
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    items, total = await service.list_items(page, page_size, keyword, category)
    return success_paginated(items, total, page, page_size)


@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    item = await service.get_item(UUID(item_id))
    if not item:
        return error(40401, "物料不存在")
    return success(item)


@router.post("/items")
async def create_item(
    data: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    item = await service.create_item(data.model_dump())
    return success(item)


@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    data: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    try:
        item = await service.update_item(UUID(item_id), data.model_dump(exclude_none=True))
        return success(item)
    except ValueError as e:
        return error(40401, str(e))


@router.get("/records")
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: str | None = None,
    record_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    iid = UUID(item_id) if item_id else None
    records, total = await service.list_records(page, page_size, iid, record_type)
    return success_paginated(records, total, page, page_size)


@router.post("/stock-in")
async def stock_in(
    data: StockRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    record = await service.stock_in(data.model_dump())
    return success(record)


@router.post("/stock-out")
async def stock_out(
    data: StockRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    try:
        record = await service.stock_out(data.model_dump())
        return success(record)
    except ValueError as e:
        return error(40001, str(e))
