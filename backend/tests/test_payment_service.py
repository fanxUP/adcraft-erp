"""Tests for PaymentService, StatementService, ExpenseService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

# Pre-import models to satisfy SQLAlchemy mapper dependencies
import app.models.customer  # noqa: F401
import app.models.business_document  # noqa: F401
import app.models.user  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.vehicle  # noqa: F401
from app.services.payment_service import PaymentService, StatementService, ExpenseService
from app.schemas.payment import PaymentCreate
from app.models.contract import Contract
from app.models.business_document import BusinessDocument
from tests.conftest import SAMPLE_USER_ID, SAMPLE_ORDER_ID, SAMPLE_CUSTOMER_ID

SAMPLE_CONTRACT_ID = UUID("66666666-6666-6666-6666-666666666666")


def make_mock_payment(**kwargs):
    p = MagicMock()
    p.id = kwargs.get("id", SAMPLE_ORDER_ID)
    p.payment_no = kwargs.get("payment_no", "PAY20260629-0001")
    p.order_id = kwargs.get("order_id", SAMPLE_ORDER_ID)
    p.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_ID)
    p.amount = kwargs.get("amount", 500.0)
    p.payment_method = kwargs.get("payment_method", "bank_transfer")
    p.paid_at = kwargs.get("paid_at", datetime.now(timezone.utc))
    p.remark = kwargs.get("remark")
    p.is_voided = kwargs.get("is_voided", False)
    p.void_reason = kwargs.get("void_reason")
    p.voided_at = kwargs.get("voided_at")
    p.receipt_url = kwargs.get("receipt_url")
    p.document = kwargs.get("document")
    p.created_by = kwargs.get("created_by", SAMPLE_USER_ID)
    p.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return p


def make_mock_contract(**kwargs):
    contract = MagicMock()
    contract.id = kwargs.get("id", SAMPLE_CONTRACT_ID)
    contract.contract_no = kwargs.get("contract_no", "C20260629-0001")
    contract.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_ID)
    contract.customer_name = kwargs.get("customer_name", "测试客户")
    contract.project_name = kwargs.get("project_name", "测试项目")
    contract.contract_type = kwargs.get("contract_type", "制作合同")
    contract.total_amount = kwargs.get("total_amount", 5000.0)
    contract.deleted_at = kwargs.get("deleted_at")
    return contract


def make_mock_statement(**kwargs):
    s = MagicMock()
    s.id = kwargs.get("id", SAMPLE_ORDER_ID)
    s.statement_no = kwargs.get("statement_no", "STMT20260629-0001")
    s.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_ID)
    s.start_date = kwargs.get("start_date", datetime.now(timezone.utc))
    s.end_date = kwargs.get("end_date", datetime.now(timezone.utc))
    s.total_order_amount = kwargs.get("total_order_amount", 5000.0)
    s.total_paid_amount = kwargs.get("total_paid_amount", 2000.0)
    s.total_unpaid_amount = kwargs.get("total_unpaid_amount", 3000.0)
    s.status = kwargs.get("status", "draft")
    s.confirmed_at = kwargs.get("confirmed_at")
    s.confirmed_by = kwargs.get("confirmed_by")
    s.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return s


def make_mock_expense(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", SAMPLE_ORDER_ID)
    e.expense_no = kwargs.get("expense_no", "EXP20260629-0001")
    e.category = kwargs.get("category", "办公")
    e.amount = kwargs.get("amount", 1000.0)
    e.description = kwargs.get("description", "测试支出")
    e.expense_date = kwargs.get("expense_date", datetime.now(timezone.utc))
    e.receipt_url = kwargs.get("receipt_url")
    e.created_by = kwargs.get("created_by", SAMPLE_USER_ID)
    e.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return e


def test_payment_create_can_be_contract_scoped_without_order():
    payload = PaymentCreate(
        contract_id="66666666-6666-6666-6666-666666666666",
        customer_id=SAMPLE_CUSTOMER_ID,
        amount=1000,
    )

    assert str(payload.contract_id) == "66666666-6666-6666-6666-666666666666"
    assert payload.order_id is None


# ══════════════════════════════════════════════════════
# PaymentService Tests
# ══════════════════════════════════════════════════════

@pytest.fixture
def mock_payment_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_payments = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()
    repo.void = AsyncMock()
    repo.get_document_paid_sum = AsyncMock(return_value=0.0)
    repo.get_contract_ids_for_document = AsyncMock(return_value=[])
    repo.get_contract_order_ids = AsyncMock(return_value=[])
    repo.get_contract_paid_sum = AsyncMock(return_value=0.0)
    return repo


@pytest.fixture
def payment_service(mock_payment_repo):
    with patch("app.services.payment_service.PaymentRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_payment_repo
        db = MagicMock()
        db.get = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        svc = PaymentService(db)
        svc.repo = mock_payment_repo
        yield svc, db


# --- List ---

@pytest.mark.asyncio
async def test_list_payments_empty(payment_service):
    svc, _ = payment_service
    svc.repo.list_payments.return_value = ([], 0)
    items, total = await svc.list_payments(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_payments_with_results(payment_service):
    svc, _ = payment_service
    p1 = make_mock_payment(amount=100.0)
    p2 = make_mock_payment(payment_no="PAY20260629-0002", amount=200.0)
    svc.repo.list_payments.return_value = ([p1, p2], 2)

    items, total = await svc.list_payments(page=1, page_size=20)
    assert total == 2
    assert items[0]["amount"] == 100.0
    assert items[1]["amount"] == 200.0


@pytest.mark.asyncio
async def test_get_payment_found(payment_service):
    svc, _ = payment_service
    p = make_mock_payment()
    svc.repo.get_by_id.return_value = p
    result = await svc.get_payment(SAMPLE_ORDER_ID)
    assert result is not None
    assert result["payment_no"] == "PAY20260629-0001"


@pytest.mark.asyncio
async def test_get_payment_not_found(payment_service):
    svc, _ = payment_service
    svc.repo.get_by_id.return_value = None
    result = await svc.get_payment(SAMPLE_ORDER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_payment(payment_service):
    svc, db = payment_service
    order = MagicMock()
    order.total_amount = 5000.0
    order.customer_id = SAMPLE_CUSTOMER_ID
    order.doc_type = "order"
    order.status = "confirmed"
    order.deleted_at = None
    order.sales_user_id = None
    order.doc_no = "O20260629-0001"
    order.project_name = "测试项目"
    contract = make_mock_contract(total_amount=5000.0)
    svc.repo.get_contract_ids_for_document.return_value = [contract.id]
    svc.repo.get_contract_order_ids.return_value = [SAMPLE_ORDER_ID]
    db.get.side_effect = [order, contract, order]

    p = make_mock_payment()
    svc.repo.create.return_value = p
    svc.repo.get_document_paid_sum.side_effect = [0.0, 500.0]

    with patch("app.services.payment_service.generate_payment_no", AsyncMock(return_value="PAY20260629-0002")):
        result = await svc.create_payment({
            "order_id": SAMPLE_ORDER_ID,
            "customer_id": SAMPLE_CUSTOMER_ID,
            "amount": 500.0,
            "payment_method": "cash",
        }, SAMPLE_USER_ID)

    assert result["payment_no"] == "PAY20260629-0002"
    assert result["amount"] == 500.0
    assert order.paid_amount == 500.0
    assert order.unpaid_amount == 4500.0
    db.get.assert_any_await(
        Contract,
        contract.id,
        with_for_update=True,
    )
    db.get.assert_any_await(
        BusinessDocument,
        SAMPLE_ORDER_ID,
        with_for_update=True,
    )


@pytest.mark.asyncio
async def test_create_payment_order_not_found(payment_service):
    svc, db = payment_service
    db.get.return_value = None

    with pytest.raises(ValueError, match="订单不存在"):
        await svc.create_payment({"order_id": SAMPLE_ORDER_ID, "customer_id": SAMPLE_CUSTOMER_ID, "amount": 500.0}, SAMPLE_USER_ID)


@pytest.mark.asyncio
async def test_create_payment_rejects_customer_mismatch(payment_service):
    svc, db = payment_service
    order = MagicMock(
        customer_id=SAMPLE_CUSTOMER_ID,
        doc_type="order",
        status="confirmed",
        total_amount=5000.0,
        deleted_at=None,
    )
    contract = make_mock_contract()
    svc.repo.get_contract_ids_for_document.return_value = [contract.id]
    db.get.return_value = order

    with pytest.raises(ValueError, match="收款客户与订单不一致"):
        await svc.create_payment(
            {
                "order_id": SAMPLE_ORDER_ID,
                "customer_id": SAMPLE_USER_ID,
                "amount": 500.0,
            },
            SAMPLE_USER_ID,
        )

    svc.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_payment_rejects_amount_above_remaining(payment_service):
    svc, db = payment_service
    order = MagicMock(
        customer_id=SAMPLE_CUSTOMER_ID,
        doc_type="order",
        status="confirmed",
        total_amount=1000.0,
        deleted_at=None,
    )
    contract = make_mock_contract(total_amount=1000.0)
    svc.repo.get_contract_ids_for_document.return_value = [contract.id]
    svc.repo.get_contract_order_ids.return_value = [SAMPLE_ORDER_ID]
    db.get.side_effect = [order, contract, order]
    svc.repo.get_contract_paid_sum.return_value = 0.0
    svc.repo.get_document_paid_sum.return_value = 800.0

    with pytest.raises(ValueError, match="超过订单未收金额 200.00 元"):
        await svc.create_payment(
            {
                "order_id": SAMPLE_ORDER_ID,
                "customer_id": SAMPLE_CUSTOMER_ID,
                "amount": 300.0,
            },
            SAMPLE_USER_ID,
        )

    svc.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_contract_payment_auto_allocates_orders_and_keeps_remainder_on_contract(payment_service):
    svc, db = payment_service
    contract = make_mock_contract(total_amount=4000.0)
    order_one = MagicMock(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        total_amount=2000.0,
        customer_id=SAMPLE_CUSTOMER_ID,
        doc_type="order",
        status="confirmed",
        deleted_at=None,
        sales_user_id=None,
    )
    order_two = MagicMock(
        id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        total_amount=1000.0,
        customer_id=SAMPLE_CUSTOMER_ID,
        doc_type="order",
        status="confirmed",
        deleted_at=None,
        sales_user_id=None,
    )
    svc.repo.get_contract_order_ids.return_value = [order_one.id, order_two.id]
    svc.repo.get_contract_paid_sum.return_value = 0.0
    svc.repo.get_document_paid_sum.side_effect = [100.0, 200.0, 100.0, 200.0]
    db.get.side_effect = [contract, order_one, order_two]

    with patch(
        "app.services.payment_service.generate_payment_no",
        AsyncMock(return_value="PAY20260629-0003"),
    ):
        result = await svc.create_payment(
            {
                "contract_id": contract.id,
                "customer_id": SAMPLE_CUSTOMER_ID,
                "amount": 3500.0,
            },
            SAMPLE_USER_ID,
        )

    assert result["amount"] == 3500.0
    assert result["allocation_status"] == "已分配"
    assert [allocation["document_id"] for allocation in result["allocations"]] == [
        str(order_one.id),
        str(order_two.id),
        None,
    ]
    assert [allocation["amount"] for allocation in result["allocations"]] == [
        1900.0,
        800.0,
        800.0,
    ]
    assert contract.paid_amount == 3500.0
    assert contract.unpaid_amount == 500.0


@pytest.mark.asyncio
async def test_contract_payment_rejects_order_outside_selected_contract(payment_service):
    svc, db = payment_service
    contract = make_mock_contract()
    outside_order = MagicMock(
        id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        customer_id=SAMPLE_CUSTOMER_ID,
        doc_type="order",
        status="confirmed",
        deleted_at=None,
    )
    svc.repo.get_contract_order_ids.return_value = [SAMPLE_ORDER_ID]
    db.get.side_effect = [outside_order, contract]

    with pytest.raises(ValueError, match="不属于所选合同"):
        await svc.create_payment(
            {
                "contract_id": contract.id,
                "order_id": UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                "customer_id": SAMPLE_CUSTOMER_ID,
                "amount": 100.0,
            },
            SAMPLE_USER_ID,
        )

    svc.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_void_allocated_payment_recomputes_each_order_and_contract(payment_service):
    svc, db = payment_service
    payment_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    contract = make_mock_contract(id=SAMPLE_CONTRACT_ID, total_amount=1000.0)
    order = MagicMock(
        id=SAMPLE_ORDER_ID,
        total_amount=1000.0,
        paid_amount=250.0,
        unpaid_amount=750.0,
    )
    allocation = MagicMock(
        id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        contract_id=contract.id,
        document_id=order.id,
        allocated_amount=250.0,
        allocation_type="order",
        contract=contract,
    )
    payment = make_mock_payment(
        id=payment_id,
        order_id=None,
        amount=250.0,
        document=None,
    )
    payment.document_id = None
    payment.allocations = [allocation]
    svc.repo.get_by_id.return_value = payment
    svc.repo.get_document_paid_sum.return_value = 0.0
    svc.repo.get_contract_paid_sum.return_value = 0.0
    db.get.side_effect = [order, contract]

    result = await svc.void_payment(payment_id, "客户要求撤销")

    assert result["allocation_status"] == "已分配"
    assert order.paid_amount == 0
    assert order.unpaid_amount == 1000
    assert contract.paid_amount == 0
    assert contract.unpaid_amount == 1000
    svc.repo.get_document_paid_sum.assert_awaited_once_with(order.id)
    svc.repo.get_contract_paid_sum.assert_awaited_once_with(contract.id)


@pytest.mark.asyncio
async def test_void_payment(payment_service):
    svc, db = payment_service
    p = make_mock_payment()
    svc.repo.get_by_id.return_value = p

    order = MagicMock()
    order.total_amount = 5000
    db.get.return_value = order
    svc.repo.get_document_paid_sum.return_value = 0.0

    result = await svc.void_payment(SAMPLE_ORDER_ID, "客户退款")
    assert result["payment_no"] == "PAY20260629-0001"
    svc.repo.get_by_id.assert_awaited_once_with(
        SAMPLE_ORDER_ID,
        for_update=True,
    )
    svc.repo.void.assert_awaited_once_with(p, "客户退款")


@pytest.mark.asyncio
async def test_void_payment_not_found(payment_service):
    svc, _ = payment_service
    svc.repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="收款记录不存在"):
        await svc.void_payment(SAMPLE_ORDER_ID, "原因")


@pytest.mark.asyncio
async def test_void_payment_already_voided(payment_service):
    svc, _ = payment_service
    p = make_mock_payment(is_voided=True)
    svc.repo.get_by_id.return_value = p
    with pytest.raises(ValueError, match="该收款已作废"):
        await svc.void_payment(SAMPLE_ORDER_ID, "原因")


# ══════════════════════════════════════════════════════
# StatementService Tests
# ══════════════════════════════════════════════════════

@pytest.fixture
def mock_statement_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_statements = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()

    async def update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj

    repo.update = AsyncMock(side_effect=update_side_effect)
    repo.get_documents_in_range = AsyncMock(return_value=[])
    repo.get_payments_in_range = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def statement_service(mock_statement_repo):
    with patch("app.services.payment_service.StatementRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_statement_repo
        db = AsyncMock()
        svc = StatementService(db)
        svc.repo = mock_statement_repo
        yield svc


@pytest.mark.asyncio
async def test_list_statements_empty(statement_service):
    svc = statement_service
    svc.repo.list_statements.return_value = ([], 0)
    items, total = await svc.list_statements(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_statement_found(statement_service):
    svc = statement_service
    s = make_mock_statement()
    svc.repo.get_by_id.return_value = s
    svc.repo.get_documents_in_range.return_value = []
    svc.repo.get_payments_in_range.return_value = []

    result = await svc.get_statement(SAMPLE_ORDER_ID)
    assert result is not None
    assert result["statement_no"] == "STMT20260629-0001"


@pytest.mark.asyncio
async def test_get_statement_not_found(statement_service):
    svc = statement_service
    svc.repo.get_by_id.return_value = None
    result = await svc.get_statement(SAMPLE_ORDER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_statement(statement_service):
    svc = statement_service
    created = make_mock_statement(statement_no="STMT20260629-0002")
    svc.repo.create.return_value = created
    svc.repo.get_documents_in_range.return_value = [
        MagicMock(total_amount=3000.0, doc_type="order", status="completed"),
        MagicMock(total_amount=2000.0, doc_type="order", status="confirmed"),
    ]
    svc.repo.get_payments_in_range.return_value = [
        make_mock_payment(amount=1000.0),
    ]

    with patch("app.services.payment_service.generate_statement_no", AsyncMock(return_value="STMT20260629-0002")):
        result = await svc.create_statement({
            "customer_id": SAMPLE_CUSTOMER_ID,
            "start_date": "2026-06-01T00:00:00",
            "end_date": "2026-06-30T23:59:59",
        })

    assert result["statement_no"] == "STMT20260629-0002"


@pytest.mark.asyncio
async def test_create_statement_excludes_quotes_and_cancelled_orders(statement_service):
    svc = statement_service
    created = make_mock_statement(statement_no="STMT20260629-0003")
    svc.repo.create.return_value = created
    svc.repo.get_documents_in_range.return_value = [
        MagicMock(total_amount=3000.0, doc_type="order", status="completed"),
        MagicMock(total_amount=9000.0, doc_type="quote", status="confirmed"),
        MagicMock(total_amount=5000.0, doc_type="order", status="cancelled"),
    ]
    svc.repo.get_payments_in_range.return_value = []

    with patch(
        "app.services.payment_service.generate_statement_no",
        AsyncMock(return_value="STMT20260629-0003"),
    ):
        await svc.create_statement({
            "customer_id": SAMPLE_CUSTOMER_ID,
            "start_date": "2026-06-01T00:00:00",
            "end_date": "2026-06-30T23:59:59",
        })

    statement = svc.repo.create.await_args.args[0]
    assert statement.total_order_amount == 3000.0


@pytest.mark.asyncio
async def test_create_statement_rejects_reverse_date_range(statement_service):
    svc = statement_service

    with pytest.raises(ValueError, match="结束时间不能早于开始时间"):
        await svc.create_statement({
            "customer_id": SAMPLE_CUSTOMER_ID,
            "start_date": "2026-06-30T23:59:59",
            "end_date": "2026-06-01T00:00:00",
        })

    svc.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_statement(statement_service):
    svc = statement_service
    s = make_mock_statement()
    svc.repo.get_by_id.return_value = s
    svc.repo.update.return_value = s

    result = await svc.confirm_statement(SAMPLE_ORDER_ID, SAMPLE_USER_ID)
    assert result["status"] == "confirmed"


@pytest.mark.asyncio
async def test_confirm_statement_not_found(statement_service):
    svc = statement_service
    svc.repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="对账单不存在"):
        await svc.confirm_statement(SAMPLE_ORDER_ID, SAMPLE_USER_ID)


@pytest.mark.asyncio
async def test_confirm_statement_rejects_duplicate_confirmation(statement_service):
    svc = statement_service
    svc.repo.get_by_id.return_value = make_mock_statement(status="confirmed")

    with pytest.raises(ValueError, match="仅草稿对账单可以确认"):
        await svc.confirm_statement(SAMPLE_ORDER_ID, SAMPLE_USER_ID)

    svc.repo.update.assert_not_awaited()


# ══════════════════════════════════════════════════════
# ExpenseService Tests
# ══════════════════════════════════════════════════════

@pytest.fixture
def mock_expense_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.list_expenses = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()

    async def update_side_effect(model_obj, data):
        for key, value in data.items():
            setattr(model_obj, key, value)
        return model_obj

    repo.update = AsyncMock(side_effect=update_side_effect)
    repo.soft_delete = AsyncMock()
    return repo


@pytest.fixture
def expense_service(mock_expense_repo):
    with patch("app.services.payment_service.ExpenseRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_expense_repo
        db = AsyncMock()
        svc = ExpenseService(db)
        svc.repo = mock_expense_repo
        yield svc


@pytest.mark.asyncio
async def test_list_expenses_empty(expense_service):
    svc = expense_service
    svc.repo.list_expenses.return_value = ([], 0)
    items, total = await svc.list_expenses(page=1, page_size=20)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_expense_found(expense_service):
    svc = expense_service
    e = make_mock_expense()
    svc.repo.get_by_id.return_value = e
    result = await svc.get_expense(SAMPLE_ORDER_ID)
    assert result is not None
    assert result["expense_no"] == "EXP20260629-0001"
    assert result["category"] == "办公"


@pytest.mark.asyncio
async def test_get_expense_not_found(expense_service):
    svc = expense_service
    svc.repo.get_by_id.return_value = None
    result = await svc.get_expense(SAMPLE_ORDER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_create_expense(expense_service):
    svc = expense_service
    created = make_mock_expense(expense_no="EXP20260629-0002", amount=500.0)
    svc.repo.create.return_value = created

    with patch("app.services.payment_service.generate_expense_no", AsyncMock(return_value="EXP20260629-0002")):
        result = await svc.create_expense({
            "category": "水电",
            "amount": 500.0,
            "description": "电费",
            "expense_date": "2026-06-15T00:00:00",
        }, SAMPLE_USER_ID)

    assert result["expense_no"] == "EXP20260629-0002"
    assert result["amount"] == 500.0


@pytest.mark.asyncio
async def test_update_expense(expense_service):
    svc = expense_service
    e = make_mock_expense()
    svc.repo.get_by_id.return_value = e

    updated = make_mock_expense(amount=1500.0)
    svc.repo.update.return_value = updated

    result = await svc.update_expense(SAMPLE_ORDER_ID, {"amount": 1500.0})
    assert result["amount"] == 1500.0


@pytest.mark.asyncio
async def test_update_expense_not_found(expense_service):
    svc = expense_service
    svc.repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="支出记录不存在"):
        await svc.update_expense(SAMPLE_ORDER_ID, {"amount": 1500.0})


@pytest.mark.asyncio
async def test_delete_expense(expense_service):
    svc = expense_service
    e = make_mock_expense()
    svc.repo.get_by_id.return_value = e
    await svc.delete_expense(SAMPLE_ORDER_ID)
    svc.repo.soft_delete.assert_awaited_once_with(e)


@pytest.mark.asyncio
async def test_delete_expense_not_found(expense_service):
    svc = expense_service
    svc.repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="支出记录不存在"):
        await svc.delete_expense(SAMPLE_ORDER_ID)
