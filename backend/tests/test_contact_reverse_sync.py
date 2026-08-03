"""单据联系人反向同步到客户管理的测试。

- CustomerRepository.upsert_contact：按 (客户, 姓名) 新增/更新联系人
- 保存单据（常规报价创建/更新、智能报价保存版本）时自动同步联系人
"""

from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.customer import CustomerContact
from app.repositories.customer_repo import CustomerRepository


# ─────────────────────────────────────────────
# CustomerRepository.upsert_contact
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_contact_creates_when_missing():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    db.add = MagicMock()
    db.flush = AsyncMock()
    repo = CustomerRepository(db)

    customer_id = uuid4()
    contact = await repo.upsert_contact(customer_id, "张三", "13800138000")

    assert contact is not None
    assert contact.customer_id == customer_id
    assert contact.name == "张三"
    assert contact.phone == "13800138000"
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_contact_updates_existing_phone():
    customer_id = uuid4()
    existing = CustomerContact(customer_id=customer_id, name="张三", phone="13800138000")
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: existing))
    db.add = MagicMock()
    db.flush = AsyncMock()
    repo = CustomerRepository(db)

    contact = await repo.upsert_contact(customer_id, "张三", "13900139000")

    assert contact is existing
    assert existing.phone == "13900139000"
    db.add.assert_not_called()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_contact_skips_empty_name():
    repo = CustomerRepository(MagicMock())

    result = await repo.upsert_contact(uuid4(), "", "13800138000")

    assert result is None


# ─────────────────────────────────────────────
# 常规报价：BusinessDocumentService 创建/更新时反向同步
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quote_create_syncs_contact_to_customer():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    db.refresh = AsyncMock()
    doc = MagicMock()
    doc.doc_type = "quote"
    doc.customer_id = uuid4()
    doc.id = uuid4()

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = BusinessDocumentService(db, doc_type="quote")
        service.repo.create = AsyncMock(return_value=doc)
        service._calculate_quote = AsyncMock()
        service._sync_customer_agreements = AsyncMock()
        service._to_detail = AsyncMock(return_value={})

        await service.create({
            "customer_id": str(doc.customer_id),
            "project_name": "测试报价",
            "contact_person": "张三",
            "contact_phone": "13800138000",
        })

        repo.upsert_contact.assert_awaited_once_with(doc.customer_id, "张三", "13800138000")


@pytest.mark.asyncio
async def test_quote_update_syncs_contact_to_customer():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])))
    doc = MagicMock()
    doc.doc_type = "quote"
    doc.status = "draft"
    doc.customer_id = uuid4()

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = BusinessDocumentService(db, doc_type="quote")
        service.repo.get_by_id = AsyncMock(return_value=doc)
        service.repo.update = AsyncMock(side_effect=lambda d, data: d)
        service.repo.get_items = AsyncMock(return_value=[])
        service._calculate_quote = AsyncMock()
        service._sync_customer_agreements = AsyncMock()
        service._to_detail = AsyncMock(return_value={})

        await service.update(doc.id, {
            "project_name": "测试报价",
            "contact_person": "张三",
            "contact_phone": "13800138000",
        })

        repo.upsert_contact.assert_awaited_once_with(doc.customer_id, "张三", "13800138000")


@pytest.mark.asyncio
async def test_quote_create_without_customer_skips_sync():
    from app.services.business_document_service import BusinessDocumentService

    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    db.refresh = AsyncMock()
    doc = MagicMock()
    doc.doc_type = "quote"
    doc.customer_id = None
    doc.id = uuid4()

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()
        service = BusinessDocumentService(db, doc_type="quote")
        service.repo.create = AsyncMock(return_value=doc)
        service._calculate_quote = AsyncMock()
        service._sync_customer_agreements = AsyncMock()
        service._to_detail = AsyncMock(return_value={})

        await service.create({
            "customer_name": "自由输入客户",
            "project_name": "测试报价",
            "contact_person": "张三",
            "contact_phone": "13800138000",
        })

        repo.upsert_contact.assert_not_awaited()


# ─────────────────────────────────────────────
# 智能报价：保存版本时反向同步联系人
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cdr_version_syncs_contact_to_customer():
    from app.services.cdr_quote_pricing_service import CdrQuotePricingService

    db = MagicMock()
    service = CdrQuotePricingService(db)
    quote_id = uuid4()
    quote = SimpleNamespace(customer_id=uuid4())
    version = SimpleNamespace(
        id=uuid4(),
        quote_id=quote_id,
        version_no=1,
        status="draft",
        subtotal_amount=Decimal("0"),
        total_amount=Decimal("0"),
        estimated_cost=Decimal("0"),
        estimated_profit=Decimal("0"),
        estimated_margin=Decimal("0"),
        notes=None,
        created_by=uuid4(),
        created_at=None,
        snapshot_json=None,
        lines=[],
    )
    service.repo.get_max_version_no = AsyncMock(return_value=0)
    service.repo.create_version = AsyncMock(return_value=version)
    service.repo.get_quote = AsyncMock(return_value=quote)
    service.repo.create_line = AsyncMock()
    service.repo.create_audit_log = AsyncMock()
    service._recalc_version_totals = AsyncMock()
    service._sync_customer_agreements = AsyncMock()

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()

        await service.create_quote_version(
            quote_id,
            {"contact_person": "张三", "contact_phone": "13800138000", "lines": []},
            uuid4(),
        )

        repo.upsert_contact.assert_awaited_once_with(quote.customer_id, "张三", "13800138000")


@pytest.mark.asyncio
async def test_cdr_version_without_customer_skips_sync():
    from app.services.cdr_quote_pricing_service import CdrQuotePricingService

    db = MagicMock()
    service = CdrQuotePricingService(db)
    quote_id = uuid4()
    quote = SimpleNamespace(customer_id=None)
    version = SimpleNamespace(
        id=uuid4(),
        quote_id=quote_id,
        version_no=1,
        status="draft",
        subtotal_amount=Decimal("0"),
        total_amount=Decimal("0"),
        estimated_cost=Decimal("0"),
        estimated_profit=Decimal("0"),
        estimated_margin=Decimal("0"),
        notes=None,
        created_by=uuid4(),
        created_at=None,
        snapshot_json=None,
        lines=[],
    )
    service.repo.get_max_version_no = AsyncMock(return_value=0)
    service.repo.create_version = AsyncMock(return_value=version)
    service.repo.get_quote = AsyncMock(return_value=quote)
    service.repo.create_line = AsyncMock()
    service.repo.create_audit_log = AsyncMock()
    service._recalc_version_totals = AsyncMock()
    service._sync_customer_agreements = AsyncMock()

    with patch("app.repositories.customer_repo.CustomerRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.upsert_contact = AsyncMock()

        await service.create_quote_version(
            quote_id,
            {"contact_person": "张三", "contact_phone": "13800138000", "lines": []},
            uuid4(),
        )

        repo.upsert_contact.assert_not_awaited()
