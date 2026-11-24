"""Preview or archive legacy receipts after cash reconciliation."""

import argparse
import asyncio
import hashlib
import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from sqlalchemy import or_, select, text
from sqlalchemy.orm import aliased

from app.main import app  # noqa: F401  Register the application's ORM models.
from app.core.database import AsyncSessionLocal
from app.core.permissions import user_has_permission
from app.models.bank_ledger import MAIN_BUSINESS_INCOME, BankLedgerEntry
from app.models.business_document import BusinessDocument
from app.models.company_account import CompanyAccount
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.payment import Payment
from app.models.user import User
from app.repositories.payment_repo import PaymentRepository
from app.services.bank_ledger_service import BankLedgerService
from app.services.operation_log_service import OBJ_PAYMENT, log_operation
from app.services.payment_service import PaymentService, StatementService


ZERO = Decimal("0.00")
CASH_NAMESPACE = UUID("dcc5a6f3-a1e5-46b0-ab87-7935227289f2")
HISTORICAL_INCOME = "历史客户收款"
HISTORICAL_REFUND = "历史客户退款"


def encode(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    raise TypeError(f"Cannot encode {type(value)}")


def plan_digest(plan):
    return hashlib.sha256(json.dumps(
        plan, default=encode, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def parse_cutoff(value):
    cutoff = datetime.fromisoformat(value)
    if cutoff.tzinfo is None:
        raise argparse.ArgumentTypeError("切换时间必须带时区，例如 +08:00")
    return cutoff.astimezone(UTC).replace(tzinfo=None)


def read_decisions(path):
    if not path:
        return {}
    decisions = json.loads(path.read_text())
    if not isinstance(decisions, dict) or any(not isinstance(value, dict) for value in decisions.values()):
        raise ValueError("核对文件须以收款记录 ID 为键、核对决定为值")
    return decisions


def cash_key(account_id, entry_date, direction, amount):
    return (account_id, entry_date, direction, amount)


def currently_projected(payment, openings):
    if payment.is_voided or payment.record_type != "receipt" or not payment.payment_account_id or not payment.paid_at:
        return None
    entry_date = payment.paid_at.date()
    opening = openings.get(payment.payment_account_id)
    if opening and entry_date < opening.entry_date:
        return None
    return {"account_id": payment.payment_account_id, "entry_date": entry_date, "amount": payment.amount}


def resolve_cash(payment, decision, old_cash, matches, manual, openings, accounts, new_id_taken, adjusted):
    if payment.is_voided:
        if decision:
            raise ValueError("已作废记录只需归档")
        return {"action": "archive_only"}
    if not decision:
        if adjusted:
            raise ValueError("涉及退款或预收转分配，请核对后填写决定")
        if not old_cash:
            raise ValueError("没有已显示的台账流水，请核实原凭证和账户")
        if matches:
            raise ValueError("已有同日同金额的台账流水，请核实是否同一笔")
        decision = {"action": "preserve"}
    else:
        evidence = decision.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("请填写核对依据 evidence")

    action = decision.get("action")
    direction = "income" if payment.amount > 0 and payment.record_type == "receipt" else "expense"
    if action == "archive_only":
        return {"action": action, "evidence": decision.get("evidence")}
    if not ((payment.record_type == "receipt" and payment.amount > 0)
            or (payment.record_type == "refund" and payment.amount < 0)):
        raise ValueError("旧金额或收支类型异常，请先核对原凭证")
    amount = abs(payment.amount)
    if action == "match":
        if not decision.get("entry_id"):
            raise ValueError("匹配已有流水时请填写 entry_id")
        entry = manual.get(UUID(decision["entry_id"]))
        if entry is None or entry.direction != direction or entry.amount != amount or entry.category == "内部账户调拨":
            raise ValueError("对应流水须有相同收支方向和金额，并属于客户收退款")
        return {"action": action, "entry_id": entry.id, "evidence": decision["evidence"]}
    if action != "preserve":
        raise ValueError("核对决定须为 match、preserve 或 archive_only")
    if new_id_taken:
        raise ValueError("历史流水已存在，请重新核对来源")

    account_id = UUID(decision["account_id"]) if decision.get("account_id") else (old_cash or {}).get("account_id")
    entry_date = date.fromisoformat(decision["entry_date"]) if decision.get("entry_date") else (old_cash or {}).get("entry_date")
    if account_id not in accounts or entry_date is None or entry_date > BankLedgerService._today():
        raise ValueError("请填写已核实的账户和到账或退款日期")
    opening = openings.get(account_id)
    if opening and entry_date < opening.entry_date:
        raise ValueError("该笔早于账户期初日期，请核对是否已含在期初金额中")
    categories = {HISTORICAL_INCOME, MAIN_BUSINESS_INCOME} if direction == "income" else {HISTORICAL_REFUND}
    category = decision.get("category") or (HISTORICAL_INCOME if direction == "income" else HISTORICAL_REFUND)
    if category not in categories:
        raise ValueError("保留流水的分类须为历史客户收款、主营业务收入或历史客户退款")
    return {
        "action": action, "entry_id": uuid5(CASH_NAMESPACE, str(payment.id)), "direction": direction,
        "account_id": account_id, "entry_date": entry_date, "amount": amount,
        "category": category, "evidence": decision.get("evidence"),
    }


async def account_totals(db, actor, accounts):
    service = BankLedgerService(db, actor)
    openings, rows = await service._load_account_rows(accounts)
    totals = {}
    for account in accounts:
        _, values = service._calculate_account_rows(rows[account.id], openings.get(account.id))
        totals[account.id] = {key: values[key] for key in ("income_amount", "expense_amount", "balance")}
    return totals


async def affected_balances(db, payments):
    repo = PaymentRepository(db)
    order_delta = defaultdict(lambda: ZERO)
    contract_delta = defaultdict(lambda: ZERO)
    for payment in payments:
        if payment.is_voided:
            continue
        if payment.allocations:
            for allocation in payment.allocations:
                contract_delta[allocation.contract_id] += allocation.allocated_amount
                if allocation.document_id:
                    order_delta[allocation.document_id] += allocation.allocated_amount
        elif payment.document_id:
            order_delta[payment.document_id] += payment.amount
            contract_ids = await repo.get_contract_ids_for_document(payment.document_id)
            if len(contract_ids) == 1:
                contract_delta[contract_ids[0]] += payment.amount

    order_totals = []
    for order_id, removed in sorted(order_delta.items()):
        order = await db.get(BusinessDocument, order_id)
        before = Decimal(str(await repo.get_document_paid_sum(order_id)))
        total = order.total_amount or ZERO
        order_totals.append(balance_preview(order_id, order.doc_no, total, before, removed))
    contracts = []
    before_by_contract = await repo.get_contract_paid_sums(list(contract_delta))
    service = PaymentService(db)
    for contract_id, removed in sorted(contract_delta.items()):
        contract = await db.get(Contract, contract_id)
        total = await service._get_contract_total(contract)
        contracts.append(balance_preview(
            contract_id, contract.contract_no, total, before_by_contract.get(contract_id, ZERO), removed,
        ))
    return order_totals, contracts


def balance_preview(object_id, number, total, before, removed):
    after = before - removed
    return {
        "id": object_id, "number": number, "paid_before": before, "paid_after": after,
        "unpaid_before": max(ZERO, total - before), "unpaid_after": max(ZERO, total - after),
    }


async def build_plan(db, cutoff, decisions, actor):
    original = aliased(Payment)
    payments = (await db.scalars(select(Payment).outerjoin(original, original.id == Payment.reference_payment_id).where(
        Payment.created_at <= cutoff,
        Payment.archive_batch_id.is_(None),
        Payment.bank_ledger_entry_id.is_(None),
        or_(Payment.reference_payment_id.is_(None), (
            original.bank_ledger_entry_id.is_(None) & original.archive_batch_id.is_(None)
        )),
    ).order_by(Payment.created_at, Payment.id))).all()
    payment_ids = {payment.id for payment in payments}
    if set(decisions) - {str(payment_id) for payment_id in payment_ids}:
        raise ValueError("核对文件含有不在本次归档范围内的收款 ID")

    active_refunds = (await db.execute(select(Payment.id, Payment.reference_payment_id).where(
        Payment.reference_payment_id.in_(payment_ids), Payment.record_type == "refund", Payment.active(),
    ))).all()
    adjusted_originals = {refund.reference_payment_id for refund in active_refunds}
    blockers = [f"收款 {refund.reference_payment_id} 有范围外退款 {refund.id}，请调整切换时间"
                for refund in active_refunds if refund.id not in payment_ids]
    blockers.extend(
        f"退款 {payment.payment_no} 的原收款不在本次归档范围"
        for payment in payments if payment.record_type == "refund" and not payment.is_voided
        and payment.reference_payment_id is not None and payment.reference_payment_id not in payment_ids
    )

    accounts = {account.id: account for account in (await db.scalars(select(CompanyAccount))).all()}
    entries = (await db.scalars(select(BankLedgerEntry))).all()
    openings = {entry.account_id: entry for entry in entries if entry.entry_type == "opening_balance"}
    manual = {entry.id: entry for entry in entries if entry.entry_type == "manual"}
    candidates = defaultdict(list)
    candidates_by_date = defaultdict(list)
    for entry in manual.values():
        candidates[cash_key(entry.account_id, entry.entry_date, entry.direction, entry.amount)].append(entry.id)
        candidates_by_date[entry.entry_date, entry.direction, entry.amount].append(entry.id)
    old_cash_by_payment = {payment.id: currently_projected(payment, openings) for payment in payments}
    legacy_copies = defaultdict(list)
    for payment_id, cash in old_cash_by_payment.items():
        if cash:
            legacy_copies[cash_key(cash["account_id"], cash["entry_date"], "income", cash["amount"])].append(payment_id)
    booked = set()
    previously_matched = set((await db.scalars(select(Payment.bank_ledger_entry_id).where(
        Payment.archive_batch_id.is_not(None), Payment.bank_ledger_entry_id.is_not(None),
    ))).all())
    active_bank_links = set((await db.scalars(select(Payment.bank_ledger_entry_id).where(
        Payment.bank_ledger_entry_id.is_not(None), Payment.active(),
    ))).all())

    deltas = defaultdict(lambda: {"income_amount": ZERO, "expense_amount": ZERO})
    rows = []
    for payment in payments:
        old_cash = old_cash_by_payment[payment.id]
        key = cash_key(
            old_cash["account_id"], old_cash["entry_date"], "income", old_cash["amount"],
        ) if old_cash else None
        matches = sorted(candidates[key]) if key else []
        if not key and payment.paid_at and not payment.is_voided:
            direction = "expense" if payment.record_type == "refund" else "income"
            matches = sorted(candidates_by_date[payment.paid_at.date(), direction, abs(payment.amount)])
        legacy_matches = sorted(set(legacy_copies[key]) - {payment.id}) if key else []
        adjusted = (
            payment.id in adjusted_originals or payment.record_type != "receipt"
            or any(allocation.allocated_amount < 0 for allocation in payment.allocations)
        )
        result = {
            "payment_id": payment.id, "payment_no": payment.payment_no, "record_type": payment.record_type,
            "amount": payment.amount, "paid_at": payment.paid_at, "is_voided": payment.is_voided,
            "customer_id": payment.customer_id, "document_id": payment.document_id,
            "payment_account_id": payment.payment_account_id, "before_cash": old_cash,
            "candidate_entry_ids": matches, "candidate_legacy_payment_ids": legacy_matches,
        }
        try:
            if legacy_matches and not decisions.get(str(payment.id)):
                raise ValueError("还有同账户、同日同金额的旧收款，请逐笔核对")
            decision = resolve_cash(
                payment, decisions.get(str(payment.id)), old_cash, matches, manual, openings, accounts,
                uuid5(CASH_NAMESPACE, str(payment.id)) in manual, adjusted,
            )
            bank_id = decision.get("entry_id")
            if bank_id in booked or bank_id in previously_matched:
                raise ValueError("这条台账流水已用于其他历史收款，请重新核对")
            if adjusted and bank_id in active_bank_links:
                raise ValueError("涉及历史调整的流水目前已关联，请先核对在用关联")
            if bank_id:
                booked.add(bank_id)
            if old_cash:
                deltas[old_cash["account_id"]]["income_amount"] -= old_cash["amount"]
            if decision["action"] == "preserve":
                column = "income_amount" if decision["direction"] == "income" else "expense_amount"
                deltas[decision["account_id"]][column] += decision["amount"]
            if decision["action"] == "match":
                target = manual[bank_id]
                decision["matched_cash"] = {
                    "account_id": target.account_id, "entry_date": target.entry_date, "category": target.category,
                    "counterparty_name": target.counterparty_name, "summary": target.summary,
                }
        except (ValueError, TypeError, KeyError) as exc:
            decision = {"action": "review", "reason": str(exc)}
            blockers.append(f"{payment.payment_no} {exc}")
        rows.append({**result, **decision})

    matched_accounts = {row["matched_cash"]["account_id"] for row in rows if "matched_cash" in row}
    affected_accounts = [accounts[key] for key in sorted(set(deltas) | matched_accounts)]
    balances = await account_totals(db, actor, affected_accounts)
    bank = []
    for account in affected_accounts:
        before = balances[account.id]
        delta = deltas[account.id]
        after = {key: before[key] + delta[key] for key in ("income_amount", "expense_amount")}
        after["balance"] = before["balance"]
        if after["balance"] is not None:
            after["balance"] += delta["income_amount"] - delta["expense_amount"]
        bank.append({"account_id": account.id, "account_name": account.name, "before": before, "after": after})
    orders, contracts = await affected_balances(db, payments)
    plan = {
        "cutoff_utc": cutoff, "blockers": blockers,
        "receipts": rows, "account_totals": bank, "orders": orders, "contracts": contracts,
        "counts": {
            "payments": len(rows), "active": sum(not row["is_voided"] for row in rows),
            "preserve": sum(row["action"] == "preserve" for row in rows),
            "matched": sum(row["action"] == "match" for row in rows),
            "review": len(blockers),
        },
        "active_payment_amount": sum((row["amount"] for row in rows if not row["is_voided"]), ZERO),
    }
    return plan, payments, affected_accounts


async def apply_plan(db, plan, payments, accounts, actor, batch_id):
    statement_service = StatementService(db)
    customer_ids = sorted({payment.customer_id for payment in payments if not payment.is_voided})
    for customer_id in customer_ids:
        await statement_service.capture_confirmed_for_customer(customer_id)

    for payment, row in zip(payments, plan["receipts"], strict=True):
        if row["action"] == "preserve":
            customer = await db.get(Customer, payment.customer_id)
            db.add(BankLedgerEntry(
                id=row["entry_id"], account_id=row["account_id"], entry_type="manual",
                direction=row["direction"], entry_date=row["entry_date"], amount=row["amount"],
                category=row["category"], counterparty_name=customer.name[:255],
                summary=(payment.remark or "")[:255], order_id=payment.document_id,
                project_name=payment.document.project_name if payment.document else None,
                department=payment.document.department if payment.document else None,
                created_at=payment.created_at, created_by=actor.id,
            ))
            await db.flush()
        payment.bank_ledger_entry_id = row.get("entry_id")
        payment.archive_batch_id = batch_id
        await log_operation(
            db, actor.id, actor.real_name or actor.username, OBJ_PAYMENT, payment.id, "archive_legacy_receipt",
            before_data={"is_voided": payment.is_voided, "payment_no": payment.payment_no},
            after_data=json.loads(json.dumps({
                "batch_id": batch_id, "action": row["action"], "bank_ledger_entry_id": row.get("entry_id"),
                "evidence": row.get("evidence"), "before_cash": row["before_cash"],
            }, default=encode)),
        )
    await db.flush()

    repo = PaymentRepository(db)
    for row in plan["orders"]:
        order = await db.get(BusinessDocument, row["id"])
        paid = Decimal(str(await repo.get_document_paid_sum(order.id)))
        if paid != row["paid_after"]:
            raise ValueError(f"订单 {order.doc_no} 已收与预览不符")
        order.paid_amount = paid
        order.unpaid_amount = row["unpaid_after"]
    for row in plan["contracts"]:
        contract = await db.get(Contract, row["id"])
        paid = await repo.get_contract_paid_sum(contract.id)
        if paid != row["paid_after"]:
            raise ValueError(f"合同 {contract.contract_no} 已收与预览不符")
        contract.paid_amount = paid
        contract.unpaid_amount = row["unpaid_after"]
    for customer_id in customer_ids:
        await statement_service.refresh_drafts_for_customer(customer_id)

    actual = await account_totals(db, actor, accounts)
    for row in plan["account_totals"]:
        if actual[row["account_id"]] != row["after"]:
            raise ValueError(f"账户 {row['account_name']} 的余额或收支与预览不符")


async def run(args):
    decisions = read_decisions(args.decisions)
    async with AsyncSessionLocal() as db, db.begin():
        if args.apply:
            await db.execute(text("SET LOCAL lock_timeout = '5s'"))
            await db.execute(text(
                "LOCK TABLE bank_ledger_entries, business_documents, contract_documents, contracts, "
                "customer_statements, framework_contract_project_documents, framework_contract_projects, "
                "payment_allocations, payments IN SHARE ROW EXCLUSIVE MODE"
            ))
        else:
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        actor = await db.scalar(select(User).where(
            User.username == args.actor, User.is_active.is_(True), User.deleted_at.is_(None),
        ))
        if not actor or not user_has_permission(actor, "system:super_admin"):
            raise ValueError("请指定有系统管理权限的有效操作人")
        plan, payments, accounts = await build_plan(db, args.cutoff, decisions, actor)
        digest = plan_digest(plan)
        if args.apply:
            if plan["blockers"] or digest != args.expect_plan:
                raise ValueError("仍有待核对事项或预览结果已变化，请重新预览")
            batch_id = uuid4()
            await apply_plan(db, plan, payments, accounts, actor, batch_id)
        else:
            batch_id = None
    print(json.dumps({
        "plan_sha256": digest, "ready_to_apply": not plan["blockers"],
        "archive_batch_id": batch_id, **plan,
    }, default=encode, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", required=True, type=parse_cutoff, help="带时区的切换时间")
    parser.add_argument("--actor", required=True, help="系统管理员的登录名")
    parser.add_argument("--decisions", type=Path, help="逐笔核对决定的 JSON 文件")
    parser.add_argument("--apply", action="store_true", help="应用已核对的预览，默认只读")
    parser.add_argument("--expect-plan", help="确认过的 plan_sha256")
    args = parser.parse_args()
    if args.apply and not args.expect_plan:
        parser.error("--apply 须指定已核对的 --expect-plan")
    try:
        asyncio.run(run(args))
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
