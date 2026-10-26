"""Real SQL checks, using an explicitly disposable database and random schema."""
import importlib
import os
import pkgutil
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import app.models
from app.models.base import Base
from app.models.business_document import BusinessDocument, OrderChangeAction
from app.models.customer import Customer
from app.models.user import User
from app.models.payment import Payment, PaymentAllocation
from app.services.order_management_service import OrderManagementService

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not os.getenv("ORDER_FIRST_TEST_URL"), reason="requires isolated order test database")]


@pytest_asyncio.fixture
async def fixture_db():
    url = os.environ["ORDER_FIRST_TEST_URL"]
    assert "audit" in url or "test" in url, "explicit disposable database required"
    for module in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module.name}")
    schema = "order_first_test_" + uuid4().hex
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as db:
            user = User(id=uuid4(), username="order_test", password_hash="unused", real_name="测试管理员", roles=[])
            db.add(user)
            customer = Customer(id=uuid4(), customer_no="TEST-C", name="测试客户")
            db.add(customer)
            await db.flush()
            viewer = SimpleNamespace(id=user.id, username=user.username, real_name=user.real_name,
                roles=[SimpleNamespace(permissions=[SimpleNamespace(code="system:super_admin")])])
            yield db, OrderManagementService(db, viewer), customer
            await db.rollback()
    finally:
        async with engine.begin() as connection:
            await connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


async def create_order(service, customer, **header):
    return await service.create({"request_id": uuid4(), "order_date": date(2026, 10, 26),
        "header": {"customer_id": str(customer.id), "project_name": "直接创建测试", **header},
        "items": [{"item_name": "灯箱", "quantity": 10, "unit_price": 100}], "groups": []})


async def test_create_retry_and_discount_noop_edit(fixture_db):
    db, service, customer = fixture_db
    request = {"request_id": uuid4(), "order_date": date(2026, 10, 26),
        "header": {"customer_id": str(customer.id), "project_name": "直接下单", "discount_amount": 100},
        "items": [{"item_name": "灯箱", "quantity": 10, "unit_price": 100}], "groups": []}
    first = await service.create(request)
    second = await service.create(request)
    assert first["id"] == second["id"]
    assert first["total_amount"] == 900
    assert first["discount_amount"] == 100 and first["tax_rate"] == 0
    assert first["status"] == "pending_confirm"
    assert (await db.scalar(sa.select(sa.func.count()).select_from(BusinessDocument))) == 1
    preview = await service.documents.preview_order_edit(UUID(first["id"]), header={}, items=first["items"], groups=[],
        expected_updated_at=first["updated_at"], reason="核对未改金额", operated_by=service.viewer.id)
    assert preview["before"]["total_amount"] == preview["after"]["total_amount"] == 900
    assert preview["diff"]["updated"] == 0


async def test_completed_edit_preserves_receipt_and_creates_surplus_work(fixture_db):
    db, service, customer = fixture_db
    result = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(result["id"]))
    doc.status = "completed"
    receipt = Payment(payment_no="TEST-R", document_id=doc.id, customer_id=customer.id,
                      amount=800, paid_at=datetime(2026, 10, 1))
    db.add(receipt)
    await db.flush()
    doc.paid_amount, doc.unpaid_amount = Decimal("800"), Decimal("200")
    current = await service.documents.get_by_id(doc.id)
    item = {**current["items"][0], "unit_price": 70, "length_unit": None}
    payload = dict(header={}, items=[item], groups=[], expected_updated_at=current["updated_at"], reason="客户确认降价", operated_by=service.viewer.id)
    preview = await service.documents.preview_order_edit(doc.id, **payload)
    assert preview["can_apply"]
    assert preview["item_diffs"][0]["changed_fields"] == ["unit_price"]
    changed = await service.documents.apply_order_edit(doc.id, **payload, preview_id=preview["preview_id"],
        plan_hash=preview["plan_hash"], preview_expires_at=preview["preview_expires_at"], confirm_high_risk=True)
    assert changed["total_amount"] == 700 and changed["overpaid_amount"] == 100
    assert receipt.amount == 800 and receipt.paid_at == datetime(2026, 10, 1)
    assert doc.status == "completed"
    actions = await service.list_actions(doc.id)
    assert any(action["action_type"] == "funds" for action in actions)


