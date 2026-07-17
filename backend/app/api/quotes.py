import logging
from datetime import date
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO
from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate, QuoteItemUpdate
from app.schemas.common import success, success_paginated
from app.services.quote_service import QuoteService
from app.utils.excel_import import ExcelImportResult, parse_excel, format_value, parse_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["Quotes"])


@router.get("/")
async def list_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=9999),
    status: str | None = None,
    customer_id: str | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    cid = UUID(customer_id) if customer_id else None
    quotes, total = await service.list_quotes(page, page_size, status, cid, keyword=keyword, date_from=date_from, date_to=date_to)
    return success_paginated(quotes, total, page, page_size)


@router.post("/")
async def create_quote(
    data: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.create_quote(data.model_dump())
    return success(quote)


# --- Column definitions for Excel import ---

QUOTE_COLUMN_MAP = {
    "客户名称": "customer_name",
    "项目名称": "project_name",
    "部门/科室": "department",
    "有效期": "valid_until",
    "税率": "tax_rate",
    "优惠金额": "discount_amount",
    "备注": "remark",
    "明细分组": "group_name",
    "项目名称(明细)": "item_name",
    "材质工艺": "material_process",
    "数量": "quantity",
    "单位": "unit",
    "单价": "unit_price",
    "长": "length",
    "长单位": "length_unit",
    "宽": "width",
    "宽单位": "width_unit",
    "高": "height",
    "高单位": "height_unit",
    "件数": "pieces",
    "加工费": "process_fee",
    "安装费": "installation_fee",
    "设计费": "design_fee",
    "运输费": "transport_fee",
    "其他费用": "other_fee",
    "面积开关": "use_area",
    "明细备注": "item_remark",
}
QUOTE_REQUIRED = ["客户名称", "项目名称", "项目名称(明细)", "数量"]
HEADER_LABELS = list(QUOTE_COLUMN_MAP.keys())


@router.get("/template")
async def download_quote_template():
    """Download Excel template for quote import."""
    wb = Workbook()
    ws = wb.active
    ws.title = "报价导入模版"

    ws.append(HEADER_LABELS)

    # Sample row 1 — item in 分项1 with full specs (面积开关=是)
    ws.append([
        "示例公司", "XX广告牌制作", "宣传部", "2026-12-31", "0.13", "",
        "", "分项1", "不锈钢烤漆字", "1.2mm不锈钢+烤漆",
        "2", "个", "350", "0.5", "m", "0.5", "m", "", "m", "1",
        "0", "50", "80", "0", "0", "是", "红色",
    ])
    # Sample row 2 — another item in same quote, different group (不计面积)
    ws.append([
        "示例公司", "XX广告牌制作", "", "", "", "",
        "", "分项2", "安装人工费", "",
        "1", "项", "2000", "", "", "", "", "", "", "1",
        "0", "0", "0", "0", "0", "", "",
    ])

    # Auto-width
    for col_idx, label in enumerate(HEADER_LABELS, start=1):
        col_letter = ws.cell(row=1, column=col_idx).column_letter if col_idx <= 26 else "ZZ"
        ws.column_dimensions[col_letter].width = max(14, len(label) * 2 + 2)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = "报价导入模版.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/import")
