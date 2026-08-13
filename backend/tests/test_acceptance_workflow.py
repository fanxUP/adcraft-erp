"""验收与订单状态同步的回归测试。"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.acceptance_service import AcceptanceService
from app.repositories.acceptance_repo import normalize_acceptance_item_data

# 导入全部模型模块，注册完整 SQLAlchemy mapper registry（与 main.py 启动时一致）
import importlib
import pkgutil
import app.models
for _m in pkgutil.iter_modules(app.models.__path__):
    if _m.name != "base":
        importlib.import_module(f"app.models.{_m.name}")




@pytest.mark.asyncio
async def test_acceptance_rejects_unfinished_items():
    """Auto-confirms pending items instead of rejecting (Problem 3 fix)."""
    db = AsyncMock()
    db.flush = AsyncMock()
    form = MagicMock()
    form.id = uuid4()
    form.status = "pending"
    form.accepted_at = None
    form.document = MagicMock(
        id=uuid4(),
        doc_type="order",
        status="pending_acceptance",
    )
    form.items = [
        MagicMock(item_name="门头", item_status="accepted"),
        MagicMock(item_name="灯箱", item_status="pending", remark=""),
    ]

    with patch(
        "app.services.acceptance_service.AcceptanceRepository"
    ) as repository_class, patch(
        "app.services.acceptance_service.BusinessDocumentService"
    ) as service_class:
        repository_class.return_value.get_by_id = AsyncMock(return_value=form)
        service_class.return_value.change_status = AsyncMock()

        service = AcceptanceService(db)
        service._to_detail_dict = MagicMock(return_value={"status": "accepted"})
        await service.change_status(
            form.id,
            "accepted",
            operated_by=uuid4(),
        )

    # Pending items should be auto-confirmed, not rejected
    for item in form.items:
        assert item.item_status == "accepted", f"Item {item.item_name} not accepted"
    assert "系统自动确认" in (form.items[1].remark or "")


@pytest.mark.asyncio
async def test_acceptance_rejects_quote_that_is_not_confirmed():
    db = MagicMock()
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = MagicMock(
        doc_type="quote",
        status="draft",
    )
    db.execute = AsyncMock(return_value=source_result)

    service = AcceptanceService(db)
    with pytest.raises(ValueError, match="报价尚未确认"):
        await service.create_acceptance({"quote_id": str(uuid4())})


@pytest.mark.asyncio
async def test_acceptance_rejects_duplicate_active_form():
    db = MagicMock()
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = MagicMock(
        doc_type="order",
        status="pending_acceptance",
    )
    duplicate_result = MagicMock()
    duplicate_result.scalar_one_or_none.return_value = uuid4()
    db.execute = AsyncMock(side_effect=[source_result, duplicate_result])

    service = AcceptanceService(db)
    with pytest.raises(ValueError, match="已有有效验收单"):
        await service.create_acceptance({"order_id": str(uuid4())})


@pytest.mark.asyncio
async def test_pending_acceptance_can_save_existing_item_results():
    db = MagicMock()
    db.flush = AsyncMock()
    item = MagicMock(
        id=uuid4(),
        item_name="原验收项目",
        item_status="pending",
        remark=None,
        image_url=None,
    )
    form = MagicMock(status="pending", items=[item], contact_person=None, contact_phone=None)

    with patch(
        "app.services.acceptance_service.AcceptanceRepository"
    ) as repository_class:
        repository_class.return_value.get_by_id = AsyncMock(
            return_value=form
        )
        service = AcceptanceService(db)
        service._to_detail_dict = MagicMock(return_value={"status": "pending"})

        result = await service.update_acceptance(
            uuid4(),
            {
                "items": [
                    {
                        "id": str(item.id),
                        "item_name": "不允许在待验收阶段改名",
                        "item_status": "accepted",
                        "remark": "现场确认通过",
                    }
                ]
            },
        )

    assert result["status"] == "pending"
    assert item.item_name == "原验收项目"
    assert item.item_status == "accepted"
    assert item.remark == "现场确认通过"


def test_acceptance_item_alias_is_normalized_for_persistence():
    document_item_id = uuid4()

    normalized = normalize_acceptance_item_data(
        {
            "id": str(uuid4()),
            "order_item_id": str(document_item_id),
            "item_name": "灯箱",
            "item_status": "pending",
        }
    )

    assert normalized["document_item_id"] == document_item_id
    assert "order_item_id" not in normalized
    assert "id" not in normalized




@pytest.mark.asyncio
async def test_copy_doc_items_skips_area_when_not_area_priced():
    """use_area=False（按数量计价）的明细复制到验收单时 area 应为 None。"""
    from types import SimpleNamespace

    from app.models.acceptance import AcceptanceItem

    def make_item(item_name: str, *, use_area: bool, area):
        return SimpleNamespace(
            id=uuid4(),
            item_name=item_name,
            material_process=None,
            width=None,
            height=None,
            pieces=1,
            width_unit=None,
            height_unit=None,
            quantity=1,
            unit="个",
            area=area,
            unit_price=50,
            subtotal_amount=300,
            group_name=None,
            remark=None,
            image_url=None,
            use_area=use_area,
        )

    doc = SimpleNamespace(
        items=[
            make_item("面积计价", use_area=True, area=0.24),
            make_item("数量计价", use_area=False, area=0.24),
        ]
    )

    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = doc
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()

    service = AcceptanceService(db)
    await service._copy_doc_items(uuid4(), uuid4())

    added = {call.args[0].item_name: call.args[0] for call in db.add.call_args_list}
    assert added["面积计价"].area == 0.24
    assert added["数量计价"].area is None
    assert isinstance(added["面积计价"], AcceptanceItem)