async def test_refund_is_signed_immutable_dated_and_idempotent(fixture_db):
    db, service, customer = fixture_db
    result = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(result["id"]))
    doc.status, doc.total_amount = "completed", Decimal("700")
    receipt = Payment(payment_no="TEST-R", document_id=doc.id, customer_id=customer.id, amount=800, paid_at=datetime(2026, 10, 1))
    db.add(receipt)
    await db.flush()
    data = dict(request_id=uuid4(), payment_id=receipt.id, operation="refund", amount=100, paid_at=date(2026, 10, 26), reason="订单降价退差额")
    first = await service.mutate_funds(doc.id, data)
    second = await service.mutate_funds(doc.id, data)
    assert first["paid_amount"] == second["paid_amount"] == 700
    assert receipt.amount == 800
    refunds = (await db.scalars(sa.select(Payment).where(Payment.record_type == "refund"))).all()
    assert len(refunds) == 1 and refunds[0].amount == -100
    assert refunds[0].paid_at == datetime(2026, 10, 26)
    assert refunds[0].reference_payment_id == receipt.id


async def test_direct_order_receipt_without_contract_enters_receivables(fixture_db):
    from app.services.report_service import ReportService
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created["id"]))
    doc.status = "designing"
    data = dict(request_id=uuid4(), operation="receipt", amount=200, paid_at=date(2026, 10, 26), reason="客户预付")
    result = await service.mutate_funds(doc.id, data)
    assert result["paid_amount"] == 200 and result["unpaid_amount"] == 800
    debts = await ReportService(db, viewer=service.viewer).get_customer_debt()
    assert debts[0]["debt_amount"] == 800
    assert debts[0]["standalone_orders"][0]["id"] == str(doc.id)


async def test_credit_release_and_reallocation_preserve_receipt_and_contract_total(fixture_db):
    from app.models.contract import Contract, ContractDocument
    from app.repositories.payment_repo import PaymentRepository
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created["id"]))
    doc.status, doc.total_amount = "completed", Decimal("700")
    contract = Contract(contract_no="TEST-CT", customer_id=customer.id, customer_name=customer.name,
                        project_name="合同", contract_type="制作合同", total_amount=1000, status="active")
    db.add(contract)
    await db.flush()
    db.add(ContractDocument(contract_id=contract.id, document_id=doc.id))
    payment = Payment(payment_no="TEST-P", customer_id=customer.id, document_id=doc.id, amount=800, paid_at=datetime(2026, 10, 1))
    db.add(payment)
    await db.flush()
    db.add(PaymentAllocation(payment_id=payment.id, contract_id=contract.id, document_id=doc.id, allocated_amount=800, allocation_type="order"))
    await db.flush()
    released = await service.mutate_funds(doc.id, dict(request_id=uuid4(), payment_id=payment.id, operation="release_credit", amount=100, paid_at=date.today(), reason="差额留作预收"))
    assert released["paid_amount"] == 700 and released["overpaid_amount"] == 0
    assert payment.amount == 800
    assert await PaymentRepository(db).get_contract_paid_sum(contract.id) == Decimal("800")
    doc.total_amount = Decimal("900")
    await db.flush()
    reapplied = await service.mutate_funds(doc.id, dict(request_id=uuid4(), payment_id=payment.id, operation="apply_credit", amount=100, paid_at=date.today(), reason="追加需求使用预收"))
    assert reapplied["paid_amount"] == 800 and reapplied["unpaid_amount"] == 100
    assert await PaymentRepository(db).get_contract_paid_sum(contract.id) == Decimal("800")
    allocations = (await db.scalars(sa.select(PaymentAllocation).where(PaymentAllocation.payment_id == payment.id))).all()
    assert len(allocations) == 5 and sum(a.allocated_amount for a in allocations) == 800


