"""QuoteService — thin wrapper around BusinessDocumentService with doc_type='quote'."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.business_document_service import BusinessDocumentService


class QuoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inner = BusinessDocumentService(db, doc_type='quote')

    async def list_quotes(self, page: int, page_size: int, status: str | None = None,
                          customer_id: UUID | None = None, keyword: str | None = None,
                          date_from=None, date_to=None) -> tuple[list, int]:
        # Exclude converted quotes by default (existing behavior)
        return await self.inner.list_all(page, page_size, status, customer_id, keyword,
                                         exclude_status="converted")

    async def get_quote(self, quote_id: UUID) -> dict | None:
        return await self.inner.get_by_id(quote_id)

    async def create_quote(self, data: dict) -> dict:
        return await self.inner.create(data)

    async def update_quote(self, quote_id: UUID, data: dict) -> dict:
        return await self.inner.update(quote_id, data)

    async def delete_quote(self, quote_id: UUID) -> bool:
        return await self.inner.delete(quote_id)

    async def calculate_quote(self, quote_id: UUID) -> dict:
        """Recalculate quote totals (compatibility wrapper)."""
        doc = await self.inner.repo.get_by_id(quote_id)
        if doc:
            from app.services.business_document_service import BusinessDocumentService
            # re-trigger calculation via the inner method
            await self.inner._calculate_quote(quote_id)
        return await self.get_quote(quote_id)

    async def confirm_quote(self, quote_id: UUID) -> dict:
        return await self.inner.change_status(quote_id, "confirmed", None, None)

    async def revert_to_draft(self, quote_id: UUID) -> dict:
        return await self.inner.change_status(quote_id, "draft", None, None)

    async def cancel_quote(self, quote_id: UUID) -> dict:
        return await self.inner.change_status(quote_id, "cancelled", None, None)

    async def convert_to_order(self, quote_id: UUID, created_by: UUID) -> dict:
        return await self.inner.convert_doc_type(quote_id, 'order', created_by)

    async def add_items(self, quote_id: UUID, items_data: list[dict]) -> dict:
        return await self.inner.add_items(quote_id, items_data)
