"""Regression scenarios for the 2026-10-30 workflow audit, with real SQL/services."""
import asyncio
import os
from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_order_first_integration import fixture_db, create_order  # noqa: F401
from app.models.acceptance import AcceptanceForm
from app.models.business_document import BusinessDocument
from app.models.contract import Contract
from app.models.framework_contract import FrameworkContractProject
from app.models.payment import Expense, Payment, PaymentAllocation
from app.models.payable import PayablePayment
from app.models.task import DesignTask, ProductionTask, InstallationTask, Attachment
from app.models.task_order_item_link import TaskOrderItemLink
from app.schemas.payment import ExpenseCreate, PayablePaymentCreate
from app.schemas.outsource import OutsourcePaymentCreate
from app.services.company_account_service import CompanyAccountService
from app.services.contract_service import ContractService
from app.services.framework_contract_service import FrameworkContractService
from app.services.outsource_service import OutsourceService
from app.services.payment_service import ExpenseService
from app.services.payable_service import PayableService
from app.services.task_service import DesignTaskService, ProductionTaskService, InstallationTaskService, get_task_delete_impact

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not os.getenv("ORDER_FIRST_TEST_URL"), reason="requires isolated order test database")]


@pytest.mark.parametrize("value", [None, "", "2026-02-30", "not-a-date"])
async def test_new_payment_dates_are_required_in_models_and_services(fixture_db, value):
    db, orders, customer = fixture_db
    payload = dict(amount=10, paid_at=value, request_id=uuid4())
    with pytest.raises(ValidationError):
        PayablePaymentCreate.model_validate(payload)
    with pytest.raises(ValidationError):
        OutsourcePaymentCreate.model_validate(dict(vendor_id=str(uuid4()), amount=10, paid_at=value))
    with pytest.raises(ValidationError):
        ExpenseCreate.model_validate(dict(paid_amount=10, expense_date=value))
    for operation in (
        PayableService(db).register_payment("expense", uuid4(), payload, orders.viewer.id),
        OutsourceService(db).create_payment(dict(vendor_id=str(uuid4()), amount=10, paid_at=value)),
        ExpenseService(db).create_expense(dict(paid_amount=10, expense_date=value), orders.viewer.id),
    ):
        with pytest.raises(ValueError, match="付款日期"):
            await operation
    # A new payable source without an actual payment is still valid.
    assert ExpenseCreate(paid_amount=0, payable_amount=10).expense_date is None


async def payable_fixture(db, viewer):
    expense = await ExpenseService(db).create_expense(dict(paid_amount=0, payable_amount=1000), viewer.id)
    account = await CompanyAccountService(db).save(dict(name=f"合成付款账户{uuid4().hex[:8]}", account_type="cash"))
    return UUID(expense["id"]), dict(request_id=uuid4(), amount=200,
        payment_account_id=account["id"], payment_method="cash", paid_at="2026-10-30")


async def test_payable_retry_conflict_void_and_real_second_payment(fixture_db):
    db, orders, _ = fixture_db
    source_id, request = await payable_fixture(db, orders.viewer)
    service = PayableService(db)
    for _ in range(2):
        result = await service.register_payment("expense", source_id, request, orders.viewer.id)
        assert result["paid_amount"] == 200
    for change in (dict(amount=100), dict(payment_account_id=str(uuid4())), dict(paid_at="2026-10-29")):
        with pytest.raises(ValueError, match="不同内容"):
            await service.register_payment("expense", source_id, {**request, **change}, orders.viewer.id)
    other_source, _ = await payable_fixture(db, orders.viewer)
    with pytest.raises(ValueError, match="不同内容"):
        await service.register_payment("expense", other_source, request, orders.viewer.id)
    result = await service.register_payment("expense", source_id, {**request, "request_id": uuid4()}, orders.viewer.id)
    assert result["paid_amount"] == 400
    payment = await db.scalar(sa.select(PayablePayment).where(PayablePayment.request_id == request["request_id"]))
    await service.void_payment("expense", source_id, payment.id, "撤销测试")
    result = await service.register_payment("expense", source_id, request, orders.viewer.id)
    assert result["paid_amount"] == 200
    assert await db.scalar(sa.select(sa.func.count()).select_from(PayablePayment)) == 2