async def test_completed_quantity_increase_creates_only_delta_scope(fixture_db):
    from app.models.task import DesignTask
    from app.models.task_order_item_link import TaskOrderItemLink
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created["id"]))
    doc.status = "completed"
    task = DesignTask(design_no="TEST-D", document_id=doc.id, customer_id=customer.id, project_name=doc.project_name, status="confirmed", progress_pct=100)
    db.add(task)
    await db.flush()
    item_id = UUID(created["items"][0]["id"])
    old = TaskOrderItemLink(task_type="design", task_id=task.id, order_item_id=item_id,
                          item_status="confirmed", item_progress_pct=100)
    db.add(old)
    await db.flush()
    current = await service.documents.get_by_id(doc.id)
    payload = dict(header={}, items=[{**current["items"][0], "quantity": 12}], groups=[], expected_updated_at=current["updated_at"], reason="追加两件", operated_by=service.viewer.id)
    preview = await service.documents.preview_order_edit(doc.id, **payload)
    result = await service.documents.apply_order_edit(doc.id, **payload, preview_id=preview["preview_id"], plan_hash=preview["plan_hash"], preview_expires_at=preview["preview_expires_at"], confirm_high_risk=True)
    assert result["status"] == "designing"
    assert task.status == "confirmed" and old.completed_quantity == 10
    assert old.scope_snapshot["quantity"] == 10
    assert old.link_status == "removed"
    links = (await db.scalars(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.link_status == "active"))).all()
    assert len(links) == 1 and links[0].planned_quantity == 2 and links[0].completed_quantity == 0


async def test_delete_retains_money_and_restore_only_its_own_tasks(fixture_db):
    from app.models.task import ProductionTask
    from app.models.acceptance import AcceptanceForm
    from app.models.outsource import OutsourceVendor, OutsourceTask
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created["id"]))
    doc.status = "in_production"
    old_cancelled = ProductionTask(production_no="TEST-OLD", document_id=doc.id, customer_id=customer.id, project_name=doc.project_name, status="cancelled")
    open_task = ProductionTask(production_no="TEST-OPEN", document_id=doc.id, customer_id=customer.id, project_name=doc.project_name, status="in_progress")
    accepted = AcceptanceForm(acceptance_no="TEST-ACCEPT", document_id=doc.id, status="accepted")
    receipt = Payment(payment_no="TEST-RECEIPT", customer_id=customer.id, document_id=doc.id, amount=200, paid_at=datetime(2026, 10, 26))
    db.add_all([old_cancelled, open_task, accepted, receipt])
    await db.flush()
    vendor = OutsourceVendor(vendor_no='TEST-V',name='测试供应商')
    db.add(vendor); await db.flush()
    outsourced = OutsourceTask(task_no='TEST-OT',vendor_id=vendor.id,related_doc_id=doc.id,related_doc_type='order',task_type='production',status='pending')
    previous = OutsourceTask(task_no='TEST-OLD-OT',vendor_id=vendor.id,related_doc_id=doc.id,related_doc_type='order',task_type='production',status='cancelled',deleted_at=datetime(2026,10,1))
    db.add_all([outsourced, previous]);await db.flush()
    current = await service.documents.get_by_id(doc.id)
    data = dict(reason="项目取消，保留实际资金", expected_updated_at=current["updated_at"], settlement_amount=0)
    preview = await service.deletion_preview(doc.id, data)
    result = await service.delete(doc.id, {**data, **{key: preview[key] for key in ("preview_id", "plan_hash", "preview_expires_at")}})
    assert result["deleted"] and open_task.status == "cancelled"
    assert outsourced.status=='cancelled' and outsourced.deleted_at
    assert receipt.amount == 200 and accepted.deleted_at is None
    assert (await service.funds(doc.id))["overpaid_amount"] == 200
    restored = await service.documents.restore(doc.id)
    assert restored["total_amount"] == 1000
    assert old_cancelled.status == "cancelled" and open_task.status == "in_progress"
    await db.refresh(outsourced);await db.refresh(previous)
    assert outsourced.status=='pending' and outsourced.deleted_at is None
    assert previous.status=='cancelled' and previous.deleted_at is not None


