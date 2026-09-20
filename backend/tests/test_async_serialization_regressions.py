"""Regression coverage for post-flush serialization and WebSocket auth."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.deps import authenticate_websocket_token, extract_websocket_token
from app.repositories.aerial_repo import AerialRepository
from app.repositories.attendance_repo import AttendanceRuleRepository
from app.repositories.department_repo import DepartmentRepository
from app.repositories.leave_repo import LeaveRequestRepository
from app.repositories.salary_repo import SalaryRecordRepository
from app.services.business_document_service import BusinessDocumentService
from app.services.leave_service import LeaveRequestService


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_business_document_update_reloads_row_before_serialization():
    db = MagicMock()
    db.flush = AsyncMock()
    repo = MagicMock()
    document = MagicMock()
    document.id = uuid4()
    document.doc_type = "order"
    document.status = "pending_confirm"
    document.customer_id = None
    repo.get_by_id = AsyncMock(side_effect=[document, document])
    repo.update = AsyncMock(return_value=document)

    service = BusinessDocumentService(db, doc_type="order")
    service.repo = repo
    service._sync_framework_contract_projects = AsyncMock()
    service._to_detail = MagicMock(return_value={"id": str(document.id)})

    result = await service.update(document.id, {"remark": "updated"})

    assert result == {"id": str(document.id)}
    assert repo.get_by_id.await_count == 2
    assert repo.get_by_id.await_args_list[-1].args == (document.id,)


@pytest.mark.asyncio
async def test_order_contact_update_reloads_row_before_serialization():
    db = MagicMock()
    db.flush = AsyncMock()
    repo = MagicMock()
    document = MagicMock()
    document.id = uuid4()
    document.doc_type = "order"
    document.status = "confirmed"
    document.customer_id = None
    repo.get_by_id = AsyncMock(side_effect=[document, document])

    service = BusinessDocumentService(db, doc_type="order")
    service.repo = repo
    service._sync_contact_to_customer = AsyncMock()
    service._to_detail = MagicMock(return_value={"id": str(document.id)})

    result = await service.update_order_contact(document.id, "张三", "13800000000")

    assert result == {"id": str(document.id)}
    assert repo.get_by_id.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("repository", "operation"),
    [
        (DepartmentRepository, "update"),
        (SalaryRecordRepository, "update"),
        (LeaveRequestRepository, "update"),
        (AttendanceRuleRepository, "update"),
        (AerialRepository, "soft_delete_vehicle"),
        (AerialRepository, "soft_delete_personnel"),
    ],
)
async def test_timestamp_sensitive_repository_operations_refresh_row(repository, operation):
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    repo = repository(db)
    row = MagicMock()

    if operation == "update":
        await repo.update(row, {"remark": "changed"})
    else:
        await getattr(repo, operation)(row)

    db.refresh.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_leave_approval_refreshes_row_before_serialization():
    db = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    repo = MagicMock()
    request = MagicMock()
    request.id = uuid4()
    request.status = "pending"
    repo.get_by_id = AsyncMock(return_value=request)

    service = LeaveRequestService(db)
    service.repo = repo
    service._d = MagicMock(return_value={"id": str(request.id)})

    result = await service.approve_request(request.id, "approved", uuid4())

    assert result == {"id": str(request.id)}
    db.refresh.assert_awaited_once_with(request)


def test_websocket_token_prefers_auth_subprotocol_over_query_string():
    websocket = MagicMock()
    websocket.headers = {"sec-websocket-protocol": "adcraft-auth, eyJhbGciOiJIUzI1NiJ9.test"}
    websocket.query_params = {"token": "legacy-token"}

    token, subprotocol = extract_websocket_token(websocket)

    assert token == "eyJhbGciOiJIUzI1NiJ9.test"
    assert subprotocol == "adcraft-auth"


@pytest.mark.asyncio
async def test_websocket_auth_checks_current_user_and_employee_state():
    user = MagicMock()
    user.id = uuid4()
    user.is_active = True
    user.deleted_at = None
    user.token_version = 3
    user.must_change_password = False
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(user), _scalar_result(None)])

    with patch(
        "app.core.deps.decode_access_token",
        return_value={"sub": str(user.id), "token_version": 3},
    ):
        authenticated = await authenticate_websocket_token(db, "signed-token")

    assert authenticated is user
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_websocket_auth_rejects_disabled_user():
    user = MagicMock()
    user.id = uuid4()
    user.is_active = False
    user.deleted_at = None
    user.token_version = 1
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(user))

    with patch(
        "app.core.deps.decode_access_token",
        return_value={"sub": str(user.id), "token_version": 1},
    ):
        authenticated = await authenticate_websocket_token(db, "signed-token")

    assert authenticated is None
    assert db.execute.await_count == 1
