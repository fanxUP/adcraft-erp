"""Read-only expenditure contracts, including financial permission boundaries."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api import payments
from app.services.expenditure_service import ExpenditureFilters, ExpenditureService


def viewer(*codes):
    return SimpleNamespace(roles=[SimpleNamespace(permissions=[SimpleNamespace(code=c) for c in codes])])


@pytest.mark.parametrize("codes,external", [
    (("expense:read",), False),
    (("expense:read", "outsource_center:read", "outsource_task:read", "outsource_payment:read"), False),
    (("expense:read", "outsource_center:read", "outsource_task:read", "outsource_payment:read", "finance:view_cost"), True),
    (("system:super_admin",), True),
])
def test_complete_external_financial_permission_group(codes, external):
    svc = ExpenditureService(AsyncMock(), viewer(*codes))
    assert ("outsource" in svc.available_sources) is external


@pytest.mark.asyncio
async def test_service_denies_missing_entry_permission_before_query():
    db = AsyncMock()
    with pytest.raises(PermissionError):
        await ExpenditureService(db, viewer()).list_records("ledger")
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_external_filter_does_not_bypass_permission():
    db = AsyncMock()
    with pytest.raises(PermissionError):
        await ExpenditureService(db, viewer("expense:read")).list_records(
            "ledger", filters=ExpenditureFilters(source_type="outsource")
        )
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_dimension_summary_denies_missing_entry_permission_before_query():
    db = AsyncMock()
    with pytest.raises(PermissionError):
        await ExpenditureService(db, viewer()).list_summary("project")
    db.execute.assert_not_awaited()


def test_date_range_validation():
    with pytest.raises(ValueError, match="日期"):
        ExpenditureFilters(start_date=date(2026, 10, 8), end_date=date(2026, 10, 1))
    with pytest.raises(ValueError):
        ExpenditureFilters(source_type="inventory")


def test_dimension_filter_validation_and_disbursement_predicates():
    with pytest.raises(ValueError, match="汇总维度"):
        ExpenditureFilters(group_by="unknown")
    with pytest.raises(ValueError, match="分组"):
        ExpenditureFilters(group_key="department:研发部")

    service = ExpenditureService(AsyncMock(), viewer("expense:read"))
    table = service._disbursements(service._ledger())
    filters = ExpenditureFilters(
        project_keyword="订单项目",
        department_keyword="研发",
        supplier_keyword="供应商甲",
        category_keyword="制作",
        group_by="department",
        group_key="department:value:研发部",
    )
    predicates = service._predicates(table, filters, "disbursements")
    sql = " ".join(str(predicate) for predicate in predicates)
    for column in ("project_name", "department", "supplier_name", "category", "department"):
        assert column in sql


def test_ledger_projection_includes_a_derived_latest_payment_date():
    service = ExpenditureService(AsyncMock(), viewer("expense:read"))

    assert "last_payment_date" in service._ledger().c
    assert "department" in service._ledger().c


def test_ledger_date_filter_uses_the_displayed_latest_payment_date():
    service = ExpenditureService(AsyncMock(), viewer("expense:read"))
    table = service._ledger()
    predicates = service._predicates(
        table,
        ExpenditureFilters(start_date=date(2026, 10, 1), end_date=date(2026, 10, 31)),
        "ledger",
    )

    assert predicates
    assert all("last_payment_date" in str(predicate) for predicate in predicates)
    assert all("source_date" not in str(predicate) for predicate in predicates)


def test_disbursement_projection_includes_parent_business_totals():
    service = ExpenditureService(AsyncMock(), viewer("expense:read"))
    projection = service._disbursements(service._ledger())

    assert {"department", "business_amount", "paid_amount", "remaining_amount"}.issubset(projection.c.keys())


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/expenses/ledger", "/expenses/disbursements"])
async def test_read_routes_precede_dynamic_expense_route_and_require_expense_read(path):
    routes = payments.exp_router.routes
    route = next(r for r in routes if r.path == path)
    assert routes.index(route) < next(i for i, r in enumerate(routes) if r.path == "/expenses/{expense_id}")
    dep = next(d.call for d in route.dependant.dependencies if getattr(d.call, "__name__", "") == "dependency")
    with pytest.raises(HTTPException) as exc:
        await dep(viewer())
    assert exc.value.status_code == 403
    assert await dep(viewer("expense:read")) is not None


@pytest.mark.asyncio
async def test_dimension_summary_route_requires_expense_read():
    routes = payments.exp_router.routes
    route = next(r for r in routes if r.path == "/expenses/summary")
    dep = next(d.call for d in route.dependant.dependencies if getattr(d.call, "__name__", "") == "dependency")
    with pytest.raises(HTTPException) as exc:
        await dep(viewer())
    assert exc.value.status_code == 403
    assert await dep(viewer("expense:read")) is not None
