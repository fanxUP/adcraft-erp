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


def test_date_range_validation():
    with pytest.raises(ValueError, match="日期"):
        ExpenditureFilters(start_date=date(2026, 10, 8), end_date=date(2026, 10, 1))
    with pytest.raises(ValueError):
        ExpenditureFilters(source_type="inventory")


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
