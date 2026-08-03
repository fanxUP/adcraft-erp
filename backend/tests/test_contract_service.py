"""Tests for ContractService: 未建立合同订单列表 + 创建合同关联订单。"""

from datetime import datetime, timezone
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


SAMPLE_ORDER_UUID = UUID("33333333-3333-3333-3333-333333333333")
SAMPLE_CUSTOMER_UUID = UUID("44444444-4444-4444-4444-444444444444")


def make_mock_order(**kwargs):
    """模拟一条 order 类型的 business_document。"""
    doc = MagicMock()
    doc.id = kwargs.get("id", SAMPLE_ORDER_UUID)
    doc.doc_type = "order"
    doc.doc_no = kwargs.get("doc_no", "O20260804-0001")
    doc.project_name = kwargs.get("project_name", "测试项目")
    doc.customer_name = kwargs.get("customer_name", "测试客户")
    doc.customer = None
    doc.department = kwargs.get("department", "工程部")
    doc.status = kwargs.get("status", "completed")
    doc.total_amount = kwargs.get("total_amount", 100.0)
    doc.paid_amount = kwargs.get("paid_amount", 0.0)
    doc.unpaid_amount = kwargs.get("unpaid_amount", 100.0)
    doc.customer_id = kwargs.get("customer_id", SAMPLE_CUSTOMER_UUID)
    doc.created_at = kwargs.get("created_at", datetime(2026, 8, 4, tzinfo=timezone.utc))
    return doc


@pytest.fixture
def contract_service():
    """ContractService with a mocked repo (patch the repo class)."""
    from app.services.contract_service import ContractService

    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    with patch("app.services.contract_service.ContractRepository") as repo_class:
        repo = repo_class.return_value
        yield ContractService(db), repo


@pytest.mark.asyncio
async def test_list_orders_without_contract(contract_service):
    service, repo = contract_service
    orders = [make_mock_order(), make_mock_order(doc_no="O20260804-0002", total_amount=200.0)]
    repo.list_orders_without_contract = AsyncMock(return_value=(orders, 2))

    items, total = await service.list_orders_without_contract(page=1, page_size=20, keyword="测试")

    repo.list_orders_without_contract.assert_awaited_once_with(
        skip=0, limit=20, keyword="测试"
    )
    assert total == 2
    assert len(items) == 2
    first = items[0]
    # _to_ref 输出
    assert first["order_no"] == "O20260804-0001"
    assert first["doc_no"] == "O20260804-0001"
    assert first["project_name"] == "测试项目"
    assert first["customer_name"] == "测试客户"
    assert first["department"] == "工程部"
    assert first["status"] == "completed"
    assert first["total_amount"] == 100.0
    # 追加字段
    assert first["customer_id"] == str(SAMPLE_CUSTOMER_UUID)
    assert first["created_at"] == "2026-08-04T00:00:00+00:00"


@pytest.mark.asyncio
async def test_list_orders_without_contract_defaults(contract_service):
    service, repo = contract_service
    repo.list_orders_without_contract = AsyncMock(return_value=([], 0))

    items, total = await service.list_orders_without_contract(page=2, page_size=10)

    repo.list_orders_without_contract.assert_awaited_once_with(
        skip=10, limit=10, keyword=None
    )
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_create_contract_links_order_ids(contract_service):
    service, repo = contract_service
    created = MagicMock()
    created.id = SAMPLE_ORDER_UUID
    repo.create = AsyncMock(return_value=created)
    repo.get_by_id = AsyncMock(return_value=created)
    # 隔离无关逻辑：只验证 order_ids → document_ids 的转换
    service._to_detail = MagicMock(return_value={"id": str(SAMPLE_ORDER_UUID), "total_amount": 100.0})
    service._auto_complete_if_paid = AsyncMock()
    service._calc_paid_amount = AsyncMock(return_value=0.0)

    with patch(
        "app.services.contract_service.generate_contract_no",
        new=AsyncMock(return_value="HT20260804-0001"),
    ):
        await service.create_contract(
            {
                "customer_id": str(SAMPLE_CUSTOMER_UUID),
                "customer_name": "测试客户",
                "project_name": "测试项目",
                "total_amount": 100.0,
                "order_ids": [str(SAMPLE_ORDER_UUID)],
            }
        )

    create_call = repo.create.await_args
    assert create_call is not None
    data = create_call.args[0]
    # order_ids 已转换为 document_ids，且多余键已被弹出
    assert data["document_ids"] == [SAMPLE_ORDER_UUID]
    assert "order_ids" not in data


@pytest.mark.asyncio
async def test_create_contract_without_order_ids(contract_service):
    service, repo = contract_service
    created = MagicMock()
    created.id = SAMPLE_ORDER_UUID
    repo.create = AsyncMock(return_value=created)
    repo.get_by_id = AsyncMock(return_value=created)
    service._to_detail = MagicMock(return_value={"id": str(SAMPLE_ORDER_UUID), "total_amount": 100.0})
    service._auto_complete_if_paid = AsyncMock()
    service._calc_paid_amount = AsyncMock(return_value=0.0)

    with patch(
        "app.services.contract_service.generate_contract_no",
        new=AsyncMock(return_value="HT20260804-0002"),
    ):
        await service.create_contract(
            {
                "customer_id": str(SAMPLE_CUSTOMER_UUID),
                "customer_name": "测试客户",
                "project_name": "测试项目",
                "total_amount": 100.0,
            }
        )

    create_call = repo.create.await_args
    assert create_call is not None
    data = create_call.args[0]
    # 无 order_ids 时不设置 document_ids，repo.create 内部默认空列表；无残留键
    assert "order_ids" not in data
    assert "document_ids" not in data


