"""Account invariants and real PostgreSQL payment attribution checks."""
import os
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, insert, select, update

from app.api.company_accounts import router
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.bank_ledger import BankLedgerEntry
from app.models.business_document import BusinessDocument
from app.models.company_account import CompanyAccount
from app.models.contract import Contract, ContractDocument
from app.models.customer import Customer
from app.models.payment import Expense, Payment, PaymentAllocation
from app.models.project_cost import ProjectCost
from app.services.company_account_service import CompanyAccountService
from app.services.bank_ledger_service import BankLedgerService
from app.services.expenditure_service import ExpenditureFilters
from app.services.outsource_service import OutsourceService
from app.services.payable_service import PayableService
from app.services.payment_service import ExpenseService, PaymentService
from app.services.project_cost_service import ProjectCostService
from tests.test_expenditure_integration import fixture_db  # noqa: F401
from tests.test_expenditure_service import viewer

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    not os.getenv("EXPENDITURE_TEST_URL"), reason="requires explicitly isolated PostgreSQL",
)]


async def cash(db, name, **extra):
    return await CompanyAccountService(db).save({"name": name, "account_type": "cash", "is_active": True, "is_default": False, **extra})


async def test_default_identity_disable_delete_and_masking(fixture_db):
    db, _, ids = fixture_db
    service = CompanyAccountService(db)
    bank = await service.save(dict(name="公司基本户", account_type="bank", holder_name="测试公司", bank_name="测试银行", account_number="1234567890123456", is_active=True, is_default=True), full=True)
    other = await cash(db, "备用金", is_default=True)
    assert await db.scalar(select(func.count()).select_from(CompanyAccount).where(CompanyAccount.is_default.is_(True))) == 1
    rows = await service.list_accounts(options=True)
    masked = next(row for row in rows if row["id"] == bank["id"])
    assert masked["label"] == "公司基本户（尾号 3456）"
    assert "1234567890123456" not in str(rows)
    assert "holder_name" not in masked
    await db.execute(update(Expense).where(Expense.id == ids["expense"]).values(payment_account_id=UUID(bank["id"])))
    for patch in ({"account_number": "99998888"}, {"account_type": "cash"}, {"holder_name": "其他公司"}):
        with pytest.raises(ValueError, match="账户身份"):
            await service.save(patch, UUID(bank["id"]))
    with pytest.raises(ValueError, match="已有付款关联"):
        await service.delete(UUID(bank["id"]))
    await service.save({"is_active": False}, UUID(bank["id"]))
    assert all(row["id"] != bank["id"] for row in await service.list_accounts(options=True))
    assert any(row["id"] == bank["id"] for row in await service.list_accounts(options=True, include_inactive=True))
    with pytest.raises(ValueError, match="已停用"):
        await service.resolve(bank["id"])
    await service.delete(UUID(other["id"]))


async def test_initial_then_partial_payments_partition_without_changing_source_totals(fixture_db):
    db, expenditure, _ = fixture_db
    first, later = await cash(db, "现金"), await cash(db, "银行备用")
    source = await ExpenseService(db).create_expense({
        "paid_amount": 300, "payable_amount": 700, "payment_account_id": first["id"],
        "payment_method": "现金支付", "expense_date": "2026-10-01",
    }, None)
    source_id = UUID(source["id"])
    for amount, account_id in [(200, later["id"]), (100, first["id"])]:
        await PayableService(db).register_payment("expense", source_id, {
            "request_id": uuid4(), "amount": amount, "payment_account_id": account_id, "payment_method": "转账支付", "paid_at": "2026-10-02",
        }, None)
    ledger = await expenditure.list_records("ledger")
    row = next(row for row in ledger["items"] if row["source_id"] == source["id"])
    assert (row["amount"], row["paid_amount"], row["remaining_amount"]) == (1000, 600, 400)
    upfront = await db.get(Expense, source_id)
    assert str(upfront.payment_account_id) == first["id"]
    assert upfront.payment_method == "现金支付"
    first_rows = await expenditure.list_records("disbursements", filters=ExpenditureFilters(payment_account_id=UUID(first["id"])))
    later_rows = await expenditure.list_records("disbursements", filters=ExpenditureFilters(payment_account_id=UUID(later["id"])))
    unassigned = await expenditure.list_records("disbursements", filters=ExpenditureFilters(account_unassigned=True))
    all_rows = await expenditure.list_records("disbursements")
    assert first_rows["summary"]["amount"] == 400
    assert later_rows["summary"]["amount"] == 200
    assert all_rows["summary"]["amount"] == first_rows["summary"]["amount"] + later_rows["summary"]["amount"] + unassigned["summary"]["amount"]
    later_payment = next(row for row in later_rows["items"] if row["payment_kind"] == "payable")
    await PayableService(db).void_payment("expense", source_id, UUID(later_payment["account_assignment_id"]), "测试撤销")
    after = await expenditure.list_records("disbursements", filters=ExpenditureFilters(payment_account_id=UUID(later["id"])))
    assert after["total"] == 0
    assert (await db.get(Expense, source_id)).amount == Decimal("1000.00")


