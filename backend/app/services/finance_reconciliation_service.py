"""Evidence-backed reconciliation of legacy finance facts."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outsource import OutsourcePayment, OutsourceTask
from app.models.payable import PayablePayment
from app.models.payment import Expense
from app.models.project_cost import ProjectCost
from app.models.finance_reconciliation import (
    FinanceCostOverlapReview,
    FinancePaymentDateReconciliation,
)
from app.models.business_document import BusinessDocument


_MONEY = Decimal("0.01")
_VALID_SOURCES = {"expense", "project_cost", "outsource_task", "outsource_payment"}
_VALID_EVIDENCE = {"bank_statement", "payment_voucher", "other"}
_VALID_DECISIONS = {
    "confirmed_duplicate",
    "confirmed_not_duplicate",
    "needs_evidence",
}
_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(_MONEY)


class FinanceReconciliationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _active_reconciled_amount(self, source_type: str, source_id: UUID) -> Decimal:
        amount = await self.db.scalar(
            select(func.coalesce(func.sum(FinancePaymentDateReconciliation.amount), 0)).where(
                FinancePaymentDateReconciliation.source_type == source_type,
                FinancePaymentDateReconciliation.source_id == source_id,
                FinancePaymentDateReconciliation.voided_at.is_(None),
            )
        )
        return _money(amount)

    async def _historical_paid_base(self, source_type: str, source_id: UUID) -> Decimal:
        if source_type == "expense":
            source = await self.db.scalar(
                select(Expense).where(
                    Expense.id == source_id,
                    Expense.deleted_at.is_(None),
                ).with_for_update()
            )
            if source is None:
                raise ValueError("经营支出来源不存在或已删除")
            return max(_money(source.amount) - _money(source.payable_amount), Decimal("0.00"))

        if source_type == "project_cost":
            source = await self.db.scalar(
                select(ProjectCost).where(
                    ProjectCost.id == source_id,
                    ProjectCost.deleted_at.is_(None),
                ).with_for_update()
            )
            if source is None:
                raise ValueError("项目成本来源不存在或已删除")
            debt = _money(source.debt_amount)
            inferred = max(_money(source.amount) - debt, Decimal("0.00"))
            history_count = int(await self.db.scalar(
                select(func.count(PayablePayment.id)).where(
                    PayablePayment.source_type == "project_cost",
                    PayablePayment.source_id == source_id,
                )
            ) or 0)
            if source.is_settled and history_count == 0:
                inferred += debt
            return inferred

        if source_type == "outsource_task":
            source = await self.db.scalar(
                select(OutsourceTask).where(
                    OutsourceTask.id == source_id,
                    OutsourceTask.deleted_at.is_(None),
                ).with_for_update()
            )
            if source is None:
                raise ValueError("外协任务来源不存在或已删除")
            recorded_payments = _money(await self.db.scalar(
                select(func.coalesce(func.sum(OutsourcePayment.amount), 0)).where(
                    OutsourcePayment.task_id == source_id,
                )
            ))
            return max(_money(source.paid_amount) - recorded_payments, Decimal("0.00"))

        raise ValueError("该来源不是汇总型历史已付款")

    async def create_payment_date_reconciliation(
        self,
        *,
        source_type: str,
        source_id: UUID,
        amount: Decimal,
        paid_at: date,
        evidence_type: str,
        evidence_reference: str,
        note: str | None,
        created_by: UUID | None,
    ) -> dict:
        if source_type not in _VALID_SOURCES:
            raise ValueError("付款核对来源类型无效")
        if evidence_type not in _VALID_EVIDENCE:
            raise ValueError("证据类型无效")
        evidence_reference = (evidence_reference or "").strip()
        if not evidence_reference:
            raise ValueError("证据参考不能为空")
        if len(evidence_reference) > 255:
            raise ValueError("证据参考不能超过255个字符")
        if paid_at > datetime.now(_SHANGHAI).date():
            raise ValueError("实际付款日期不能晚于今天")
        amount = _money(amount)
        if amount <= 0:
            raise ValueError("核实金额必须大于0")

        source_type_db = source_type
        if source_type == "outsource_payment":
            source = await self.db.scalar(
                select(OutsourcePayment).where(OutsourcePayment.id == source_id).with_for_update()
            )
            if source is None:
                raise ValueError("外协付款记录不存在")
            if source.paid_at is not None:
                raise ValueError("该外协付款已有付款日期，无需重复核对")
            base_amount = _money(source.amount)
            allocated = await self._active_reconciled_amount(source_type_db, source_id)
            available = base_amount - allocated
            if allocated > 0:
                raise ValueError("该外协付款已核对，请先撤销原核对记录")
            if amount != base_amount:
                raise ValueError("外协付款日期核对必须对应原付款整笔金额")
        else:
            base_amount = await self._historical_paid_base(source_type, source_id)
            allocated = await self._active_reconciled_amount(source_type_db, source_id)
            if allocated > base_amount:
                raise ValueError("已有日期核对金额超过当前来源历史已付，请先撤销冲突核对")
            available = base_amount - allocated

        if amount > available:
            raise ValueError(f"核实金额超过尚未核实金额 {available:.2f} 元")

        record = FinancePaymentDateReconciliation(
            source_type=source_type_db,
            source_id=source_id,
            amount=amount,
            paid_at=datetime.combine(paid_at, time.min),
            evidence_type=evidence_type,
            evidence_reference=evidence_reference,
            note=(note or "").strip() or None,
            created_by=created_by,
        )
        self.db.add(record)
        await self.db.flush()
        return self._payment_reconciliation_dict(record, remaining=available - amount)

    async def void_payment_date_reconciliation(
        self,
        *,
        reconciliation_id: UUID,
        reason: str,
        voided_by: UUID | None,
    ) -> dict:
        record = await self.db.scalar(
            select(FinancePaymentDateReconciliation)
            .where(FinancePaymentDateReconciliation.id == reconciliation_id)
            .with_for_update()
        )
        if record is None:
            raise ValueError("付款日期核对记录不存在")
        if record.voided_at is not None:
            raise ValueError("该付款日期核对已撤销")
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("撤销原因不能为空")
        record.voided_at = datetime.now(_SHANGHAI).replace(tzinfo=None)
        record.voided_by = voided_by
        record.void_reason = reason
        await self.db.flush()
        return self._payment_reconciliation_dict(record)

    async def review_cost_overlap(
        self,
        *,
        cost_id: UUID,
        task_id: UUID,
        decision: str,
        evidence_type: str | None,
        evidence_reference: str | None,
        note: str | None,
        reviewed_by: UUID | None,
    ) -> dict:
        if decision not in _VALID_DECISIONS:
            raise ValueError("疑似重复核对结论无效")
        if evidence_type is not None and evidence_type not in _VALID_EVIDENCE:
            raise ValueError("证据类型无效")
        evidence_reference = (evidence_reference or "").strip() or None
        if decision in {"confirmed_duplicate", "confirmed_not_duplicate"} and not evidence_reference:
            raise ValueError("证据参考不能为空")
        if evidence_reference and len(evidence_reference) > 255:
            raise ValueError("证据参考不能超过255个字符")

        cost = await self.db.scalar(
            select(ProjectCost).where(ProjectCost.id == cost_id).with_for_update()
        )
        task = await self.db.scalar(
            select(OutsourceTask).where(OutsourceTask.id == task_id).with_for_update()
        )
        if cost is None or task is None:
            raise ValueError("疑似重复候选的来源记录不存在")
        document_type = await self.db.scalar(
            select(BusinessDocument.doc_type).where(BusinessDocument.id == cost.document_id)
        ) if cost.document_id else None
        candidate = (
            cost.deleted_at is None
            and task.deleted_at is None
            and document_type == "order"
            and cost.document_id is not None
            and cost.document_id == task.related_doc_id
            and cost.supplier_id is not None
            and cost.supplier_id == task.vendor_id
            and _money(cost.amount) == _money(task.total_amount)
            and task.status in {"completed", "settled"}
            and any(word in (cost.category or "").lower() for word in ("外协", "加工"))
        )
        existing = await self.db.scalar(
            select(FinanceCostOverlapReview)
            .where(
                FinanceCostOverlapReview.project_cost_id == cost_id,
                FinanceCostOverlapReview.outsource_task_id == task_id,
            )
            .with_for_update()
        )
        if not candidate and existing is None:
            raise ValueError("该成本与外协任务不属于当前疑似重复候选")
        if existing is None:
            existing = FinanceCostOverlapReview(
                project_cost_id=cost_id,
                outsource_task_id=task_id,
            )
            self.db.add(existing)
        existing.decision = decision
        existing.evidence_type = evidence_type if evidence_reference else None
        existing.evidence_reference = evidence_reference
        existing.note = (note or "").strip() or None
        existing.reviewed_by = reviewed_by
        existing.reviewed_at = datetime.now(_SHANGHAI).replace(tzinfo=None)
        await self.db.flush()
        return self._overlap_review_dict(existing)

    async def assert_source_base_covers_reconciliations(
        self,
        *,
        source_type: str,
        source_id: UUID,
        proposed_base: Decimal,
    ) -> None:
        allocated = await self._active_reconciled_amount(source_type, source_id)
        if allocated > _money(proposed_base):
            raise ValueError("来源历史已付金额低于已核实分配，请先撤销超出的付款日期核对记录")

    async def assert_project_cost_base_covers_reconciliations(
        self,
        *,
        source_id: UUID,
        amount: Decimal,
        debt_amount: Decimal,
        is_settled: bool,
    ) -> None:
        debt = _money(debt_amount)
        base = max(_money(amount) - debt, Decimal("0.00"))
        payment_history = int(await self.db.scalar(
            select(func.count(PayablePayment.id)).where(
                PayablePayment.source_type == "project_cost",
                PayablePayment.source_id == source_id,
            )
        ) or 0)
        if is_settled and payment_history == 0:
            base += debt
        await self.assert_source_base_covers_reconciliations(
            source_type="project_cost",
            source_id=source_id,
            proposed_base=base,
        )

    async def assert_source_has_no_active_reconciliations(
        self,
        *,
        source_type: str,
        source_id: UUID,
    ) -> None:
        allocated = await self._active_reconciled_amount(source_type, source_id)
        if allocated > 0:
            raise ValueError("该来源存在已核实付款日期，删除前请先按原因撤销核对记录")

    async def assert_outsource_task_has_no_active_reconciliations(self, task_id: UUID) -> None:
        """Protect both task-level legacy allocations and child payment allocations."""
        await self.assert_source_has_no_active_reconciliations(
            source_type="outsource_task",
            source_id=task_id,
        )
        payment_ids = list((await self.db.scalars(
            select(OutsourcePayment.id)
            .where(OutsourcePayment.task_id == task_id)
            .with_for_update()
        )).all())
        for payment_id in payment_ids:
            await self.assert_source_has_no_active_reconciliations(
                source_type="outsource_payment",
                source_id=payment_id,
            )

    @staticmethod
    def _payment_reconciliation_dict(record, *, remaining: Decimal | None = None) -> dict:
        result = {
            "id": str(record.id),
            "source_type": record.source_type,
            "source_id": str(record.source_id),
            "amount": float(record.amount),
            "paid_at": record.paid_at.isoformat(),
            "evidence_type": record.evidence_type,
            "evidence_reference": record.evidence_reference,
            "note": record.note,
            "voided_at": record.voided_at.isoformat() if record.voided_at else None,
            "void_reason": record.void_reason,
        }
        if remaining is not None:
            result["remaining_undated_amount"] = float(remaining)
        return result

    @staticmethod
    def _overlap_review_dict(review) -> dict:
        return {
            "id": str(review.id),
            "cost_id": str(review.project_cost_id),
            "task_id": str(review.outsource_task_id),
            "decision": review.decision,
            "evidence_type": review.evidence_type,
            "evidence_reference": review.evidence_reference,
            "note": review.note,
            "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
        }
