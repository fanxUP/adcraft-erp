from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.contract import Contract, ContractOrder, ContractQuote


class ContractRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, contract_id: UUID) -> Contract | None:
        result = await self.db.execute(
            select(Contract)
            .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
            .options(selectinload(Contract.orders), selectinload(Contract.quotes))
        )
        return result.scalar_one_or_none()

    async def list_contracts(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        keyword: str | None = None,
        customer_id: str | None = None,
    ) -> tuple[list[Contract], int]:
        q = select(Contract).where(Contract.deleted_at.is_(None))
        if status:
            q = q.where(Contract.status == status)
        if keyword:
            q = q.where(
                Contract.contract_no.ilike(f"%{keyword}%")
                | Contract.project_name.ilike(f"%{keyword}%")
                | Contract.customer_name.ilike(f"%{keyword}%")
            )
        if customer_id:
            q = q.where(Contract.customer_id == customer_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(Contract.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> Contract:
        order_ids = data.pop("order_ids", [])
        quote_ids = data.pop("quote_ids", [])
        contract = Contract(**data)
        if contract.id is None:
            contract.id = uuid4()
        self.db.add(contract)

        for oid in order_ids:
            self.db.add(ContractOrder(contract_id=contract.id, order_id=oid))
        for qid in quote_ids:
            self.db.add(ContractQuote(contract_id=contract.id, quote_id=qid))

        await self.db.flush()
        return contract

    async def update(self, contract: Contract, data: dict) -> Contract:
        order_ids = data.pop("order_ids", None)
        quote_ids = data.pop("quote_ids", None)

        for key, value in data.items():
            setattr(contract, key, value)

        if order_ids is not None:
            result = await self.db.execute(
                select(ContractOrder).where(ContractOrder.contract_id == contract.id)
            )
            for row in result.scalars().all():
                await self.db.delete(row)
            for oid in order_ids:
                self.db.add(ContractOrder(contract_id=contract.id, order_id=oid))

        if quote_ids is not None:
            result = await self.db.execute(
                select(ContractQuote).where(ContractQuote.contract_id == contract.id)
            )
            for row in result.scalars().all():
                await self.db.delete(row)
            for qid in quote_ids:
                self.db.add(ContractQuote(contract_id=contract.id, quote_id=qid))

        await self.db.flush()
        return contract

    async def soft_delete(self, contract: Contract) -> Contract:
        contract.deleted_at = datetime.now()
        await self.db.flush()
        return contract
