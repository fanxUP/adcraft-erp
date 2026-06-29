from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.customer import Customer, CustomerContact


class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_customers(self, skip: int = 0, limit: int = 20, keyword: str | None = None, customer_type: str | None = None) -> tuple[list[Customer], int]:
        q = select(Customer).where(Customer.deleted_at.is_(None))
        if keyword:
            q = q.where(Customer.name.ilike(f"%{keyword}%") | Customer.phone.ilike(f"%{keyword}%"))
        if customer_type:
            q = q.where(Customer.customer_type == customer_type)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(Customer.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> Customer:
        contacts_data = data.pop("contacts", [])
        customer = Customer(**data)
        self.db.add(customer)
        for c in contacts_data:
            contact = CustomerContact(customer_id=customer.id, **c)
            self.db.add(contact)
        await self.db.flush()
        return customer

    async def update(self, customer: Customer, data: dict) -> Customer:
        for key, value in data.items():
            if value is not None:
                setattr(customer, key, value)
        await self.db.flush()
        return customer

    async def soft_delete(self, customer: Customer) -> Customer:
        customer.deleted_at = datetime.utcnow()
        await self.db.flush()
        return customer
