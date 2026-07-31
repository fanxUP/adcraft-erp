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

    async def get_customer_tree(self) -> list[dict]:
        """Return customer type -> level -> customers tree structure."""
        from sqlalchemy import select
        from app.models.customer import Customer
        q = select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.customer_type, Customer.level, Customer.name)
        result = await self.db.execute(q)
        customers = result.scalars().all()

        type_map: dict[str, dict[str, list[dict]]] = {}
        for c in customers:
            ct = c.customer_type or "未分类"
            lv = c.level or "未分级"
            type_map.setdefault(ct, {}).setdefault(lv, []).append({"id": str(c.id), "name": c.name})

        tree = []
        for ct in sorted(type_map.keys()):
            levels = []
            for lv in sorted(type_map[ct].keys()):
                custs = type_map[ct][lv]
                levels.append({"level": lv, "customers": custs, "count": len(custs)})
            tree.append({"customer_type": ct, "levels": levels, "count": sum(l["count"] for l in levels)})
        return tree
