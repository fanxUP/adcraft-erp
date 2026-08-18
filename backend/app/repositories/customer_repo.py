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
        # 先 flush 生成 customer.id（列默认值仅在 INSERT 时生效），
        # 否则联系人会带着 customer_id=None 入库，违反非空约束
        await self.db.flush()
        for c in contacts_data:
            contact = CustomerContact(customer_id=customer.id, **c)
            self.db.add(contact)
        await self.db.flush()
        return customer

    async def update(self, customer: Customer, data: dict) -> Customer:
        contacts_data = data.pop("contacts", None)
        for key, value in data.items():
            setattr(customer, key, value)
        if contacts_data is not None:
            # Delete all existing contacts
            result = await self.db.execute(
                select(CustomerContact).where(CustomerContact.customer_id == customer.id)
            )
            for c in result.scalars().all():
                await self.db.delete(c)
            # Create new contacts
            for c in contacts_data:
                contact = CustomerContact(customer_id=customer.id, **c)
                self.db.add(contact)
        await self.db.flush()
        return customer

    async def upsert_contact(self, customer_id: UUID, name: str, phone: str | None = None) -> CustomerContact | None:
        """按 (客户, 姓名) 查找联系人：存在则更新电话，不存在则新增。

        供单据保存时反向同步：单据里填的联系人自动存入客户管理的联系人列表。
        """
        name = (name or "").strip()
        if not name:
            return None
        result = await self.db.execute(
            select(CustomerContact).where(
                CustomerContact.customer_id == customer_id,
                CustomerContact.name == name,
            )
        )
        contact = result.scalar_one_or_none()
        if contact:
            if phone:
                contact.phone = phone
        else:
            contact = CustomerContact(customer_id=customer_id, name=name, phone=phone)
            self.db.add(contact)
        await self.db.flush()
        return contact

    async def soft_delete(self, customer: Customer) -> Customer:
        customer.deleted_at = datetime.now()
        await self.db.flush()
        return customer
