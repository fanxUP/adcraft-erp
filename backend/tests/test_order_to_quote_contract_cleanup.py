"""订单转报价时的合同关联清理单元测试。

覆盖 business_document_service._cleanup_contract_links_on_order_to_quote：
- 普通合同：移除订单与合同的关联；合同不再关联任何单据时整份软删除
- 框架合同：从框架合同项目移除订单；项目不再关联任何单据时软删项目并同步合同金额
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.business_document_service import BusinessDocumentService

ORDER_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CONTRACT_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
FW_CONTRACT_UUID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
PROJECT_UUID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def mock_result(rows):
    """模拟 SQLAlchemy Result：r.scalars().all() 返回 rows。"""
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows
    return r


@pytest.fixture
def service():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    with patch(
        "app.services.business_document_service.BusinessDocumentRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.get_next_version_no = AsyncMock(return_value=1)
        repository.create_version = AsyncMock()
        repository.create_status_log = AsyncMock()
        yield BusinessDocumentService(db, doc_type="order"), db


def make_doc():
    doc = MagicMock()
    doc.id = ORDER_UUID
    return doc


def make_link(**attrs):
    link = MagicMock()
    for k, v in attrs.items():
        setattr(link, k, v)
    return link


def make_contract():
    c = MagicMock()
    c.id = CONTRACT_UUID
    c.deleted_at = None
    return c


def make_project():
    p = MagicMock()
    p.id = PROJECT_UUID
    p.contract_id = FW_CONTRACT_UUID
    p.deleted_at = None
    return p


# ── 普通合同 ──


@pytest.mark.asyncio
async def test_regular_contract_empty_is_soft_deleted(service):
    service, db = service
    link = make_link(contract_id=CONTRACT_UUID)
    contract = make_contract()
    db.execute.side_effect = [
        mock_result([link]),   # ContractDocument 按 document_id 查询
        mock_result([]),       # 该合同剩余关联单据（空）
        mock_result([]),       # FrameworkContractProjectDocument 查询（空）
    ]
    db.get.side_effect = [contract]

    await service._cleanup_contract_links_on_order_to_quote(make_doc())

    db.delete.assert_awaited_once_with(link)
    assert contract.deleted_at is not None  # 空合同被软删除


@pytest.mark.asyncio
async def test_regular_contract_with_other_docs_is_kept(service):
    service, db = service
    link = make_link(contract_id=CONTRACT_UUID)
    contract = make_contract()
    db.execute.side_effect = [
        mock_result([link]),   # ContractDocument 按 document_id 查询
        mock_result([make_link(contract_id=CONTRACT_UUID)]),  # 合同下还有其他单据
        mock_result([]),
    ]
    db.get.side_effect = [contract]

    await service._cleanup_contract_links_on_order_to_quote(make_doc())

    db.delete.assert_awaited_once_with(link)
    assert contract.deleted_at is None  # 合同保留


# ── 框架合同 ──


@pytest.mark.asyncio
async def test_framework_project_empty_is_deleted_and_total_synced(service):
    service, db = service
    fw_link = make_link(project_id=PROJECT_UUID)
    project = make_project()
    db.execute.side_effect = [
        mock_result([]),           # ContractDocument 空
        mock_result([fw_link]),    # FrameworkContractProjectDocument 按 document_id 查询
        mock_result([]),           # 该项目剩余关联单据（空）
    ]
    db.get.side_effect = [project]

    with patch(
        "app.services.framework_contract_service.FrameworkContractService.delete_project",
        new=AsyncMock(return_value=True),
    ) as mock_delete_project:
        await service._cleanup_contract_links_on_order_to_quote(make_doc())

    db.delete.assert_awaited_once_with(fw_link)
    mock_delete_project.assert_awaited_once_with(PROJECT_UUID)  # 空项目软删并同步合同金额


@pytest.mark.asyncio
async def test_framework_project_with_other_orders_is_kept(service):
    service, db = service
    fw_link = make_link(project_id=PROJECT_UUID)
    project = make_project()
    db.execute.side_effect = [
        mock_result([]),           # ContractDocument 空
        mock_result([fw_link]),    # FrameworkContractProjectDocument 按 document_id 查询
        mock_result([make_link(project_id=PROJECT_UUID)]),  # 项目下还有其他订单
    ]
    db.get.side_effect = [project]

    with patch(
        "app.services.framework_contract_service.FrameworkContractService.delete_project",
        new=AsyncMock(return_value=True),
    ) as mock_delete_project:
        await service._cleanup_contract_links_on_order_to_quote(make_doc())

    db.delete.assert_awaited_once_with(fw_link)
    mock_delete_project.assert_not_awaited()  # 项目保留


# ── 无关联 / 全链路 ──


@pytest.mark.asyncio
async def test_no_contract_links_is_noop(service):
    service, db = service
    db.execute.side_effect = [
        mock_result([]),  # ContractDocument 空
        mock_result([]),  # FrameworkContractProjectDocument 空
    ]

    await service._cleanup_contract_links_on_order_to_quote(make_doc())

    db.delete.assert_not_awaited()
    db.get.assert_not_awaited()


def make_order_doc():
    """构造一条已取消订单（含全部 _to_detail 需要的字段，order+quote 字段齐全）。"""
    now = datetime.now(timezone.utc)
    doc = MagicMock()
    defaults = {
        "id": ORDER_UUID,
        "doc_type": "order",
        "doc_no": "O20260803-0001",
        "customer_id": None,
        "customer_name": None,
        "customer": None,
        "project_name": "测试订单",
        "sales_user_id": None,
        "status": "cancelled",
        "total_amount": Decimal("1000"),
        "remark": None,
        "department": None,
        "contact_person": None,
        "contact_phone": None,
        "created_at": now,
        "items": [],
        "status_logs": [],
        "source_quote_id": None,
        "paid_amount": Decimal("0"),
        "unpaid_amount": Decimal("0"),
        "cost_amount": Decimal("0"),
        "gross_profit": Decimal("0"),
        "delivery_deadline": None,
        "installation_address": None,
        "design_tasks": [],
        "production_tasks": [],
        "installation_tasks": [],
        # quote 字段（转换后 _to_detail 会走 quote 分支）
        "quote_mode": "regular",
        "subtotal_amount": Decimal("1000"),
        "discount_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "valid_until": None,
    }
    for key, value in defaults.items():
        setattr(doc, key, value)
    return doc


@pytest.mark.asyncio
async def test_convert_order_to_quote_works_without_contract_links(service):
    service, db = service
    doc = make_order_doc()
    first = MagicMock()
    first.scalar_one_or_none.return_value = doc
    db.execute.side_effect = [
        first,           # 查询单据
        mock_result([]),  # ContractDocument 空
        mock_result([]),  # FrameworkContractProjectDocument 空
    ]

    with patch(
        "app.services.number_generator.generate_quote_no",
        AsyncMock(return_value="Q20260804-9999"),
    ):
        result = await service.convert_doc_type(ORDER_UUID, "quote", uuid4())

    assert result["doc_type"] == "quote"
    assert result["quote_no"] == "Q20260804-9999"
    assert result["status"] == "draft"
    db.delete.assert_not_awaited()  # 无合同关联，不做任何清理