# ── link_orders_to_contract：把订单追加关联到已有合同 ────────────────────────

def make_mock_contract(**kwargs):
    """模拟一条 contract。"""
    c = MagicMock()
    c.id = kwargs.get("id", UUID("22222222-2222-2222-2222-222222222222"))
    c.contract_type = kwargs.get("contract_type", "制作合同")
    c.status = kwargs.get("status", "draft")
    c.total_amount = kwargs.get("total_amount", 100.0)
    return c


@pytest.mark.asyncio
async def test_link_orders_to_contract(contract_service):
    service, repo = contract_service
    contract = make_mock_contract()
    repo.get_by_id = AsyncMock(return_value=contract)
    repo.link_orders = AsyncMock(return_value=contract)
    service._load_linkable_orders = AsyncMock(return_value=[SAMPLE_ORDER_UUID])
    service._auto_complete_if_paid = AsyncMock()
    service._to_detail = MagicMock(return_value={"id": str(contract.id), "total_amount": 100.0})
    service._calc_paid_amount = AsyncMock(return_value=50.0)

    result = await service.link_orders_to_contract(contract.id, [str(SAMPLE_ORDER_UUID)])

    service._load_linkable_orders.assert_awaited_once_with([SAMPLE_ORDER_UUID], contract.id)
    repo.link_orders.assert_awaited_once_with(contract, [SAMPLE_ORDER_UUID])
    assert result["total_amount"] == 100.0


@pytest.mark.asyncio
async def test_link_orders_to_contract_no_linkable(contract_service):
    """全部订单已关联目标合同时，不调用 repo.link_orders，幂等返回。"""
    service, repo = contract_service
    contract = make_mock_contract()
    repo.get_by_id = AsyncMock(return_value=contract)
    repo.link_orders = AsyncMock(return_value=contract)
    service._load_linkable_orders = AsyncMock(return_value=[])
    service._auto_complete_if_paid = AsyncMock()
    service._to_detail = MagicMock(return_value={"id": str(contract.id), "total_amount": 100.0})
    service._calc_paid_amount = AsyncMock(return_value=0.0)

    result = await service.link_orders_to_contract(contract.id, [str(SAMPLE_ORDER_UUID)])

    repo.link_orders.assert_not_awaited()
    assert result["total_amount"] == 100.0


@pytest.mark.asyncio
async def test_link_orders_framework_rejected(contract_service):
    service, repo = contract_service
    contract = make_mock_contract(contract_type="框架合同")
    repo.get_by_id = AsyncMock(return_value=contract)
    repo.link_orders = AsyncMock(return_value=contract)

    with pytest.raises(ValueError):
        await service.link_orders_to_contract(contract.id, [str(SAMPLE_ORDER_UUID)])

    repo.link_orders.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_orders_contract_missing(contract_service):
    service, repo = contract_service
    repo.get_by_id = AsyncMock(return_value=None)
    repo.link_orders = AsyncMock()

    with pytest.raises(ValueError):
        await service.link_orders_to_contract(SAMPLE_ORDER_UUID, [str(SAMPLE_ORDER_UUID)])

    repo.link_orders.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_linkable_orders(contract_service):
    service, repo = contract_service
    order = make_mock_order()

    def make_result(rows):
        r = MagicMock()
        r.scalars.return_value.all.return_value = rows
        return r

    # 查询顺序：订单 → 其他合同已关联 → 框架项目已关联 → 目标合同已关联
    orders_result = make_result([order])
    other_result = make_result([])
    fw_result = make_result([])
    target_result = make_result([UUID("11111111-1111-1111-1111-111111111111")])  # 目标已关联另一条
    service.db.execute = AsyncMock(
        side_effect=[orders_result, other_result, fw_result, target_result]
    )

    linkable = await service._load_linkable_orders([SAMPLE_ORDER_UUID], UUID("22222222-2222-2222-2222-222222222222"))

    # SAMPLE_ORDER_UUID 未被目标关联 → 返回；另一条已被关联 → 排除
    assert linkable == [SAMPLE_ORDER_UUID]


@pytest.mark.asyncio
async def test_load_linkable_orders_linked_elsewhere(contract_service):
    """订单已关联其他合同时抛错。"""
    service, repo = contract_service
    order = make_mock_order()

    def make_result(rows):
        r = MagicMock()
        r.scalars.return_value.all.return_value = rows
        return r

    orders_result = make_result([order])
    other_result = make_result([SAMPLE_ORDER_UUID])
    service.db.execute = AsyncMock(
        side_effect=[orders_result, other_result]
    )

    with pytest.raises(ValueError):
        await service._load_linkable_orders([SAMPLE_ORDER_UUID], UUID("22222222-2222-2222-2222-222222222222"))
