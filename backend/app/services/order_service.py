"""OrderService — thin wrapper around BusinessDocumentService with doc_type='order'."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.business_document_service import BusinessDocumentService


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inner = BusinessDocumentService(db, doc_type='order')

    async def list_orders(self, page: int, page_size: int, status: str | None = None,
                          customer_id: UUID | None = None, keyword: str | None = None) -> tuple[list, int]:
        return await self.inner.list_all(page, page_size, status, customer_id, keyword)

    async def get_order(self, order_id: UUID) -> dict | None:
        return await self.inner.get_by_id(order_id)

    async def change_status(self, order_id: UUID, to_status: str,
                            reason: str | None, operated_by: UUID) -> dict:
        return await self.inner.change_status(order_id, to_status, reason, operated_by)

    async def set_cost(self, order_id: UUID, cost_amount: float) -> dict:
        return await self.inner.set_cost(order_id, cost_amount)

    async def auto_calculate_cost(self, order_id: UUID) -> dict:
        return await self.inner.auto_calculate_cost(order_id)

    async def delete_order(self, order_id: UUID) -> None:
        await self.inner.delete(order_id)

    async def convert_to_quote(self, order_id: UUID, created_by: UUID) -> dict:
        return await self.inner.convert_doc_type(order_id, 'quote', created_by)

    async def list_deleted(self, page: int, page_size: int,
                           keyword: str | None = None) -> tuple[list, int]:
        return await self.inner.list_deleted(page, page_size, keyword)

    async def restore_order(self, order_id: UUID) -> dict:
        return await self.inner.restore(order_id)
