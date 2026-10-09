"""SQL execution against a disposable PostgreSQL schema, never app DATABASE_URL."""
import asyncio
import importlib
import os
import pkgutil
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import app.models
from app.models.base import Base
from app.models.business_document import BusinessDocument
from app.models.finance_reconciliation import FinancePaymentDateReconciliation
from app.models.outsource import OutsourcePayment, OutsourceTask, OutsourceVendor
from app.models.payable import PayablePayment
from app.models.payment import Expense
from app.models.project_cost import ProjectCost
from app.services.finance_center_service import FinanceCenterService
from app.services.finance_reconciliation_service import FinanceReconciliationService
from app.services.expenditure_service import ExpenditureFilters, ExpenditureService
from app.services.payment_service import ExpenseService
from app.services.project_cost_service import ProjectCostService
from app.services.outsource_service import OutsourceService
from tests.test_expenditure_service import viewer
from app.api.payments import exp_router
from app.api.finance_center import router as finance_center_router
from app.core.database import get_db
from app.core.deps import get_current_user

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    not os.getenv("EXPENDITURE_TEST_URL"), reason="requires explicitly isolated PostgreSQL",
)]


@pytest_asyncio.fixture
async def fixture_db():
    for module in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module.name}")
    schema = "expenditure_test_" + uuid4().hex
    engine = create_async_engine(os.environ["EXPENDITURE_TEST_URL"], connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSession(engine) as db:
            vendor_id, doc_id, cost_id, expense_id, task_id = [uuid4() for _ in range(5)]
            await db.execute(sa.insert(OutsourceVendor.__table__).values(
                id=vendor_id, vendor_no="TEST-V", name="测试供应商", supplier_types=["material", "outsource"], service_types=["production"],
            ))
            await db.execute(sa.insert(BusinessDocument.__table__).values(
                id=doc_id, doc_type="order", doc_no="TEST-O", order_date=date(2026, 9, 1), project_name="测试项目", status="confirmed", cost_amount=999999,
            ))
            await db.execute(sa.insert(ProjectCost.__table__).values(
                id=cost_id, cost_no="TEST-C", document_id=doc_id, supplier_id=vendor_id, category="材料",
                amount=10000, debt_amount=7000, cost_date=datetime(2026, 9, 1),
            ))
            await db.execute(sa.insert(Expense.__table__).values(
                id=expense_id, expense_no="TEST-E", amount=1000, payable_amount=1000,
                expense_date=datetime(2026, 9, 1), category="办公", supplier_id=vendor_id,
            ))
            await db.execute(sa.insert(OutsourceTask.__table__).values(
                id=task_id, task_no="TEST-T", vendor_id=vendor_id, task_type="production", status="completed",
                related_doc_id=doc_id, related_doc_type="order", total_amount=2000, paid_amount=500,
                completed_at=datetime(2026, 9, 3),
            ))
            await db.execute(sa.insert(PayablePayment.__table__), [
                dict(id=uuid4(), payment_no="TEST-P", source_type="project_cost", source_id=cost_id, amount=4000,
                     payment_method="转账支付", paid_at=datetime(2026, 10, 7, 16, 30), is_voided=False),
                dict(id=uuid4(), payment_no="TEST-VOID", source_type="project_cost", source_id=cost_id, amount=2000,
                     payment_method="转账支付", paid_at=datetime(2026, 10, 8), is_voided=True),
            ])
            await db.execute(sa.insert(OutsourcePayment.__table__).values(
                payment_no="TEST-OP", vendor_id=vendor_id, task_id=task_id, amount=500,
                paid_at=datetime(2026, 10, 8), payment_method="转账支付",
            ))
            await db.commit()
            full = viewer("expense:read", "outsource_center:read", "outsource_task:read", "outsource_payment:read", "finance:view_cost")
            yield db, ExpenditureService(db, full), dict(vendor=vendor_id, doc=doc_id, cost=cost_id, expense=expense_id, task=task_id)
            await db.rollback()
    finally:
        async with engine.begin() as conn:
            await conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


async def test_principal_once_partial_payments_and_full_page_summary(fixture_db):
    db, svc, ids = fixture_db
    result = await svc.list_records("ledger", page_size=1)
    assert result["total"] == 3
    assert len(result["items"]) == 1
    assert result["summary"] == dict(amount=13000, paid_amount=7500, remaining_amount=5500, undated_paid_amount=3000)
    cost = await svc.list_records("ledger", filters=ExpenditureFilters(source_type="project_cost"))
    assert cost["total"] == 1
    assert cost["items"][0]["paid_amount"] == 7000
    assert cost["items"][0]["remaining_amount"] == 3000
    assert cost["items"][0]["document_id"] == str(ids["doc"])
    page2 = await svc.list_records("ledger", page=2, page_size=1)
    assert page2["summary"] == result["summary"]
    assert page2["items"][0]["row_key"] != result["items"][0]["row_key"]
    # Service performs no writes, including synthetic payment backfill.
    assert (await db.scalar(sa.select(sa.func.count()).select_from(PayablePayment.__table__))) == 2
    assert await db.scalar(sa.select(ProjectCost.__table__.c.amount).where(ProjectCost.__table__.c.id == ids["cost"])) == Decimal("10000")


async def test_actual_payment_day_timezone_and_unknown_date_not_in_period(fixture_db):
    _, svc, _ = fixture_db
    filters = ExpenditureFilters(start_date=date(2026, 10, 8), end_date=date(2026, 10, 8))
    result = await svc.list_records("disbursements", filters=filters)
    assert result["total"] == 2
    assert result["summary"]["confirmed_paid_amount"] == 4500
    assert result["summary"]["unverified_paid_amount"] == 3000
    assert result["summary"]["unverified_count"] == 1
    assert next(r for r in result["items"] if r["payment_no"] == "TEST-P")["paid_at"] == "2026-10-08T00:30:00"
    previous = await svc.list_records("disbursements", filters=ExpenditureFilters(start_date=date(2026, 10, 7), end_date=date(2026, 10, 7)))
    assert previous["total"] == 0
    all_rows = await svc.list_records("disbursements")
    unknown = [r for r in all_rows["items"] if r["date_status"] == "unverified"]
    assert len(unknown) == 1 and unknown[0]["amount"] == 3000 and unknown[0]["paid_at"] is None
    assert all(r["payment_no"] != "TEST-VOID" for r in all_rows["items"])


async def test_source_permission_filters_apply_to_totals_and_rows(fixture_db):
    db, _, ids = fixture_db
    restricted = ExpenditureService(db, viewer("expense:read"))
    ledger = await restricted.list_records("ledger")
    assert ledger["total"] == 2 and ledger["summary"]["amount"] == 11000
    flow = await restricted.list_records("disbursements")
    assert flow["summary"]["confirmed_paid_amount"] == 4000
    assert "outsource" not in flow["available_sources"]
    scoped = await restricted.list_records("ledger", filters=ExpenditureFilters(supplier_id=ids["vendor"], document_id=ids["doc"], category="材料", keyword="TEST-C"))
    assert scoped["total"] == 1 and scoped["summary"]["amount"] == 10000
    wildcard = await restricted.list_records("ledger", filters=ExpenditureFilters(keyword="%"))
    assert wildcard["total"] == 0


async def test_unknown_external_dates_standalone_and_cancelled_payment_facts(fixture_db):
    db, svc, ids = fixture_db
    await db.execute(sa.update(OutsourceTask.__table__).where(OutsourceTask.__table__.c.id == ids["task"]).values(
        status="cancelled", deleted_at=datetime(2026, 10, 8), paid_amount=700,
    ))
    await db.execute(sa.update(OutsourcePayment.__table__).values(paid_at=None))
    await db.execute(sa.insert(OutsourcePayment.__table__).values(
        payment_no="TEST-STANDALONE", vendor_id=ids["vendor"], amount=100, paid_at=datetime(2026, 10, 8),
    ))
    await db.commit()
    result = await svc.list_records("ledger", filters=ExpenditureFilters(source_type="outsource"))
    assert result["total"] == 2
    task = next(r for r in result["items"] if r["source_kind"] == "outsource_task")
    assert task["remaining_amount"] == 0 and task["source_status"] == "deleted"
    assert task["paid_amount"] == 700 and task["undated_paid_amount"] == 700
    flow = await svc.list_records("disbursements", filters=ExpenditureFilters(source_type="outsource"))
    assert flow["total"] == 3  # 500 actual undated + 200 legacy + 100 standalone
    assert flow["summary"]["amount"] == 800 and flow["summary"]["unverified_paid_amount"] == 700
    assert flow["summary"]["confirmed_paid_amount"] == 100


async def test_legacy_settlement_quote_actual_cost_and_deleted_sources(fixture_db):
    db, svc, ids = fixture_db
    await db.execute(sa.insert(ProjectCost.__table__).values(
        cost_no="TEST-LEGACY", amount=800, debt_amount=800, is_settled=True,
        category="材料", cost_date=datetime(2026, 9, 1),
    ))
    # Any payment history, including voids, prevents legacy fallback.
    await db.execute(sa.update(ProjectCost.__table__).where(ProjectCost.__table__.c.id == ids["cost"]).values(is_settled=True))
    await db.execute(sa.update(PayablePayment.__table__).values(is_voided=True))
    await db.execute(sa.update(Expense.__table__).values(deleted_at=datetime(2026, 10, 8)))
    quote = uuid4()
    await db.execute(sa.insert(BusinessDocument.__table__).values(
        id=quote, doc_type="quote", doc_no="TEST-Q", project_name="打样项目", status="draft", cost_amount=99999,
    ))
    await db.execute(sa.insert(ProjectCost.__table__).values(
        cost_no="TEST-SAMPLE", amount=100, debt_amount=0, document_id=quote, category="打样",
    ))
    await db.commit()
    result = await svc.list_records("ledger", filters=ExpenditureFilters(source_type="project_cost"))
    assert result["total"] == 3
    assert result["summary"]["amount"] == 10900
    assert result["summary"]["paid_amount"] == 3900
    assert result["summary"]["remaining_amount"] == 7000
    assert next(r for r in result["items"] if r["source_no"] == "TEST-SAMPLE")["document_type"] == "quote"
    expense = await svc.list_records("ledger", filters=ExpenditureFilters(source_type="expense"))
    assert expense["total"] == 0


async def test_http_contract_auth_validation_and_real_sql(fixture_db):
    db, _, _ = fixture_db
    app = FastAPI()
    app.include_router(exp_router)
    async def isolated_db():
        yield db
    current = viewer("expense:read")
    async def current_viewer():
        return current
    app.dependency_overrides[get_db] = isolated_db
    app.dependency_overrides[get_current_user] = current_viewer
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ledger = await client.get("/expenses/ledger", params={"page_size": 1})
        assert ledger.status_code == 200
        assert ledger.json()["data"]["summary"]["amount"] == 11000
        assert len(ledger.json()["data"]["items"]) == 1
        flow = await client.get("/expenses/disbursements", params={"start_date": "2026-10-08", "end_date": "2026-10-08"})
        assert flow.json()["data"]["summary"]["confirmed_paid_amount"] == 4000
        for params in ({"start_date": "2026-13-01"}, {"start_date": "2026-10-09", "end_date": "2026-10-08"},
                       {"source_type": "inventory"}, {"supplier_id": "bad"}, {"page_size": 201}):
            assert (await client.get("/expenses/ledger", params=params)).status_code == 422
        assert (await client.get("/expenses/ledger", params={"source_type": "outsource"})).status_code == 403
        current = viewer()
        assert (await client.get("/expenses/ledger")).status_code == 403


async def test_finance_reconciliation_http_routes_enforce_permissions_and_audit(fixture_db):
    db, _, ids = fixture_db
    app = FastAPI()
    app.include_router(exp_router)
    app.include_router(finance_center_router)

    async def isolated_db():
        yield db

    current = viewer("expense:read")
    current.id = None
    current.real_name = "财务核对测试"
    current.username = "finance-review-test"

    async def current_viewer():
        return current

    app.dependency_overrides[get_db] = isolated_db
    app.dependency_overrides[get_current_user] = current_viewer
    payload = {
        "source_type": "project_cost",
        "source_id": str(ids["cost"]),
        "amount": 500,
        "paid_at": "2026-10-03",
        "evidence_type": "bank_statement",
        "evidence_reference": "HTTP流水-RECON-01",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post("/finance-center/payment-reconciliations", json=payload)
        assert denied.status_code == 403

        current.roles = viewer("expense:read", "expense:update").roles
        created = await client.post("/finance-center/payment-reconciliations", json=payload)
        assert created.status_code == 200
        reconciliation_id = created.json()["data"]["id"]
        flow = await client.get("/expenses/disbursements", params={
            "source_type": "project_cost", "start_date": "2026-10-03", "end_date": "2026-10-03",
        })
        assert flow.status_code == 200
        assert any(row.get("reconciliation_id") == reconciliation_id for row in flow.json()["data"]["items"])

        voided = await client.post(
            f"/finance-center/payment-reconciliations/{reconciliation_id}/void",
            json={"reason": "HTTP测试撤销"},
        )
        assert voided.status_code == 200
        unverified = await client.get("/expenses/disbursements", params={
            "source_type": "project_cost", "date_status": "unverified",
        })
        assert unverified.status_code == 200
        assert unverified.json()["data"]["summary"]["unverified_paid_amount"] == 3000

        cost_id, task_id = uuid4(), uuid4()
        await db.execute(sa.insert(ProjectCost.__table__).values(
            id=cost_id, cost_no="HTTP-DUP-C", document_id=ids["doc"], supplier_id=ids["vendor"],
            category="外协加工", amount=600, debt_amount=600,
        ))
        await db.execute(sa.insert(OutsourceTask.__table__).values(
            id=task_id, task_no="HTTP-DUP-T", vendor_id=ids["vendor"], task_type="production", status="completed",
            related_doc_id=ids["doc"], related_doc_type="order", total_amount=600, paid_amount=0,
        ))
        await db.flush()
        current.roles = viewer(
            "expense:read", "expense:update", "finance:view_cost", "outsource_center:read",
            "outsource_task:read", "outsource_vendor:read",
        ).roles
        review = await client.post("/finance-center/cost-overlaps/reviews", json={
            "cost_id": str(cost_id),
            "task_id": str(task_id),
            "decision": "confirmed_not_duplicate",
            "evidence_type": "payment_voucher",
            "evidence_reference": "HTTP凭证-DUP-01",
            "note": "两项费用对应不同交付内容",
        })
        assert review.status_code == 200
        assert review.json()["data"]["decision"] == "confirmed_not_duplicate"
        assert await db.scalar(sa.select(ProjectCost.__table__.c.amount).where(ProjectCost.__table__.c.id == cost_id)) == Decimal("600.00")


async def test_historical_payment_date_reconciliation_splits_amount_without_adding_payment(fixture_db):
    db, expenditure, ids = fixture_db
    reviewer = FinanceReconciliationService(db)

    reconciliation = await reviewer.create_payment_date_reconciliation(
        source_type="project_cost",
        source_id=ids["cost"],
        amount=Decimal("1000.00"),
        paid_at=date(2026, 10, 3),
        evidence_type="bank_statement",
        evidence_reference="流水号-TEST-001",
        note="依据银行回单核对",
        created_by=None,
    )

    flow = await expenditure.list_records(
        "disbursements", filters=ExpenditureFilters(source_type="project_cost")
    )
    dated = next(item for item in flow["items"] if item.get("reconciliation_id") == str(reconciliation["id"]))
    legacy = next(item for item in flow["items"] if item["payment_kind"] == "historical")
    ledger = await expenditure.list_records(
        "ledger", filters=ExpenditureFilters(source_type="project_cost")
    )

    assert dated["amount"] == 1000
    assert dated["paid_at"].startswith("2026-10-03")
    assert dated["evidence_reference"] == "流水号-TEST-001"
    assert dated["reconciliation_source_type"] == "project_cost"
    assert dated["reconciliation_source_id"] == str(ids["cost"])
    assert legacy["amount"] == 2000
    assert flow["summary"]["confirmed_paid_amount"] == 5000
    assert flow["summary"]["unverified_paid_amount"] == 2000
    assert ledger["items"][0]["paid_amount"] == 7000
    assert ledger["summary"]["paid_amount"] == 7000
    assert await db.scalar(sa.select(sa.func.count()).select_from(PayablePayment.__table__)) == 2


async def test_payment_date_reconciliation_rejects_overallocation_and_void_restores_unknown_amount(fixture_db):
    db, expenditure, ids = fixture_db
    reviewer = FinanceReconciliationService(db)
    record = await reviewer.create_payment_date_reconciliation(
        source_type="project_cost",
        source_id=ids["cost"],
        amount=Decimal("2500.00"),
        paid_at=date(2026, 10, 3),
        evidence_type="payment_voucher",
        evidence_reference="凭证-TEST-002",
        note=None,
        created_by=None,
    )
    with pytest.raises(ValueError, match="超过尚未核实金额"):
        await reviewer.create_payment_date_reconciliation(
            source_type="project_cost",
            source_id=ids["cost"],
            amount=Decimal("600.00"),
            paid_at=date(2026, 10, 4),
            evidence_type="bank_statement",
            evidence_reference="流水号-TEST-003",
            note=None,
            created_by=None,
        )

    await reviewer.void_payment_date_reconciliation(
        reconciliation_id=record["id"],
        reason="误选了不相关的回单",
        voided_by=None,
    )
    flow = await expenditure.list_records(
        "disbursements", filters=ExpenditureFilters(source_type="project_cost")
    )
    assert flow["summary"]["unverified_paid_amount"] == 3000
    assert flow["summary"]["confirmed_paid_amount"] == 4000
    assert all(item.get("reconciliation_id") != str(record["id"]) for item in flow["items"])


async def test_concurrent_payment_date_allocations_cannot_overallocate_a_source(fixture_db):
    db, _, ids = fixture_db
    engine = db.bind

    async def allocate(reference: str):
        async with AsyncSession(engine) as session:
            try:
                result = await FinanceReconciliationService(session).create_payment_date_reconciliation(
                    source_type="project_cost",
                    source_id=ids["cost"],
                    amount=Decimal("2000.00"),
                    paid_at=date(2026, 10, 6),
                    evidence_type="bank_statement",
                    evidence_reference=reference,
                    note=None,
                    created_by=None,
                )
                await session.commit()
                return result
            except ValueError as error:
                await session.rollback()
                return str(error)

    results = await asyncio.gather(allocate("并发流水-1"), allocate("并发流水-2"))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert sum(isinstance(result, str) and "超过尚未核实金额" in result for result in results) == 1
    allocated = await db.scalar(sa.select(sa.func.sum(FinancePaymentDateReconciliation.amount)).where(
        FinancePaymentDateReconciliation.source_type == "project_cost",
        FinancePaymentDateReconciliation.source_id == ids["cost"],
        FinancePaymentDateReconciliation.voided_at.is_(None),
    ))
    assert allocated == Decimal("2000.00")


async def test_undated_outsource_payment_date_reconciliation_reuses_original_payment(fixture_db):
    db, expenditure, ids = fixture_db
    result = await db.execute(sa.insert(OutsourcePayment.__table__).values(
        payment_no="TEST-UNDATED-OP", vendor_id=ids["vendor"], task_id=ids["task"], amount=125,
        paid_at=None, payment_method="转账支付",
    ).returning(OutsourcePayment.__table__.c.id))
    payment_id = result.scalar_one()
    await db.commit()

    reconciliation = await FinanceReconciliationService(db).create_payment_date_reconciliation(
        source_type="outsource_payment",
        source_id=payment_id,
        amount=Decimal("125.00"),
        paid_at=date(2026, 10, 5),
        evidence_type="bank_statement",
        evidence_reference="流水号-TEST-004",
        note=None,
        created_by=None,
    )
    flow = await expenditure.list_records(
        "disbursements", filters=ExpenditureFilters(source_type="outsource")
    )
    matched = next(item for item in flow["items"] if item.get("reconciliation_id") == str(reconciliation["id"]))
    assert matched["payment_no"] == "TEST-UNDATED-OP"
    assert matched["amount"] == 125
    assert matched["date_status"] == "confirmed"
    assert matched["reconciliation_source_type"] == "outsource_payment"
    assert matched["reconciliation_source_id"] == str(payment_id)
    original = await db.scalar(sa.select(OutsourcePayment.__table__.c.paid_at).where(OutsourcePayment.__table__.c.id == payment_id))
    assert original is None
    with pytest.raises(ValueError, match="已核实付款日期"):
        await OutsourceService(db).delete_task(ids["task"])


async def test_deleted_outsource_task_cannot_receive_new_date_reconciliation(fixture_db):
    db, _, ids = fixture_db
    await db.execute(
        sa.update(OutsourceTask.__table__)
        .where(OutsourceTask.__table__.c.id == ids["task"])
        .values(deleted_at=datetime(2026, 10, 8))
    )
    await db.commit()

    with pytest.raises(ValueError, match="来源不存在或已删除"):
        await FinanceReconciliationService(db).create_payment_date_reconciliation(
            source_type="outsource_task",
            source_id=ids["task"],
            amount=Decimal("200.00"),
            paid_at=date(2026, 10, 5),
            evidence_type="bank_statement",
            evidence_reference="已删除任务不可核对-001",
            note=None,
            created_by=None,
        )


async def test_cost_overlap_review_records_evidence_without_changing_cost_or_task(fixture_db):
    db, _, ids = fixture_db
    cost_id, task_id = uuid4(), uuid4()
    await db.execute(sa.insert(ProjectCost.__table__).values(
        id=cost_id, cost_no="TEST-DUP-C", document_id=ids["doc"], supplier_id=ids["vendor"],
        category="外协加工", amount=500, debt_amount=500, cost_date=datetime(2026, 9, 1),
    ))
    await db.execute(sa.insert(OutsourceTask.__table__).values(
        id=task_id, task_no="TEST-DUP-T", vendor_id=ids["vendor"], task_type="production", status="completed",
        related_doc_id=ids["doc"], related_doc_type="order", total_amount=500, paid_amount=0,
        completed_at=datetime(2026, 9, 3),
    ))
    await db.commit()

    await FinanceReconciliationService(db).review_cost_overlap(
        cost_id=cost_id,
        task_id=task_id,
        decision="confirmed_duplicate",
        evidence_type="payment_voucher",
        evidence_reference="凭证-重复核对-001",
        note="同一笔外协费用",
        reviewed_by=None,
    )
    result = await FinanceCenterService(db).cost_overlap_candidates(1, 20)
    reviewed = next(item for item in result["items"] if item["cost_id"] == str(cost_id))
    cost_amount = await db.scalar(sa.select(ProjectCost.__table__.c.amount).where(ProjectCost.__table__.c.id == cost_id))
    task_amount = await db.scalar(sa.select(OutsourceTask.__table__.c.total_amount).where(OutsourceTask.__table__.c.id == task_id))

    assert reviewed["review_status"] == "confirmed_duplicate"
    assert reviewed["evidence_reference"] == "凭证-重复核对-001"
    assert cost_amount == Decimal("500.00")
    assert task_amount == Decimal("500.00")


async def test_duplicate_overlap_requires_evidence_for_final_decision(fixture_db):
    db, _, ids = fixture_db
    cost_id, task_id = uuid4(), uuid4()
    await db.execute(sa.insert(ProjectCost.__table__).values(
        id=cost_id, cost_no="TEST-DUP-NO-EVIDENCE-C", document_id=ids["doc"], supplier_id=ids["vendor"],
        category="外协", amount=300, debt_amount=300,
    ))
    await db.execute(sa.insert(OutsourceTask.__table__).values(
        id=task_id, task_no="TEST-DUP-NO-EVIDENCE-T", vendor_id=ids["vendor"], task_type="production", status="completed",
        related_doc_id=ids["doc"], related_doc_type="order", total_amount=300, paid_amount=0,
    ))
    await db.commit()

    with pytest.raises(ValueError, match="证据参考不能为空"):
        await FinanceReconciliationService(db).review_cost_overlap(
            cost_id=cost_id,
            task_id=task_id,
            decision="confirmed_not_duplicate",
            evidence_type="bank_statement",
            evidence_reference=" ",
            note=None,
            reviewed_by=None,
        )


async def test_reconciled_source_cannot_be_lowered_or_deleted_below_allocated_amount(fixture_db):
    db, _, ids = fixture_db
    cost_id = uuid4()
    await db.execute(sa.update(Expense.__table__).where(Expense.__table__.c.id == ids["expense"]).values(
        amount=2000, payable_amount=1500,
    ))
    await db.execute(sa.insert(ProjectCost.__table__).values(
        id=cost_id, cost_no="TEST-LOCK-C", document_id=ids["doc"], supplier_id=ids["vendor"],
        category="材料", amount=1000, debt_amount=900,
    ))
    await db.commit()
    reviewer = FinanceReconciliationService(db)
    await reviewer.create_payment_date_reconciliation(
        source_type="expense", source_id=ids["expense"], amount=Decimal("400"),
        paid_at=date(2026, 10, 3), evidence_type="bank_statement", evidence_reference="流水-LOCK-E",
        note=None, created_by=None,
    )
    await reviewer.create_payment_date_reconciliation(
        source_type="project_cost", source_id=cost_id, amount=Decimal("80"),
        paid_at=date(2026, 10, 3), evidence_type="payment_voucher", evidence_reference="凭证-LOCK-C",
        note=None, created_by=None,
    )

    with pytest.raises(ValueError, match="历史已付金额低于已核实分配"):
        await ExpenseService(db).update_expense(
            ids["expense"], {"amount": 1800, "payable_amount": 1500}
        )
    with pytest.raises(ValueError, match="历史已付金额低于已核实分配"):
        await ProjectCostService(db).update_cost(
            cost_id, {"amount": 970, "debt_amount": 900}
        )
    with pytest.raises(ValueError, match="存在已核实付款日期"):
        await ExpenseService(db).delete_expense(ids["expense"])
    with pytest.raises(ValueError, match="存在已核实付款日期"):
        await ProjectCostService(db).delete_cost(cost_id)