async def test_outstanding_payables_excludes_fully_paid_and_keeps_partial_sources(fixture_db):
    db, _, _ = fixture_db
    account = await cash(db, "应付测试账户")
    expense_service = ExpenseService(db)
    payable_service = PayableService(db)
    unpaid = await expense_service.create_expense({"paid_amount": 0, "payable_amount": 80}, None)
    partial = await expense_service.create_expense({
        "paid_amount": 20, "payable_amount": 80,
        "payment_account_id": account["id"], "expense_date": "2026-10-01",
    }, None)
    paid = await expense_service.create_expense({"paid_amount": 0, "payable_amount": 30}, None)
    await payable_service.register_payment("expense", UUID(paid["id"]), {
        "request_id": uuid4(), "amount": 30, "payment_account_id": account["id"],
        "paid_at": "2026-10-02",
    }, None)

    rows, total = await payable_service.list_payables(1, 200, status="outstanding")
    ids = {row["source_id"] for row in rows}
    assert total == len(rows)
    assert unpaid["id"] in ids
    assert partial["id"] in ids
    assert paid["id"] not in ids
    assert next(row for row in rows if row["source_id"] == partial["id"])["remaining_amount"] == 80


async def test_partial_expense_appears_as_cash_payment_and_outstanding_balance(fixture_db):
    db, expenditure, _ = fixture_db
    bank = await CompanyAccountService(db).save({
        "name": "分类测试银行户", "account_type": "bank", "holder_name": "测试公司",
        "bank_name": "测试银行", "account_number": "1234567890123456", "is_active": True,
    }, full=True)
    ledger = BankLedgerService(db, expenditure.viewer)
    await ledger.set_opening_balance(UUID(bank["id"]), {"entry_date": datetime(2026, 9, 1).date(), "amount": 0}, None)
    expense = await ExpenseService(db).create_expense({
        "paid_amount": 300, "payable_amount": 700, "payment_account_id": bank["id"],
        "expense_date": "2026-10-01", "category": "材料采购",
    }, None)

    cash = await ledger.get_ledger(UUID(bank["id"]))
    payment = next(row for row in cash["items"] if row.get("source_id") == expense["id"])
    payable = await PayableService(db).get_payable("expense", UUID(expense["id"]))
    assert payment["source_label"] == "费用付款"
    assert payment["expense_amount"] == 300
    assert payment["balance"] == -300
    assert payable["remaining_amount"] == 700


async def test_bank_ledger_same_day_income_sits_below_expenses_and_balances_calculate_bottom_up(fixture_db):
    db, expenditure, _ = fixture_db
    bank = await CompanyAccountService(db).save({
        "name": "同日顺序测试银行户", "account_type": "bank", "holder_name": "测试公司",
        "bank_name": "测试银行", "account_number": "1234567890123456", "is_active": True,
    }, full=True)
    account_id = UUID(bank["id"])
    ledger = BankLedgerService(db, expenditure.viewer)
    await ledger.set_opening_balance(account_id, {"entry_date": date(2026, 9, 2), "amount": 100}, None)
    db.add_all([
        BankLedgerEntry(
            account_id=account_id, entry_type="manual", direction="expense",
            entry_date=date(2026, 9, 2), amount=Decimal("30.00"), summary="当天支出",
        ),
        BankLedgerEntry(
            account_id=account_id, entry_type="manual", direction="income",
            entry_date=date(2026, 9, 2), amount=Decimal("50.00"), summary="当天收入",
        ),
    ])

    result = await ledger.get_ledger(account_id)
    same_day = [
        row for row in result["items"]
        if row["entry_type"] in {"manual", "opening_balance"} and row["entry_date"] == "2026-09-02"
    ]

    assert [(row["entry_type"], row["summary"]) for row in same_day] == [
        ("manual", "当天支出"), ("manual", "当天收入"), ("opening_balance", ""),
    ]
    assert [row["balance"] for row in same_day] == [120, 150, 100]
    assert result["summary"]["balance"] == 120


