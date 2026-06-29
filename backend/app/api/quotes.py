from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate, QuoteItemUpdate
from app.schemas.common import success, success_paginated
from app.services.quote_service import QuoteService

router = APIRouter(prefix="/quotes", tags=["Quotes"])


@router.get("/")
async def list_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    customer_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    cid = UUID(customer_id) if customer_id else None
    quotes, total = await service.list_quotes(page, page_size, status, cid)
    return success_paginated(quotes, total, page, page_size)


@router.post("/")
async def create_quote(
    data: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.create_quote(data.model_dump())
    return success(quote)


@router.get("/{quote_id}")
async def get_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.get_quote(UUID(quote_id))
    if not quote:
        return {"code": 40401, "message": "报价单不存在", "data": None}
    return success(quote)


@router.put("/{quote_id}")
async def update_quote(
    quote_id: str,
    data: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.update_quote(UUID(quote_id), data.model_dump(exclude_none=True))
    return success(quote)


@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    ok = await service.delete_quote(UUID(quote_id))
    if not ok:
        return {"code": 40401, "message": "报价单不存在", "data": None}
    return success(None)


@router.post("/{quote_id}/items")
async def add_quote_item(
    quote_id: str,
    data: QuoteItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.repo.create_item(UUID(quote_id), data.model_dump())
    await service.calculate_quote(UUID(quote_id))
    return success(service._quote_to_detail(await service.repo.get_by_id(UUID(quote_id))))


@router.put("/{quote_id}/items/{item_id}")
async def update_quote_item(
    quote_id: str,
    item_id: str,
    data: QuoteItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    item = await service.repo.get_item(UUID(item_id))
    if not item:
        return {"code": 40401, "message": "明细不存在", "data": None}
    await service.repo.update_item(item, data.model_dump(exclude_none=True))
    await service.calculate_quote(UUID(quote_id))
    return success(service._quote_to_detail(await service.repo.get_by_id(UUID(quote_id))))


@router.delete("/{quote_id}/items/{item_id}")
async def delete_quote_item(
    quote_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    item = await service.repo.get_item(UUID(item_id))
    if not item:
        return {"code": 40401, "message": "明细不存在", "data": None}
    await service.repo.delete_item(item)
    await service.calculate_quote(UUID(quote_id))
    return success(service._quote_to_detail(await service.repo.get_by_id(UUID(quote_id))))


@router.post("/{quote_id}/calculate")
async def calculate_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.calculate_quote(UUID(quote_id))
    return success(quote)


@router.post("/{quote_id}/confirm")
async def confirm_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.confirm_quote(UUID(quote_id))
    return success(quote)


@router.post("/{quote_id}/convert-to-order")
async def convert_quote_to_order(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    order = await service.convert_to_order(UUID(quote_id), current_user.id)
    return success(order)