async def test_payable_concurrent_retry_and_rollback(fixture_db):
    db, orders, _ = fixture_db
    source_id, request = await payable_fixture(db, orders.viewer)
    actor_id = orders.viewer.id
    await db.commit()
    async def send(payload, fail=False):
        async with AsyncSession(db.bind, expire_on_commit=False) as session:
            result = await PayableService(session).register_payment("expense", source_id, payload, actor_id)
            if fail:
                await session.rollback()
            else:
                await session.commit()
            return result
    await send(request, fail=True)
    assert await db.scalar(sa.select(sa.func.count()).select_from(PayablePayment)) == 0
    results = await asyncio.gather(send(request), send(request))
    assert [row["paid_amount"] for row in results] == [200, 200]
    assert await db.scalar(sa.select(sa.func.count()).select_from(PayablePayment)) == 1


async def test_legacy_missing_expense_date_read_and_unrelated_edit(fixture_db):
    db, orders, _ = fixture_db
    expense = Expense(expense_no="TEST-LEGACY-UNDATED", amount=100, payable_amount=0, expense_date=None)
    db.add(expense)
    await db.flush()
    service = ExpenseService(db)
    result = await service.update_expense(expense.id, dict(description="仅补充说明"))
    assert result["expense_date"] is None
    with pytest.raises(ValueError, match="付款日期"):
        await service.update_expense(expense.id, dict(paid_amount=150))
    with pytest.raises(ValueError, match="付款日期"):
        await service.update_expense(expense.id, dict(expense_date=""))


async def test_framework_order_edit_parent_amount_status_and_readonly_filter(fixture_db):
    db, orders, customer = fixture_db
    order = await create_order(orders, customer)
    oid = UUID(order["id"])
    await orders.documents.change_status(oid, "confirmed", "合成确认", orders.viewer.id)
    contracts = ContractService(db, orders.viewer)
    contract = await contracts.create_contract(dict(customer_id=str(customer.id), customer_name=customer.name,
        project_name="框架草稿", contract_type="框架合同", status="draft", total_amount=1000))
    cid = UUID(contract["id"])
    project = await FrameworkContractService(db, orders.viewer).create_project(dict(contract_id=str(cid),
        customer_id=str(customer.id), customer_name=customer.name, project_name="子项目", project_amount=1000,
        document_ids=[str(oid)]))
    current = await orders.documents.get_by_id(oid)
    payload = dict(header={}, items=[{**current["items"][0], "unit_price":150}], groups=[],
        expected_updated_at=current["updated_at"], reason="合成调价", operated_by=orders.viewer.id)
    preview = await orders.documents.preview_order_edit(oid, **payload)
    await orders.documents.apply_order_edit(oid, **payload, preview_id=preview["preview_id"], plan_hash=preview["plan_hash"],
        preview_expires_at=preview["preview_expires_at"], confirm_high_risk=True)
    parent = await db.get(Contract, cid)
    assert parent.total_amount == parent.unpaid_amount == 1500
    assert (await db.get(FrameworkContractProject, UUID(project["id"]))).project_amount == 1500
    await contracts.update_contract(cid, dict(status="active"))
    await orders.mutate_funds(oid, dict(request_id=uuid4(), operation="receipt", amount=1000,
        paid_at=date(2026, 10, 30), reason="分批收款"))
    await db.commit()
    async with AsyncSession(db.bind, expire_on_commit=False) as readonly:
        await readonly.execute(sa.text("SET TRANSACTION READ ONLY"))
        service = ContractService(readonly)
        for _ in range(2):
            rows, total = await service.list_contracts(1, 20, status="active")
            assert total == len(rows) == 1
            assert (rows[0]["status"], rows[0]["total_amount"], rows[0]["paid_amount"], rows[0]["unpaid_amount"]) == ("active", 1500, 1000, 500)
            detail = await service.get_contract(cid)
            assert detail["status"] == "active" and detail["unpaid_amount"] == 500
            assert (await service.list_contracts(1, 20, status="completed"))[1] == 0
        assert not readonly.dirty


