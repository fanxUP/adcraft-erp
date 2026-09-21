"""订单与财务路由的细粒度权限契约。"""

from io import BytesIO
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import UploadFile
import pytest

from app.api import orders, payments, payables
from app.api.payments import _validate_expense_attachment
from app.schemas.payment import ExpenseDeleteConfirmed


def _route_permission(router, method: str, path: str) -> str | None:
    route = next(
        route
        for route in router.routes
        if method in route.methods and route.path == path
    )
    for dependency in route.dependant.dependencies:
        call = dependency.call
        closure = getattr(call, "__closure__", None)
        if getattr(call, "__name__", None) == "dependency" and closure:
            return closure[0].cell_contents
    return None


def _route_permission_tuple(router, method: str, path: str) -> tuple[str, ...]:
    route = next(
        route
        for route in router.routes
        if method in route.methods and route.path == path
    )
    for dependency in route.dependant.dependencies:
        call = dependency.call
        closure = getattr(call, "__closure__", None)
        if getattr(call, "__name__", None) != "dependency" or not closure:
            continue
        for cell in closure:
            value = cell.cell_contents
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    return ()


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/orders/", "order:read"),
        ("GET", "/orders/{order_id}", "order:read"),
        ("GET", "/orders/{order_id}/task-attachments", "order:read"),
        ("POST", "/orders/{order_id}/task-attachments", "order:read"),
        ("GET", "/orders/{order_id}/task-attachments/{attachment_id}/file", "order:read"),
        ("DELETE", "/orders/{order_id}/task-attachments/{attachment_id}", "order:read"),
        ("GET", "/orders/{order_id}/items/editability", "order:read"),
        ("GET", "/orders/{order_id}/items/change-batches", "order:read"),
        ("GET", "/orders/{order_id}/items/change-batches/{change_batch_id}", "order:read"),
        ("GET", "/orders/{order_id}/items/reconciliation", "order:read"),
        ("POST", "/orders/{order_id}/items/preview", "order:update"),
        ("POST", "/orders/{order_id}/items", "order:update"),
        ("PATCH", "/orders/{order_id}/items/{item_id}", "order:update"),
        ("DELETE", "/orders/{order_id}/items/{item_id}", "order:update"),
        ("POST", "/orders/{order_id}/set-cost", "order:update"),
        ("POST", "/orders/{order_id}/auto-cost", "order:update"),
        ("DELETE", "/orders/{order_id}", "order:delete"),
        ("POST", "/orders/{order_id}/restore", "order:delete"),
    ],
)
def test_order_routes_require_business_permissions(method, path, permission):
    assert _route_permission(orders.router, method, path) == permission


@pytest.mark.parametrize(
    ("method", "path", "permissions"),
    [
        (
            "GET",
            "/orders/{order_id}/attachments",
            (
                "order:read",
                "design_task:read",
                "production_task:read",
                "installation_task:read",
                "task_completion:read",
            ),
        ),
        (
            "POST",
            "/orders/{order_id}/attachments",
            (
                "order:read",
                "design_task:update",
                "production_task:update",
                "installation_task:update",
            ),
        ),
        (
            "GET",
            "/orders/{order_id}/attachments/{attachment_id}/file",
            (
                "order:read",
                "design_task:read",
                "production_task:read",
                "installation_task:read",
                "task_completion:read",
            ),
        ),
        (
            "DELETE",
            "/orders/{order_id}/attachments/{attachment_id}",
            (
                "order:read",
                "design_task:update",
                "production_task:update",
                "installation_task:update",
            ),
        ),
    ],
)
def test_canonical_order_material_routes_have_stage_aware_permissions(method, path, permissions):
    assert _route_permission_tuple(orders.router, method, path) == permissions


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/expenses/", "expense:read"),
        ("GET", "/expenses/{expense_id}", "expense:read"),
        ("GET", "/expenses/{expense_id}/attachments", "expense:read"),
        ("GET", "/expenses/{expense_id}/attachments/{attachment_id}/file", "expense:read"),
        ("POST", "/expenses/", "expense:create"),
        ("POST", "/expenses/{expense_id}/attachments", "expense:update"),
        ("PUT", "/expenses/{expense_id}", "expense:update"),
        ("DELETE", "/expenses/{expense_id}/attachments/{attachment_id}", "expense:delete"),
        ("DELETE", "/expenses/{expense_id}", "expense:delete"),
    ],
)
def test_expense_routes_require_business_permissions(method, path, permission):
    assert _route_permission(payments.exp_router, method, path) == permission


