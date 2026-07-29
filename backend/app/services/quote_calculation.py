"""常规报价金额计算的唯一后端实现。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping


MONEY_QUANTUM = Decimal("0.01")
AREA_QUANTUM = Decimal("0.01")
ZERO = Decimal("0")

FEE_FIELDS = (
    "process_fee",
    "installation_fee",
    "design_fee",
    "transport_fee",
    "other_fee",
)


def as_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _to_meters(value: Any, unit: str | None) -> Decimal:
    number = as_decimal(value)
    if unit == "cm":
        return number / Decimal("100")
    if unit == "mm":
        return number / Decimal("1000")
    return number


def calculate_quote_item_values(item: Mapping[str, Any]) -> dict[str, Decimal]:
    """计算面积与行小计，规则与前端报价编辑器保持一致。"""
    quantity = as_decimal(item.get("quantity"), "1")
    pieces = as_decimal(item.get("pieces"), "1")
    width = _to_meters(item.get("width"), item.get("width_unit"))
    height = _to_meters(item.get("height"), item.get("height_unit"))
    if quantity <= ZERO:
        raise ValueError("报价明细数量必须大于 0")
    if pieces <= ZERO:
        raise ValueError("报价明细件数必须大于 0")
    if width < ZERO or height < ZERO:
        raise ValueError("报价明细宽高不能为负数")

    unit_price = as_decimal(item.get("unit_price"))
    fees = [as_decimal(item.get(field)) for field in FEE_FIELDS]
    if unit_price < ZERO or any(fee < ZERO for fee in fees):
        raise ValueError("报价明细单价和附加费用不能为负数")

    area = (width * height * pieces).quantize(
        AREA_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
    use_area = bool(item.get("use_area"))
    if use_area and area <= ZERO:
        raise ValueError("面积计价明细必须填写大于 0 的宽和高")
    base = area if use_area else quantity
    subtotal = base * unit_price
    subtotal += sum(fees, ZERO)
    return {
        "area": area,
        "subtotal_amount": subtotal.quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        ),
    }


def normalize_quote_item_data(item: Mapping[str, Any]) -> dict[str, Any]:
    """将 API 明细转换为可持久化数据，并由后端重算金额字段。"""
    normalized = dict(item)
    for field in ("quantity", "pieces", "unit_price", *FEE_FIELDS):
        default = "1" if field in {"quantity", "pieces"} else "0"
        normalized[field] = as_decimal(normalized.get(field), default)
    normalized.update(calculate_quote_item_values(normalized))
    return normalized


def calculate_quote_totals(
    item_subtotals: list[Any],
    *,
    discount_amount: Any,
    tax_rate: Any,
) -> dict[str, Decimal]:
    subtotal = sum((as_decimal(value) for value in item_subtotals), ZERO)
    discount = as_decimal(discount_amount)
    rate = as_decimal(tax_rate)
    if discount < ZERO:
        raise ValueError("优惠金额不能为负数")
    if discount > subtotal:
        raise ValueError("优惠金额不能超过报价小计")
    if rate < ZERO or rate > Decimal("100"):
        raise ValueError("税率必须在 0 到 100 之间")
    taxable = subtotal - discount
    tax = (
        taxable * rate / Decimal("100")
    ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    return {
        "subtotal_amount": subtotal.quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        ),
        "tax_amount": tax,
        "total_amount": (taxable + tax).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        ),
    }
