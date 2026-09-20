from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, exists, func, or_, select, union
from sqlalchemy.orm import selectinload

from app.models.business_document import BusinessDocument
from app.models.contract import Contract, ContractDocument
from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument
from app.models.payment import Expense, Payment, PaymentAllocation, CustomerStatement


def active_unambiguous_contract_links():
    """Build active one-contract-per-order links for legacy receipts.

    Historical payments predate ``payment_allocations`` and only point to an
    order. They are safely attributed during compatibility only when that
    order has exactly one active regular/framework contract. Ambiguous orders
    intentionally produce no link, preventing duplicate debt totals.
    """
    regular = (
        select(
            ContractDocument.document_id.label("document_id"),
            ContractDocument.contract_id.label("contract_id"),
        )
        .select_from(ContractDocument)
        .join(Contract, Contract.id == ContractDocument.contract_id)
        .join(BusinessDocument, BusinessDocument.id == ContractDocument.document_id)
        .where(
            Contract.deleted_at.is_(None),
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        )
    )
    framework = (
        select(
            FrameworkContractProjectDocument.document_id.label("document_id"),
            FrameworkContractProject.contract_id.label("contract_id"),
        )
        .select_from(FrameworkContractProjectDocument)
        .join(
            FrameworkContractProject,
            FrameworkContractProject.id == FrameworkContractProjectDocument.project_id,
        )
        .join(Contract, Contract.id == FrameworkContractProject.contract_id)
        .join(BusinessDocument, BusinessDocument.id == FrameworkContractProjectDocument.document_id)
        .where(
            FrameworkContractProject.deleted_at.is_(None),
            Contract.deleted_at.is_(None),
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        )
    )
    active_links = union(regular, framework).subquery("active_contract_links")
    other_contract = active_links.alias("other_contract")
    return (
        select(active_links.c.document_id, active_links.c.contract_id)
        .where(
            ~exists(
                select(1)
                .select_from(other_contract)
                .where(
                    other_contract.c.document_id == active_links.c.document_id,
                    other_contract.c.contract_id != active_links.c.contract_id,
                )
            )
        )
        .subquery("unambiguous_contract_links")
    )


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        payment_id: UUID,
        *,
        for_update: bool = False,
    ) -> Payment | None:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.document).selectinload(BusinessDocument.customer),
                selectinload(Payment.allocations).selectinload(PaymentAllocation.contract),
                selectinload(Payment.allocations).selectinload(PaymentAllocation.document),
            )
            .where(Payment.id == payment_id)
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_payments(
        self,
        skip: int = 0,
        limit: int = 20,
        order_id: UUID | None = None,
        customer_id: UUID | None = None,
        is_voided: bool | None = None,
        contract_id: UUID | None = None,
    ) -> tuple[list[Payment], int]:
        q = select(Payment).options(
            selectinload(Payment.document).selectinload(BusinessDocument.customer),
            selectinload(Payment.allocations).selectinload(PaymentAllocation.contract),
            selectinload(Payment.allocations).selectinload(PaymentAllocation.document),
        )
        allocation_exists = exists(
            select(PaymentAllocation.id).where(
                PaymentAllocation.payment_id == Payment.id
            )
        )
        if order_id and not contract_id:
            q = q.where(
                or_(
                    Payment.document_id == order_id,
                    exists(
                        select(PaymentAllocation.id).where(
                            PaymentAllocation.payment_id == Payment.id,
                            PaymentAllocation.document_id == order_id,
                        )
                    ),
                )
            )
        if contract_id:
            regular_contract_match = exists(
                select(ContractDocument.id).where(
                    ContractDocument.contract_id == contract_id,
                    ContractDocument.document_id == Payment.document_id,
                )
            )
            framework_contract_match = exists(
                select(FrameworkContractProjectDocument.id)
                .join(
                    FrameworkContractProject,
                    FrameworkContractProject.id == FrameworkContractProjectDocument.project_id,
                )
                .where(
                    FrameworkContractProject.contract_id == contract_id,
                    FrameworkContractProjectDocument.document_id == Payment.document_id,
                )
            )
            allocation_contract_match = exists(
                select(PaymentAllocation.id).where(
                    PaymentAllocation.payment_id == Payment.id,
                    PaymentAllocation.contract_id == contract_id,
                )
            )
            if order_id:
                allocation_order_match = exists(
                    select(PaymentAllocation.id).where(
                        PaymentAllocation.payment_id == Payment.id,
                        PaymentAllocation.contract_id == contract_id,
                        PaymentAllocation.document_id == order_id,
                    )
                )
                q = q.where(
                    or_(
                        allocation_order_match,
                        and_(
                            ~allocation_exists,
                            Payment.document_id == order_id,
                            or_(regular_contract_match, framework_contract_match),
                        ),
                    )
                )
            else:
                q = q.where(
                    or_(
                        allocation_contract_match,
                        and_(
                            ~allocation_exists,
                            or_(regular_contract_match, framework_contract_match),
                        ),
                    )
                )
        if customer_id:
            q = q.where(Payment.customer_id == customer_id)
        if is_voided is not None:
            q = q.where(Payment.is_voided == is_voided)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def void(self, payment: Payment, reason: str) -> Payment:
        payment.is_voided = True
        payment.void_reason = reason
        payment.voided_at = datetime.now()
        await self.db.flush()
        return payment

    async def get_document_paid_sum(self, document_id: UUID) -> float:
        """Return effective paid amount for an order without double counting.

        New receipts are represented by allocations. The legacy fallback keeps
        old order-only payments visible when a historical row has not yet been
        backfilled or has no contract relation.
        """
        allocated = await self.db.execute(
            select(func.coalesce(func.sum(PaymentAllocation.allocated_amount), 0))
            .select_from(PaymentAllocation)
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(
                PaymentAllocation.document_id == document_id,
                Payment.is_voided.is_(False),
            )
        )
        legacy = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(
                Payment.document_id == document_id,
                Payment.is_voided.is_(False),
                ~exists(
                    select(PaymentAllocation.id).where(
                        PaymentAllocation.payment_id == Payment.id
                    )
                ),
            )
        )
        return Decimal(str(allocated.scalar() or 0)) + Decimal(str(legacy.scalar() or 0))

    async def get_contract_order_ids(self, contract_id: UUID) -> list[UUID]:
        """Return active order ids under a regular or framework contract."""
        regular = await self.db.execute(
            select(ContractDocument.document_id)
            .select_from(ContractDocument)
            .join(Contract, Contract.id == ContractDocument.contract_id)
            .join(BusinessDocument, BusinessDocument.id == ContractDocument.document_id)
            .where(
                ContractDocument.contract_id == contract_id,
                Contract.deleted_at.is_(None),
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.status.not_in(("pending_confirm", "cancelled")),
            )
            .order_by(ContractDocument.created_at, ContractDocument.id)
        )
        framework = await self.db.execute(
            select(FrameworkContractProjectDocument.document_id)
            .select_from(FrameworkContractProjectDocument)
            .join(
                FrameworkContractProject,
                FrameworkContractProject.id == FrameworkContractProjectDocument.project_id,
            )
            .join(Contract, Contract.id == FrameworkContractProject.contract_id)
            .join(BusinessDocument, BusinessDocument.id == FrameworkContractProjectDocument.document_id)
            .where(
                FrameworkContractProject.contract_id == contract_id,
                FrameworkContractProject.deleted_at.is_(None),
                Contract.deleted_at.is_(None),
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.status.not_in(("pending_confirm", "cancelled")),
            )
            .order_by(
                FrameworkContractProjectDocument.created_at,
                FrameworkContractProjectDocument.id,
            )
        )
        return list(dict.fromkeys([*regular.scalars().all(), *framework.scalars().all()]))

    async def get_contract_ids_for_document(self, document_id: UUID) -> list[UUID]:
        """Find non-deleted contracts that own an order document."""
        regular = await self.db.execute(
            select(ContractDocument.contract_id)
            .select_from(ContractDocument)
            .join(Contract, Contract.id == ContractDocument.contract_id)
            .where(
                ContractDocument.document_id == document_id,
                Contract.deleted_at.is_(None),
            )
        )
        framework = await self.db.execute(
            select(FrameworkContractProject.contract_id)
            .select_from(FrameworkContractProjectDocument)
            .join(
                FrameworkContractProject,
                FrameworkContractProject.id == FrameworkContractProjectDocument.project_id,
            )
            .join(Contract, Contract.id == FrameworkContractProject.contract_id)
            .where(FrameworkContractProjectDocument.document_id == document_id)
            .where(
                FrameworkContractProject.deleted_at.is_(None),
                Contract.deleted_at.is_(None),
            )
        )
        ids = list(dict.fromkeys([*regular.scalars().all(), *framework.scalars().all()]))
        return ids

    async def get_contract_paid_sum(self, contract_id: UUID) -> Decimal:
        return (await self.get_contract_paid_sums([contract_id])).get(contract_id, Decimal("0"))

    async def get_contract_paid_sums(self, contract_ids: list[UUID]) -> dict[UUID, Decimal]:
        """Aggregate valid allocations plus unbackfilled legacy receipts."""
        if not contract_ids:
            return {}
        paid: dict[UUID, Decimal] = {}
        allocation_result = await self.db.execute(
            select(
                PaymentAllocation.contract_id,
                func.coalesce(func.sum(PaymentAllocation.allocated_amount), 0),
            )
            .select_from(PaymentAllocation)
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(
                PaymentAllocation.contract_id.in_(contract_ids),
                Payment.is_voided.is_(False),
            )
            .group_by(PaymentAllocation.contract_id)
        )
        for contract_id, amount in allocation_result.all():
            paid[contract_id] = Decimal(str(amount or 0))

        allocation_exists = ~exists(
            select(PaymentAllocation.id).where(
                PaymentAllocation.payment_id == Payment.id
            )
        )
        unique_links = active_unambiguous_contract_links()
        legacy_rows = (
            select(
                unique_links.c.contract_id,
                Payment.id.label("payment_id"),
                Payment.amount.label("amount"),
            )
            .select_from(Payment)
            .join(unique_links, unique_links.c.document_id == Payment.document_id)
            .where(
                unique_links.c.contract_id.in_(contract_ids),
                Payment.is_voided.is_(False),
                allocation_exists,
            )
        )
        legacy_result = await self.db.execute(
            select(
                legacy_rows.c.contract_id,
                func.coalesce(func.sum(legacy_rows.c.amount), 0),
            )
            .select_from(legacy_rows)
            .group_by(legacy_rows.c.contract_id)
        )
        for contract_id, amount in legacy_result.all():
            paid[contract_id] = paid.get(contract_id, Decimal("0")) + Decimal(str(amount or 0))
        return paid

    async def get_project_paid_sums(self, project_ids: list[UUID]) -> dict[UUID, Decimal]:
        """Aggregate framework-project allocations with a legacy fallback."""
        if not project_ids:
            return {}
        paid: dict[UUID, Decimal] = {}
        allocation_result = await self.db.execute(
            select(
                FrameworkContractProjectDocument.project_id,
                func.coalesce(func.sum(PaymentAllocation.allocated_amount), 0),
            )
            .select_from(FrameworkContractProjectDocument)
            .join(
                PaymentAllocation,
                PaymentAllocation.document_id == FrameworkContractProjectDocument.document_id,
            )
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .join(
                FrameworkContractProject,
                FrameworkContractProject.id == FrameworkContractProjectDocument.project_id,
            )
            .where(
                FrameworkContractProjectDocument.project_id.in_(project_ids),
                PaymentAllocation.contract_id == FrameworkContractProject.contract_id,
                Payment.is_voided.is_(False),
            )
            .group_by(FrameworkContractProjectDocument.project_id)
        )
        for project_id, amount in allocation_result.all():
            paid[project_id] = Decimal(str(amount or 0))

        legacy_result = await self.db.execute(
            select(
                FrameworkContractProjectDocument.project_id,
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .select_from(FrameworkContractProjectDocument)
            .join(Payment, Payment.document_id == FrameworkContractProjectDocument.document_id)
            .join(
                FrameworkContractProject,
                FrameworkContractProject.id == FrameworkContractProjectDocument.project_id,
            )
            .where(
                FrameworkContractProjectDocument.project_id.in_(project_ids),
                FrameworkContractProject.deleted_at.is_(None),
                Payment.is_voided.is_(False),
                ~exists(
                    select(PaymentAllocation.id).where(
                        PaymentAllocation.payment_id == Payment.id
                    )
                ),
            )
            .group_by(FrameworkContractProjectDocument.project_id)
        )
        for project_id, amount in legacy_result.all():
            paid[project_id] = paid.get(project_id, Decimal("0")) + Decimal(str(amount or 0))
        return paid


class StatementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, statement_id: UUID) -> CustomerStatement | None:
        result = await self.db.execute(select(CustomerStatement).where(CustomerStatement.id == statement_id))
        return result.scalar_one_or_none()

    async def list_statements(self, skip: int = 0, limit: int = 20, customer_id: UUID | None = None) -> tuple[list[CustomerStatement], int]:
        q = select(CustomerStatement)
        if customer_id:
            q = q.where(CustomerStatement.customer_id == customer_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(CustomerStatement.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, statement: CustomerStatement) -> CustomerStatement:
        self.db.add(statement)
        await self.db.flush()
        return statement

    async def update(self, statement: CustomerStatement, data: dict) -> CustomerStatement:
        for k, v in data.items():
            if v is not None:
                setattr(statement, k, v)
        await self.db.flush()
        return statement

    async def get_documents_in_range(self, customer_id: UUID, start: datetime, end: datetime) -> list[BusinessDocument]:
        result = await self.db.execute(
            select(BusinessDocument).where(
                and_(
                    BusinessDocument.customer_id == customer_id,
                    BusinessDocument.doc_type == "order",
                    BusinessDocument.status != "cancelled",
                    BusinessDocument.deleted_at.is_(None),
                    BusinessDocument.order_date >= start.date(),
                    BusinessDocument.order_date <= end.date(),
                )
            ).order_by(
                BusinessDocument.order_date.asc().nullslast(),
                BusinessDocument.created_at.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_payments_in_range(self, customer_id: UUID, start: datetime, end: datetime) -> list[Payment]:
        result = await self.db.execute(
            select(Payment).where(
                and_(
                    Payment.customer_id == customer_id,
                    Payment.is_voided == False,
                    Payment.paid_at >= start,
                    Payment.paid_at <= end,
                )
            ).order_by(Payment.paid_at.asc())
        )
        return list(result.scalars().all())

    async def get_all_documents_unpaid(self, customer_id: UUID) -> list[BusinessDocument]:
        result = await self.db.execute(
            select(BusinessDocument).where(
                and_(
                    BusinessDocument.customer_id == customer_id,
                    BusinessDocument.doc_type == "order",
                    BusinessDocument.deleted_at.is_(None),
                    BusinessDocument.unpaid_amount > 0,
                )
            ).order_by(
                BusinessDocument.order_date.asc().nullslast(),
                BusinessDocument.created_at.asc(),
            )
        )
        return list(result.scalars().all())


class ExpenseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, expense_id: UUID) -> Expense | None:
        result = await self.db.execute(
            select(Expense)
            .options(selectinload(Expense.supplier))
            .where(Expense.id == expense_id, Expense.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_expenses(self, skip: int = 0, limit: int = 20, category: str | None = None,
                            start_date: str | None = None, end_date: str | None = None) -> tuple[list[Expense], int]:
        q = select(Expense).options(selectinload(Expense.supplier)).where(Expense.deleted_at.is_(None))
        if category:
            q = q.where(Expense.category == category)
        if start_date:
            q = q.where(Expense.expense_date >= start_date)
        if end_date:
            q = q.where(Expense.expense_date <= end_date)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Expense.expense_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, expense: Expense) -> Expense:
        self.db.add(expense)
        await self.db.flush()
        return expense

    async def update(
        self,
        expense: Expense,
        data: dict,
        *,
        allow_null_fields: set[str] | None = None,
    ) -> Expense:
        allow_null_fields = allow_null_fields or set()
        for k, v in data.items():
            if v is not None or k in allow_null_fields:
                setattr(expense, k, v)
        await self.db.flush()
        return expense

    async def soft_delete(self, expense: Expense) -> Expense:
        expense.deleted_at = datetime.now()
        await self.db.flush()
        return expense