def test_confirmed_expense_delete_requires_delete_and_update_permissions():
    assert _route_permission_tuple(
        payments.exp_router,
        "POST",
        "/expenses/{expense_id}/delete-confirmed",
    ) == ("expense:delete", "expense:update")


@pytest.mark.asyncio
async def test_delete_expense_returns_business_error_instead_of_server_error():
    current_user = SimpleNamespace(id=uuid4(), real_name="系统管理员", username="admin")
    request = SimpleNamespace(client=None)
    db = MagicMock()

    with patch.object(payments, "ExpenseService") as service_class:
        service_class.return_value.delete_expense = AsyncMock(
            side_effect=ValueError("已有付款记录，不能删除该支出；请先撤销付款流水")
        )

        result = await payments.delete_expense(
            str(uuid4()),
            request=request,
            db=db,
            current_user=current_user,
        )

    assert result == {
        "code": 40001,
        "message": "已有付款记录，不能删除该支出；请先撤销付款流水",
        "data": None,
    }
    service_class.return_value.delete_expense.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmed_expense_delete_returns_cleanup_summary():
    current_user = SimpleNamespace(id=uuid4(), real_name="系统管理员", username="admin")
    request = SimpleNamespace(client=None)
    db = MagicMock()
    data = ExpenseDeleteConfirmed(
        expected_payment_count=1,
        expected_paid_amount=1000,
    )

    with patch.object(payments, "ExpenseService") as service_class:
        service_class.return_value.delete_expense_with_payments = AsyncMock(
            return_value={
                "deleted": True,
                "payment_ids": [str(uuid4())],
                "payment_count": 1,
                "paid_amount": 1000.0,
            }
        )
        with patch.object(payments, "log_operation", new_callable=AsyncMock):
            result = await payments.delete_expense_confirmed(
                str(uuid4()),
                data=data,
                request=request,
                db=db,
                current_user=current_user,
            )

    assert result["code"] == 0
    assert result["data"]["deleted"] is True
    assert result["data"]["payment_count"] == 1
    service_class.return_value.delete_expense_with_payments.assert_awaited_once()


@pytest.mark.parametrize(
    ("filename", "content_type", "contents", "expected"),
    [
        ("voucher.jpg", "image/jpeg", b"\xff\xd8\xff\xe0", (".jpg", "image/jpeg")),
        ("voucher.png", "image/png", b"\x89PNG\r\n\x1a\n", (".png", "image/png")),
        ("voucher.webp", "image/webp", b"RIFF\x00\x00\x00\x00WEBP", (".webp", "image/webp")),
        ("voucher.pdf", "application/pdf", b"%PDF-1.7", (".pdf", "application/pdf")),
        ("voucher.exe", "application/octet-stream", b"MZ", None),
        ("voucher.jpg", "image/png", b"\xff\xd8\xff\xe0", None),
        ("voucher.pdf", "application/pdf", b"not-a-pdf", None),
    ],
)
def test_expense_voucher_file_policy(filename, content_type, contents, expected):
    assert _validate_expense_attachment(filename, content_type, contents) == expected


