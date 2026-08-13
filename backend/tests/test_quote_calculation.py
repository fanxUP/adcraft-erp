"""常规报价后端金额计算回归测试。"""

from decimal import Decimal

import pytest

from app.services.quote_calculation import (
    calculate_quote_item_values,
    calculate_quote_totals,
    normalize_quote_item_data,
)


def test_area_quote_includes_pieces_and_other_fee():
    values = calculate_quote_item_values(
        {
            "width": 50,
            "width_unit": "cm",
            "height": 500,
            "height_unit": "mm",
            "pieces": 2,
            "quantity": 1,
            "use_area": True,
            "unit_price": 1000,
            "process_fee": 20,
            "installation_fee": 30,
            "design_fee": 40,
            "transport_fee": 10,
            "other_fee": 5,
        }
    )

    assert values["area"] == Decimal("0.50")
    assert values["subtotal_amount"] == Decimal("505.00")


def test_quantity_quote_ignores_geometry_for_pricing():
    values = normalize_quote_item_data(
        {
            "item_name": "安装服务",
            "width": 10,
            "height": 10,
            "quantity": 3,
            "use_area": False,
            "unit_price": 200,
            "installation_fee": 50,
        }
    )

    assert values["area"] == Decimal("100.00")
    assert values["subtotal_amount"] == Decimal("600.00")


def test_quote_totals_use_percentage_tax_rate():
    totals = calculate_quote_totals(
        [Decimal("1000"), Decimal("500")],
        discount_amount=100,
        tax_rate=6,
    )

    assert totals == {
        "subtotal_amount": Decimal("1500.00"),
        "tax_amount": Decimal("84.00"),
        "total_amount": Decimal("1484.00"),
    }


def test_discount_cannot_exceed_subtotal():
    with pytest.raises(ValueError, match="优惠金额不能超过报价小计"):
        calculate_quote_totals(
            [100],
            discount_amount=101,
            tax_rate=0,
        )


@pytest.mark.parametrize(
    "item,message",
    [
        ({"quantity": 0, "unit_price": 10}, "数量必须大于"),
        ({"quantity": 1, "pieces": 0, "unit_price": 10}, "件数必须大于"),
        (
            {
                "quantity": 1,
                "use_area": True,
                "width": 0,
                "height": 1,
                "unit_price": 10,
            },
            "面积计价明细",
        ),
        ({"quantity": 1, "unit_price": -1}, "不能为负数"),
    ],
)
def test_quote_item_rejects_invalid_business_values(item, message):
    with pytest.raises(ValueError, match=message):
        calculate_quote_item_values(item)