async def import_quotes(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch import quotes from Excel file.
    Rows with the same (客户名称, 项目名称) are grouped into one quote.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return {"code": 40001, "message": "请上传 .xlsx 或 .xls 格式的 Excel 文件", "data": None}

    content = await file.read()
    rows, header_errors = parse_excel(content, QUOTE_REQUIRED, QUOTE_COLUMN_MAP)
    if header_errors:
        return {"code": 40002, "message": "文件格式错误", "data": {"errors": header_errors}}

    result = ExcelImportResult()
    result.total_rows = len(rows)
    if not rows:
        return success(result.to_dict())

    service = QuoteService(db)

    # Group rows by (customer_name, project_name) — each group = one quote
    from collections import OrderedDict
    quote_groups: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()
    for row in rows:
        key = (row.get("customer_name") or "", row.get("project_name") or "")
        if key not in quote_groups:
            quote_groups[key] = []
        quote_groups[key].append(row)

    for (customer_name, project_name), item_rows in quote_groups.items():
        try:
            if not customer_name or not project_name:
                result.failed += len(item_rows)
                result.errors.append({"row": item_rows[0].get("_excel_row", "?"), "message": "客户名称和项目名称不能为空"})
                continue

            first = item_rows[0]
            valid_until_str = format_value(first.get("valid_until"))
            valid_until = None
            if valid_until_str:
                try:
                    valid_until = date.fromisoformat(valid_until_str)
                except ValueError:
                    result.errors.append({"row": first.get("_excel_row", "?"), "message": f"无效的日期格式: {valid_until_str}"})
                    continue

            quote_data = {
                "customer_name": customer_name,
                "project_name": project_name,
                "department": format_value(first.get("department")),
                "valid_until": valid_until,
                "tax_rate": parse_number(first.get("tax_rate")) or 0,
                "discount_amount": parse_number(first.get("discount_amount")) or 0,
                "remark": format_value(first.get("remark")),
                "items": [],
            }

            for item_row in item_rows:
                item_name = format_value(item_row.get("item_name"))
                if not item_name:
                    result.failed += 1
                    result.errors.append({"row": item_row.get("_excel_row", "?"), "message": "项目名称(明细)不能为空"})
                    continue

                item_data = {
                    "item_name": item_name,
                    "group_name": format_value(item_row.get("group_name")),
                    "material_process": format_value(item_row.get("material_process")),
                    "quantity": parse_number(item_row.get("quantity")) or 1,
                    "unit": format_value(item_row.get("unit")),
                    "unit_price": parse_number(item_row.get("unit_price")) or 0,
                    "length": parse_number(item_row.get("length")),
                    "length_unit": format_value(item_row.get("length_unit")) or "m",
                    "width": parse_number(item_row.get("width")),
                    "width_unit": format_value(item_row.get("width_unit")) or "m",
                    "height": parse_number(item_row.get("height")),
                    "height_unit": format_value(item_row.get("height_unit")) or "m",
                    "pieces": parse_number(item_row.get("pieces")) or 1,
                    "process_fee": parse_number(item_row.get("process_fee")) or 0,
                    "installation_fee": parse_number(item_row.get("installation_fee")) or 0,
                    "design_fee": parse_number(item_row.get("design_fee")) or 0,
                    "transport_fee": parse_number(item_row.get("transport_fee")) or 0,
                    "other_fee": parse_number(item_row.get("other_fee")) or 0,
                    "remark": format_value(item_row.get("item_remark")),
                }

                # 面积开关：如果填了值，手动控制；否则根据长宽自动判断
                area_raw = format_value(item_row.get("use_area"))
                if area_raw:
                    item_data["use_area"] = area_raw.lower() in ("是", "1", "y", "yes", "true")
                elif item_data["length"] and item_data["width"]:
                    item_data["use_area"] = True
                else:
                    item_data["use_area"] = False

                quote_data["items"].append(item_data)

            if not quote_data["items"]:
                result.errors.append({"row": first.get("_excel_row", "?"), "message": f"报价「{project_name}」没有有效的明细行"})
                result.failed += 1
                continue

            await service.create_quote(quote_data)
            result.succeeded += 1

        except Exception as e:
            logger.exception("Quote import failed for group %s: %s", (customer_name, project_name), e)
            for r in item_rows:
                result.failed += 1
                result.errors.append({"row": r.get("_excel_row", "?"), "message": str(e)})

    return success(result.to_dict())


@router.get("/{quote_id}")
async def get_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.get_quote(UUID(quote_id))
    if not quote:
        return {"code": 40401, "message": "报价单不存在", "data": None}
    return success(quote)


@router.put("/{quote_id}")
async def update_quote(
    quote_id: str,
    data: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.update_quote(UUID(quote_id), data.model_dump(exclude_unset=True))
    return success(quote)


@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = QuoteService(db)
    ok = await service.delete_quote(UUID(quote_id))
    if not ok:
        return {"code": 40401, "message": "报价单不存在", "data": None}
    return success(None)


@router.post("/{quote_id}/items")
async def add_quote_item(
    quote_id: str,
    data: QuoteItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.repo.create_item(UUID(quote_id), data.model_dump())
    await service.calculate_quote(UUID(quote_id))
    return success(service._quote_to_detail(await service.repo.get_by_id(UUID(quote_id))))


@router.put("/{quote_id}/items/{item_id}")
async def update_quote_item(
    quote_id: str,
    item_id: str,
    data: QuoteItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    item = await service.repo.get_item(UUID(item_id))
    if not item:
        return {"code": 40401, "message": "明细不存在", "data": None}
    await service.repo.update_item(item, data.model_dump(exclude_none=True))
    await service.calculate_quote(UUID(quote_id))
    return success(service._quote_to_detail(await service.repo.get_by_id(UUID(quote_id))))


@router.delete("/{quote_id}/items/{item_id}")
async def delete_quote_item(
    quote_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    item = await service.repo.get_item(UUID(item_id))
    if not item:
        return {"code": 40401, "message": "明细不存在", "data": None}
    await service.repo.delete_item(item)
    await service.calculate_quote(UUID(quote_id))
    return success(service._quote_to_detail(await service.repo.get_by_id(UUID(quote_id))))

@router.post("/{quote_id}/confirm")
async def confirm_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    quote = await service.confirm_quote(UUID(quote_id))
    return success(quote)


@router.post("/{quote_id}/revert-to-draft")
async def revert_quote_to_draft(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    try:
        quote = await service.revert_to_draft(UUID(quote_id))
        return success(quote)
    except ValueError as e:
        return error(40001, str(e))


@router.post("/{quote_id}/convert-to-order")
async def convert_quote_to_order(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = QuoteService(db)
    order = await service.convert_to_order(UUID(quote_id), current_user.id)
    return success(order)
