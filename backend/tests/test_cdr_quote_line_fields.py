"""智能报价明细与常规报价字段一致性的回归测试。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.cdr_quote import QuoteLine
from app.schemas.cdr_quote import QuoteLineCreate
from app.services.cdr_quote_pricing_service import CdrQuotePricingService


REGULAR_QUOTE_LINE_COLUMNS = {
    "material_process",
    "width",
    "width_unit",
    "height",
    "height_unit",
    "use_area",
    "process_fee",
    "installation_fee",
    "design_fee",
    "transport_fee",
    "other_fee",
    "remark",
    "image_url",
    "sort_order",
    "group_name",
}


def test_cdr_quote_line_model_contains_regular_quote_fields():
    assert REGULAR_QUOTE_LINE_COLUMNS.issubset(QuoteLine.__table__.columns.keys())


def test_cdr_quote_line_schema_accepts_regular_quote_fields():
    line = QuoteLineCreate(
        item_name="门头制作",
        material_process="门头 / 铝塑板 / UV打印",
        width=Decimal("3"),
        width_unit="m",
        height=Decimal("120"),
        height_unit="cm",
        pieces=Decimal("2"),
        use_area=True,
        quantity=Decimal("7.2"),
        unit="㎡",
        unit_price=Decimal("100"),
        process_fee=Decimal("20"),
        installation_fee=Decimal("30"),
        design_fee=Decimal("10"),
        transport_fee=Decimal("40"),
        other_fee=Decimal("5"),
        remark="测试备注",
        image_url="/uploads/sample.png",
        sort_order=3,
        group_name="门头部分",
    )

    assert line.item_name == "门头制作"
    assert line.description == "门头制作"
    assert line.material_process == "门头 / 铝塑板 / UV打印"


def test_cdr_quote_line_adapter_uses_regular_quote_amount_formula():
    from app.services.cdr_quote_line_adapter import (
        calculate_regular_line_subtotal,
        normalize_regular_quote_line,
    )

    normalized = normalize_regular_quote_line(
        {
            "item_name": "门头制作",
            "width": Decimal("3"),
            "width_unit": "m",
            "height": Decimal("120"),
            "height_unit": "cm",
            "pieces": Decimal("2"),
            "use_area": True,
            "quantity": Decimal("1"),
            "unit_price": Decimal("100"),
            "process_fee": Decimal("20"),
            "installation_fee": Decimal("30"),
            "design_fee": Decimal("10"),
            "transport_fee": Decimal("40"),
            "other_fee": Decimal("5"),
        }
    )

    assert normalized["width_mm"] == Decimal("3000")
    assert normalized["height_mm"] == Decimal("1200")
    assert normalized["length_m"] is None
    assert calculate_regular_line_subtotal(normalized) == Decimal("725")


def test_cdr_quote_line_adapter_preserves_regular_fields_when_converting_order():
    from app.services.cdr_quote_line_adapter import to_business_document_item_data

    line = SimpleNamespace(
        description="门头制作",
        product_id=None,
        material_id=None,
        material_process="门头 / 铝塑板 / UV打印",
        width=Decimal("3"),
        width_unit="m",
        height=Decimal("120"),
        height_unit="cm",
        quantity=Decimal("7.2"),
        unit="㎡",
        use_area=True,
        pieces=Decimal("2"),
        unit_price=Decimal("100"),
        process_fee=Decimal("20"),
        installation_fee=Decimal("30"),
        design_fee=Decimal("10"),
        transport_fee=Decimal("40"),
        other_fee=Decimal("5"),
        amount=Decimal("825"),
        remark="测试备注",
        image_url="/uploads/sample.png",
        sort_order=3,
        group_name="门头部分",
    )

    data = to_business_document_item_data(line)

    assert data["item_name"] == "门头制作"
    assert data["material_process"] == "门头 / 铝塑板 / UV打印"
    assert data["width"] == 3.0
    assert data["width_unit"] == "m"
    assert data["process_fee"] == 20.0
    assert data["subtotal_amount"] == 825.0


@pytest.mark.asyncio
async def test_cdr_pricing_resolves_legacy_cost_data_from_product_combination():
    service = CdrQuotePricingService(MagicMock())
    product_id = uuid4()
    material_id = uuid4()
    process_id = uuid4()
    service.repo.get_product = AsyncMock(return_value=SimpleNamespace(
        id=product_id,
        pricing_method="area",
        default_price=Decimal("100"),
        min_charge=Decimal("0"),
        default_loss_rate=Decimal("0"),
        requires_geometry=False,
        needs_installation=False,
        allows_outsource=False,
        needs_approval=False,
        unit="㎡",
        material_name="铝塑板",
        process_name="UV打印",
    ))
    service.repo.get_material_by_name = AsyncMock(return_value=SimpleNamespace(
        id=material_id,
        name="铝塑板",
        purchase_price=Decimal("30"),
        sale_price=Decimal("50"),
        loss_rate=Decimal("0.05"),
        unit="㎡",
        thickness_mm=None,
        sheet_width_mm=None,
        sheet_height_mm=None,
    ))
    service.repo.get_processes_by_names = AsyncMock(return_value=[
        SimpleNamespace(
            id=process_id,
            name="UV打印",
            billing_basis="area",
            default_price=Decimal("10"),
            startup_fee=Decimal("0"),
            min_charge=Decimal("0"),
            standard_hours=None,
        )
    ])

    request = await service._build_calculate_request({
        "product_id": str(product_id),
        "quantity": 1,
    })

    assert request.material is not None
    assert request.material.name == "铝塑板"
    assert [process.name for process in request.processes] == ["UV打印"]


@pytest.mark.asyncio
async def test_cdr_version_saves_regular_quote_fields_and_fees():
    service = CdrQuotePricingService(MagicMock())
    quote_id = uuid4()
    version_id = uuid4()
    version = SimpleNamespace(
        id=version_id,
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
        lines=[],
    )
    service.repo.get_max_version_no = AsyncMock(return_value=0)
    service.repo.create_version = AsyncMock(return_value=version)

    async def create_line(data):
        line = SimpleNamespace(
            id=uuid4(),
            source="auto",
            processes=[],
            **data,
        )
        version.lines.append(line)
        return line

    service.repo.create_line = AsyncMock(side_effect=create_line)
    service.repo.create_audit_log = AsyncMock()
    service.repo.get_quote = AsyncMock(return_value=None)
    service.calculate = AsyncMock(return_value={
        "billable_quantity": "7.2",
        "unit_price": "100",
        "subtotal_amount": "720",
        "total_cost": "300",
        "requires_approval": False,
        "pricing_trace": [],
    })
    service._recalc_version_totals = AsyncMock()

    await service.create_quote_version(
        quote_id,
        {
            "lines": [{
                "item_name": "门头制作",
                "material_process": "门头 / 铝塑板 / UV打印",
                "width": 3,
                "width_unit": "m",
                "height": 1.2,
                "height_unit": "m",
                "pieces": 2,
                "use_area": True,
                "quantity": 7.2,
                "unit": "㎡",
                "unit_price": 100,
                "process_fee": 20,
                "installation_fee": 30,
                "design_fee": 10,
                "transport_fee": 40,
                "other_fee": 5,
            }]
        },
        uuid4(),
    )

    saved = service.repo.create_line.await_args.args[0]
    pricing_input = service.calculate.await_args.args[0]
    assert saved["description"] == "门头制作"
    assert saved["width_mm"] == Decimal("3000")
    assert saved["height_mm"] == Decimal("1200.0")
    assert saved["amount"] == Decimal("725.00")
    assert pricing_input["quantity"] == Decimal("2")
