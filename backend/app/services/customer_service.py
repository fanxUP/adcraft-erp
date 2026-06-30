from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.customer_repo import CustomerRepository
from app.services.number_generator import generate_customer_no


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerRepository(db)

    def _to_response(self, customer) -> dict:
        return {
            "id": str(customer.id),
            "customer_no": customer.customer_no,
            "name": customer.name,
            "customer_type": customer.customer_type,
            "level": customer.level,
            "phone": customer.phone,
            "wechat": customer.wechat,
            "address": customer.address,
            "tax_no": customer.tax_no,
            "invoice_info": customer.invoice_info,
            "default_payment_days": customer.default_payment_days,
            "default_discount": float(customer.default_discount) if customer.default_discount else 1.0,
            "remark": customer.remark,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "contacts": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "phone": c.phone,
                    "wechat": c.wechat,
                    "position": c.position,
                    "is_primary": c.is_primary,
                    "remark": c.remark,
                }
                for c in (customer.contacts or [])
            ],
        }

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
        return self._to_response(customer)

    async def delete_customer(self, customer_id: UUID) -> bool:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            return False
        await self.repo.soft_delete(customer)
        return True
