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

# 注册完整模型注册表：查询/删除会实例化真实 ORM 模型，字符串关系需全部模型模块加载后解析
import app.main  # noqa: F401
from sqlalchemy.sql.dml import Update

from app.services.business_document_service import BusinessDocumentService
from app.models.acceptance import AcceptanceForm
from app.models.business_document import BusinessDocument
from app.models.inventory import StockRecord
from app.models.outsource import OutsourceTask
from app.models.payment import Payment
from app.models.project_cost import ProjectCost
from app.models.task import DesignTask, InstallationTask
from app.models.vehicle import VehicleDispatch, VehicleUseRequest

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


def make_convert_execute(doc):
    """convert_doc_type 的 db.execute 分发器：单据查询返回 doc，其余查询返回空，Update 返回空。"""
    async def fake_execute(stmt):
        if isinstance(stmt, Update):
            return mock_result([])
        entity = stmt.column_descriptions[0]["entity"] if stmt.column_descriptions else None
        if entity is BusinessDocument:
            first = MagicMock()
            first.scalar_one_or_none.return_value = doc
            return first
        return mock_result([])
    return fake_execute


@pytest.mark.asyncio
async def test_convert_order_to_quote_works_without_contract_links(service):
    service, db = service
    doc = make_order_doc()
    db.execute.side_effect = make_convert_execute(doc)

    with patch(
        "app.services.number_generator.generate_quote_no",
        AsyncMock(return_value="Q20260804-9999"),
    ):
        result = await service.convert_doc_type(ORDER_UUID, "quote", uuid4())

    assert result["doc_type"] == "quote"
    assert result["quote_no"] == "Q20260804-9999"
    assert result["status"] == "draft"
    db.delete.assert_not_awaited()  # 无合同/业务关联，不做任何清理


# ── 订单转报价：业务关联数据清理 ──


def make_form(**attrs):
    f = MagicMock()
    f.deleted_at = None
    for k, v in attrs.items():
        setattr(f, k, v)
    return f


def make_dispatch_execute(results_by_model):
    """按 ORM 实体分发 db.execute 结果；Update 语句一律返回空，并记录调用。"""
    calls = []

    async def fake_execute(stmt):
        calls.append(stmt)
        if isinstance(stmt, Update):
            return mock_result([])
        entity = stmt.column_descriptions[0]["entity"] if stmt.column_descriptions else None
        return mock_result(results_by_model.get(entity, []))

    return fake_execute, calls


@pytest.mark.asyncio
async def test_cleanup_soft_deletes_all_acceptance_forms(service):
    service, db = service
    draft = make_form(status="draft")
    accepted = make_form(status="accepted")
    fake_execute, _ = make_dispatch_execute({AcceptanceForm: [draft, accepted]})
    db.execute.side_effect = fake_execute

    await service._cleanup_associations_on_order_to_quote(ORDER_UUID)

    assert draft.deleted_at is not None
    assert accepted.deleted_at is not None


@pytest.mark.asyncio
async def test_cleanup_hard_deletes_payments(service):
    service, db = service
    payment = make_form(id=uuid4(), amount=100)
    fake_execute, _ = make_dispatch_execute({Payment: [payment]})
    db.execute.side_effect = fake_execute

    await service._cleanup_associations_on_order_to_quote(ORDER_UUID)

    db.delete.assert_awaited_once_with(payment)


@pytest.mark.asyncio
async def test_cleanup_deletes_tasks_and_unlinks_vehicle_install_refs(service):
    service, db = service
    design = make_form(id=uuid4(), attachments=[])
    install = make_form(id=uuid4(), attachments=[])
    fake_execute, calls = make_dispatch_execute({
        DesignTask: [design],
        InstallationTask: [install],
    })
    db.execute.side_effect = fake_execute

    await service._cleanup_associations_on_order_to_quote(ORDER_UUID)

    db.delete.assert_any_await(design)
    db.delete.assert_any_await(install)
    # 车辆对安装任务的引用被置空（每个车辆模型一次 UPDATE）
    assert sum(isinstance(c, Update) for c in calls) >= 4


@pytest.mark.asyncio
async def test_cleanup_soft_deletes_outsource_and_project_cost(service):
    service, db = service
    out = make_form()
    cost = make_form()
    fake_execute, _ = make_dispatch_execute({OutsourceTask: [out], ProjectCost: [cost]})
    db.execute.side_effect = fake_execute

    await service._cleanup_associations_on_order_to_quote(ORDER_UUID)

    assert out.deleted_at is not None
    assert cost.deleted_at is not None


@pytest.mark.asyncio
async def test_cleanup_unlinks_vehicle_order_ref_and_stock(service):
    service, db = service
    fake_execute, calls = make_dispatch_execute({})
    db.execute.side_effect = fake_execute

    await service._cleanup_associations_on_order_to_quote(ORDER_UUID)

    # 4 个车辆模型 + 1 个库存 = 5 次解除关联 UPDATE
    assert sum(isinstance(c, Update) for c in calls) >= 5