async def test_contract_effective_status_before_count_and_page(fixture_db):
    db, orders, customer = fixture_db
    stored = []
    for index, (project, paid) in enumerate(((None, 1000), (1500, 1000), (500, 500), (0, 0))):
        contract = Contract(contract_no=f"TEST-STATE-{index}", customer_id=customer.id, customer_name=customer.name,
            project_name="合同", total_amount=1000, status="active", contract_type="框架合同" if project is not None else "制作合同")
        db.add(contract)
        await db.flush()
        if project is not None:
            db.add(FrameworkContractProject(contract_id=contract.id, customer_id=customer.id,
                customer_name=customer.name, project_name="子项目", project_amount=project))
        if paid:
            receipt = Payment(payment_no=f"TEST-STATE-P{index}", customer_id=customer.id, amount=paid)
            db.add(receipt)
            await db.flush()
            db.add(PaymentAllocation(payment_id=receipt.id, contract_id=contract.id, allocated_amount=paid, allocation_type="contract"))
        stored.append(contract)
    await db.flush()
    service = ContractService(db)
    for status in ("active", "completed"):
        all_rows, total = await service.list_contracts(1, 20, status=status)
        assert total == len(all_rows) == 2
        page_ids = set()
        for page in (1, 2):
            rows, count = await service.list_contracts(page, 1, status=status)
            assert count == 2 and rows[0]["status"] == status
            page_ids.add(rows[0]["id"])
        assert page_ids == {row["id"] for row in all_rows}
    assert all(row.status == "active" for row in stored)
    assert not db.dirty


async def mixed_tasks(db, orders, customer):
    order = await orders.create(dict(request_id=uuid4(), order_date=date(2026, 10, 30),
        header=dict(customer_id=str(customer.id), project_name="混合任务"), groups=[],
        items=[dict(item_name="已交付A", quantity=1, unit_price=100), dict(item_name="待设计B", quantity=1, unit_price=100)]))
    oid = UUID(order["id"])
    await orders.documents.change_status(oid, "confirmed", "合成确认", orders.viewer.id)
    a, b = [UUID(item["id"]) for item in order["items"]]
    design = await db.scalar(sa.select(DesignTask).where(DesignTask.document_id == oid))
    links = list((await db.scalars(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.task_id == design.id))).all())
    for link in links:
        if link.order_item_id == a:
            link.item_status, link.item_progress_pct, link.completed_quantity = "confirmed", 100, 1
    base = dict(document_id=oid, customer_id=customer.id, project_name="混合任务")
    production = ProductionTask(production_no="TEST-MIX-P", status="in_progress", **base)
    installation = InstallationTask(installation_no="TEST-MIX-I", status="completed", completed_at=datetime(2026,10,29), **base)
    acceptance = AcceptanceForm(acceptance_no="TEST-MIX-A", document_id=oid, status="accepted")
    db.add_all([production, installation, acceptance])
    await db.flush()
    for kind, task, item, status in (("production",production,a,"completed"),("production",production,b,"in_progress"),("installation",installation,a,"completed")):
        db.add(TaskOrderItemLink(task_type=kind, task_id=task.id, order_item_id=item, item_status=status,
            item_progress_pct=100 if item == a else 40, completed_quantity=1 if item == a else 0))
    db.add(Attachment(related_type="production_task", related_id=production.id, filename="合成记录", file_path="/api/uploads/test", file_size=10))
    await db.flush()
    return oid, a, b, design, production, installation, acceptance


async def test_scoped_delete_preserves_sibling_execution_acceptance_and_attachments(fixture_db):
    db, orders, customer = fixture_db
    oid, a, b, design, production, installation, acceptance = await mixed_tasks(db, orders, customer)
    service = DesignTaskService(db, orders.viewer)
    for missing in (None, "", "bad"):
        with pytest.raises(ValueError, match="查看删除影响"):
            await service.delete_task(design.id, plan_hash=missing)
    preview = await get_task_delete_impact(db, "design", design.id, orders.viewer)
    assert preview["allowed"]
    assert "recycle_acceptance" not in [entry["effect"] for entry in preview["entries"]]
    await service.delete_task(design.id, plan_hash=preview["plan_hash"])
    for kind, task in (("design", design), ("production", production), ("installation", installation)):
        link = await db.scalar(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.task_type == kind,
            TaskOrderItemLink.task_id == task.id, TaskOrderItemLink.order_item_id == a))
        assert link.link_status == "active" and link.item_status in ("confirmed", "completed")
        assert link.item_progress_pct == 100 and link.completed_quantity == 1
        assert await db.get(type(task), task.id) is not None
    assert installation.completed_at == datetime(2026, 10, 29)
    assert acceptance.status == "accepted" and acceptance.deleted_at is None
    assert await db.scalar(sa.select(sa.func.count()).select_from(Attachment).where(Attachment.related_id == production.id)) == 1
    assert (await db.get(BusinessDocument, oid)).status != "confirmed"
    assert await db.scalar(sa.select(TaskOrderItemLink.link_status).where(
        TaskOrderItemLink.task_id == production.id, TaskOrderItemLink.order_item_id == b)) == "removed"


