from app.api import quotes
from app.core.permissions import PERM_QUOTE_DELETE


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
