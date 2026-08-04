"""Tests for FrameworkContractService.create_project 合同类型校验。

覆盖 _validate_contract_is_framework：
- 仅框架合同允许添加项目，制作合同等普通合同被拒
- 合同不存在 / 已软删 被拒
- 框架合同正常创建（复用 repo 与 _sync_contract_total）
"""

from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


CONTRACT_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CUSTOMER_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def make_contract(contract_type="框架合同"):
    c = MagicMock()
    c.id = CONTRACT_UUID
    c.contract_type = contract_type
    c.deleted_at = None
    return c


def make_project():
    p = MagicMock()
    p.id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    p.contract_id = CONTRACT_UUID
    p.customer_id = CUSTOMER_UUID
    p.customer_name = "测试客户"
    p.department = None
    p.project_name = "测试项目"
    p.project_amount = 100.0
    p.remark = None
    p.attachment_path = None
    p.attachment_name = None
    p.created_at = None
    return p


@pytest.fixture
def fw_service():
    from app.services.framework_contract_service import FrameworkContractService

    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.get = AsyncMock()
    with patch(
        "app.services.framework_contract_service.FrameworkContractProjectRepository"
    ) as repo_class:
        yield FrameworkContractService(db), db, repo_class.return_value


@pytest.mark.asyncio
async def test_create_project_rejects_non_framework_contract(fw_service):
    service, db, repo = fw_service
    db.get = AsyncMock(return_value=make_contract(contract_type="制作合同"))

    with pytest.raises(ValueError, match="仅框架合同支持添加项目"):
        await service.create_project(
            {"contract_id": str(CONTRACT_UUID), "customer_id": str(CUSTOMER_UUID)}
        )
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_project_rejects_missing_contract(fw_service):
    service, db, repo = fw_service
    db.get = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="合同不存在"):
        await service.create_project(
            {"contract_id": str(CONTRACT_UUID), "customer_id": str(CUSTOMER_UUID)}
        )
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_project_rejects_soft_deleted_contract(fw_service):
    service, db, repo = fw_service
    contract = make_contract()
    contract.deleted_at = object()  # 软删合同不可再挂项目
    db.get = AsyncMock(return_value=contract)

    with pytest.raises(ValueError, match="合同不存在"):
        await service.create_project(
            {"contract_id": str(CONTRACT_UUID), "customer_id": str(CUSTOMER_UUID)}
        )
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_project_accepts_framework_contract(fw_service):
    service, db, repo = fw_service
    db.get = AsyncMock(return_value=make_contract(contract_type="框架合同"))
    project = make_project()
    repo.create = AsyncMock(return_value=project)
    repo.get_by_id = AsyncMock(return_value=project)
    service._sync_contract_total = AsyncMock()

    result = await service.create_project(
        {"contract_id": str(CONTRACT_UUID), "customer_id": str(CUSTOMER_UUID)}
    )

    repo.create.assert_awaited_once()
    service._sync_contract_total.assert_awaited_once_with(CONTRACT_UUID)
    assert result["project_name"] == "测试项目"
    assert result["unpaid_amount"] == 100.0
