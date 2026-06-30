from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.payment import Payment, CustomerStatement, Expense
from app.models.order import Order


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def list_payments(self, skip: int = 0, limit: int = 20, order_id: UUID | None = None,
                            customer_id: UUID | None = None, is_voided: bool | None = None) -> tuple[list[Payment], int]:
        q = select(Payment)
        if order_id:
            q = q.where(Payment.order_id == order_id)
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

    async def get_order_paid_sum(self, order_id: UUID) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.order_id == order_id, Payment.is_voided == False)
        )
        return float(result.scalar() or 0)


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

    async def get_orders_in_range(self, customer_id: UUID, start: datetime, end: datetime) -> list[Order]:
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.customer_id == customer_id,
                    Order.deleted_at.is_(None),
                    Order.created_at >= start,
                    Order.created_at <= end,
                )
            ).order_by(Order.created_at.asc())
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

    async def get_all_orders_unpaid(self, customer_id: UUID) -> list[Order]:
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.customer_id == customer_id,
                    Order.deleted_at.is_(None),
                    Order.unpaid_amount > 0,
                )
            ).order_by(Order.created_at.asc())
        )
        return list(result.scalars().all())


class ExpenseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, expense_id: UUID) -> Expense | None:
        result = await self.db.execute(
            select(Expense).where(Expense.id == expense_id, Expense.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_expenses(self, skip: int = 0, limit: int = 20, category: str | None = None,
                            start_date: str | None = None, end_date: str | None = None) -> tuple[list[Expense], int]:
        q = select(Expense).where(Expense.deleted_at.is_(None))
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

    async def update(self, expense: Expense, data: dict) -> Expense:
        for k, v in data.items():
            if v is not None:
                setattr(expense, k, v)
        await self.db.flush()
        return expense

    async def soft_delete(self, expense: Expense) -> Expense:
        expense.deleted_at = datetime.now()
        await self.db.flush()
        return expense