async def test_new_migration_preserves_existing_order_data(fixture_db):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    import importlib.util
    from pathlib import Path
    db, _, _ = fixture_db
    connection = await db.connection()
    def migrate(conn):
        conn.execute(sa.text("DROP TABLE order_change_actions"))
        for table, columns in {"business_documents": ["creation_request_id", "settlement_adjustment"],
                               "payments": ["record_type", "reference_payment_id", "request_id"],
                               "customer_statements": ["snapshot_json"],
                               "task_order_item_links": ["planned_quantity", "completed_quantity", "scope_snapshot"]}.items():
            for column in columns:
                conn.execute(sa.text(f'ALTER TABLE {table} DROP COLUMN {column} CASCADE'))
        conn.execute(sa.text("ALTER TABLE payment_allocations DROP CONSTRAINT ck_payment_allocations_amount_positive"))
        conn.execute(sa.text("ALTER TABLE payment_allocations ADD CONSTRAINT ck_payment_allocations_amount_positive CHECK (allocated_amount > 0)"))
        path = Path(__file__).parents[1] / "alembic/versions/order_first_01.py"
        spec = importlib.util.spec_from_file_location("order_first_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade()
        assert "order_change_actions" in sa.inspect(conn).get_table_names()
        assert conn.scalar(sa.text("SELECT count(*) FROM customers")) == 1
        conn.execute(BusinessDocument.__table__.insert().values(doc_type='order',doc_no='MIGRATE-NEW',
            project_name='迁移后直接下单',creation_request_id=uuid4(),status='pending_confirm',order_date=date(2026,10,26)))
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError,match='禁止删除真实业务记录'):
                module.downgrade()
        assert conn.scalar(sa.text("SELECT count(*) FROM business_documents")) == 1
    await connection.run_sync(migrate)


async def test_completed_scope_records_actual_work_units_not_current_order_quantity(fixture_db):
    from app.models.task import DesignTask
    from app.models.task_order_item_link import TaskOrderItemLink
    from app.services.task_service import _capture_completed_scope, _assert_live_task_order
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created["id"]))
    task = DesignTask(design_no="TEST-D", document_id=doc.id, customer_id=customer.id, project_name=doc.project_name, status="pending")
    db.add(task)
    await db.flush()
    with pytest.raises(ValueError, match="未确认"):
        await _assert_live_task_order(db, task)
    doc.status = "designing"
    await db.flush()
    await _assert_live_task_order(db, task)
    link = TaskOrderItemLink(task_type="design", task_id=task.id, order_item_id=UUID(created["items"][0]["id"]), planned_quantity=2)
    db.add(link)
    await db.flush()
    await _capture_completed_scope(db, [link], [link.order_item_id])
    assert link.completed_quantity == 2
    assert link.scope_snapshot["quantity"] == 10


async def test_new_receipt_invalidates_existing_delete_preview(fixture_db):
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created["id"]))
    doc.status = "designing"
    await db.flush()
    current = await service.documents.get_by_id(doc.id)
    data = dict(reason="客户取消", expected_updated_at=current["updated_at"], settlement_amount=0)
    preview = await service.deletion_preview(doc.id, data)
    await service.mutate_funds(doc.id, dict(request_id=uuid4(), operation="receipt", amount=100, reason="客户付款", paid_at=date.today()))
    with pytest.raises(ValueError):
        await service.delete(doc.id, {**data, **{key: preview[key] for key in ("preview_id", "plan_hash", "preview_expires_at")}})
    assert doc.deleted_at is None


async def test_order_change_rolls_back_all_lines_on_associated_failure(fixture_db):
    from unittest.mock import AsyncMock, patch
    from app.models.business_document import BusinessDocumentItem, BusinessDocumentVersion
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    order_id = UUID(created["id"])
    payload = dict(header={}, items=[{**created["items"][0], "unit_price": 200}], groups=[],
                   expected_updated_at=created["updated_at"], reason="模拟关联失败", operated_by=service.viewer.id)
    preview = await service.documents.preview_order_edit(order_id, **payload)
    with pytest.raises(RuntimeError, match="关联写入失败"):
        async with db.begin_nested():
            with patch.object(OrderManagementService, "sync_execution", AsyncMock(side_effect=RuntimeError("关联写入失败"))):
                await service.documents.apply_order_edit(order_id, **payload, preview_id=preview["preview_id"], plan_hash=preview["plan_hash"],
                    preview_expires_at=preview["preview_expires_at"], confirm_high_risk=True)
    row = await db.get(BusinessDocument, order_id)
    assert row.total_amount == 1000
    assert await db.scalar(sa.select(BusinessDocumentItem.unit_price).where(BusinessDocumentItem.document_id == order_id)) == 100
    assert await db.scalar(sa.select(sa.func.count()).select_from(BusinessDocumentVersion).where(BusinessDocumentVersion.document_id == order_id)) == 1


