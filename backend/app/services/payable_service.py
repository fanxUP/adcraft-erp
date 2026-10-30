"""统一应付台账服务。

应付记录不复制项目成本或经营支出。每一条应付来源仍由原业务表保存，
``payable_payments`` 只保存实际付款流水；页面上的已付款、待付款和状态
均由来源金额与有效付款流水动态计算。
"""

from __future__ import annotations

import hashlib
import json

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import and_, case, func, literal, or_, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.presentation import make_action_capability, make_status_view
from app.domain.payment_dates import require_payment_date
from app.models.business_document import BusinessDocument
from app.models.payment import Expense
from app.models.payable import PayablePayment
from app.models.project_cost import ProjectCost, ProjectCostItemLink
from app.models.customer import Customer
from app.models.outsource import OutsourceVendor
from app.services.company_account_service import CompanyAccountService
from app.services.number_generator import generate_payable_payment_no


MONEY_QUANTUM = Decimal("0.01")
SUPPORTED_SOURCE_TYPES = {"expense", "project_cost"}
PAYABLE_STATUS_LABELS = {
    "unpaid": ("待付款", "warning", False),
    "partial": ("部分付款", "warning", False),
    "paid": ("已付款", "success", True),
}


def _money(value: Decimal | int | float | str | None) -> Decimal:
    """把金额统一为两位小数，避免 float 直接参与比较。"""

    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_payable_status(total_amount: Decimal, paid_amount: Decimal) -> str:
    """根据应付总额和有效付款总额计算应付状态。"""

    total = _money(total_amount)
    paid = _money(paid_amount)
    if total < 0:
        raise ValueError("应付总额不能小于0")
    if paid < 0:
        raise ValueError("已付款金额不能小于0")
    if total == 0 or paid >= total:
        return "paid"
    return "partial" if paid > 0 else "unpaid"


def validate_payable_amount(
    source_amount: Decimal,
    payable_amount: Decimal,
) -> Decimal:
    """校验来源总额与待付款金额的关系，并返回规范化金额。"""

    source = _money(source_amount)
    payable = _money(payable_amount)
    if source <= 0:
        raise ValueError("支出金额必须大于0")
    if payable < 0 or payable > source:
        raise ValueError("待付款金额不能大于支出总额且不能小于0")
    return payable


def _utc_now() -> datetime:
    """返回与现有付款表一致的无时区 UTC 时间。"""

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_source_type(source_type: str) -> str:
    normalized = (source_type or "").strip()
    if normalized not in SUPPORTED_SOURCE_TYPES:
        raise ValueError("不支持的应付来源，只能是支出或项目成本")
    return normalized


class PayableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _source_amounts(source_type: str, source) -> tuple[Decimal, Decimal]:
        if source_type == "project_cost":
            source_total = _money(getattr(source, "amount", 0))
            payable_total = _money(getattr(source, "debt_amount", 0))
        else:
            source_total = _money(getattr(source, "amount", 0))
            payable_total = _money(getattr(source, "payable_amount", 0))
        return source_total, validate_payable_amount(source_total, payable_total)

    @staticmethod
    def _legacy_paid_amount(source_type: str, source, payment_count: int, paid: Decimal) -> Decimal:
        """兼容旧项目成本的 is_settled 标记，不对历史数据做猜测性回填。"""

        if (
            source_type == "project_cost"
            and bool(getattr(source, "is_settled", False))
            and payment_count == 0
        ):
            return _money(getattr(source, "debt_amount", 0))
        return _money(paid)

    @staticmethod
    def _status_view(status: str) -> dict:
        label, tone, terminal = PAYABLE_STATUS_LABELS[status]
        return make_status_view(
            status,
            label,
            tone=tone,
            terminal=terminal,
        ).model_dump(mode="json")

    @staticmethod
    def _source_load_options():
        return (
            selectinload(ProjectCost.document).selectinload(BusinessDocument.customer),
            selectinload(ProjectCost.document_item),
            selectinload(ProjectCost.item_links).selectinload(
                ProjectCostItemLink.document_item
            ),
            selectinload(ProjectCost.customer),
            selectinload(ProjectCost.supplier),
        )

    async def _page_source_keys(self, page, page_size, keyword, status, source_type, supplier_id):
        """Filter and page in SQL before loading any ORM relationships."""
        payments = select(
            PayablePayment.source_type.label("source_type"), PayablePayment.source_id.label("source_id"),
            func.sum(PayablePayment.amount).label("paid"), func.count().label("payment_count"),
        ).where(PayablePayment.is_voided.is_(False)).group_by(
            PayablePayment.source_type, PayablePayment.source_id).cte("payable_totals")
        branches = []
        for kind, model, amount, date, number, payee in (
            ("project_cost", ProjectCost, ProjectCost.debt_amount, ProjectCost.cost_date, ProjectCost.cost_no, ProjectCost.payee_company_name),
            ("expense", Expense, Expense.payable_amount, Expense.expense_date, Expense.expense_no, Expense.payee_name),
        ):
            if source_type and kind != source_type:
                continue
            paid = func.coalesce(payments.c.paid, 0)
            if kind == "project_cost":
                paid = case((and_(ProjectCost.is_settled.is_(True), func.coalesce(payments.c.payment_count, 0) == 0), amount), else_=paid)
            paid = func.greatest(0, func.least(paid, amount))
            state = case((paid >= amount, "paid"), (paid > 0, "partial"), else_="unpaid")
            query = select(literal(kind).label("source_type"), model.id.label("source_id"),
                func.coalesce(date, model.created_at).label("source_date")).outerjoin(payments,
                and_(payments.c.source_type == kind, payments.c.source_id == model.id))
            query = query.outerjoin(OutsourceVendor, model.supplier_id == OutsourceVendor.id)
            terms = [number, func.coalesce(OutsourceVendor.name, payee), model.category, model.description]
            if kind == "project_cost":
                query = query.outerjoin(BusinessDocument, ProjectCost.document_id == BusinessDocument.id).outerjoin(Customer, ProjectCost.customer_id == Customer.id)
                terms += [BusinessDocument.doc_no, BusinessDocument.project_name, func.coalesce(Customer.name, BusinessDocument.customer_name)]
            query = query.where(model.deleted_at.is_(None), func.coalesce(amount, 0) > 0)
            if supplier_id:
                query = query.where(model.supplier_id == supplier_id)
            if status:
                query = query.where(state == status)
            if keyword:
                query = query.where(func.concat_ws(" ", *terms).icontains(keyword, autoescape=True))
            branches.append(query)
        sources = union_all(*branches).subquery("payable_sources")
        total = int(await self.db.scalar(select(func.count()).select_from(sources)) or 0)
        result = await self.db.execute(select(sources.c.source_type, sources.c.source_id).order_by(
            sources.c.source_date.desc().nulls_last(), sources.c.source_type, sources.c.source_id,
        ).offset((page - 1) * page_size).limit(page_size))
        return list(result.all()), total

    async def _load_sources(self, keys) -> list[tuple[str, object]]:
        if not keys:
            return []
        cost_result = await self.db.execute(
            select(ProjectCost)
            .options(*self._source_load_options())
            .where(
                ProjectCost.deleted_at.is_(None),
                func.coalesce(ProjectCost.debt_amount, 0) > 0,
                ProjectCost.id.in_([key for kind, key in keys if kind == "project_cost"]),
            )
        )
        expense_result = await self.db.execute(
            select(Expense).options(selectinload(Expense.supplier)).where(
                Expense.deleted_at.is_(None),
                func.coalesce(Expense.payable_amount, 0) > 0,
                Expense.id.in_([key for kind, key in keys if kind == "expense"]),
            )
        )
        return [
            ("project_cost", cost) for cost in cost_result.scalars().all()
        ] + [
            ("expense", expense) for expense in expense_result.scalars().all()
        ]

    async def _load_source(
        self,
        source_type: str,
        source_id: UUID,
        *,
        for_update: bool = False,
    ):
        source_type = _normalize_source_type(source_type)
        if source_type == "project_cost":
            query = (
                select(ProjectCost)
                .options(*self._source_load_options())
                .where(
                    ProjectCost.id == source_id,
                    ProjectCost.deleted_at.is_(None),
                )
            )
        else:
            query = select(Expense).options(selectinload(Expense.supplier)).where(
                Expense.id == source_id,
                Expense.deleted_at.is_(None),
            )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _payment_summary(
        self,
        source_pairs: list[tuple[str, UUID]],
    ) -> dict[tuple[str, UUID], tuple[Decimal, int]]:
        if not source_pairs:
            return {}
        predicates = [
            and_(
                PayablePayment.source_type == source_type,
                PayablePayment.source_id == source_id,
            )
            for source_type, source_id in source_pairs
        ]
        result = await self.db.execute(
            select(
                PayablePayment.source_type,
                PayablePayment.source_id,
                func.coalesce(func.sum(PayablePayment.amount), 0),
                func.count(PayablePayment.id),
            )
            .where(
                PayablePayment.is_voided.is_(False),
                or_(*predicates),
            )
            .group_by(PayablePayment.source_type, PayablePayment.source_id)
        )
        return {
            (source_type, source_id): (_money(amount), int(count or 0))
            for source_type, source_id, amount, count in result.all()
        }

    async def get_payment_summaries(
        self,
        source_pairs: list[tuple[str, UUID]],
    ) -> dict[tuple[str, UUID], tuple[Decimal, int]]:
        """Return active payment totals for source records.

        Expense and project-cost pages must use the same payment ledger as the
        payable page.  Keep the query behind this public service method so
        callers do not duplicate the source-type/source-id aggregation rules.
        """

        return await self._payment_summary(source_pairs)

    async def _payments_for_source(
        self,
        source_type: str,
        source_id: UUID,
    ) -> list[PayablePayment]:
        result = await self.db.execute(
            select(PayablePayment)
            .where(
                PayablePayment.source_type == source_type,
                PayablePayment.source_id == source_id,
            )
            .order_by(PayablePayment.paid_at.desc(), PayablePayment.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _payment_dict(payment: PayablePayment) -> dict:
        return {
            "id": str(payment.id),
            "payment_no": payment.payment_no,
            "source_type": payment.source_type,
            "source_id": str(payment.source_id),
            "amount": float(_money(payment.amount)),
            "payment_account_id": str(payment.payment_account_id) if getattr(payment, "payment_account_id", None) else None,
            "payment_method": payment.payment_method,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "remark": payment.remark,
            "receipt_url": payment.receipt_url,
            "is_voided": bool(payment.is_voided),
            "void_reason": payment.void_reason,
            "voided_at": payment.voided_at.isoformat() if payment.voided_at else None,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
            "created_by": str(payment.created_by) if payment.created_by else None,
        }

    @staticmethod
    def _source_payload(
        source_type: str,
        source,
        paid_amount: Decimal,
        payment_count: int,
        *,
        payments: list[PayablePayment] | None = None,
    ) -> dict:
        source_total, payable_total = PayableService._source_amounts(source_type, source)
        paid = PayableService._legacy_paid_amount(
            source_type, source, payment_count, paid_amount
        )
        # A historical row may contain a stale settlement flag. Never expose a
        # negative balance or let a stale sum make the list mathematically wrong.
        paid = max(Decimal("0"), min(paid, payable_total))
        remaining = max(Decimal("0"), payable_total - paid)
        status = calculate_payable_status(payable_total, paid)

        if source_type == "project_cost":
            document = getattr(source, "document", None)
            customer = getattr(source, "customer", None)
            customer_name = getattr(customer, "name", None) or getattr(
                document, "customer_name", None
            )
            document_type = getattr(document, "doc_type", None)
            document_no = getattr(document, "doc_no", None)
            item = getattr(source, "document_item", None)
            item_name = getattr(item, "item_name", None)
            if not item_name:
                item_name = next(
                    (
                        getattr(getattr(link, "document_item", None), "item_name", None)
                        for link in (getattr(source, "item_links", None) or [])
                        if getattr(getattr(link, "document_item", None), "item_name", None)
                    ),
                    None,
                )
            source_no = source.cost_no
            project_name = getattr(document, "project_name", None)
            supplier = getattr(source, "supplier", None)
            supplier_id = getattr(source, "supplier_id", None)
            supplier_name = getattr(supplier, "name", None)
            payee_name = supplier_name or getattr(source, "payee_company_name", None)
            source_date = getattr(source, "cost_date", None) or getattr(
                source, "created_at", None
            )
            category = source.category
            description = source.description
            remark = source.remark
            payment_method = source.payment_method
        else:
            document_type = None
            document_no = None
            item_name = None
            source_no = source.expense_no
            project_name = None
            customer_name = None
            supplier = getattr(source, "supplier", None)
            supplier_id = getattr(source, "supplier_id", None)
            supplier_name = getattr(supplier, "name", None)
            payee_name = supplier_name or getattr(source, "payee_name", None)
            source_date = getattr(source, "expense_date", None) or getattr(
                source, "created_at", None
            )
            category = source.category
            description = source.description
            remark = None
            payment_method = None

        payload = {
            # Stable generic fields used by the new 应付管理 page.
            "id": str(source.id),
            "source_type": source_type,
            "source_id": str(source.id),
            "source_label": "项目成本" if source_type == "project_cost" else "支出",
            "source_no": source_no,
            "source_total_amount": float(source_total),
            "payable_total_amount": float(payable_total),
            "paid_amount": float(paid),
            "remaining_amount": float(remaining),
            "payee_name": payee_name,
            "supplier_id": str(supplier_id) if supplier_id else None,
            "supplier_name": supplier_name,
            "status": status,
            "status_view": PayableService._status_view(status),
            "capabilities": {
                "pay": make_action_capability(
                    remaining > 0,
                    "该来源已全部付款" if remaining <= 0 else None,
                ).model_dump(mode="json"),
            },
            "payments": (
                [PayableService._payment_dict(payment) for payment in payments]
                if payments is not None
                else []
            ),
            # Common detail fields make the row useful without a second request.
            "order_no": document_no if document_type == "order" else None,
            "quote_no": document_no if document_type == "quote" else None,
            "project_name": project_name,
            "customer_name": customer_name,
            "document_item_name": item_name,
            "category": category,
            "description": description,
            "remark": remark,
            "payment_method": payment_method,
            "source_date": source_date.isoformat() if source_date else None,
            # Compatibility fields for callers still reading the old list.
            "cost_no": source_no if source_type == "project_cost" else None,
            "expense_no": source_no if source_type == "expense" else None,
            "amount": float(source_total),
            "debt_amount": float(remaining),
            "is_debt": source_type == "project_cost",
            "is_settled": status == "paid",
            "settled_at": (
                getattr(source, "settled_at", None).isoformat()
                if source_type == "project_cost"
                and status == "paid"
                and getattr(source, "settled_at", None)
                else None
            ),
        }
        return payload

    async def list_payables(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        status: str | None = None,
        source_type: str | None = None,
        supplier_id: UUID | None = None,
    ) -> tuple[list[dict], int]:
        if status and status not in PAYABLE_STATUS_LABELS:
            raise ValueError("不支持的应付状态")
        normalized_type = _normalize_source_type(source_type) if source_type else None
        keys, total = await self._page_source_keys(page, page_size, keyword, status, normalized_type, supplier_id)
        sources = await self._load_sources(keys)

        summary = await self._payment_summary(
            [(source_type_value, source.id) for source_type_value, source in sources]
        )
        rows = []
        for source_type_value, source in sources:
            paid, count = summary.get((source_type_value, source.id), (Decimal("0"), 0))
            row = self._source_payload(source_type_value, source, paid, count)
            rows.append(row)

        positions = {(kind, str(key)): index for index, (kind, key) in enumerate(keys)}
        rows.sort(key=lambda row: positions[(row["source_type"], row["source_id"])])
        return rows, total

    async def get_payable(self, source_type: str, source_id: UUID) -> dict | None:
        normalized_type = _normalize_source_type(source_type)
        source = await self._load_source(normalized_type, source_id)
        if not source:
            return None
        paid_map = await self._payment_summary([(normalized_type, source.id)])
        paid, count = paid_map.get((normalized_type, source.id), (Decimal("0"), 0))
        payments = await self._payments_for_source(normalized_type, source.id)
        return self._source_payload(
            normalized_type,
            source,
            paid,
            count,
            payments=payments,
        )

    async def validate_source_update(
        self,
        source_type: str,
        source_id: UUID,
        new_payable_amount: Decimal | float | str,
    ) -> None:
        normalized_type = _normalize_source_type(source_type)
        source = await self._load_source(normalized_type, source_id)
        if not source:
            raise ValueError("应付来源不存在或已删除")
        self._source_amounts(normalized_type, source)
        # The caller supplies the new payable value; validating it against the
        # current source total happens in the source service before update.
        new_payable = _money(new_payable_amount)
        paid_map = await self._payment_summary([(normalized_type, source.id)])
        paid, count = paid_map.get((normalized_type, source.id), (Decimal("0"), 0))
        paid = self._legacy_paid_amount(normalized_type, source, count, paid)
        if new_payable < paid:
            raise ValueError(f"新的待付款金额不能低于已付款金额 {paid:.2f} 元")

    async def assert_source_can_be_deleted(
        self,
        source_type: str,
        source_id: UUID,
    ) -> None:
        normalized_type = _normalize_source_type(source_type)
        # Lock the source while checking its payment total so a concurrent
        # payment cannot be inserted between this check and a soft delete.
        source = await self._load_source(normalized_type, source_id, for_update=True)
        if not source:
            return
        paid_map = await self._payment_summary([(normalized_type, source.id)])
        paid, count = paid_map.get((normalized_type, source.id), (Decimal("0"), 0))
        paid = self._legacy_paid_amount(normalized_type, source, count, paid)
        if paid > 0:
            raise ValueError("已有付款记录，不能删除该支出；请先撤销付款流水")

    async def void_active_payments_for_source(
        self,
        source_type: str,
        source_id: UUID,
        reason: str,
        *,
        expected_payment_count: int | None = None,
        expected_paid_amount: Decimal | float | str | None = None,
    ) -> dict:
        """在锁定来源后撤销其有效付款流水并返回处理摘要。

        这是支出“确认联动删除”专用的原子步骤。付款流水不会被物理删除，
        仍保留编号、金额和撤销原因；调用方负责在同一事务中软删除来源。
        """

        normalized_type = _normalize_source_type(source_type)
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("撤销原因不能为空")
        if expected_payment_count is not None and expected_payment_count < 0:
            raise ValueError("付款流水数量不能小于0")

        source = await self._load_source(normalized_type, source_id, for_update=True)
        if not source:
            raise ValueError("应付来源不存在或已删除")

        result = await self.db.execute(
            select(PayablePayment)
            .where(
                PayablePayment.source_type == normalized_type,
                PayablePayment.source_id == source.id,
                PayablePayment.is_voided.is_(False),
            )
            .order_by(PayablePayment.paid_at.asc(), PayablePayment.created_at.asc())
            .with_for_update()
        )
        payments = list(result.scalars().all())
        paid_amount = _money(
            sum((_money(payment.amount) for payment in payments), Decimal("0"))
        )
        payment_count = len(payments)
        expected_amount = (
            _money(expected_paid_amount)
            if expected_paid_amount is not None
            else None
        )
        if (
            expected_payment_count is not None
            and expected_payment_count != payment_count
        ) or (
            expected_amount is not None
            and expected_amount != paid_amount
        ):
            raise ValueError("付款情况已发生变化，请刷新后重新确认")

        voided_at = _utc_now()
        for payment in payments:
            payment.is_voided = True
            payment.void_reason = reason
            payment.voided_at = voided_at

        if payments:
            await self.db.flush()
        if normalized_type == "project_cost":
            source.is_settled = False
            source.settled_at = None
            await self.db.flush()

        return {
            "payment_ids": [str(payment.id) for payment in payments],
            "payment_count": payment_count,
            "paid_amount": float(paid_amount),
        }

    @staticmethod
    def _parse_paid_at(value: str | None) -> datetime:
        return require_payment_date(value)

    async def register_payment(
        self,
        source_type: str,
        source_id: UUID,
        data: dict,
        created_by: UUID | None,
    ) -> dict:
        normalized_type = _normalize_source_type(source_type)
        paid_at = self._parse_paid_at(data.get("paid_at"))
        try:
            request_id = UUID(str(data.get("request_id")))
        except (ValueError, TypeError) as exc:
            raise ValueError("缺少有效付款请求标识，请重新打开登记窗口") from exc
        amount = _money(data.get("amount"))
        method = (data.get("payment_method") or "转账支付").strip()
        digest = hashlib.sha256(json.dumps({
            "source_type": normalized_type, "source_id": str(source_id),
            "created_by": str(created_by), "amount": str(amount),
            "payment_account_id": str(data.get("payment_account_id") or ""),
            "paid_at": paid_at.isoformat(), "payment_method": method,
            "remark": data.get("remark") or "", "receipt_url": data.get("receipt_url") or "",
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        # Serialize retries globally before source locks, including concurrent
        # attempts to reuse an ID against different sources.
        await self.db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                              {"key": f"payable-request:{request_id}"})
        source = await self._load_source(normalized_type, source_id, for_update=True)
        if not source:
            raise ValueError("应付来源不存在或已删除")
        previous = (await self.db.execute(select(PayablePayment).where(
            PayablePayment.request_id == request_id,
        ))).scalar_one_or_none()
        if previous is not None:
            if previous.request_digest != digest:
                raise ValueError("付款请求标识已用于不同内容，请重新打开登记窗口")
            return await self.get_payable(normalized_type, source.id)
        _, payable_total = self._source_amounts(normalized_type, source)
        payment_map = await self._payment_summary([(normalized_type, source.id)])
        paid, count = payment_map.get((normalized_type, source.id), (Decimal("0"), 0))
        paid = self._legacy_paid_amount(normalized_type, source, count, paid)
        remaining = max(Decimal("0"), payable_total - paid)
        if amount <= 0:
            raise ValueError("付款金额必须大于0")
        if amount > remaining:
            raise ValueError(f"本次付款金额不能大于待付款金额 {remaining:.2f} 元")

        account_id = await CompanyAccountService(self.db).resolve(data.get("payment_account_id"))
        payment = PayablePayment(
            request_id=request_id,
            request_digest=digest,
            payment_account_id=account_id,
            payment_no=await generate_payable_payment_no(self.db),
            source_type=normalized_type,
            source_id=source.id,
            amount=amount,
            payment_method=method,
            paid_at=paid_at,
            remark=data.get("remark"),
            receipt_url=data.get("receipt_url"),
            created_by=created_by,
        )
        self.db.add(payment)
        await self.db.flush()

        new_paid = paid + amount
        new_status = calculate_payable_status(payable_total, new_paid)
        if normalized_type == "project_cost":
            source.is_settled = new_status == "paid"
            source.settled_at = _utc_now() if new_status == "paid" else None
        await self.db.flush()
        result = await self.get_payable(normalized_type, source.id)
        if result is None:
            raise ValueError("付款已登记，但应付来源读取失败")
        return result

    async def void_payment(
        self,
        source_type: str,
        source_id: UUID,
        payment_id: UUID,
        reason: str,
    ) -> dict:
        normalized_type = _normalize_source_type(source_type)
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("撤销原因不能为空")
        source = await self._load_source(normalized_type, source_id, for_update=True)
        if not source:
            raise ValueError("应付来源不存在或已删除")
        result = await self.db.execute(
            select(PayablePayment)
            .where(
                PayablePayment.id == payment_id,
                PayablePayment.source_type == normalized_type,
                PayablePayment.source_id == source.id,
            )
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise ValueError("付款流水不存在")
        if payment.is_voided:
            raise ValueError("该付款流水已撤销")
        payment.is_voided = True
        payment.void_reason = reason
        payment.voided_at = _utc_now()
        await self.db.flush()

        payment_map = await self._payment_summary([(normalized_type, source.id)])
        paid, count = payment_map.get((normalized_type, source.id), (Decimal("0"), 0))
        if normalized_type == "project_cost":
            _, payable_total = self._source_amounts(normalized_type, source)
            source.is_settled = paid >= payable_total and payable_total > 0
            source.settled_at = _utc_now() if source.is_settled else None
        await self.db.flush()
        result_payload = await self.get_payable(normalized_type, source.id)
        if result_payload is None:
            raise ValueError("付款已撤销，但应付来源读取失败")
        return result_payload
