from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.order import Order
from app.models.payment import Payment
from app.models.task import DesignTask, ProductionTask, InstallationTask
from app.models.customer import Customer
from app.models.quote import Quote
from app.models.contract import Contract


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self) -> dict:
        now = datetime.now()
        today = now.date()
        month_start = today.replace(day=1)

        today_start = datetime(today.year, today.month, today.day)
        today_end = datetime(today.year, today.month, today.day, 23, 59, 59)
        month_start_dt = datetime(month_start.year, month_start.month, 1)

        today_orders = await self._sum_orders(today_start, today_end)
        month_orders = await self._sum_orders(month_start_dt, now)

        today_payments = await self._sum_payments(today_start, today_end)
        month_payments = await self._sum_payments(month_start_dt, now)

        month_unpaid = await self._calc_month_unpaid(month_start_dt, now)

        pending_design = await self._count_tasks(DesignTask, ["pending", "designing", "pending_review", "revision"])
        pending_production = await self._count_tasks(ProductionTask, ["pending", "queued", "in_progress", "qc_check", "rework"])
        pending_installation = await self._count_tasks(InstallationTask, ["pending", "assigned", "in_progress", "pending_acceptance"])

        overdue_orders = await self._count_overdue_orders()

        customer_debt_ranking = await self._customer_debt_ranking()

        return {
            "today_order_amount": float(today_orders or 0),
            "today_payment_amount": float(today_payments or 0),
            "month_order_amount": float(month_orders or 0),
            "month_payment_amount": float(month_payments or 0),
            "month_unpaid_amount": float(month_unpaid or 0),
            "pending_design_count": pending_design,
            "pending_production_count": pending_production,
            "pending_installation_count": pending_installation,
            "overdue_order_count": overdue_orders,
            "customer_debt_ranking": customer_debt_ranking,
        }

    async def get_daily_report(self, report_date: str | None = None) -> dict:
        if report_date:
            d = datetime.fromisoformat(report_date)
        else:
            d = datetime.now()
        day_start = datetime(d.year, d.month, d.day)
        day_end = datetime(d.year, d.month, d.day, 23, 59, 59)

        orders = await self._list_orders_in_range(day_start, day_end)
        payments = await self._list_payments_in_range(day_start, day_end)
        new_customers = await self._count_new_customers(day_start, day_end)

        return {
            "date": d.strftime("%Y-%m-%d"),
            "order_count": len(orders),
            "order_amount": float(sum(o.total_amount for o in orders)),
            "payment_count": len(payments),
            "payment_amount": float(sum(p.amount for p in payments)),
            "new_customer_count": new_customers,
            "orders": [
                {"id": str(o.id), "order_no": o.order_no, "project_name": o.project_name,
                 "total_amount": float(o.total_amount), "status": o.status}
                for o in orders
            ],
            "payments": [
                {"id": str(p.id), "payment_no": p.payment_no, "amount": float(p.amount),
                 "payment_method": p.payment_method, "is_voided": p.is_voided}
                for p in payments
            ],
        }

    async def get_monthly_report(self, year: int | None = None, month: int | None = None) -> dict:
        now = datetime.now()
        y = year or now.year
        m = month or now.month
        month_start = datetime(y, m, 1)
        if m == 12:
            month_end = datetime(y + 1, 1, 1)
        else:
            month_end = datetime(y, m + 1, 1)

        orders = await self._list_orders_in_range(month_start, month_end)
        payments = await self._list_payments_in_range(month_start, month_end)

        order_amount = float(sum(o.total_amount for o in orders))
        payment_amount = float(sum(p.amount for p in payments))

        status_breakdown = {}
        for o in orders:
            s = o.status
            status_breakdown[s] = status_breakdown.get(s, 0) + 1

        return {
            "year": y,
            "month": m,
            "order_count": len(orders),
            "order_amount": order_amount,
            "payment_count": len(payments),
            "payment_amount": payment_amount,
            "unpaid_amount": order_amount - payment_amount,
            "status_breakdown": status_breakdown,
            "orders": [
                {"id": str(o.id), "order_no": o.order_no, "project_name": o.project_name,
                 "total_amount": float(o.total_amount), "paid_amount": float(o.paid_amount),
                 "unpaid_amount": float(o.unpaid_amount), "status": o.status}
                for o in orders
            ],
        }

    async def get_customer_debt(self) -> list:
        """Return all customers with their contracts, orders and quotes for the receivables overview."""
        # Fetch all active customers
        c_result = await self.db.execute(
            select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.name)
        )
        customers = c_result.scalars().all()

        if not customers:
            return []

        customer_ids = [c.id for c in customers]

        # Batch-fetch all contracts grouped by customer
        contracts_result = await self.db.execute(
            select(Contract)
            .where(Contract.deleted_at.is_(None), Contract.customer_id.in_(customer_ids))
            .order_by(Contract.created_at.desc())
        )
        all_contracts = contracts_result.scalars().all()

        # Batch-fetch all orders grouped by customer
        orders_result = await self.db.execute(
            select(Order)
            .where(Order.deleted_at.is_(None), Order.customer_id.in_(customer_ids))
            .order_by(Order.created_at.desc())
        )
        all_orders = orders_result.scalars().all()

        # Batch-fetch all quotes grouped by customer (exclude converted ones)
        quotes_result = await self.db.execute(
            select(Quote)
            .where(Quote.deleted_at.is_(None), Quote.customer_id.in_(customer_ids), Quote.status != "converted")
            .order_by(Quote.created_at.desc())
        )
        all_quotes = quotes_result.scalars().all()

        # Batch-fetch last payment date per customer
        lp_result = await self.db.execute(
            select(
                Payment.customer_id,
                func.max(Payment.paid_at).label("last_payment"),
            )
            .where(Payment.customer_id.in_(customer_ids), Payment.is_voided == False)
            .group_by(Payment.customer_id)
        )
        last_payments = {r.customer_id: r.last_payment for r in lp_result.all()}

        # Build response
        debts = []
        for c in customers:
            customer_contracts = [ct for ct in all_contracts if ct.customer_id == c.id]
            customer_orders = [o for o in all_orders if o.customer_id == c.id]
            customer_quotes = [q for q in all_quotes if q.customer_id == c.id]

            # Skip customers with no contracts, orders and no quotes
            if not customer_contracts and not customer_orders and not customer_quotes:
                continue

            # Stats from contracts
            total_contract = sum(ct.total_amount for ct in customer_contracts)
            total_paid = sum(ct.paid_amount for ct in customer_contracts)
            total_debt = sum(ct.unpaid_amount for ct in customer_contracts)
            lp = last_payments.get(c.id)

            debts.append({
                "customer_id": str(c.id),
                "customer_name": c.name,
                "debt_amount": float(total_debt),
                "total_order_amount": float(total_contract),
                "total_paid": float(total_paid),
                "contract_count": len(customer_contracts),
                "order_count": len(customer_orders),
                "quote_count": len(customer_quotes),
                "last_payment_date": lp.isoformat() if lp else None,
                "contracts": [
                    {
                        "id": str(ct.id),
                        "contract_no": ct.contract_no,
                        "project_name": ct.project_name,
                        "total_amount": float(ct.total_amount),
                        "paid_amount": float(ct.paid_amount),
                        "unpaid_amount": float(ct.unpaid_amount),
                        "status": ct.status,
                        "contract_type": ct.contract_type,
                    }
                    for ct in customer_contracts
                ],
                "orders": [
                    {
                        "id": str(o.id),
                        "order_no": o.order_no,
                        "project_name": o.project_name,
                        "total_amount": float(o.total_amount),
                        "paid_amount": float(o.paid_amount),
                        "unpaid_amount": float(o.unpaid_amount),
                        "status": o.status,
                    }
                    for o in customer_orders
                ],
                "quotes": [
                    {
                        "id": str(q.id),
                        "quote_no": q.quote_no,
                        "project_name": q.project_name,
                        "total_amount": float(q.total_amount),
                        "status": q.status,
                    }
                    for q in customer_quotes
                ],
            })
        return debts

    async def _sum_orders(self, start: datetime, end: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0))
            .where(and_(Order.deleted_at.is_(None), Order.created_at >= start, Order.created_at <= end))
        )
        return result.scalar() or 0

    async def _sum_payments(self, start: datetime, end: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(and_(Payment.is_voided == False, Payment.created_at >= start, Payment.created_at <= end))
        )
        return result.scalar() or 0

    async def _calc_month_unpaid(self, start: datetime, end: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Order.unpaid_amount), 0))
            .where(and_(Order.deleted_at.is_(None), Order.created_at >= start, Order.created_at <= end))
        )
        return result.scalar() or 0

    async def _count_tasks(self, model, statuses: list[str]) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(model).where(model.status.in_(statuses))
        )
        return result.scalar() or 0

    async def _count_overdue_orders(self) -> int:
        now = datetime.now()
        result = await self.db.execute(
            select(func.count()).select_from(Order).where(
                and_(
                    Order.deleted_at.is_(None),
                    Order.status.in_(["confirmed", "in_progress", "in_production", "in_installation"]),
                    Order.delivery_deadline < now,
                )
            )
        )
        return result.scalar() or 0

    async def _customer_debt_ranking(self, limit: int = 10) -> list:
        result = await self.db.execute(
            select(Order.customer_id, func.sum(Order.unpaid_amount).label("debt"))
            .where(Order.deleted_at.is_(None), Order.unpaid_amount > 0)
            .group_by(Order.customer_id)
            .order_by(func.sum(Order.unpaid_amount).desc())
            .limit(limit)
        )
        rows = result.all()
        ranking = []
        for customer_id, debt in rows:
            c_result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
            c = c_result.scalar_one_or_none()
            ranking.append({
                "customer_id": str(customer_id),
                "customer_name": c.name if c else "未知",
                "debt_amount": float(debt),
            })
        return ranking

    async def _list_orders_in_range(self, start: datetime, end: datetime) -> list[Order]:
        result = await self.db.execute(
            select(Order).where(
                and_(Order.deleted_at.is_(None), Order.created_at >= start, Order.created_at <= end)
            ).order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def _list_payments_in_range(self, start: datetime, end: datetime) -> list[Payment]:
        result = await self.db.execute(
            select(Payment).where(
                and_(Payment.is_voided == False, Payment.created_at >= start, Payment.created_at <= end)
            ).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def _count_new_customers(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Customer).where(
                and_(Customer.deleted_at.is_(None), Customer.created_at >= start, Customer.created_at <= end)
            )
        )
        return result.scalar() or 0
