import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api import quotes
from app.core.permissions import (
    PERM_QUOTE_CONFIRM,
    PERM_QUOTE_CONVERT,
    PERM_QUOTE_CREATE,
    PERM_QUOTE_DELETE,
    PERM_QUOTE_READ,
    PERM_QUOTE_UPDATE,
)


def _route_permission(method: str, path: str) -> str | None:
    for route in quotes.router.routes:
        if path != route.path or method.upper() not in route.methods:
            continue
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) == "dependency" and closure:
                for cell in closure:
                    if isinstance(cell.cell_contents, str):
                        return cell.cell_contents
    return None


def test_delete_quote_uses_quote_delete_permission():
    assert _route_permission("DELETE", "/quotes/{quote_id}") == PERM_QUOTE_DELETE


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/quotes/", PERM_QUOTE_READ),
        ("POST", "/quotes/", PERM_QUOTE_CREATE),
        ("POST", "/quotes/import", PERM_QUOTE_CREATE),
        ("GET", "/quotes/{quote_id}", PERM_QUOTE_READ),
        ("PUT", "/quotes/{quote_id}", PERM_QUOTE_UPDATE),
        ("POST", "/quotes/{quote_id}/items", PERM_QUOTE_UPDATE),
        (
            "PUT",
            "/quotes/{quote_id}/items/{item_id}",
            PERM_QUOTE_UPDATE,
        ),
        (
            "DELETE",
            "/quotes/{quote_id}/items/{item_id}",
            PERM_QUOTE_UPDATE,
        ),
        ("POST", "/quotes/{quote_id}/confirm", PERM_QUOTE_CONFIRM),
        (
            "POST",
            "/quotes/{quote_id}/revert-to-draft",
            PERM_QUOTE_CONFIRM,
        ),
        ("POST", "/quotes/{quote_id}/cancel", PERM_QUOTE_CONFIRM),
        (
            "POST",
            "/quotes/{quote_id}/convert-to-order",
            PERM_QUOTE_CONVERT,
        ),
        (
            "POST",
            "/quotes/{quote_id}/import-items",
            PERM_QUOTE_UPDATE,
        ),
    ],
)
def test_quote_routes_use_business_permissions(method, path, permission):
    assert _route_permission(method, path) == permission


@pytest.mark.asyncio
async def test_quote_list_hides_terminal_statuses_by_default_but_allows_explicit_filter():
    db = MagicMock()
    current_user = MagicMock()

    with patch("app.api.quotes.BusinessDocumentService") as service_class:
        service = service_class.return_value
        service.list_all = AsyncMock(return_value=([], 0))

        await quotes.list_quotes(
            page=1,
            page_size=20,
            status=None,
            customer_id=None,
            keyword=None,
            date_from=None,
            date_to=None,
            db=db,
            current_user=current_user,
        )
        service.list_all.assert_awaited_once_with(
            1,
            20,
            None,
            None,
            keyword=None,
            exclude_status=["converted", "cancelled"],
        )

        service.list_all.reset_mock()
        await quotes.list_quotes(
            page=1,
            page_size=20,
            status="cancelled",
            customer_id=None,
            keyword=None,
            date_from=None,
            date_to=None,
            db=db,
            current_user=current_user,
        )
        service.list_all.assert_awaited_once_with(
            1,
            20,
            "cancelled",
            None,
            keyword=None,
            exclude_status=None,
        )