async def test_concurrent_retries_create_one_order(fixture_db):
    import asyncio
    db, service, customer = fixture_db
    data = dict(request_id=uuid4(), order_date=date.today(), header={"customer_id": str(customer.id), "project_name": "并发创建"},
                items=[{"item_name": "灯箱", "quantity": 1, "unit_price": 100}], groups=[])
    await db.commit()
    async def create():
        async with AsyncSession(db.bind, expire_on_commit=False) as session:
            result = await OrderManagementService(session, service.viewer).create(data)
            await session.commit()
            return result["id"]
    first, second = await asyncio.gather(create(), create())
    assert first == second
    assert await db.scalar(sa.select(sa.func.count()).select_from(BusinessDocument)) == 1


async def test_http_creation_and_retired_quotation_writes(fixture_db):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api import orders, quotes, cdr_quotes
    from app.core.database import get_db
    from app.core.deps import get_current_user
    from app.ai_assistant.tools import register_all_tools
    from app.ai_assistant.tool_registry import ToolRegistry
    db, service, customer = fixture_db
    application = FastAPI()
    for router in [orders.router, quotes.router, cdr_quotes.router]:
        application.include_router(router, prefix="/api/v1")
    async def database():
        yield db
    application.dependency_overrides[get_db] = database
    application.dependency_overrides[get_current_user] = lambda: service.viewer
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.post("/api/v1/orders/", json={"request_id": str(uuid4()), "order_date": "2026-10-26",
            "header": {"customer_id": str(customer.id), "project_name": "HTTP 直接下单"}, "items": [{"item_name": "灯箱", "quantity": 2, "unit_price": 100}]})
        assert response.status_code == 200 and response.json()["data"]["total_amount"] == 200
        assert (await client.post("/api/v1/quotes/", json={})).status_code == 410
        assert (await client.post("/api/v1/cdr/quotes", json={})).status_code == 410
    assert await db.scalar(sa.select(sa.func.count()).select_from(BusinessDocument).where(BusinessDocument.doc_type == "quote")) == 0
    register_all_tools()
    registry = ToolRegistry()
    assert registry.get("create_order_confirmed").required_permission == "order:create"
    assert registry.get("create_quote_confirmed") is None
    assert registry.get("convert_quote_to_order") is None


async def test_after_commit_dispatch_discards_rolled_back_savepoints(fixture_db):
    import asyncio
    from app.core.after_commit import after_commit
    db, _, _ = fixture_db
    sent = []
    async def send(label):
        sent.append(label)
    after_commit(db, lambda: send('outer'))
    nested = await db.begin_nested()
    after_commit(db, lambda: send('rolled-back'))
    await nested.rollback()
    nested = await db.begin_nested()
    after_commit(db, lambda: send('committed-savepoint'))
    await nested.commit()
    await asyncio.sleep(0)
    assert sent == []
    await db.commit()
    await asyncio.sleep(0)
    assert sent == ['outer', 'committed-savepoint']
    await db.begin()
    after_commit(db, lambda: send('rolled-back-outer'))
    await db.rollback()
    await db.commit()
    await asyncio.sleep(0)
    assert sent == ['outer', 'committed-savepoint']


