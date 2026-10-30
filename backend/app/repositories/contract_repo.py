from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Date, and_, case, cast, exists, not_, or_, select, func
from sqlalchemy.orm import selectinload

from app.models.contract import Contract, ContractDocument


def contract_total_expression():
    """An existing zero-valued project scope must not fall back to an old total."""
    from app.models.framework_contract import FrameworkContractProject
    projects = select(func.sum(FrameworkContractProject.project_amount)).where(
        FrameworkContractProject.contract_id == Contract.id,
        FrameworkContractProject.deleted_at.is_(None),
    ).correlate(Contract).scalar_subquery()
    return func.coalesce(projects, Contract.total_amount, 0)


def contract_status_expression(today):
    from app.models.payment import Payment, PaymentAllocation
    from app.repositories.payment_repo import active_unambiguous_contract_links
    allocated = select(func.coalesce(func.sum(PaymentAllocation.allocated_amount), 0)).join(
        Payment, Payment.id == PaymentAllocation.payment_id,
    ).where(PaymentAllocation.contract_id == Contract.id, Payment.is_voided.is_(False)).correlate(Contract).scalar_subquery()
    links = active_unambiguous_contract_links()
    legacy = select(func.coalesce(func.sum(Payment.amount), 0)).join(
        links, links.c.document_id == Payment.document_id,
    ).where(links.c.contract_id == Contract.id, Payment.is_voided.is_(False),
        ~exists(select(PaymentAllocation.id).where(PaymentAllocation.payment_id == Payment.id)),
    ).correlate(Contract).scalar_subquery()
    total = contract_total_expression()
    return case(
        (Contract.status.in_(["cancelled", "terminated"]), Contract.status),
        (and_(total > 0, allocated + legacy >= total,
              or_(Contract.end_date.is_(None), cast(Contract.end_date, Date) < today)), "completed"),
        (or_(cast(Contract.start_date, Date) <= today, Contract.status.in_(["active", "completed"])), "active"),
        else_=Contract.status,
    )


class ContractRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, contract_id: UUID) -> Contract | None:
        result = await self.db.execute(
            select(Contract)
            .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
            .options(selectinload(Contract.documents))
        )
        return result.scalar_one_or_none()

    async def list_contracts(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        keyword: str | None = None,
        customer_id: str | None = None,
        contract_type: str | None = None,
        exclude_contract_type: str | None = None,
        business_day=None,
    ) -> tuple[list[Contract], int]:
        q = select(Contract).options(
            selectinload(Contract.documents),
        ).where(Contract.deleted_at.is_(None))
        if status:
            if business_day is None:
                from zoneinfo import ZoneInfo
                business_day = datetime.now(ZoneInfo("Asia/Shanghai")).date()
            q = q.where(contract_status_expression(business_day) == status)
        if keyword:
            q = q.where(
                Contract.contract_no.ilike(f"%{keyword}%")
                | Contract.project_name.ilike(f"%{keyword}%")
                | Contract.customer_name.ilike(f"%{keyword}%")
            )
        if customer_id:
            q = q.where(Contract.customer_id == customer_id)
        if contract_type:
            q = q.where(Contract.contract_type == contract_type)
        if exclude_contract_type:
            q = q.where(Contract.contract_type != exclude_contract_type)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(Contract.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def list_orders_without_contract(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
    ) -> tuple[list["BusinessDocument"], int]:
        """返回未被任何（未删除）合同/框架合同项目关联的订单（排除已取消）。"""
        from app.models.business_document import BusinessDocument
        from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument

        # 只统计未删除合同/框架项目的关联：软删除合同不再占用订单
        used_sub = (
            select(ContractDocument.document_id)
            .join(Contract, Contract.id == ContractDocument.contract_id)
            .where(Contract.deleted_at.is_(None))
        )
        fw_sub = (
            select(FrameworkContractProjectDocument.document_id)
            .join(FrameworkContractProject, FrameworkContractProject.id == FrameworkContractProjectDocument.project_id)
            .where(FrameworkContractProject.deleted_at.is_(None))
        )
        q = select(BusinessDocument).where(
            BusinessDocument.deleted_at.is_(None),
            BusinessDocument.doc_type == "order",
            BusinessDocument.status != "cancelled",
            not_(BusinessDocument.id.in_(used_sub)),
            not_(BusinessDocument.id.in_(fw_sub)),
        )
        if keyword:
            q = q.where(
                BusinessDocument.doc_no.ilike(f"%{keyword}%")
                | BusinessDocument.customer_name.ilike(f"%{keyword}%")
                | BusinessDocument.project_name.ilike(f"%{keyword}%")
            )

        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        q = q.order_by(BusinessDocument.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> Contract:
        document_ids = data.pop("document_ids", [])
        contract = Contract(**data)
        if contract.id is None:
            contract.id = uuid4()
        self.db.add(contract)

        for did in document_ids:
            self.db.add(ContractDocument(contract_id=contract.id, document_id=did))

        await self.db.flush()
        return contract

    async def update(self, contract: Contract, data: dict) -> Contract:
        document_ids = data.pop("document_ids", None)

        for key, value in data.items():
            setattr(contract, key, value)

        if document_ids is not None:
            result = await self.db.execute(
                select(ContractDocument).where(ContractDocument.contract_id == contract.id)
            )
            for row in result.scalars().all():
                await self.db.delete(row)
            for did in document_ids:
                self.db.add(ContractDocument(contract_id=contract.id, document_id=did))

        await self.db.flush()
        return contract

    async def soft_delete(self, contract: Contract) -> Contract:
        contract.deleted_at = datetime.now()
        await self.db.flush()
        return contract
