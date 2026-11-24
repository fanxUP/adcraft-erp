from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import aliased

from app.models.bank_ledger import BankLedgerEntry
from app.models.business_document import BusinessDocument
from app.models.company_account import CompanyAccount
from app.models.contract import Contract
from app.models.payment import Payment, PaymentAllocation
from app.services.bank_ledger_service import BankLedgerService
from app.services.payment_service import PaymentService


class BankReceiptService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _requires_review(entry_id):
        original = aliased(Payment)
        refund = aliased(Payment)
        has_refund = exists(select(refund.id).where(
            refund.reference_payment_id == original.id,
            refund.record_type == "refund",
            refund.is_voided.is_(False),
        ).correlate(original))
        has_credit_transfer = exists(select(PaymentAllocation.id).where(
            PaymentAllocation.payment_id == original.id,
            PaymentAllocation.allocated_amount < 0,
        ).correlate(original))
        return exists(select(original.id).where(
            original.bank_ledger_entry_id == entry_id,
            original.archive_batch_id.is_not(None),
            original.is_voided.is_(False),
            or_(has_refund, has_credit_transfer),
        ).correlate(BankLedgerEntry))

    async def list_entries(
        self, page: int, page_size: int, *, account_id=None, status=None,
        start_date=None, end_date=None, keyword=None, contract_id=None,
        order_id=None, customer_id=None, entry_id=None,
    ):
        if start_date and end_date and start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        allocation_contract = (
            select(PaymentAllocation.contract_id)
            .where(PaymentAllocation.payment_id == Payment.id)
            .order_by(PaymentAllocation.created_at, PaymentAllocation.id)
            .limit(1)
            .correlate(Payment)
            .scalar_subquery()
        )
        requires_review = self._requires_review(BankLedgerEntry.id)
        status_column = case(
            (Payment.id.is_not(None), "linked"), (requires_review, "review"), else_="unlinked"
        )
        order_hint = func.coalesce(Payment.document_id, BankLedgerEntry.order_id)
        query = (
            select(
                BankLedgerEntry.id, BankLedgerEntry.account_id, BankLedgerEntry.entry_date,
                BankLedgerEntry.counterparty_name, BankLedgerEntry.summary, BankLedgerEntry.amount,
                BankLedgerEntry.created_at, order_hint.label("order_id"),
                BusinessDocument.doc_no.label("order_no"),
                CompanyAccount.name.label("account_name"),
                case(
                    (CompanyAccount.account_type == "bank", func.right(CompanyAccount.account_number, 4)),
                    else_=None,
                ).label("account_last_four"),
                Payment.id.label("payment_id"), Payment.payment_no,
                Contract.id.label("contract_id"), Contract.contract_no, Contract.customer_name,
                status_column.label("status"),
            )
            .select_from(BankLedgerEntry)
            .join(CompanyAccount, CompanyAccount.id == BankLedgerEntry.account_id)
            .outerjoin(Payment, and_(
                Payment.bank_ledger_entry_id == BankLedgerEntry.id,
                Payment.record_type == "receipt", Payment.active(),
            ))
            .outerjoin(Contract, Contract.id == allocation_contract)
            .outerjoin(BusinessDocument, BusinessDocument.id == order_hint)
            .where(BankLedgerEntry.main_business_income())
        )
        if account_id:
            query = query.where(BankLedgerEntry.account_id == account_id)
        if status:
            query = query.where(status_column == status)
        if start_date:
            query = query.where(BankLedgerEntry.entry_date >= start_date)
        if end_date:
            query = query.where(BankLedgerEntry.entry_date <= end_date)
        if keyword and keyword.strip():
            pattern = f"%{keyword.strip()}%"
            query = query.where(or_(
                BankLedgerEntry.counterparty_name.ilike(pattern), BankLedgerEntry.summary.ilike(pattern),
                Contract.contract_no.ilike(pattern), Contract.customer_name.ilike(pattern),
                BusinessDocument.doc_no.ilike(pattern), Payment.payment_no.ilike(pattern),
            ))
        if contract_id:
            query = query.where(Contract.id == contract_id)
        if customer_id:
            query = query.where(Payment.customer_id == customer_id)
        if order_id:
            query = query.where(or_(
                and_(Payment.id.is_(None), BankLedgerEntry.order_id == order_id),
                exists(select(PaymentAllocation.id).where(
                    PaymentAllocation.payment_id == Payment.id, PaymentAllocation.document_id == order_id,
                ).correlate(Payment)),
            ))
        if entry_id:
            query = query.where(BankLedgerEntry.id == entry_id)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        rows = (await self.db.execute(
            query.order_by(
                BankLedgerEntry.entry_date.desc(), BankLedgerEntry.created_at.desc(), BankLedgerEntry.id.desc(),
            ).offset((page - 1) * page_size).limit(page_size)
        )).mappings().all()
        return [dict(row) for row in rows], total or 0

    async def _lock_entry(self, entry_id: UUID):
        entry = await self.db.scalar(
            select(BankLedgerEntry).where(
                BankLedgerEntry.id == entry_id, BankLedgerEntry.main_business_income(),
            ).with_for_update()
        )
        if entry is None:
            raise ValueError("流水不存在，或其分类已变更，请刷新收款记录")
        return entry

    async def link(
        self, entry_id: UUID, contract_id: UUID, order_id: UUID | None, *,
        expected_amount: Decimal, expected_date: date, created_by: UUID,
    ):
        entry = await self._lock_entry(entry_id)
        if entry.amount != expected_amount or entry.entry_date != expected_date:
            raise ValueError("流水的金额或日期已变更，请刷新后重新关联")
        if await self._active_payment_id(entry.id):
            raise ValueError("该流水已经关联，请刷新收款记录")
        if await self.db.scalar(select(self._requires_review(entry.id))):
            raise ValueError("该流水的历史收款涉及退款或预收转分配，请先核对再处理")
        contract = await self.db.get(Contract, contract_id)
        if contract is None or contract.deleted_at is not None or not contract.customer_id:
            raise ValueError("请选择已关联客户的有效合同")
        account = await self.db.get(CompanyAccount, entry.account_id)

        return await PaymentService(self.db).create_payment(
            {
                "contract_id": contract_id,
                "order_id": order_id,
                "customer_id": contract.customer_id,
                "amount": entry.amount,
                "paid_at": entry.entry_date.isoformat(),
                "payment_account_id": entry.account_id,
                "payment_method": BankLedgerService._payment_method(account),
                "remark": entry.summary,
            },
            created_by,
            bank_ledger_entry_id=entry.id,
        )

    async def _active_payment_id(self, entry_id):
        return await self.db.scalar(select(Payment.id).where(
            Payment.bank_ledger_entry_id == entry_id, Payment.active(),
        ))

    async def unlink(self, entry_id: UUID, payment_id: UUID, reason: str):
        entry = await self._lock_entry(entry_id)
        if await self._active_payment_id(entry.id) != payment_id:
            raise ValueError("流水关联已变更，请刷新后重试")
        return await PaymentService(self.db).void_payment(payment_id, reason, bank_ledger_entry_id=entry.id)
