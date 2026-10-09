from datetime import date, datetime
import importlib
import pkgutil
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Select

import app.models
from app.api import finance_center
from app.services.finance_center_service import FinanceCenterService


# ORM selects can trigger relationship mapper configuration, which requires
# the same complete model registration used by database-backed integration tests.
for model_info in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{model_info.name}")


def _route_permissions(method: str, path: str) -> tuple[str, ...]:
    route = next(
        route
        for route in finance_center.router.routes
        if method in route.methods and route.path == path
    )
    for dependency in route.dependant.dependencies:
        call = dependency.call
        closure = getattr(call, "__closure__", None)
        if getattr(call, "__name__", None) != "dependency" or not closure:
            continue
        for cell in closure:
            value = cell.cell_contents
            if isinstance(value, str):
                return (value,)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    return ()


def _sql(statement: Select) -> tuple[str, dict]:
    compiled = statement.compile(dialect=postgresql.dialect())
    return compiled.string.lower(), compiled.params


@pytest.mark.asyncio
async def test_receipt_summary_uses_actual_paid_at_and_keeps_undated_amount_separate():
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                one=lambda: SimpleNamespace(
                    period_count=2,
                    period_amount=1250,
                    undated_count=1,
                    undated_amount=300,
                )
            )
        )
    )

    result = await FinanceCenterService(db).receipt_summary(
        date(2026, 10, 1), date(2026, 10, 9)
    )

    statement = db.execute.await_args.args[0]
    sql, params = _sql(statement)
    assert isinstance(statement, Select)
    assert "payments.paid_at" in sql
    assert "payments.is_voided is false" in sql
    assert "created_at" not in sql
    assert datetime(2026, 10, 1) in params.values()
    assert datetime(2026, 10, 10) in params.values()
    assert result == {
        "period": {"count": 2, "amount": 1250.0},
        "undated": {"count": 1, "amount": 300.0},
        "source": "payments",
        "date_basis": "paid_at",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (date(2026, 10, 10), date(2026, 10, 9)),
        (date(2026, 1, 1), date.max),
    ],
)
async def test_receipt_summary_rejects_invalid_or_overflowing_date_ranges(
    start_date, end_date
):
    db = SimpleNamespace(execute=AsyncMock())

    with pytest.raises(ValueError, match="收款统计日期范围无效"):
        await FinanceCenterService(db).receipt_summary(start_date, end_date)

    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cost_overlap_returns_review_candidates_without_classifying_or_mutating():
    cost_id = uuid4()
    task_id = uuid4()
    completed_at = datetime(2026, 10, 8, 12, 30)
    row = {
        "cost_id": cost_id,
        "cost_no": "PC-001",
        "category": "外协加工",
        "cost_amount": 500,
        "doc_no": "O20261008-0001",
        "project_name": "项目甲",
        "task_id": task_id,
        "task_no": "OT-001",
        "task_type": "production",
        "task_status": "completed",
        "task_amount": 500,
        "completed_at": completed_at,
        "supplier_name": "供应商甲",
    }
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=1),
        execute=AsyncMock(
            return_value=SimpleNamespace(
                mappings=lambda: SimpleNamespace(all=lambda: [row])
            )
        ),
    )

    result = await FinanceCenterService(db).cost_overlap_candidates(1, 20)

    statement = db.execute.await_args.args[0]
    sql, params = _sql(statement)
    assert isinstance(statement, Select)
    assert "completed_outsource_task.related_doc_id = manual_cost.document_id" in sql
    assert "completed_outsource_task.vendor_id = manual_cost.supplier_id" in sql
    assert "completed_outsource_task.total_amount = manual_cost.amount" in sql
    assert "cost_document.doc_type" in sql
    assert "completed_outsource_task.status" in sql
    assert "manual_cost.category ilike" in sql
    assert "manual_cost.deleted_at is null" in sql
    assert "completed_outsource_task.deleted_at is null" in sql
    assert "order" in params.values()
    param_values = {
        item
        for value in params.values()
        for item in (value if isinstance(value, (list, tuple)) else [value])
    }
    assert {"completed", "settled"}.issubset(param_values)
    assert result == {
        "items": [
            {
                "row_key": f"{cost_id}:{task_id}",
                "cost_id": str(cost_id),
                "cost_no": "PC-001",
                "category": "外协加工",
                "cost_amount": 500.0,
                "document_no": "O20261008-0001",
                "project_name": "项目甲",
                "task_id": str(task_id),
                "task_no": "OT-001",
                "task_type": "production",
                "task_status": "completed",
                "task_amount": 500.0,
                "completed_at": "2026-10-08T12:30:00",
                "supplier_name": "供应商甲",
                "match_rule": "同一订单、同一供应商、相同金额，且项目成本分类包含外协或加工",
                "review_status": "待人工核对",
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    db.scalar.assert_awaited_once()
    db.execute.assert_awaited_once()


def test_finance_center_routes_require_the_relevant_read_permissions():
    assert _route_permissions("GET", "/finance-center/cashflow") == ("payment:read",)
    assert _route_permissions("GET", "/finance-center/cost-overlaps") == (
        "finance:view_cost",
        "outsource_center:read",
        "outsource_task:read",
        "outsource_vendor:read",
    )