@pytest.mark.asyncio
async def test_project_cost_voucher_upload_validates_and_stores_safe_file(tmp_path, monkeypatch):
    """项目成本凭证应校验文件签名，并以受限权限写入应用上传目录。"""
    monkeypatch.setattr(payments.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    cost_id = uuid4()
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(deleted_at=None))
    current_user = SimpleNamespace(id=uuid4())
    attachment = {"id": str(uuid4()), "filename": "凭证.png"}

    with patch.object(payments, "AttachmentService") as service_class:
        service_class.return_value.add_attachment = AsyncMock(return_value=attachment)
        result = await payments.upload_project_cost_attachment(
            cost_id=str(cost_id),
            file=UploadFile(
                filename="../../凭证.png",
                file=BytesIO(b"\x89PNG\r\n\x1a\nvalid-png"),
                headers={"content-type": "image/png"},
            ),
            db=db,
            current_user=current_user,
        )

    assert result["code"] == 0
    payload = service_class.return_value.add_attachment.await_args.kwargs
    assert payload["related_id"] == cost_id
    assert payload["data"]["filename"] == "凭证.png"
    assert payload["data"]["file_type"] == "image/png"
    stored_files = list(tmp_path.rglob("*.png"))
    assert len(stored_files) == 1
    assert stored_files[0].stat().st_mode & 0o777 == 0o640
    assert stored_files[0].parent.stat().st_mode & 0o777 == 0o750


@pytest.mark.asyncio
async def test_project_cost_voucher_upload_rejects_invalid_file_before_persisting(tmp_path, monkeypatch):
    monkeypatch.setattr(payments.settings, "LOCAL_UPLOAD_DIR", str(tmp_path))
    db = MagicMock()
    db.get = AsyncMock(return_value=SimpleNamespace(deleted_at=None))

    with patch.object(payments, "AttachmentService") as service_class:
        service_class.return_value.add_attachment = AsyncMock()
        result = await payments.upload_project_cost_attachment(
            cost_id=str(uuid4()),
            file=UploadFile(
                filename="凭证.exe",
                file=BytesIO(b"MZ-not-a-voucher"),
                headers={"content-type": "application/octet-stream"},
            ),
            db=db,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert result["code"] == 40001
    service_class.return_value.add_attachment.assert_not_awaited()
    assert not list(tmp_path.rglob("*"))


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/project-costs/", "expense:read"),
        ("GET", "/project-costs/summary", "expense:read"),
        ("GET", "/project-costs/orders/{order_id}/item-summary", "expense:read"),
        ("GET", "/project-costs/template", "expense:read"),
        ("GET", "/project-costs/quotes", "expense:read"),
        ("GET", "/project-costs/debts/list", "expense:read"),
        ("GET", "/project-costs/{cost_id}", "expense:read"),
        ("GET", "/project-costs/{cost_id}/attachments", "expense:read"),
        ("POST", "/project-costs/", "expense:create"),
        ("POST", "/project-costs/import", "expense:create"),
        ("PUT", "/project-costs/{cost_id}", "expense:update"),
        ("POST", "/project-costs/{cost_id}/settle-debt", "expense:update"),
        ("POST", "/project-costs/{cost_id}/upload", "expense:update"),
        ("DELETE", "/project-costs/batch", "expense:delete"),
        ("DELETE", "/project-costs/{cost_id}", "expense:delete"),
        ("DELETE", "/project-costs/attachments/{attachment_id}", "expense:delete"),
    ],
)
def test_project_cost_routes_require_expense_permissions(method, path, permission):
    assert _route_permission(payments.cost_router, method, path) == permission


def test_project_cost_mutations_keep_operation_log_contract():
    handlers = (
        payments.create_project_cost,
        payments.update_project_cost,
        payments.batch_delete_project_costs,
        payments.delete_project_cost,
        payments.import_project_costs,
        payments.settle_cost_debt,
    )

    for handler in handlers:
        source = inspect.getsource(handler)
        assert "log_operation" in source
        assert "OBJ_PROJECT_COST" in source


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [
        ("GET", "/payables/", "expense:read"),
        ("GET", "/payables/{source_type}/{source_id}", "expense:read"),
        ("POST", "/payables/{source_type}/{source_id}/payments", "expense:update"),
        (
            "POST",
            "/payables/{source_type}/{source_id}/payments/{payment_id}/void",
            "expense:update",
        ),
    ],
)
def test_payable_routes_require_expense_permissions(method, path, permission):
    assert _route_permission(payables.router, method, path) == permission
