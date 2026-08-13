"""智能报价明细与统一业务单据明细之间的字段适配。"""

from decimal import Decimal
from typing import Any


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _dimension_to_millimeters(value: Any, unit: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    number = _decimal(value)
    if unit == "m":
        return number * Decimal("1000")
    if unit == "cm":
        return number * Decimal("10")
    return number


def _dimension_to_meters(value: Any, unit: str | None) -> Decimal:
    number = _decimal(value)
    if unit == "cm":
        return number / Decimal("100")
    if unit == "mm":
        return number / Decimal("1000")
    return number


def normalize_regular_quote_line(data: dict[str, Any]) -> dict[str, Any]:
    """规范常规报价字段，并生成 CDR 计价引擎需要的毫米字段。"""
    description = data.get("item_name") or data.get("description") or "待填写"
    width_value = data.get("width")
    height_value = data.get("height")
    width_unit = data.get("width_unit") or "m"
    height_unit = data.get("height_unit") or "m"
    if width_value in (None, "") and data.get("width_mm") not in (None, ""):
        width_value = data["width_mm"]
        width_unit = "mm"
    if height_value in (None, "") and data.get("height_mm") not in (None, ""):
        height_value = data["height_mm"]
        height_unit = "mm"
    width = _decimal(width_value) if width_value not in (None, "") else None
    height = _decimal(height_value) if height_value not in (None, "") else None

    return {
        "description": description,
        "material_process": data.get("material_process"),
        "width": width,
        "width_unit": width_unit,
        "height": height,
        "height_unit": height_unit,
        "width_mm": _dimension_to_millimeters(width, width_unit),
        "height_mm": _dimension_to_millimeters(height, height_unit),
        "length_m": None,
        "quantity": _decimal(data.get("quantity"), "1"),
        "unit": data.get("unit"),
        "use_area": bool(data.get("use_area", False)),
        "pieces": _decimal(data.get("pieces"), "1"),
        "unit_price": _decimal(data.get("unit_price")),
        "process_fee": _decimal(data.get("process_fee")),
        "installation_fee": _decimal(data.get("installation_fee")),
        "design_fee": _decimal(data.get("design_fee")),
        "transport_fee": _decimal(data.get("transport_fee")),
        "other_fee": _decimal(data.get("other_fee")),
        "remark": data.get("remark"),
        "image_url": data.get("image_url"),
        "sort_order": int(data.get("sort_order") or 0),
        "group_name": data.get("group_name"),
    }


def calculate_regular_line_area(data: dict[str, Any]) -> Decimal:
    width = _dimension_to_meters(data.get("width"), data.get("width_unit"))
    height = _dimension_to_meters(data.get("height"), data.get("height_unit"))
    pieces = _decimal(data.get("pieces"), "1")
    return (width * height * pieces).quantize(Decimal("0.01"))


def calculate_regular_line_subtotal(data: dict[str, Any]) -> Decimal:
    base = (
        calculate_regular_line_area(data)
        if data.get("use_area")
        else _decimal(data.get("quantity"))
    )
    subtotal = base * _decimal(data.get("unit_price"))
    # 工艺费/安装费/设计费/运输费已移除，仅其他费计入行小计
    subtotal += _decimal(data.get("other_fee"))
    return subtotal.quantize(Decimal("0.01"))


def to_business_document_item_data(line: Any) -> dict[str, Any]:
    """将智能报价版本明细无损转换为统一订单明细。"""
    return {
        "item_name": line.description,
        "product_id": line.product_id,
        "material_id": line.material_id,
        "material_process": line.material_process,
        "width": float(line.width) if line.width is not None else None,
        "width_unit": line.width_unit,
        "height": float(line.height) if line.height is not None else None,
        "height_unit": line.height_unit,
        "quantity": float(line.quantity or 1),
        "unit": line.unit or "件",
        "use_area": bool(line.use_area),
        "pieces": float(line.pieces or 1),
        "unit_price": float(line.unit_price or 0),
        "process_fee": float(line.process_fee or 0),
        "installation_fee": float(line.installation_fee or 0),
        "design_fee": float(line.design_fee or 0),
        "transport_fee": float(line.transport_fee or 0),
        "other_fee": float(line.other_fee or 0),
        "subtotal_amount": float(line.amount or 0),
        "remark": line.remark,
        "image_url": line.image_url,
        "sort_order": line.sort_order or 0,
        "group_name": line.group_name,
    }