@pytest.mark.parametrize("has_contract", [True, False])
async def test_bank_business_registration_updates_ledger_costs_and_receivables(fixture_db, has_contract):
    db, _, ids = fixture_db
    account = await CompanyAccountService(db).save({
        "name": "台账测试微信户", "account_type": "wechat", "account_number": "wechat-test",
    })
    account_id = UUID(account["id"])
    customer = Customer(customer_no="TEST-CUSTOMER", name="验收客户")
    db.add(customer)
    await db.flush()
    await db.execute(update(BusinessDocument).where(BusinessDocument.id == ids["doc"]).values(
        customer_id=customer.id, total_amount=500, unpaid_amount=500,
    ))
    if has_contract:
        contract = Contract(contract_no="TEST-CONTRACT", customer_id=customer.id, customer_name=customer.name,
                            project_name="测试项目", total_amount=500, unpaid_amount=500)
        db.add(contract)
        await db.flush()
        db.add(ContractDocument(contract_id=contract.id, document_id=ids["doc"]))
        await db.flush()

    app = FastAPI()
    app.include_router(router)
    current = viewer(
        "company_account:ledger_create", "company_account:ledger_read", "company_account:select", "company_account:read",
        "expense:read", "expense:create", "finance:view_cost",
        "outsource_center:read", "outsource_task:read", "outsource_payment:read",
    )
    current.id, current.username, current.real_name = None, "测试", "测试"
    app.dependency_overrides[get_current_user] = lambda: current

    async def database():
        yield db

    app.dependency_overrides[get_db] = database
    ledger = BankLedgerService(db, current)
    await ledger.set_opening_balance(account_id, {"entry_date": date(2026, 9, 1), "amount": 1000}, None)
    prefix = f"/company-accounts/{account_id}"
    common = {"order_id": str(ids["doc"]), "entry_date": "2026-09-02"}
    cost_data = {**common, "request_id": str(uuid4()), "amount": 80.15, "summary": "采购纸张",
                 "category": "材料费", "supplier_id": str(ids["vendor"])}
    receipt_data = {**common, "request_id": str(uuid4()), "amount": 120.25, "summary": "首笔回款"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post(f"{prefix}/customer-receipts", json=receipt_data)
        assert denied.status_code == 403
        current.roles[0].permissions.extend(viewer("payment:create", "payment:read").roles[0].permissions)

        async def post(endpoint, payload):
            response = await client.post(f"{prefix}/{endpoint}", json=payload)
            assert response.status_code == 200, response.text
            return response.json()

        cost = await post("project-cost-payments", cost_data)
        assert cost["code"] == 0, cost
        assert await post("project-cost-payments", cost_data) == cost
        assert (await post("project-cost-payments", {**cost_data, "amount": 81}))["code"] != 0
        assert (await post("customer-receipts", {**receipt_data, "amount": 501}))["code"] != 0
        receipt = await post("customer-receipts", receipt_data)
        assert receipt["code"] == 0, receipt
        assert await post("customer-receipts", receipt_data) == receipt

    cost_id, payment_id = UUID(cost["data"]["id"]), UUID(receipt["data"]["id"])
    new_cost = await db.get(ProjectCost, cost_id)
    assert (new_cost.document_id, new_cost.amount, new_cost.debt_amount) == (ids["doc"], Decimal("80.15"), 0)
    assert new_cost.supplier_id == ids["vendor"]
    order = await db.get(BusinessDocument, ids["doc"])
    assert (order.paid_amount, order.unpaid_amount, order.cost_amount) == (
        Decimal("120.25"), Decimal("379.75"), Decimal("12080.15"),
    )
    allocations = await db.scalar(select(func.count()).select_from(PaymentAllocation).where(PaymentAllocation.payment_id == payment_id))
    assert allocations == int(has_contract)
    if has_contract:
        await db.refresh(contract)
        assert (contract.paid_amount, contract.unpaid_amount) == (Decimal("120.25"), Decimal("379.75"))
    assert await db.scalar(select(func.count()).select_from(Payment)) == 1
    assert await db.scalar(select(func.count()).select_from(BankLedgerEntry)) == 1  # Opening balance only.
    before_void = await ledger.get_ledger(account_id)
    assert before_void["summary"] == {
        "opening_balance": 1000, "income_amount": 120.25, "expense_amount": 80.15,
        "balance": 1040.10, "transaction_count": 2,
    }
    assert {row["summary"] for row in before_void["items"]} == {"", "采购纸张", "首笔回款"}
    limited_ledger = await BankLedgerService(db, viewer("expense:read")).get_ledger(account_id)
    assert limited_ledger["summary"] == before_void["summary"]
    hidden_receipt = next(row for row in limited_ledger["items"] if row["entry_type"] == "source_receipt")
    assert hidden_receipt["document_id"] is None and hidden_receipt["counterparty_name"] is None

    await PaymentService(db).void_payment(payment_id, "重复收款凭据")
    await db.refresh(order)
    assert order.unpaid_amount == 500
    assert (await ledger.get_ledger(account_id))["summary"]["balance"] == 919.85


async def test_new_cash_requires_account_but_all_unpaid_and_historical_notes_remain_valid(fixture_db):
    db, _, ids = fixture_db
    expense = ExpenseService(db)
    with pytest.raises(ValueError, match="请选择付款账户"):
        await expense.create_expense({"paid_amount": 1, "payable_amount": 0, "expense_date": "2026-10-30"}, None)
    unpaid = await expense.create_expense({"paid_amount": 0, "payable_amount": 50}, None)
    assert unpaid["payment_account_id"] is None
    await db.execute(update(Expense).where(Expense.id == ids["expense"]).values(payable_amount=500))
    before = await expense.get_expense(ids["expense"])
    await db.execute(update(Expense).where(Expense.id == ids["expense"]).values(expense_date=datetime(2026, 9, 1, 14, 20)))
    await expense.update_expense(ids["expense"], {"description": "历史备注", "payment_account_id": None, "expense_date": "2026-09-01"})
    after = await expense.get_expense(ids["expense"])
    assert after["initial_paid_amount"] == before["initial_paid_amount"] == 500
    with pytest.raises(ValueError, match="请选择付款账户"):
        await expense.update_expense(ids["expense"], {"paid_amount": 600})
    account = await cash(db, "暂时停用")
    await db.execute(update(Expense).where(Expense.id == ids["expense"]).values(payment_account_id=UUID(account["id"])))
    await CompanyAccountService(db).save({"is_active": False}, UUID(account["id"]))
    await expense.update_expense(ids["expense"], {"description": "旧账户仍保留"})
    with pytest.raises(ValueError, match="已停用"):
        await expense.update_expense(ids["expense"], {"paid_amount": 550})


async def test_project_cost_and_outsource_payment_account_and_legacy_settlement(fixture_db):
    db, expenditure, ids = fixture_db
    account = await cash(db, "项目付款户")
    cost = await ProjectCostService(db).create_cost({"amount": 100, "debt_amount": 40, "category": "材料", "cost_date": "2026-10-10", "payment_account_id": account["id"]}, None)
    assert cost["payment_account_id"] == account["id"]
    external = await OutsourceService(db).create_payment({"vendor_id": str(ids["vendor"]), "task_id": str(ids["task"]), "amount": 100, "paid_at": "2026-10-10", "payment_account_id": account["id"]}, None)
    assert external["payment_account_id"] == account["id"]
    result = await expenditure.list_records("disbursements", filters=ExpenditureFilters(payment_account_id=UUID(account["id"])))
    assert result["summary"]["amount"] == 160
    # An old settled flag without a payment row must not assign its unknown
    # settlement to the account used for the upfront portion.
    await db.execute(insert(ProjectCost).values(cost_no="OLD-SETTLED", amount=100, debt_amount=70, category="历史", cost_date=datetime(2026, 10, 1), is_settled=True, payment_account_id=UUID(account["id"])))
    result = await expenditure.list_records("disbursements", filters=ExpenditureFilters(payment_account_id=UUID(account["id"])))
    assert result["summary"]["amount"] == 190  # Only upfront 30, not historical settlement 70.


async def test_account_api_permissions_historical_assignment_and_audit(fixture_db):
    db, expenditure, ids = fixture_db
    account = await cash(db, "历史补录户")
    await db.execute(update(Expense).where(Expense.id == ids["expense"]).values(payable_amount=500))
    app = FastAPI()
    app.include_router(router)
    current = viewer("company_account:select", "expense:update")
    current.id, current.username, current.real_name = None, "测试", "测试"
    app.dependency_overrides[get_current_user] = lambda: current
    async def database():
        yield db
    app.dependency_overrides[get_db] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/company-accounts/")).status_code == 403
        options = (await client.get("/company-accounts/options")).json()["data"]
        assert options[0]["id"] == account["id"]
        before = await expenditure.list_records("ledger")
        response = await client.put(f"/company-accounts/assignments/expense/{ids['expense']}", json={"payment_account_id": account["id"]})
        assert response.json()["code"] == 0, response.text
        after = await expenditure.list_records("ledger")
        assert after["summary"] == before["summary"]
        assert str((await db.get(Expense, ids["expense"])).payment_account_id) == account["id"]
        assert (await client.post("/company-accounts/", json={"name": "越权", "account_type": "cash"})).status_code == 403
        current = viewer("company_account:read")
        read_rows = (await client.get("/company-accounts/")).json()["data"]
        assert read_rows[0]["account_number"] is None
        assert (await client.post("/company-accounts/", json={"name": "只读越权", "account_type": "cash"})).status_code == 403
        current = viewer("company_account:select")
        assert (await client.put(f"/company-accounts/assignments/expense/{ids['expense']}", json={"payment_account_id": account["id"]})).status_code == 403
