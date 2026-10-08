from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.outsource_service import OutsourceService


@pytest.mark.asyncio
@pytest.mark.parametrize("active,roles,services,message", [
    (False, ["material", "outsource"], ["production"], "停用"),
    (True, ["material"], [], "外协"),
    (True, ["outsource"], ["installation"], "制作"),
])
async def test_new_task_rejects_ineligible_vendor(active, roles, services, message):
    svc = OutsourceService(AsyncMock())
    svc.vendor_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(
        is_active=active, supplier_types=roles, service_types=services,
    ))
    with pytest.raises(ValueError, match=message):
        await svc._validate_task_vendor(uuid4(), "production")


@pytest.mark.asyncio
async def test_multi_role_vendor_is_eligible_for_each_declared_service():
    svc = OutsourceService(AsyncMock())
    svc.vendor_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(
        is_active=True, supplier_types=["material", "outsource"],
        service_types=["production", "installation"],
    ))
    await svc._validate_task_vendor(uuid4(), "production")
    await svc._validate_task_vendor(uuid4(), "installation")