async def test_draft_contract_acceptance_refresh_and_signed_facts_preserved(fixture_db):
    from app.models.contract import Contract, ContractDocument
    from app.models.acceptance import AcceptanceForm, AcceptanceItem
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created['id']))
    doc.status = 'designing'
    draft = Contract(contract_no='TEST-DRAFT', customer_id=customer.id, customer_name=customer.name, project_name='草稿', contract_type='制作合同', total_amount=1000, status='draft')
    signed = Contract(contract_no='TEST-SIGNED', customer_id=customer.id, customer_name=customer.name, project_name='已签', contract_type='制作合同', total_amount=1000, status='active')
    form = AcceptanceForm(acceptance_no='TEST-DRAFT-A', document_id=doc.id, status='draft')
    accepted = AcceptanceForm(acceptance_no='TEST-SIGNED-A', document_id=doc.id, status='accepted')
    partial = AcceptanceForm(acceptance_no='TEST-PARTIAL-A', document_id=doc.id, status='draft')
    db.add_all([draft, signed, form, accepted, partial]); await db.flush()
    db.add_all([ContractDocument(contract_id=c.id, document_id=doc.id) for c in [draft,signed]])
    item_id = UUID(created['items'][0]['id'])
    db.add_all([AcceptanceItem(acceptance_id=f.id, document_item_id=item_id, item_name='灯箱', quantity=10, unit_price=100, subtotal=1000) for f in [form,accepted]])
    db.add(AcceptanceItem(acceptance_id=partial.id,document_item_id=item_id,item_name='灯箱',quantity=10,unit_price=100,subtotal=1000,item_status='accepted'))
    await db.flush()
    current = await service.documents.get_by_id(doc.id)
    payload = dict(header={}, items=[{**current['items'][0], 'unit_price': 80}], groups=[], expected_updated_at=current['updated_at'], reason='调价测试', operated_by=service.viewer.id)
    preview = await service.documents.preview_order_edit(doc.id, **payload)
    await service.documents.apply_order_edit(doc.id, **payload, **{k:preview[k] for k in ['preview_id','plan_hash','preview_expires_at']}, confirm_high_risk=True)
    await db.refresh(draft); await db.refresh(signed)
    lines = (await db.scalars(sa.select(AcceptanceItem).order_by(AcceptanceItem.acceptance_id))).all()
    by_form = {line.acceptance_id:line for line in lines}
    assert draft.total_amount == 800 and signed.total_amount == 1000
    assert by_form[form.id].subtotal == 800 and by_form[accepted.id].subtotal == 1000
    assert by_form[partial.id].subtotal == 1000
    actions = await service.list_actions(doc.id)
    assert any(row['module']=='contracts' and row['action_type']=='adjustment' for row in actions)
    assert any(row['module']=='acceptance_items' and row['action_type']=='adjustment' for row in actions)


async def test_dashboard_excludes_pending_and_retains_cancelled_settlement(fixture_db):
    from app.services.report_service import ReportService
    db, service, customer = fixture_db
    await create_order(service, customer)
    active = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(active['id']))
    doc.status = 'cancelled'; doc.deleted_at = datetime(2026,10,26)
    doc.total_amount = 300; doc.paid_amount=100; doc.unpaid_amount=200
    await db.flush()
    report = ReportService(db, service.viewer)
    assert await report._sum_orders(datetime(2026,10,1),datetime(2026,10,31,23,59,59)) == 300
    assert await report._calc_month_unpaid(datetime(2026,10,1),datetime(2026,10,31,23,59,59)) == 200
    ranking = await report._customer_debt_ranking()
    assert ranking[0]['debt_amount'] == 200


async def test_draft_statement_tracks_order_and_confirmed_statement_is_frozen(fixture_db):
    from app.models.payment import CustomerStatement
    from app.services.payment_service import StatementService
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created['id']))
    doc.status = 'designing'
    draft = CustomerStatement(statement_no='TEST-ST-DRAFT', customer_id=customer.id, start_date=datetime(2026,10,1), end_date=datetime(2026,10,31), total_order_amount=1000,total_paid_amount=0,total_unpaid_amount=1000,status='draft')
    confirmed = CustomerStatement(statement_no='TEST-ST-CONF', customer_id=customer.id, start_date=datetime(2026,10,1), end_date=datetime(2026,10,31), total_order_amount=1000,total_paid_amount=0,total_unpaid_amount=1000,status='confirmed',confirmed_at=datetime(2026,10,26))
    db.add_all([draft,confirmed]); await db.flush()
    current = await service.documents.get_by_id(doc.id)
    payload = dict(header={},items=[{**current['items'][0],'unit_price':80}],groups=[],expected_updated_at=current['updated_at'],reason='对账后调价',operated_by=service.viewer.id)
    preview = await service.documents.preview_order_edit(doc.id,**payload)
    await service.documents.apply_order_edit(doc.id,**payload,**{k:preview[k] for k in ['preview_id','plan_hash','preview_expires_at']},confirm_high_risk=True)
    await db.refresh(draft); await db.refresh(confirmed)
    assert draft.total_order_amount == 800 and confirmed.total_order_amount == 1000
    detail = await StatementService(db).get_statement(confirmed.id)
    assert detail['orders'][0]['total_amount'] == 1000
    await service.mutate_funds(doc.id,dict(request_id=uuid4(),operation='receipt',amount=200,paid_at=date(2026,10,26),reason='收款'))
    await db.refresh(draft)
    assert draft.total_paid_amount == 200 and draft.total_unpaid_amount == 600
    assert (await StatementService(db).get_statement(confirmed.id))['payments'] == []


