"""联系人跨单据解耦测试。

报价单/订单/验收单是给不同的人看的，联系人不再从报价单一路传递：
- 转订单（CDR 智能报价 / 普通报价转单）不再继承报价单联系人
- 订单联系人可独立编辑（update_order_contact），保存时反向同步客户管理
- 验收单用自己的联系人字段（不再从订单派生），保存时反向同步客户管理
"""

from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 注册完整模型注册表：convert_to_order 会实例化真实 BusinessDocument，
# 其字符串关系（如 -> Customer）需全部模型模块加载后才能解析
import app.main  # noqa: F401


# ─────────────────────────────────────────────
# CDR 智能报价 → 订单：不再复制报价单联系人
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_convert_to_order_does_not_inherit_quote_contact():
    from app.services.cdr_quote_conversion_service import CdrQuoteConversionService

    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    quote_doc = MagicMock()
    quote_doc.id = uuid4()
    quote_doc.doc_type = "quote"
    quote_doc.quote_mode = "cdr"
    quote_doc.status = "confirmed"
    quote_doc.deleted_at = None
    quote_doc.customer_id = uuid4()
    quote_doc.customer_name = "测试客户"
    quote_doc.project_name = "测试项目"
    quote_doc.sales_user_id = uuid4()
    quote_doc.department = "业务部"
    quote_doc.contact_person = "张三"  # 报价单有联系人
    quote_doc.contact_phone = "13800138000"
    quote_doc.installation_address = None

    version = SimpleNamespace(
        id=uuid4(),
        quote_id=quote_doc.id,
        version_no=1,
        status="confirmed",
        total_amount=Decimal("1000"),
        lines=[],
    )

    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=lambda: quote_doc)
    )

    added_objects = []
    def capture_add(obj):
        added_objects.append(obj)
    db.add = MagicMock(side_effect=capture_add)

    with (
        patch("app.services.order_customer_service.ensure_document_customer",
              new=AsyncMock()),
        patch("app.services.number_generator.generate_order_no",
              new=AsyncMock(return_value="O20260803-0001")),
    ):
        service = CdrQuoteConversionService(db)
        service.repo.get_latest_version = AsyncMock(return_value=version)
        service.repo.create_audit_log = AsyncMock()

        await service.convert_to_order(quote_doc.id, uuid4())

    # 报价单有联系人，但订单不再继承
    order_doc = next(
        obj for obj in added_objects
        if obj.__class__.__name__ == "BusinessDocument"
    )
    assert quote_doc.contact_person == "张三"
    assert order_doc.contact_person is None
    assert order_doc.contact_phone is None


# ─────────────────────────────────────────────
# 普通报价 → 订单（同一行改类型）：转单时清空联系人
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_convert_doc_type_quote_to_order_clears_contact():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    db.flush = AsyncMock()

    doc = MagicMock()
    doc.id = uuid4()
    doc.doc_type = "quote"
    doc.status = "confirmed"
    doc.contact_person = "张三"
    doc.contact_phone = "13800138000"
    doc.total_amount = Decimal("1000")
    doc.discount_amount = 100

    initial = MagicMock(scalar_one_or_none=lambda: doc)
    empty = MagicMock()
    empty.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[initial, empty, empty, empty, empty])

    with (
        patch("app.services.order_customer_service.ensure_document_customer",
              new=AsyncMock()),
        patch("app.services.number_generator.generate_order_no",
              new=AsyncMock(return_value="O20260803-0002")),
    ):
        service = BusinessDocumentService(db, doc_type="quote")
        service.repo.get_next_version_no = AsyncMock(return_value=1)
        service.repo.create_version = AsyncMock(return_value=MagicMock())
        service.repo.create_status_log = AsyncMock()
        service._to_detail = AsyncMock(return_value={})

        await service.convert_doc_type(doc.id, "order", uuid4())

    assert doc.doc_type == "order"
    assert doc.contact_person is None
    assert doc.contact_phone is None


# ─────────────────────────────────────────────
# 订单联系人独立编辑 + 反向同步
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_order_contact_updates_and_syncs():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    db.flush = AsyncMock()
    doc = MagicMock()
    doc.id = uuid4()
    doc.doc_type = "order"
    doc.customer_id = uuid4()

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = BusinessDocumentService(db, doc_type="order")
        service.repo.get_by_id = AsyncMock(return_value=doc)
        service._to_detail = AsyncMock(return_value={})

        await service.update_order_contact(doc.id, "李四", "13900139000")

        assert doc.contact_person == "李四"
        assert doc.contact_phone == "13900139000"
        repo.upsert_contact.assert_awaited_once_with(
            doc.customer_id, "李四", "13900139000"
        )


