from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer import CustomerResponse
from app.services.number_generator import generate_customer_no


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerRepository(db)

    def _to_response(self, customer) -> dict:
        return CustomerResponse.model_validate(customer).model_dump(mode="json")

    async def list_customers(self, page: int, page_size: int, keyword: str | None = None, customer_type: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        customers, total = await self.repo.list_customers(skip=skip, limit=page_size, keyword=keyword, customer_type=customer_type)
        return [self._to_response(c) for c in customers], total

    async def get_customer(self, customer_id: UUID) -> dict | None:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            return None
        return self._to_response(customer)

    async def create_customer(self, data: dict) -> dict:
        data["customer_no"] = await generate_customer_no(self.db)
        customer = await self.repo.create(data)
        await self.db.refresh(customer, ["contacts"])
        return self._to_response(customer)

    async def update_customer(self, customer_id: UUID, data: dict) -> dict:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            raise ValueError("客户不存在")
        customer = await self.repo.update(customer, data)
        await self.db.refresh(customer, ["contacts"])
        return self._to_response(customer)

    async def delete_customer(self, customer_id: UUID) -> bool:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            return False
        await self.repo.soft_delete(customer)
        return True
