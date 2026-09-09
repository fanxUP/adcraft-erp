"""学校清单报价导入的清洗、分组和计量类型回归测试。"""

from io import BytesIO
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import openpyxl
import pytest

from app.services.quote_school_import_service import (
    commit_school_quote_preview,
    commit_school_quote_dimension_backfill,
    parse_school_quote_workbook,
    preview_school_quote_dimension_backfill,
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


def test_school_list_import_extracts_product_dimensions_and_normalizes_units():
    content = _make_workbook([
        ["学校甲", "宣传牌", "1.名称:宣传牌\n2.尺寸:4000×1200mm\n3.材质:10mm厚PT板", 1, "块", 100, None, None],
        ["学校甲", "图书角", "1.名称:图书角\n2.台柜规格:长2.4米，高2.8米\n3.材料:18mm厚生态板", 1, "个", 100, None, None],
        ["学校甲", "文化长廊", "1.尺寸:长27米、宽9.0米、高3.0米\n2.骨架:50×50方钢", 1, "m2", 100, None, None],
        ["学校甲", "校徽", "1.直径0.4m\n2.基材:10mm厚铝板", 1, "个", 100, None, None],
    ])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    items = preview.groups[0].items
    assert (items[0].width, items[0].height, items[0].width_unit, items[0].height_unit) == (
        Decimal("4"), Decimal("1.2"), "m", "m"
    )
    assert (items[1].width, items[1].height) == (Decimal("2.4"), Decimal("2.8"))
    assert (items[2].length, items[2].width, items[2].height) == (
        Decimal("27"), Decimal("9"), Decimal("3")
    )
    assert items[3].width == Decimal("0.4")
    assert items[3].height == Decimal("0.4")
    assert all(item.dimension_status == "auto" for item in items)


def test_school_list_import_does_not_treat_material_or_foundation_specs_as_product_size():
    content = _make_workbook([
        ["学校甲", "钢支撑", "1.钢材规格:30*40*2mm方钢\n2.工作内容:安装", 1, "t", 100, None, None],
        ["学校甲", "铜像", "1.铜像尺寸及材质:0.7m不锈钢仿铜半身像\n2.基座:0.8m\n3.基础:1m×1m，埋深0.5m", 1, "组", 100, None, None],
        ["学校甲", "宣传牌", "1.名称:宣传牌\n2.工作内容:10mm厚PT板+15mmPT板", 1, "块", 100, None, None],
    ])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    items = preview.groups[0].items
    assert all(item.width is None and item.height is None for item in items)
    assert all(item.dimension_status in {"none", "review"} for item in items)


def test_school_list_import_marks_three_dimensional_items_for_review():
    content = _make_workbook([
        ["学校甲", "会议桌", "1.尺寸:2.4*1.2*0.75m\n2.成品市售", 1, "张", 100, None, None],
    ])

    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )

    item = preview.groups[0].items[0]
    assert item.dimension_status == "review"
    assert item.length == Decimal("2.4")
    assert item.width == Decimal("1.2")
    assert item.height == Decimal("0.75")
    assert "三维" in (item.dimension_reason or "")


@pytest.mark.asyncio
async def test_school_dimension_backfill_matches_existing_quote_and_only_updates_dimensions():
    content = _make_workbook([
        ["学校甲", "宣传牌", "1.尺寸:2.4*1.2m\n2.材质:10mm厚PT板", 1, "块", 100, None, None],
    ])
    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )
    target_item = SimpleNamespace(
        id=uuid4(),
        item_name="宣传牌",
        material_process="1.尺寸:2.4*1.2m\n2.材质:10mm厚PT板",
        quantity=Decimal("1"),
        unit="块",
        unit_price=Decimal("100"),
        sort_order=2,
        length=None,
        length_unit=None,
        width=None,
        width_unit=None,
        height=None,
        height_unit=None,
    )
    quote = SimpleNamespace(
        id=uuid4(),
        doc_no="Q-TEST",
        department="学校甲",
        customer_id=None,
        customer_name="客户甲",
        project_name="统一项目",
        status="draft",
        items=[target_item],
    )
    db = SimpleNamespace()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [quote])))
    db.flush = AsyncMock()

    report = await preview_school_quote_dimension_backfill(db, preview)
    assert report["valid"] is True
    assert report["change_count"] == 1
    assert report["conflict_count"] == 0

    committed = await commit_school_quote_dimension_backfill(db, preview)
    assert committed["change_count"] == 1
    assert target_item.width == Decimal("2.400")
    assert target_item.height == Decimal("1.200")
    assert target_item.width_unit == "m"
    assert target_item.height_unit == "m"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_school_dimension_backfill_does_not_overwrite_manual_dimensions():
    content = _make_workbook([
        ["学校甲", "宣传牌", "1.尺寸:2.4*1.2m", 1, "块", 100, None, None],
    ])
    preview = parse_school_quote_workbook(
        content,
        customer_name="客户甲",
        project_name="统一项目",
    )
    target_item = SimpleNamespace(
        id=uuid4(),
        item_name="宣传牌",
        material_process="1.尺寸:2.4*1.2m",
        quantity=Decimal("1"),
        unit="块",
        unit_price=Decimal("100"),
        sort_order=2,
        length=None,
        length_unit=None,
        width=Decimal("2.400"),
        width_unit="m",
        height=Decimal("1.100"),
        height_unit="m",
    )
    quote = SimpleNamespace(
        id=uuid4(), doc_no="Q-TEST", department="学校甲", customer_id=None,
        customer_name="客户甲", project_name="统一项目", status="draft", items=[target_item],
    )
    db = SimpleNamespace()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [quote])))
    db.flush = AsyncMock()

    report = await preview_school_quote_dimension_backfill(db, preview)
    assert report["valid"] is False
    assert report["change_count"] == 0
    assert report["conflict_count"] == 1
    assert target_item.height == Decimal("1.100")


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
