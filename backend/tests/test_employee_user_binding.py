"""Regression tests for the employee <-> login-user binding contract."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.services.employee_service import EmployeeService
from app.services.user_service import UserService


EMPLOYEE_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
OTHER_EMPLOYEE_ID = UUID("33333333-3333-3333-3333-333333333333")


class Result:
    def __init__(self, *, scalar=None, rows=None):
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows


def make_employee(**kwargs):
    employee = MagicMock()
    employee.id = kwargs.get("id", EMPLOYEE_ID)
    employee.employee_no = kwargs.get("employee_no", "001")
    employee.name = kwargs.get("name", "测试员工")
    employee.phone = None
    employee.gender = None
    employee.ethnicity = None
    employee.birth_date = None
    employee.department = "production"
    employee.position = "技术员"
    employee.employment_type = "full_time"
    employee.hire_date = None
    employee.resignation_date = None
    employee.employment_status = kwargs.get("employment_status", "active")
    employee.id_card = None
    employee.education = None
    employee.license_no = None
    employee.license_type = None
    employee.license_expire_date = None
    employee.id_card_front_url = None
    employee.id_card_back_url = None
    employee.emergency_contact = None
    employee.emergency_phone = None
    employee.skills = []
    employee.bank_name = None
    employee.bank_account = None
    employee.address = None
    employee.user_id = kwargs.get("user_id")
    employee.remark = None
    employee.is_active = kwargs.get("is_active", True)
    employee.created_at = datetime.now(timezone.utc)
    return employee


def make_user(**kwargs):
    user = MagicMock()
    user.id = kwargs.get("id", USER_ID)
    user.username = kwargs.get("username", "testuser")
    user.real_name = kwargs.get("real_name", "测试用户")
    user.is_active = kwargs.get("is_active", True)
    user.deleted_at = None
    user.roles = []
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def employee_service():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    with patch("app.services.employee_service.EmployeeRepository", return_value=repo):
        service = EmployeeService(db)
        service.repo = repo
        yield service, repo, db


@pytest.mark.asyncio
async def test_account_options_only_return_available_active_users(employee_service):
    service, _, db = employee_service
    available = make_user()
    db.execute.return_value = Result(rows=[available])

    options = await service.list_account_options()

    assert options == [{"id": str(USER_ID), "username": "testuser", "real_name": "测试用户"}]


@pytest.mark.asyncio
async def test_bind_user_rejects_an_account_bound_to_another_employee(employee_service):
    service, repo, db = employee_service
    employee = make_employee()
    other_employee = make_employee(id=OTHER_EMPLOYEE_ID, employee_no="002", name="另一员工")
    repo.get_by_id.return_value = employee
    db.execute.side_effect = [Result(scalar=make_user()), Result(scalar=other_employee)]

    with pytest.raises(ValueError, match="已绑定员工"):
        await service.bind_user(EMPLOYEE_ID, USER_ID)

    assert employee.user_id is None
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_bind_user_rejects_malformed_account_id_with_plain_language_error(employee_service):
    service, repo, db = employee_service
    repo.get_by_id.return_value = make_employee()

    with pytest.raises(ValueError, match="登录账号编号格式不正确"):
        await service.bind_user(EMPLOYEE_ID, "not-a-uuid")

    db.execute.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_unbind_user_clears_only_the_binding(employee_service):
    service, repo, db = employee_service
    employee = make_employee(user_id=USER_ID)
    repo.get_by_id.return_value = employee

    result = await service.bind_user(EMPLOYEE_ID, None)

    assert employee.user_id is None
    assert result["user_id"] is None
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_list_includes_the_linked_employee(employee_service):
    del employee_service
    repo = MagicMock()
    user = make_user()
    repo.list_users = AsyncMock(return_value=([user], 1))
    db = MagicMock()
    db.execute = AsyncMock(return_value=Result(rows=[make_employee(user_id=USER_ID)]))
    service = UserService(db)
    service.repo = repo

    items, total = await service.list_users(page=1, page_size=20)

    assert total == 1
    assert items[0]["linked_employee"] == {
        "id": str(EMPLOYEE_ID),
        "employee_no": "001",
        "name": "测试员工",
        "department": "production",
    }
