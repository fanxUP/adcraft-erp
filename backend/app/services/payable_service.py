"""统一应付台账服务。

应付记录不复制项目成本或经营支出。每一条应付来源仍由原业务表保存，
``payable_payments`` 只保存实际付款流水；页面上的已付款、待付款和状态
均由来源金额与有效付款流水动态计算。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.presentation import make_action_capability, make_status_view
from app.models.business_document import BusinessDocument
from app.models.payment import Expense
from app.models.payable import PayablePayment
from app.models.project_cost import ProjectCost, ProjectCostItemLink
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
        raise ValueError("不支持的应付来源，只能是经营支出或项目成本")
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

    async def _load_sources(self) -> list[tuple[str, object]]:
        cost_result = await self.db.execute(
            select(ProjectCost)
            .options(*self._source_load_options())
            .where(
                ProjectCost.deleted_at.is_(None),
                func.coalesce(ProjectCost.debt_amount, 0) > 0,
            )
        )
        expense_result = await self.db.execute(
            select(Expense).options(selectinload(Expense.supplier)).where(
                Expense.deleted_at.is_(None),
                func.coalesce(Expense.payable_amount, 0) > 0,
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
            "source_label": "项目成本" if source_type == "project_cost" else "经营支出",
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
        sources = await self._load_sources()
        if normalized_type:
            sources = [item for item in sources if item[0] == normalized_type]
        if supplier_id:
            sources = [
                item for item in sources
                if getattr(item[1], "supplier_id", None) == supplier_id
            ]

        summary = await self._payment_summary(
            [(source_type_value, source.id) for source_type_value, source in sources]
        )
        rows = []
        for source_type_value, source in sources:
            paid, count = summary.get((source_type_value, source.id), (Decimal("0"), 0))
            row = self._source_payload(source_type_value, source, paid, count)
            if status and row["status"] != status:
                continue
            if keyword:
                haystack = " ".join(
                    str(row.get(key) or "")
                    for key in (
                        "source_no",
                        "order_no",
                        "quote_no",
                        "project_name",
                        "customer_name",
                        "payee_name",
                        "category",
                        "description",
                    )
                ).casefold()
                if keyword.casefold() not in haystack:
                    continue
            rows.append(row)

        rows.sort(key=lambda row: row.get("source_date") or "", reverse=True)
        total = len(rows)
        skip = (page - 1) * page_size
        return rows[skip : skip + page_size], total

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

    @staticmethod
    def _parse_paid_at(value: str | None) -> datetime:
        if not value:
            return _utc_now()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (
            parsed.astimezone(timezone.utc).replace(tzinfo=None)
            if parsed.tzinfo
            else parsed
        )

    async def register_payment(
        self,
        source_type: str,
        source_id: UUID,
        data: dict,
        created_by: UUID | None,
    ) -> dict:
        normalized_type = _normalize_source_type(source_type)
        source = await self._load_source(normalized_type, source_id, for_update=True)
        if not source:
            raise ValueError("应付来源不存在或已删除")
        _, payable_total = self._source_amounts(normalized_type, source)
        payment_map = await self._payment_summary([(normalized_type, source.id)])
        paid, count = payment_map.get((normalized_type, source.id), (Decimal("0"), 0))
        paid = self._legacy_paid_amount(normalized_type, source, count, paid)
        remaining = max(Decimal("0"), payable_total - paid)
        amount = _money(data.get("amount"))
        if amount <= 0:
            raise ValueError("付款金额必须大于0")
        if amount > remaining:
            raise ValueError(f"本次付款金额不能大于待付款金额 {remaining:.2f} 元")

        payment = PayablePayment(
            payment_no=await generate_payable_payment_no(self.db),
            source_type=normalized_type,
            source_id=source.id,
            amount=amount,
            payment_method=(data.get("payment_method") or "转账支付").strip(),
            paid_at=self._parse_paid_at(data.get("paid_at")),
            remark=data.get("remark"),
            receipt_url=data.get("receipt_url"),
            created_by=created_by,
        )
        self.db.add(payment)
        await self.db.flush()

        new_paid = paid + amount
        new_status = calculate_payable_status(payable_total, new_paid)
        if normalized_type == "project_cost":
            source.payment_method = payment.payment_method
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