@pytest.mark.parametrize("kind", ["production", "installation"])
async def test_delete_rework_creates_new_previous_scope_without_resetting_completed_history(fixture_db, kind):
    db, orders, customer = fixture_db
    oid, a, b, design, production, installation, acceptance = await mixed_tasks(db, orders, customer)
    prior = design if kind == "production" else production
    previous_kind = "design" if kind == "production" else "production"
    previous_status = "confirmed" if kind == "production" else "completed"
    prior_link = await db.scalar(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.task_id == prior.id, TaskOrderItemLink.order_item_id == b))
    prior_link.item_status, prior_link.item_progress_pct, prior_link.completed_quantity = previous_status, 100, 1
    if kind == "installation":
        db.add(TaskOrderItemLink(task_type=kind, task_id=installation.id, order_item_id=b, item_status="in_progress", item_progress_pct=40))
        installation.status = "in_progress"
    await db.flush()
    task = production if kind == "production" else installation
    cls = ProductionTaskService if kind == "production" else InstallationTaskService
    preview = await get_task_delete_impact(db, kind, task.id, orders.viewer)
    assert (await get_task_delete_impact(db, kind, task.id, orders.viewer, lock=True))["plan_hash"] == preview["plan_hash"]
    await cls(db, orders.viewer).delete_task(task.id, plan_hash=preview["plan_hash"])
    assert prior_link.item_status == previous_status and prior_link.item_progress_pct == 100 and prior_link.completed_quantity == 1
    assert await db.scalar(sa.select(sa.func.count()).select_from(TaskOrderItemLink).where(
        TaskOrderItemLink.task_type == previous_kind, TaskOrderItemLink.order_item_id == b,
        TaskOrderItemLink.item_status == "pending", TaskOrderItemLink.link_status == "active")) == 1
    assert acceptance.deleted_at is None


async def test_delete_stale_preview_and_low_permission_rejected_atomically(fixture_db):
    db, orders, customer = fixture_db
    _, a, b, design, production, _, _ = await mixed_tasks(db, orders, customer)
    preview = await get_task_delete_impact(db, "design", design.id, orders.viewer)
    link = await db.scalar(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.task_id == production.id, TaskOrderItemLink.order_item_id == b))
    link.item_progress_pct = 80
    await db.flush()
    with pytest.raises(ValueError, match="关联数据已变化"):
        await DesignTaskService(db, orders.viewer).delete_task(design.id, plan_hash=preview["plan_hash"])
    assert link.link_status == "active"
    limited = SimpleNamespace(id=orders.viewer.id, roles=[SimpleNamespace(permissions=[SimpleNamespace(code="design_task:delete")])])
    # Visibility is separately scoped; use the same employee-visible order.
    from unittest.mock import AsyncMock, patch
    with patch("app.services.task_service.get_visible_task", AsyncMock(return_value=design)):
        preview = await get_task_delete_impact(db, "design", design.id, limited)
        assert not preview["allowed"]
        with pytest.raises(ValueError, match="权限"):
            await DesignTaskService(db, limited).delete_task(design.id, plan_hash=preview["plan_hash"])
    assert link.link_status == "active"


async def test_deleted_execution_scope_is_not_reused_during_reentry(fixture_db):
    from app.services.task_service import _create_production_task_for_item
    db, orders, customer = fixture_db
    _, _, b, design, production, _, _ = await mixed_tasks(db, orders, customer)
    preview = await get_task_delete_impact(db, "production", production.id, orders.viewer)
    # Design B was already open; withdrawal must not reset A or revive B's old link.
    await ProductionTaskService(db, orders.viewer).delete_task(production.id, plan_hash=preview["plan_hash"])
    prior = await db.scalar(sa.select(TaskOrderItemLink).where(TaskOrderItemLink.task_id == production.id, TaskOrderItemLink.order_item_id == b))
    assert prior.item_progress_pct == 40 and prior.link_status == "removed"
    await _create_production_task_for_item(db, design, b)
    assert prior.link_status == "removed" and prior.item_progress_pct == 40
    current = list((await db.scalars(sa.select(TaskOrderItemLink).where(
        TaskOrderItemLink.task_type == "production", TaskOrderItemLink.order_item_id == b,
        TaskOrderItemLink.link_status == "active"))).all())
    assert len(current) == 1 and current[0].task_id != production.id


