from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, CustomerStatement, Expense
from app.repositories.payment_repo import PaymentRepository, StatementRepository, ExpenseRepository
from app.services.number_generator import generate_payment_no, generate_statement_no, generate_expense_no


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaymentRepository(db)

    async def list_payments(self, page: int, page_size: int, order_id: UUID | None = None,
                            customer_id: UUID | None = None, is_voided: bool | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        payments, total = await self.repo.list_payments(skip, page_size, order_id, customer_id, is_voided)
        return [self._to_dict(p) for p in payments], total

    async def get_payment(self, payment_id: UUID) -> dict | None:
        p = await self.repo.get_by_id(payment_id)
        return self._to_dict(p) if p else None

    async def create_payment(self, data: dict, created_by: UUID) -> dict:
        from app.repositories.order_repo import OrderRepository
        order_repo = OrderRepository(self.db)
        order = await order_repo.get_by_id(data["order_id"])
        if not order:
            raise ValueError("订单不存在")

        payment = Payment(
            payment_no=await generate_payment_no(self.db),
            order_id=data["order_id"],
            customer_id=data["customer_id"],
            amount=data["amount"],
            payment_method=data.get("payment_method"),
            paid_at=datetime.fromisoformat(data["paid_at"]) if data.get("paid_at") else None,
            remark=data.get("remark"),
            receipt_url=data.get("receipt_url"),
            created_by=created_by,
        )
        await self.repo.create(payment)

        # Notify admin/finance about payment
        from app.services.notification_service import NotificationService
        notif_svc = NotificationService(self.db)
        # Notify all admin users (simplified - in production, query users with finance/admin roles)
        if order.sales_user_id:
            await notif_svc.create_system_notification(
                user_id=order.sales_user_id,
                type_="payment_received",
                title=f"收款到账: {payment.payment_no}",
                content=f"订单 {order.order_no} 收到 {data['amount']} 元",
                link=f"/payments",
            )

        paid = await self.repo.get_order_paid_sum(data["order_id"])
        unpaid = max(0, float(order.total_amount) - paid)
        await order_repo.update(order, {"paid_amount": paid, "unpaid_amount": unpaid})

        return self._to_dict(payment)

    async def void_payment(self, payment_id: UUID, reason: str) -> dict:
        p = await self.repo.get_by_id(payment_id)
        if not p:
            raise ValueError("收款记录不存在")
        if p.is_voided:
            raise ValueError("该收款已作废")

        await self.repo.void(p, reason)

        from app.repositories.order_repo import OrderRepository
        order_repo = OrderRepository(self.db)
        order = await order_repo.get_by_id(p.order_id)
        if order:
            paid = await self.repo.get_order_paid_sum(p.order_id)
            unpaid = max(0, float(order.total_amount) - paid)
            await order_repo.update(order, {"paid_amount": paid, "unpaid_amount": unpaid})

        return self._to_dict(p)

    def _to_dict(self, p: Payment) -> dict:
        return {
            "id": str(p.id),
            "payment_no": p.payment_no,
            "order_id": str(p.order_id),
            "order_no": p.order.order_no if p.order else None,
            "customer_id": str(p.customer_id),
            "customer_name": p.order.customer.name if p.order and p.order.customer else None,
            "project_name": p.order.project_name if p.order else None,
            "amount": float(p.amount),
            "payment_method": p.payment_method,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "remark": p.remark,
            "is_voided": p.is_voided,
            "void_reason": p.void_reason,
            "voided_at": p.voided_at.isoformat() if p.voided_at else None,
            "receipt_url": p.receipt_url,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "created_by": str(p.created_by) if p.created_by else None,
        }


class StatementService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = StatementRepository(db)

    async def list_statements(self, page: int, page_size: int, customer_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        stmts, total = await self.repo.list_statements(skip, page_size, customer_id)
        return [self._to_summary(s) for s in stmts], total

    async def get_statement(self, statement_id: UUID) -> dict | None:
        s = await self.repo.get_by_id(statement_id)
        if not s:
            return None
        return await self._to_detail(s)

    async def create_statement(self, data: dict) -> dict:
        start = datetime.fromisoformat(data["start_date"])
        end = datetime.fromisoformat(data["end_date"])

        orders = await self.repo.get_orders_in_range(data["customer_id"], start, end)
        payments = await self.repo.get_payments_in_range(data["customer_id"], start, end)

        total_order = sum(float(o.total_amount) for o in orders)
        total_paid = sum(float(p.amount) for p in payments)
        total_unpaid = total_order - total_paid

        stmt = CustomerStatement(
            statement_no=await generate_statement_no(self.db),
            customer_id=data["customer_id"],
            start_date=start,
            end_date=end,
            total_order_amount=total_order,
            total_paid_amount=total_paid,
            total_unpaid_amount=total_unpaid,
            status="draft",
        )
        await self.repo.create(stmt)
        return await self._to_detail(stmt)

    async def confirm_statement(self, statement_id: UUID, confirmed_by: UUID) -> dict:
        s = await self.repo.get_by_id(statement_id)
        if not s:
            raise ValueError("对账单不存在")
        await self.repo.update(s, {"status": "confirmed", "confirmed_at": datetime.now(), "confirmed_by": confirmed_by})
        return await self._to_detail(s)

    def _to_summary(self, s: CustomerStatement) -> dict:
        return {
            "id": str(s.id), "statement_no": s.statement_no,
            "customer_id": str(s.customer_id),
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "total_order_amount": float(s.total_order_amount),
            "total_paid_amount": float(s.total_paid_amount),
            "total_unpaid_amount": float(s.total_unpaid_amount),
            "status": s.status,
            "confirmed_at": s.confirmed_at.isoformat() if s.confirmed_at else None,
            "confirmed_by": str(s.confirmed_by) if s.confirmed_by else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    async def _to_detail(self, s: CustomerStatement) -> dict:
        orders = await self.repo.get_orders_in_range(s.customer_id, s.start_date, s.end_date)
        payments = await self.repo.get_payments_in_range(s.customer_id, s.start_date, s.end_date)
        base = self._to_summary(s)
        base["orders"] = [
            {
                "id": str(o.id), "order_no": o.order_no, "project_name": o.project_name,
                "status": o.status, "total_amount": float(o.total_amount),
                "paid_amount": float(o.paid_amount), "unpaid_amount": float(o.unpaid_amount),
            }
            for o in orders
        ]
        base["payments"] = [
            {
                "id": str(p.id), "payment_no": p.payment_no, "amount": float(p.amount),
                "payment_method": p.payment_method,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "is_voided": p.is_voided,
            }
            for p in payments
        ]
        return base


class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseRepository(db)

    async def list_expenses(self, page: int, page_size: int, category: str | None = None,
                            start_date: str | None = None, end_date: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        expenses, total = await self.repo.list_expenses(skip, page_size, category, start_date, end_date)
        return [self._to_dict(e) for e in expenses], total

    async def get_expense(self, expense_id: UUID) -> dict | None:
        e = await self.repo.get_by_id(expense_id)
        return self._to_dict(e) if e else None

    async def create_expense(self, data: dict, created_by: UUID) -> dict:
        expense = Expense(
            expense_no=await generate_expense_no(self.db),
            category=data.get("category"),
            amount=data["amount"],
            description=data.get("description"),
            expense_date=datetime.fromisoformat(data["expense_date"]) if data.get("expense_date") else None,
            receipt_url=data.get("receipt_url"),
            created_by=created_by,
        )
        await self.repo.create(expense)
        return self._to_dict(expense)

    async def update_expense(self, expense_id: UUID, data: dict) -> dict:
        e = await self.repo.get_by_id(expense_id)
        if not e:
            raise ValueError("支出记录不存在")
        await self.repo.update(e, data)
        return self._to_dict(e)

    async def delete_expense(self, expense_id: UUID) -> None:
        e = await self.repo.get_by_id(expense_id)
        if not e:
            raise ValueError("支出记录不存在")
        await self.repo.soft_delete(e)

    def _to_dict(self, e: Expense) -> dict:
        return {
            "id": str(e.id), "expense_no": e.expense_no,
            "category": e.category, "amount": float(e.amount),
            "description": e.description,
            "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            "receipt_url": e.receipt_url,
            "created_by": str(e.created_by) if e.created_by else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
