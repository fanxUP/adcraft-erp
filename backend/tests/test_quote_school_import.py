"""学校清单报价导入的清洗、分组和计量类型回归测试。"""

from io import BytesIO
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import openpyxl
import pytest

from app.services.quote_school_import_service import (
    commit_school_quote_preview,
    parse_school_quote_workbook,
)


def _make_workbook(rows: list[list], *, merge_remark: tuple[int, int] | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["部门/科室", "项目内容", "产品/材质/工艺", "数量", "单位", "单价", "小计", "备注"])
    for row in rows:
        ws.append(row)
    if merge_remark:
        start, end = merge_remark
        ws.merge_cells(start_row=start, start_column=8, end_row=end, end_column=8)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_school_list_import_groups_by_school_and_maps_explicit_area():
    content = _make_workbook([
        ["学校甲\t", "文化长廊", "规格文本", 243, "m2", 300, None, None],
        ["学校甲", "宣传栏", "2.4*1.2m", 26, "块", 1400, None, None],
        ["学校乙", "石材平台", "花岗岩", 8.4, "m", 210, None, None],
        [None, "合计", None, None, None, None, None, None],
    ])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    assert preview.errors == []
    assert preview.school_count == 2
    assert preview.item_count == 3
    assert preview.total_amount == Decimal("111064.00")
    assert [group.department for group in preview.groups] == ["学校甲", "学校乙"]
    assert preview.skipped_rows == [{"row": 5, "reason": "汇总行"}]

    area_item = preview.groups[0].items[0]
    assert area_item.quantity == Decimal("243")
    assert area_item.source_unit == "m2"
    assert area_item.unit == "㎡"
    assert area_item.measure_kind == "area"
    assert area_item.quantity_mode == "area"
    assert area_item.subtotal_amount == Decimal("72900.00")

    piece_item = preview.groups[0].items[1]
    assert piece_item.measure_kind == "quantity"
    assert piece_item.quantity_mode == "piece"
    assert piece_item.unit == "块"


def test_school_list_import_preserves_zero_price_and_merged_remarks():
    content = _make_workbook([
        ["学校甲", "明细一", "工艺一", 2, "个", 0, None, "适用备注"],
        ["学校甲", "明细二", "工艺二", 3, "个", 100, None, None],
    ], merge_remark=(2, 3))

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    assert preview.errors == []
    assert preview.groups[0].items[0].unit_price == Decimal("0")
    assert preview.groups[0].items[0].subtotal_amount == Decimal("0.00")
    assert preview.groups[0].items[1].remark == "适用备注"


def test_school_list_import_reports_invalid_quantity_instead_of_defaulting_to_one():
    content = _make_workbook([
        ["学校甲", "明细一", "工艺一", None, "个", 100, None, None],
    ])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    assert preview.item_count == 0
    assert preview.errors == [{"row": 2, "message": "数量不能为空"}]


def test_school_list_import_reports_empty_detail_list():
    content = _make_workbook([])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    assert preview.valid is False
    assert preview.errors == [{"row": 0, "message": "未找到有效学校明细"}]


@pytest.mark.asyncio
async def test_school_list_import_passes_customer_uuid_as_string_to_quote_service():
    content = _make_workbook([
        ["学校甲", "文化长廊", "", 2, "㎡", 100, None, None],
    ])
    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )
    customer_id = uuid4()

    with patch("app.services.quote_school_import_service.BusinessDocumentService") as service_class:
        service = service_class.return_value
        service.create = AsyncMock(return_value={
            "id": uuid4(),
            "quote_no": "Q-TEST",
            "total_amount": Decimal("200.00"),
        })

        created = await commit_school_quote_preview(
            object(),
            preview,
            customer_id=customer_id,
        )

    payload = service.create.await_args.args[0]
    assert payload["customer_id"] == str(customer_id)
    assert payload["customer_name"] is None
    assert created[0]["total_amount"] == 200.0


@pytest.mark.parametrize(
    ("source_unit", "measure_kind"),
    [("㎡", "area"), ("m²", "area"), ("平方米", "area"), ("m3", "volume"), ("t", "weight"), ("m", "length")],
)
def test_school_list_import_recognizes_measure_units(source_unit, measure_kind):
    content = _make_workbook([
        ["学校甲", "明细一", "", 2, source_unit, 10, None, None],
    ])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    assert preview.errors == []
    assert preview.groups[0].items[0].measure_kind == measure_kind