async def test_task_withdrawal_preserves_paid_outsource_and_rejects_new_payment_after_preview(fixture_db):
    from app.models.outsource import OutsourceVendor, OutsourceTask, OutsourcePayment
    db, orders, customer = fixture_db
    oid, a, b, design, production, _, _ = await mixed_tasks(db, orders, customer)
    vendor = OutsourceVendor(vendor_no="TEST-VENDOR", name="合成外协")
    db.add(vendor)
    await db.flush()
    external = OutsourceTask(task_no="TEST-EXT", vendor_id=vendor.id, related_doc_id=oid,
        related_doc_type="order", order_item_id=b, task_type="production", source_task_type="production",
        source_task_id=production.id, total_amount=100, paid_amount=20, unpaid_amount=80)
    db.add(external)
    await db.flush()
    initial = await get_task_delete_impact(db, "design", design.id, orders.viewer)
    payment = OutsourcePayment(payment_no="TEST-OP", vendor_id=vendor.id, task_id=external.id,
        amount=20, paid_at=datetime(2026, 10, 30))
    db.add(payment)
    await db.flush()
    service = DesignTaskService(db, orders.viewer)
    with pytest.raises(ValueError, match="关联数据已变化"):
        await service.delete_task(design.id, plan_hash=initial["plan_hash"])
    preview = await get_task_delete_impact(db, "design", design.id, orders.viewer)
    await service.delete_task(design.id, plan_hash=preview["plan_hash"])
    assert external.source_task_id is None and external.source_task_type is None
    assert external.related_doc_id == oid and external.order_item_id == b
    assert (external.total_amount, external.paid_amount, external.unpaid_amount) == (100, 20, 80)
    assert payment.amount == 20 and payment.task_id == external.id
    assert await db.get(OutsourcePayment, payment.id) is not None


async def test_task_withdrawal_failure_rolls_back_all_scope_changes(fixture_db):
    from unittest.mock import AsyncMock, patch
    db, orders, customer = fixture_db
    _, a, b, design, production, _, acceptance = await mixed_tasks(db, orders, customer)
    production_id, design_id, acceptance_id = production.id, design.id, acceptance.id
    preview = await get_task_delete_impact(db, "production", production.id, orders.viewer)
    with pytest.raises(RuntimeError, match="合成故障"):
        async with db.begin_nested():
            with patch("app.services.task_service.record_task_event", AsyncMock(side_effect=RuntimeError("合成故障"))):
                await ProductionTaskService(db, orders.viewer).delete_task(production_id, plan_hash=preview["plan_hash"])
    assert await db.scalar(sa.select(TaskOrderItemLink.link_status).where(TaskOrderItemLink.task_id == production_id,
        TaskOrderItemLink.order_item_id == b)) == "active"
    assert await db.scalar(sa.select(AcceptanceForm.status).where(AcceptanceForm.id == acceptance_id)) == "accepted"
    assert await db.scalar(sa.select(DesignTask.scope_status).where(DesignTask.id == design_id)) == "active"


async def test_fully_completed_task_cannot_be_withdrawn(fixture_db):
    db, orders, customer = fixture_db
    _, _, _, _, _, installation, acceptance = await mixed_tasks(db, orders, customer)
    preview = await get_task_delete_impact(db, "installation", installation.id, orders.viewer)
    assert not preview["allowed"] and "已完成" in preview["blocked_reason"]
    with pytest.raises(ValueError, match="已完成"):
        await InstallationTaskService(db, orders.viewer).delete_task(installation.id, plan_hash=preview["plan_hash"])
    assert installation.scope_status == "active" and installation.status == "completed" and acceptance.deleted_at is None