@pytest.mark.asyncio
async def test_update_order_contact_clears_when_empty():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    db.flush = AsyncMock()
    doc = MagicMock()
    doc.id = uuid4()
    doc.doc_type = "order"
    doc.customer_id = uuid4()
    doc.contact_person = "张三"  # 原联系人，清空后应为 None
    doc.contact_phone = "13800138000"

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = BusinessDocumentService(db, doc_type="order")
        service.repo.get_by_id = AsyncMock(return_value=doc)
        service._to_detail = AsyncMock(return_value={})

        await service.update_order_contact(doc.id, "   ", "   ")

        assert doc.contact_person is None
        assert doc.contact_phone is None
        repo.upsert_contact.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_order_contact_rejects_quote():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    doc = MagicMock()
    doc.id = uuid4()
    doc.doc_type = "quote"

    service = BusinessDocumentService(db, doc_type="order")
    service.repo.get_by_id = AsyncMock(return_value=doc)

    with pytest.raises(ValueError, match="仅订单可设置联系人"):
        await service.update_order_contact(doc.id, "李四", "13900139000")


# ─────────────────────────────────────────────
# 验收单：用自己的联系人，不再从订单派生
# ─────────────────────────────────────────────

def test_acceptance_doc_info_uses_own_contact_not_order():
    from app.services.acceptance_service import AcceptanceService

    order_doc = MagicMock()
    order_doc.doc_type = "order"
    order_doc.contact_person = "张三"  # 订单的联系人不应被采用
    order_doc.contact_phone = "13800138000"
    order_doc.customer_name = None
    order_doc.project_name = "测试项目"
    order_doc.department = "业务部"
    order_doc.created_at = None

    form = MagicMock()
    form.contact_person = "李四"
    form.contact_phone = "13900139000"
    form.document = order_doc

    info = AcceptanceService._doc_info(form)

    assert info["contact_person"] == "李四"
    assert info["contact_phone"] == "13900139000"


@pytest.mark.asyncio
async def test_acceptance_create_stores_contact_and_syncs():
    from app.services.acceptance_service import AcceptanceService

    db = MagicMock()
    order_id = uuid4()
    source_doc = MagicMock()
    source_doc.id = order_id
    source_doc.doc_type = "order"
    source_doc.status = "pending_acceptance"
    source_doc.customer_id = uuid4()

    form = MagicMock()
    form.id = uuid4()
    form2 = MagicMock()
    form2.id = form.id
    form2.document_id = order_id
    form2.document = source_doc
    # repo.create 保存的联系人，get_by_id 读回
    form2.contact_person = "李四"
    form2.contact_phone = "13900139000"

    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: source_doc),  # 关联单据
        MagicMock(scalar_one_or_none=lambda: None),        # 重复校验
    ])

    with (
        # acceptance_service 顶部 module-level import：
        # from app.services.number_generator import generate_acceptance_no
        patch("app.services.acceptance_service.generate_acceptance_no",
              new=AsyncMock(return_value="YS20260803-0001")),
        patch("app.repositories.customer_repo.CustomerRepository") as repo_cls,
    ):
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = AcceptanceService(db)
        service.repo.create = AsyncMock(return_value=form)
        service.repo.get_by_id = AsyncMock(return_value=form2)
        service._to_detail_dict = MagicMock(return_value={})

        await service.create_acceptance({
            "order_id": str(order_id),
            "contact_person": "李四",
            "contact_phone": "13900139000",
            "items": [{"item_name": "测试项"}],
        })

        created_data = service.repo.create.await_args.args[0]
        assert created_data["contact_person"] == "李四"
        assert created_data["contact_phone"] == "13900139000"
        repo.upsert_contact.assert_awaited_once_with(
            source_doc.customer_id, "李四", "13900139000"
        )


@pytest.mark.asyncio
async def test_acceptance_update_stores_contact_and_syncs():
    from app.services.acceptance_service import AcceptanceService

    db = MagicMock()
    source_doc = MagicMock()
    source_doc.customer_id = uuid4()

    form = MagicMock()
    form.id = uuid4()
    form.status = "draft"
    form.document_id = uuid4()
    form.document = source_doc

    async def apply_update(f, data):
        for key, value in data.items():
            setattr(f, key, value)
        return f

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = AcceptanceService(db)
        service.repo.get_by_id = AsyncMock(return_value=form)
        service.repo.update = AsyncMock(side_effect=apply_update)
        service._to_detail_dict = MagicMock(return_value={})

        await service.update_acceptance(form.id, {
            "contact_person": "李四",
            "contact_phone": "13900139000",
        })

        assert form.contact_person == "李四"
        assert form.contact_phone == "13900139000"
        repo.upsert_contact.assert_awaited_once_with(
            source_doc.customer_id, "李四", "13900139000"
        )


@pytest.mark.asyncio
async def test_acceptance_sync_skips_standalone_without_customer():
    from app.services.acceptance_service import AcceptanceService

    db = MagicMock()
    form = MagicMock()
    form.contact_person = "李四"
    form.contact_phone = "13900139000"
    form.document_id = uuid4()
    form.document = MagicMock(customer_id=None)

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()

        await AcceptanceService(db)._sync_contact_to_customer(form)

        repo.upsert_contact.assert_not_awaited()