async def test_followup_scope_increase_does_not_repeat_historical_ten_units(fixture_db):
    from app.models.task import DesignTask
    from app.models.task_order_item_link import TaskOrderItemLink
    db, service, customer = fixture_db
    created = await create_order(service, customer)
    doc = await db.get(BusinessDocument, UUID(created['id'])); doc.status='completed'
    task = DesignTask(design_no='TEST-D',document_id=doc.id,customer_id=customer.id,project_name=doc.project_name,status='confirmed')
    db.add(task); await db.flush()
    db.add(TaskOrderItemLink(task_type='design',task_id=task.id,order_item_id=UUID(created['items'][0]['id']),item_status='confirmed',item_progress_pct=100))
    await db.flush()
    for quantity in [12,14]:
        current = await service.documents.get_by_id(doc.id)
        data = dict(header={},items=[{**current['items'][0],'quantity':quantity}],groups=[],expected_updated_at=current['updated_at'],reason='追加需求',operated_by=service.viewer.id)
        preview = await service.documents.preview_order_edit(doc.id,**data)
        await service.documents.apply_order_edit(doc.id,**data,**{k:preview[k] for k in ['preview_id','plan_hash','preview_expires_at']},confirm_high_risk=True)
    links=(await db.scalars(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.link_status=='active'))).all()
    assert len(links)==1 and links[0].planned_quantity==4 and links[0].completed_quantity==0


async def test_price_edit_keeps_fixed_supplier_cost_and_quantity_change_requires_review(fixture_db):
    from app.models.outsource import OutsourceTask, OutsourceVendor
    db, service, customer = fixture_db
    created = await create_order(service,customer)
    doc = await db.get(BusinessDocument,UUID(created['id']));doc.status='designing'
    vendor=OutsourceVendor(vendor_no='TEST-V',name='测试供应商');db.add(vendor);await db.flush()
    task=OutsourceTask(task_no='TEST-OT',vendor_id=vendor.id,related_doc_id=doc.id,related_doc_type='order',order_item_id=UUID(created['items'][0]['id']),task_type='production',quantity=10,unit_price=0,total_amount=500,unpaid_amount=500,status='pending')
    db.add(task);await db.flush()
    for update in [{'unit_price':80},{'quantity':12}]:
        current=await service.documents.get_by_id(doc.id)
        data=dict(header={},items=[{**current['items'][0],**update}],groups=[],expected_updated_at=current['updated_at'],reason='调整订单',operated_by=service.viewer.id)
        preview=await service.documents.preview_order_edit(doc.id,**data)
        await service.documents.apply_order_edit(doc.id,**data,**{k:preview[k] for k in ['preview_id','plan_hash','preview_expires_at']},confirm_high_risk=True)
        await db.refresh(task)
        assert task.total_amount==500 and task.quantity==10
    assert any(row['module']=='outsource_tasks' and row['status']=='pending' for row in await service.list_actions(doc.id))


async def test_last_line_delete_restore_preserves_discount_receipts_and_original_scope(fixture_db):
    from app.models.task import DesignTask
    from app.models.task_order_item_link import TaskOrderItemLink
    db,service,customer=fixture_db
    created=await create_order(service,customer,discount_amount=100)
    doc=await db.get(BusinessDocument,UUID(created['id']));doc.status='designing'
    task=DesignTask(design_no='TEST-D',document_id=doc.id,customer_id=customer.id,project_name=doc.project_name,status='pending')
    receipt=Payment(payment_no='TEST-P',customer_id=customer.id,document_id=doc.id,amount=800,paid_at=datetime(2026,10,26))
    db.add_all([task,receipt]);await db.flush()
    db.add(TaskOrderItemLink(task_type='design',task_id=task.id,order_item_id=UUID(created['items'][0]['id']),item_status='pending'))
    await db.flush()
    current=await service.documents.get_by_id(doc.id)
    data=dict(header={},items=[],groups=[],expected_updated_at=current['updated_at'],reason='删除最后一条明细',operated_by=service.viewer.id)
    preview=await service.documents.preview_order_edit(doc.id,**data)
    result=await service.documents.apply_order_edit(doc.id,**data,**{k:preview[k] for k in ['preview_id','plan_hash','preview_expires_at']},confirm_high_risk=True)
    assert result['status']=='cancelled' and result['overpaid_amount']==800
    restored=await service.documents.restore(doc.id)
    assert restored['total_amount']==900 and restored['discount_amount']==100 and restored['paid_amount']==800
    assert len(restored['items'])==1 and task.status=='pending'