@pytest.mark.parametrize("stored,start,end,paid,expected", [
    ("draft", "2026-11-01", None, 0, "draft"),
    ("draft", "2026-10-30", None, 0, "active"),
    ("active", None, "2026-10-30", 1000, "active"),
    ("active", None, "2026-10-29", 1000, "completed"),
    ("completed", None, "2026-10-29", 500, "active"),
    ("terminated", "2026-10-01", "2026-10-29", 1000, "terminated"),
])
async def test_contract_effective_dates_filter_and_detail_share_rules(fixture_db, monkeypatch, stored, start, end, paid, expected):
    monkeypatch.setattr("app.services.contract_service._business_today", lambda: date(2026,10,30))
    db, orders, customer = fixture_db
    contract = Contract(contract_no="TEST-DATE-CT", customer_id=customer.id, customer_name=customer.name,
        project_name="日期边界", total_amount=1000, status=stored,
        start_date=datetime.fromisoformat(start) if start else None, end_date=datetime.fromisoformat(end) if end else None)
    db.add(contract)
    await db.flush()
    if paid:
        payment = Payment(payment_no="TEST-DATE-P", customer_id=customer.id, amount=paid)
        db.add(payment)
        await db.flush()
        db.add(PaymentAllocation(payment_id=payment.id, contract_id=contract.id, allocated_amount=paid, allocation_type="contract"))
    await db.flush()
    service = ContractService(db)
    assert (await service.list_contracts(1,20,status=expected))[1] == 1
    assert (await service.get_contract(contract.id))["status"] == expected
    assert contract.status == stored and not db.dirty


async def test_framework_concurrent_projects_sync_one_parent_total(fixture_db):
    db, orders, customer = fixture_db
    contract = Contract(contract_no="TEST-CONCURRENT-FW", customer_id=customer.id, customer_name=customer.name,
        project_name="并发子项目", contract_type="框架合同", status="draft", total_amount=0)
    db.add(contract)
    await db.commit()
    cid, customer_id, name = contract.id, customer.id, customer.name
    async def create(amount):
        async with AsyncSession(db.bind, expire_on_commit=False) as session:
            result = await FrameworkContractService(session).create_project(dict(contract_id=str(cid),
                customer_id=str(customer_id), customer_name=name, project_name=f"子项目{amount}", project_amount=amount))
            await session.commit()
            return result
    await asyncio.wait_for(asyncio.gather(create(100), create(200)), timeout=15)
    async with AsyncSession(db.bind) as session:
        parent = await session.get(Contract, cid)
        assert parent.total_amount == parent.unpaid_amount == 300


async def test_deleted_design_item_does_not_inherit_sibling_installation_stage(fixture_db):
    from app.services.task_service import _task_order_item_option_map
    db, orders, customer = fixture_db
    oid, a, b, design, _, _, _ = await mixed_tasks(db, orders, customer)
    order = await db.get(BusinessDocument, oid)
    order.status = "in_installation"
    await db.flush()
    preview = await get_task_delete_impact(db, "design", design.id, orders.viewer)
    assert any(entry["effect"] == "reopen_task" for entry in preview["entries"])
    await DesignTaskService(db, orders.viewer).delete_task(design.id, plan_hash=preview["plan_hash"])
    states = await _task_order_item_option_map(db, oid, "design", viewer=orders.viewer)
    assert states[a]["stage"] == "completed"
    assert states[b]["stage"] == "designing"
    pending = list((await db.scalars(sa.select(TaskOrderItemLink).where(
        TaskOrderItemLink.task_type == "design", TaskOrderItemLink.order_item_id == b,
        TaskOrderItemLink.link_status == "active", TaskOrderItemLink.item_status == "pending"))).all())
    assert len(pending) == 1 and pending[0].task_id != design.id


async def test_legacy_payment_account_change_requires_explicit_date(fixture_db):
    db, orders, _ = fixture_db
    old = Expense(expense_no="TEST-OLD-ACCOUNT", amount=100, payable_amount=0, expense_date=None)
    db.add(old)
    await db.flush()
    account = await CompanyAccountService(db).save(dict(name="补录付款账户", account_type="cash"))
    service = ExpenseService(db)
    with pytest.raises(ValueError, match="付款日期"):
        await service.update_expense(old.id, dict(payment_account_id=account["id"]))
    result = await service.update_expense(old.id, dict(payment_account_id=account["id"], expense_date="2026-10-30"))
    assert result["payment_account_id"] == account["id"]
    assert result["expense_date"].startswith("2026-10-30")
