from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_document import BusinessDocument
from app.models.contract import Contract
from app.models.framework_contract import FrameworkContractProject
from app.models.payment import CustomerStatement, Expense, Payment, PaymentAllocation
from app.repositories.payment_repo import (
    ExpenseRepository,
    PaymentRepository,
    StatementRepository,
)
from app.schemas.payment import StatementPaymentItem
from app.services.business_document_service import BusinessDocumentService
from app.services.number_generator import (
    generate_expense_no,
    generate_payment_no,
    generate_statement_no,
)
from app.services.payable_service import (
    PayableService,
    calculate_payable_status,
    validate_payable_amount,
)
from app.services.supplier_service import SupplierService
from app.domain.presentation import make_action_capability, make_payment_status_view, make_statement_status_view


def _utc_now() -> datetime:
    """Return naive UTC for the existing payment timestamp columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def _uuid_or_none(value) -> UUID | None:
    """Normalize UUID input without treating mock/dynamic attributes as IDs."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _decimal_or_zero(value) -> Decimal:
    """读取兼容字段时，把旧对象或空值安全转换为金额。"""

    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _money_or_zero(value) -> Decimal:
    """Normalize a money value without allowing float residue."""

    return _decimal_or_zero(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_expense_date(value) -> datetime | None:
    """Normalize expense dates before assigning them to the naive DB column."""

    if value is None:
        return None
    if isinstance(value, datetime):
        normalized = value
    elif isinstance(value, date):
        normalized = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str):
        raw_value = value.strip()
        if not raw_value or raw_value == "-":
            return None
        try:
            normalized = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("支出日期格式无效，请使用 YYYY-MM-DD") from exc
    else:
        raise ValueError("支出日期格式无效，请使用 YYYY-MM-DD")

    if normalized.tzinfo is not None:
        normalized = normalized.astimezone(UTC).replace(tzinfo=None)
    return normalized


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaymentRepository(db)

    async def list_payments(
        self,
        page: int,
        page_size: int,
        order_id: UUID | None = None,
        customer_id: UUID | None = None,
        is_voided: bool | None = None,
        contract_id: UUID | None = None,
    ) -> tuple[list, int]:
        skip = (page - 1) * page_size
        payments, total = await self.repo.list_payments(
            skip,
            page_size,
            order_id,
            customer_id,
            is_voided,
            contract_id,
        )
        return [self._to_dict(p) for p in payments], total

    async def get_payment(self, payment_id: UUID) -> dict | None:
        p = await self.repo.get_by_id(payment_id)
        return self._to_dict(p) if p else None

    async def _get_contract_total(self, contract: Contract) -> Decimal:
        """Return the effective receivable total for a contract."""
        if contract.contract_type == "框架合同":
            result = await self.db.execute(
                select(func.coalesce(func.sum(FrameworkContractProject.project_amount), 0))
                .where(
                    FrameworkContractProject.contract_id == contract.id,
                    FrameworkContractProject.deleted_at.is_(None),
                )
            )
            project_total = Decimal(str(result.scalar() or 0))
            if project_total > 0:
                return project_total
        return Decimal(str(contract.total_amount or 0))

    async def _resolve_contract_for_order(self, order_id: UUID) -> UUID:
        contract_ids = await self.repo.get_contract_ids_for_document(order_id)
        if len(contract_ids) == 1:
            return contract_ids[0]
        if len(contract_ids) > 1:
            raise ValueError("该订单关联了多个合同，请先明确收款合同")
        raise ValueError("该订单尚未关联合同，请先关联合同后再登记收款")

    @staticmethod
    def _validate_order_for_payment(order: BusinessDocument | None) -> None:
        if not order:
            raise ValueError("订单不存在")
        if order.doc_type != "order":
            raise ValueError("收款只能分配到订单")
        if order.status in ("pending_confirm", "cancelled") or order.deleted_at is not None:
            raise ValueError("当前订单状态不允许登记收款")

    async def create_payment(self, data: dict, created_by: UUID) -> dict:
        """Create a contract-based receipt and immutable allocations.

        ``order_id`` is retained for old clients. It resolves to the unique
        contract and therefore cannot bypass the new contract requirement.
        Without an explicit order, the amount is automatically spread across
        the contract's unpaid orders in stable order; any remainder stays
        contract-level instead of being fabricated as an order payment.
        """
        contract_id = _uuid_or_none(data.get("contract_id"))
        document_id = _uuid_or_none(data.get("order_id") or data.get("document_id"))
        customer_id = _uuid_or_none(data.get("customer_id"))
        if not customer_id:
            raise ValueError("请选择收款客户")

        # Validate the explicit order before resolving the legacy order →
        # contract relation. This keeps errors actionable for old clients:
        # a missing/invalid order must not be reported as a missing contract.
        if document_id:
            candidate_order = await self.db.get(BusinessDocument, document_id)
            self._validate_order_for_payment(candidate_order)
            if candidate_order.customer_id != customer_id:
                raise ValueError("收款客户与订单不一致")

        if not contract_id:
            if not document_id:
                raise ValueError("请选择收款合同")
            contract_id = await self._resolve_contract_for_order(document_id)

        contract = await self.db.get(Contract, contract_id, with_for_update=True)
        if not contract or contract.deleted_at is not None:
            raise ValueError("合同不存在或已删除")
        if contract.customer_id != customer_id:
            raise ValueError("收款客户与合同不一致")

        amount = Decimal(str(data["amount"])).quantize(Decimal("0.01"))
        if amount <= 0:
            raise ValueError("收款金额必须大于0")
        total_amount = await self._get_contract_total(contract)
        existing_paid = Decimal(str(await self.repo.get_contract_paid_sum(contract.id)))
        remaining = max(Decimal("0"), total_amount - existing_paid)
        if amount > remaining:
            raise ValueError(f"收款金额超过合同未收金额 {remaining:.2f} 元")

        contract_order_ids = await self.repo.get_contract_order_ids(contract.id)
        locked_orders: dict[UUID, BusinessDocument] = {}
        allocations_spec: list[tuple[UUID | None, Decimal]] = []

        if document_id:
            if document_id not in contract_order_ids:
                raise ValueError("该订单不属于所选合同，不能分配收款")
            doc = await self.db.get(BusinessDocument, document_id, with_for_update=True)
            self._validate_order_for_payment(doc)
            if doc.customer_id != customer_id:
                raise ValueError("收款客户与订单不一致")
            order_paid = Decimal(str(await self.repo.get_document_paid_sum(doc.id)))
            order_remaining = max(Decimal("0"), Decimal(str(doc.total_amount or 0)) - order_paid)
            if amount > order_remaining:
                raise ValueError(f"收款金额超过订单未收金额 {order_remaining:.2f} 元")
            locked_orders[doc.id] = doc
            allocations_spec.append((doc.id, amount))
        else:
            pending = amount
            for order_id in contract_order_ids:
                if pending <= 0:
                    break
                order = await self.db.get(BusinessDocument, order_id, with_for_update=True)
                self._validate_order_for_payment(order)
                if order.customer_id != customer_id:
                    raise ValueError("合同关联订单与合同客户不一致，无法自动分配")
                locked_orders[order.id] = order
                order_paid = Decimal(str(await self.repo.get_document_paid_sum(order.id)))
                order_remaining = max(
                    Decimal("0"), Decimal(str(order.total_amount or 0)) - order_paid
                )
                if order_remaining <= 0:
                    continue
                allocated = min(pending, order_remaining)
                allocations_spec.append((order.id, allocated))
                pending -= allocated
            if pending > 0:
                allocations_spec.append((None, pending))

        compatibility_document_id = document_id
        if compatibility_document_id is None:
            order_ids = [oid for oid, _ in allocations_spec if oid is not None]
            if len(order_ids) == 1:
                compatibility_document_id = order_ids[0]

        payment = Payment(
            payment_no=await generate_payment_no(self.db),
            document_id=compatibility_document_id,
            customer_id=customer_id,
            amount=amount,
            payment_method=data.get("payment_method"),
            paid_at=datetime.fromisoformat(data["paid_at"]) if data.get("paid_at") else None,
            remark=data.get("remark"),
            receipt_url=data.get("receipt_url"),
            created_by=created_by,
        )
        if compatibility_document_id:
            payment.document = locked_orders.get(compatibility_document_id)
        await self.repo.create(payment)

        allocations = []
        for order_id, allocated_amount in allocations_spec:
            allocation = PaymentAllocation(
                payment_id=payment.id,
                contract_id=contract.id,
                document_id=order_id,
                allocated_amount=allocated_amount,
                allocation_type="order" if order_id else "contract",
                created_by=created_by,
            )
            allocation.contract = contract
            allocation.document = locked_orders.get(order_id) if order_id else None
            self.db.add(allocation)
            allocations.append(allocation)
        payment.allocations = allocations
        await self.db.flush()

        for order in locked_orders.values():
            paid = Decimal(str(await self.repo.get_document_paid_sum(order.id)))
            order.paid_amount = paid
            order.unpaid_amount = max(Decimal("0"), Decimal(str(order.total_amount or 0)) - paid)
        contract_paid = existing_paid + amount
        contract.paid_amount = contract_paid
        contract.unpaid_amount = max(Decimal("0"), total_amount - contract_paid)

        # Notify the sales owner(s) of affected orders. Contract-only receipts
        # intentionally do not invent a notification target.
        from app.services.notification_service import NotificationService
        notif_svc = NotificationService(self.db)
        notified_users = set()
        for order in locked_orders.values():
            if order.sales_user_id and order.sales_user_id not in notified_users:
                await notif_svc.create_system_notification(
                    user_id=order.sales_user_id,
                    type_="payment_received",
                    title=f"收款到账: {payment.payment_no}",
                    content=f"合同 {contract.contract_no} 收到 {amount:.2f} 元",
                    link="/receivables",
                )
                notified_users.add(order.sales_user_id)
        await self.db.flush()

        return self._to_dict(payment)

    async def void_payment(self, payment_id: UUID, reason: str) -> dict:
        reason = reason.strip()
        if not reason:
            raise ValueError("作废原因不能为空")

        p = await self.repo.get_by_id(payment_id, for_update=True)
        if not p:
            raise ValueError("收款记录不存在")
        if p.is_voided:
            raise ValueError("该收款已作废")

        await self.repo.void(p, reason)

        raw_allocations = getattr(p, "allocations", None)
        allocations = (
            list(raw_allocations)
            if isinstance(raw_allocations, (list, tuple, set))
            else []
        )
        order_ids = {
            order_id
            for order_id in (_uuid_or_none(getattr(a, "document_id", None)) for a in allocations)
            if order_id
        }
        legacy_order_id = _uuid_or_none(getattr(p, "document_id", None))
        if legacy_order_id:
            order_ids.add(legacy_order_id)
        for order_id in order_ids:
            doc = await self.db.get(BusinessDocument, order_id)
            if doc:
                paid = Decimal(str(await self.repo.get_document_paid_sum(order_id)))
                doc.paid_amount = paid
                doc.unpaid_amount = max(Decimal("0"), Decimal(str(doc.total_amount or 0)) - paid)

        contract_ids = {
            contract_id
            for contract_id in (_uuid_or_none(getattr(a, "contract_id", None)) for a in allocations)
            if contract_id
        }
        if legacy_order_id and not contract_ids:
            contract_ids.update(
                await self.repo.get_contract_ids_for_document(legacy_order_id)
            )
        for contract_id in contract_ids:
            contract = await self.db.get(Contract, contract_id, with_for_update=True)
            if contract and contract.deleted_at is None:
                paid = Decimal(str(await self.repo.get_contract_paid_sum(contract.id)))
                total = await self._get_contract_total(contract)
                contract.paid_amount = paid
                contract.unpaid_amount = max(Decimal("0"), total - paid)
        await self.db.flush()

        return self._to_dict(p)

    def _to_dict(self, p: Payment) -> dict:
        doc = getattr(p, "document", None)
        raw_allocations = getattr(p, "allocations", None)
        allocations = (
            list(raw_allocations)
            if isinstance(raw_allocations, (list, tuple, set))
            else []
        )
        contract = next(
            (getattr(allocation, "contract", None) for allocation in allocations if getattr(allocation, "contract", None)),
            None,
        )
        document_id = _uuid_or_none(getattr(p, "document_id", None)) or _uuid_or_none(
            getattr(p, "order_id", None)
        )
        customer = getattr(doc, "customer", None) if doc else None
        customer_name = getattr(customer, "name", None) if customer else None
        if not customer_name and contract:
            customer_name = getattr(contract, "customer_name", None)
        allocation_total = sum(
            (Decimal(str(getattr(allocation, "allocated_amount", 0) or 0)) for allocation in allocations),
            Decimal("0"),
        )
        if not allocations:
            allocation_status = "待分配"
        elif allocation_total < Decimal(str(p.amount or 0)):
            allocation_status = "部分分配"
        else:
            allocation_status = "已分配"
        return {
            "id": str(p.id) if p.id else None,
            "payment_no": p.payment_no,
            "document_id": str(document_id) if document_id else None,
            "order_id": str(document_id) if document_id else None,  # backward-compat alias
            "doc_no": doc.doc_no if doc else None,
            "order_no": doc.doc_no if doc else None,  # backward-compat alias
            "customer_id": str(p.customer_id) if p.customer_id else None,
            "customer_name": customer_name,
            "project_name": doc.project_name if doc else None,
            "department": doc.department if doc else None,
            "contract_id": str(contract.id) if contract else None,
            "contract_no": contract.contract_no if contract else None,
            "amount": float(p.amount),
            "payment_method": p.payment_method,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "remark": p.remark,
            "is_voided": p.is_voided,
            "status_view": make_payment_status_view(p.is_voided).model_dump(mode="json"),
            "void_reason": p.void_reason,
            "voided_at": p.voided_at.isoformat() if p.voided_at else None,
            "receipt_url": p.receipt_url,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "created_by": str(p.created_by) if p.created_by else None,
            "allocation_status": allocation_status,
            "allocation_total": float(allocation_total),
            "allocations": [
                {
                    "id": str(allocation.id) if allocation.id else None,
                    "contract_id": str(allocation.contract_id),
                    "document_id": str(allocation.document_id) if allocation.document_id else None,
                    "order_id": str(allocation.document_id) if allocation.document_id else None,
                    "amount": float(allocation.allocated_amount),
                    "allocation_type": allocation.allocation_type,
                }
                for allocation in allocations
            ],
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
        if end < start:
            raise ValueError("结束时间不能早于开始时间")

        documents = await self.repo.get_documents_in_range(data["customer_id"], start, end)
        documents = [
            document for document in documents
            if document.doc_type == "order" and document.status != "cancelled"
        ]
        payments = await self.repo.get_payments_in_range(data["customer_id"], start, end)

        total_order = sum(float(d.total_amount) for d in documents)
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
        return await self._to_detail(stmt, documents, payments)

    async def confirm_statement(self, statement_id: UUID, confirmed_by: UUID) -> dict:
        s = await self.repo.get_by_id(statement_id)
        if not s:
            raise ValueError("对账单不存在")
        if s.status != "draft":
            raise ValueError("仅草稿对账单可以确认")
        await self.repo.update(s, {"status": "confirmed", "confirmed_at": _utc_now(), "confirmed_by": confirmed_by})
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
            "status_view": make_statement_status_view(s.status).model_dump(mode="json"),
            "capabilities": {
                "confirm": make_action_capability(
                    s.status == "draft",
                    "对账单已确认，不能重复确认" if s.status != "draft" else None,
                ).model_dump(mode="json"),
            },
            "confirmed_at": s.confirmed_at.isoformat() if s.confirmed_at else None,
            "confirmed_by": str(s.confirmed_by) if s.confirmed_by else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    async def _to_detail(self, s: CustomerStatement, documents: list | None = None, payments: list | None = None) -> dict:
        if documents is None:
            documents = await self.repo.get_documents_in_range(s.customer_id, s.start_date, s.end_date)
        if payments is None:
            payments = await self.repo.get_payments_in_range(s.customer_id, s.start_date, s.end_date)
        base = self._to_summary(s)
        base["orders"] = [BusinessDocumentService._to_ref(d) for d in documents]
        base["payments"] = [
            StatementPaymentItem.model_validate(p).model_dump(mode="json")
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
        payment_summaries = await self._get_payable_payment_summaries(expenses)
        rows = []
        for expense in expenses:
            payable_paid_amount, payment_count = payment_summaries.get(
                ("expense", expense.id), (Decimal("0"), 0)
            )
            rows.append(
                self._to_dict(
                    expense,
                    payable_paid_amount=payable_paid_amount,
                    payment_count=payment_count,
                )
            )
        return rows, total

    async def get_expense(self, expense_id: UUID) -> dict | None:
        e = await self.repo.get_by_id(expense_id)
        if not e:
            return None
        payment_summaries = await self._get_payable_payment_summaries([e])
        payable_paid_amount, payment_count = payment_summaries.get(
            ("expense", e.id), (Decimal("0"), 0)
        )
        return self._to_dict(
            e,
            payable_paid_amount=payable_paid_amount,
            payment_count=payment_count,
        )

    async def _get_payable_payment_summaries(
        self,
        expenses: list[Expense],
    ) -> dict[tuple[str, UUID], tuple[Decimal, int]]:
        if not expenses:
            return {}
        source_pairs = [
            ("expense", expense.id)
            for expense in expenses
            if _money_or_zero(getattr(expense, "payable_amount", 0)) > 0
        ]
        return await PayableService(self.db).get_payment_summaries(source_pairs)

    async def create_expense(self, data: dict, created_by: UUID) -> dict:
        requested_payable_amount = _money_or_zero(data.get("payable_amount"))
        if requested_payable_amount < 0:
            raise ValueError("欠款金额不能小于0")
        if "paid_amount" in data and data.get("paid_amount") is not None:
            initial_paid_amount = _money_or_zero(data.get("paid_amount"))
            if initial_paid_amount < 0:
                raise ValueError("支付金额不能小于0")
            amount = _money_or_zero(initial_paid_amount + requested_payable_amount)
        else:
            # Legacy clients sent the source total as ``amount``. Keep that
            # contract working while deriving the historical upfront-paid
            # portion from total minus payable.
            amount = _money_or_zero(data.get("amount"))
            if amount < 0:
                raise ValueError("支出总金额不能小于0")
            # A payable-only legacy entry has no upfront payment; its payable
            # amount is therefore also the source total.
            if amount == 0 and requested_payable_amount > 0:
                amount = requested_payable_amount
        if amount <= 0:
            raise ValueError("支出总金额必须大于0")
        payable_amount = validate_payable_amount(
            amount,
            requested_payable_amount,
        )
        supplier = await SupplierService(self.db).resolve_active_supplier(data.get("supplier_id"))
        expense = Expense(
            expense_no=await generate_expense_no(self.db),
            category=data.get("category"),
            payment_method=data.get("payment_method"),
            amount=amount,
            payee_name=data.get("payee_name") or (supplier.name if supplier else None),
            payable_amount=payable_amount,
            supplier_id=supplier.id if supplier else None,
            description=data.get("description"),
            expense_date=_normalize_expense_date(data.get("expense_date")),
            receipt_url=data.get("receipt_url"),
            created_by=created_by,
        )
        await self.repo.create(expense)
        return self._to_dict(expense)

    async def update_expense(self, expense_id: UUID, data: dict) -> dict:
        e = await self.repo.get_by_id(expense_id)
        if not e:
            raise ValueError("支出记录不存在")
        current_payable_amount = _money_or_zero(getattr(e, "payable_amount", 0))
        requested_payable_amount = _money_or_zero(
            data.get("payable_amount", current_payable_amount)
        )
        if requested_payable_amount < 0:
            raise ValueError("欠款金额不能小于0")
        if "paid_amount" in data and data.get("paid_amount") is not None:
            initial_paid_amount = _money_or_zero(data.get("paid_amount"))
            if initial_paid_amount < 0:
                raise ValueError("支付金额不能小于0")
            amount = _money_or_zero(initial_paid_amount + requested_payable_amount)
        else:
            # Preserve the legacy update contract where amount means total.
            amount_value = data.get("amount", e.amount)
            amount = _money_or_zero(e.amount) if amount_value is None else _money_or_zero(amount_value)
        if amount <= 0:
            raise ValueError("支出总金额必须大于0")
        payable_amount = validate_payable_amount(
            amount,
            requested_payable_amount,
        )
        normalized = dict(data)
        normalized["amount"] = amount
        normalized["payable_amount"] = payable_amount
        if "expense_date" in normalized:
            normalized["expense_date"] = _normalize_expense_date(normalized["expense_date"])
        # ``paid_amount`` is a derived input convenience field, not a second
        # database column.  Persist total amount and payable total only.
        normalized.pop("paid_amount", None)
        allow_null_fields: set[str] = set()
        if "expense_date" in normalized:
            allow_null_fields.add("expense_date")
        if "supplier_id" in normalized:
            supplier = await SupplierService(self.db).resolve_active_supplier(normalized["supplier_id"])
            normalized["supplier_id"] = supplier.id if supplier else None
            allow_null_fields.add("supplier_id")
        if "payment_method" in normalized:
            allow_null_fields.add("payment_method")
        if payable_amount > 0 or current_payable_amount > 0:
            await PayableService(self.db).validate_source_update(
                "expense",
                e.id,
                payable_amount,
            )
        if allow_null_fields:
            await self.repo.update(e, normalized, allow_null_fields=allow_null_fields)
        else:
            # Preserve the legacy repository call shape when no nullable
            # supplier field needs special handling.
            await self.repo.update(e, normalized)
        return self._to_dict(e)

    async def delete_expense(self, expense_id: UUID) -> None:
        e = await self.repo.get_by_id(expense_id)
        if not e:
            raise ValueError("支出记录不存在")
        payable_amount = _decimal_or_zero(getattr(e, "payable_amount", 0))
        if payable_amount > 0:
            await PayableService(self.db).assert_source_can_be_deleted("expense", e.id)
        await self.repo.soft_delete(e)

    def _to_dict(
        self,
        e: Expense,
        *,
        payable_paid_amount: Decimal = Decimal("0"),
        payment_count: int = 0,
    ) -> dict:
        amount = _money_or_zero(e.amount)
        payable_amount = _money_or_zero(getattr(e, "payable_amount", 0))
        initial_paid_amount = max(Decimal("0"), amount - payable_amount)
        payable_paid_amount = max(
            Decimal("0"), min(_money_or_zero(payable_paid_amount), payable_amount)
        )
        remaining_payable_amount = max(
            Decimal("0"), payable_amount - payable_paid_amount
        )
        total_paid_amount = initial_paid_amount + payable_paid_amount
        return {
            "id": str(e.id), "expense_no": e.expense_no,
            "category": e.category, "amount": float(amount),
            "payment_method": getattr(e, "payment_method", None),
            "payee_name": getattr(e, "payee_name", None),
            "supplier_id": str(getattr(e, "supplier_id", None)) if getattr(e, "supplier_id", None) else None,
            "supplier_name": getattr(getattr(e, "supplier", None), "name", None),
            # Compatibility field: this remains the original payable total,
            # not the residual balance after later payments.
            "payable_amount": float(payable_amount),
            "initial_paid_amount": float(initial_paid_amount),
            "payable_paid_amount": float(payable_paid_amount),
            "total_paid_amount": float(total_paid_amount),
            "remaining_payable_amount": float(remaining_payable_amount),
            "payable_status": calculate_payable_status(
                payable_amount, payable_paid_amount
            ),
            "payable_payment_count": payment_count,
            "description": e.description,
            "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            "receipt_url": e.receipt_url,
            "created_by": str(e.created_by) if e.created_by else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