async def test_financial_mutation_permission_cannot_be_inherited_from_order_edit(fixture_db):
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.api import orders
    from app.core.database import get_db
    from app.core.deps import get_current_user
    db,service,customer=fixture_db
    created=await create_order(service,customer)
    restricted=SimpleNamespace(id=service.viewer.id,roles=[SimpleNamespace(permissions=[SimpleNamespace(code='order:read'),SimpleNamespace(code='order:update')])])
    application=FastAPI();application.include_router(orders.router,prefix='/api/v1')
    async def database(): yield db
    application.dependency_overrides[get_db]=database
    application.dependency_overrides[get_current_user]=lambda:restricted
    async with AsyncClient(transport=ASGITransport(app=application),base_url='http://test') as client:
        response=await client.post('/api/v1/orders/'+created['id']+'/funds',json=dict(request_id=str(uuid4()),operation='receipt',amount=10,paid_at='2026-10-26',reason='无权限'))
        assert response.status_code==403
        assert (await client.get('/api/v1/orders/'+created['id']+'/funds')).status_code==403
    assert await db.scalar(sa.select(sa.func.count()).select_from(Payment))==0


async def test_historical_quote_cost_is_readonly(fixture_db):
    from app.services.project_cost_service import ProjectCostService
    db, service, customer = fixture_db
    legacy = BusinessDocument(doc_type='quote',doc_no='Q-LEGACY',customer_id=customer.id,project_name='历史报价',status='confirmed')
    db.add(legacy); await db.flush()
    costs = ProjectCostService(db)
    with pytest.raises(ValueError, match='新成本请登记到订单'):
        await costs.create_cost({'quote_id':str(legacy.id),'category':'材料','amount':100},service.viewer.id)
    with pytest.raises(ValueError, match='历史报价成本只读'):
        await costs._assert_cost_document_mutable(SimpleNamespace(document=legacy))


async def test_confirmation_retry_and_customer_change_refresh_both_draft_statements(fixture_db):
    from app.models.payment import CustomerStatement
    from app.models.task import DesignTask
    db, service, customer = fixture_db
    created=await create_order(service,customer)
    other=Customer(customer_no='OTHER-C',name='另一个客户');db.add(other);await db.flush()
    statements=[CustomerStatement(statement_no='TEST-ST-'+str(i),customer_id=c.id,start_date=datetime(2026,10,1),end_date=datetime(2026,10,31),status='draft') for i,c in enumerate([customer,other])]
    db.add_all(statements);await db.flush()
    doc_id=UUID(created['id'])
    for _ in range(2):
        result=await service.documents.change_status(doc_id,'confirmed',None,service.viewer.id)
        assert result['status']=='designing'
    assert await db.scalar(sa.select(sa.func.count()).select_from(DesignTask).where(DesignTask.document_id==doc_id))==1
    await db.refresh(statements[0]);assert statements[0].total_order_amount==1000
    current=await service.documents.get_by_id(doc_id)
    data=dict(header={'customer_id':str(other.id)},items=current['items'],groups=[],expected_updated_at=current['updated_at'],reason='更正无资金订单客户',operated_by=service.viewer.id)
    preview=await service.documents.preview_order_edit(doc_id,**data)
    await service.documents.apply_order_edit(doc_id,**data,**{k:preview[k] for k in ['preview_id','plan_hash','preview_expires_at']},confirm_high_risk=True)
    for statement in statements:await db.refresh(statement)
    assert statements[0].total_order_amount==0 and statements[1].total_order_amount==1000
