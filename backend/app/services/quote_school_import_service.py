"""学校清单报价导入：清洗、计量识别、预览和批量写入准备。"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_document import BusinessDocument
from app.models.customer import Customer
from app.services.business_document_service import BusinessDocumentService


MONEY_QUANTUM = Decimal("0.01")
AREA_QUANTUM = Decimal("0.01")
PREVIEW_VERSION = "school-list-v1"
REQUIRED_HEADERS = (
    "部门/科室",
    "项目内容",
    "产品/材质/工艺",
    "数量",
    "单位",
    "单价",
)


class SchoolQuoteImportFormatError(ValueError):
    """清单表头或导入参数不符合学校清单模式。"""


def _clean_scalar(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").replace("\u3000", " ")
    return " ".join(text.replace("\t", " ").split()).strip()


def _clean_detail_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    return text.strip()


def _parse_decimal(value: Any, *, row: int, field_name: str) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name}不是有效数字") from exc


def _normalize_unit(unit: str) -> tuple[str, str]:
    """Return (display unit, measure kind)."""
    normalized = unit.strip().lower().replace(" ", "")
    normalized = normalized.replace("²", "2").replace("³", "3")
    if normalized in {"m2", "㎡", "平方米", "平米"}:
        return "㎡", "area"
    if normalized in {"m3", "立方米", "立方"}:
        return unit, "volume"
    if normalized in {"m", "米"}:
        return unit, "length"
    if normalized in {"t", "吨"}:
        return unit, "weight"
    return unit, "quantity"


def _preview_id(file_bytes: bytes, customer_name: str, project_name: str) -> str:
    source_hash = sha256(file_bytes).hexdigest()
    identity = f"{PREVIEW_VERSION}:{source_hash}:{customer_name}:{project_name}"
    return sha256(identity.encode("utf-8")).hexdigest()


@dataclass
class SchoolQuoteImportItem:
    row_number: int
    item_name: str
    material_process: str
    quantity: Decimal
    source_unit: str
    unit: str
    measure_kind: str
    quantity_mode: str
    unit_price: Decimal
    remark: str | None
    subtotal_amount: Decimal

    def to_quote_item(self) -> dict[str, Any]:
        # Excel 的 m2 是已经给出的显式面积数量，不是宽×高几何面积。
        return {
            "item_name": self.item_name,
            "material_process": self.material_process or None,
            "quantity": self.quantity,
            "unit": self.unit,
            "quantity_mode": self.quantity_mode,
            "use_area": False,
            "pieces": Decimal("1"),
            "unit_price": self.unit_price,
            "other_fee": Decimal("0"),
            "remark": self.remark,
            "sort_order": self.row_number,
        }

    def to_preview_dict(self) -> dict[str, Any]:
        return {
            "row": self.row_number,
            "item_name": self.item_name,
            "quantity": float(self.quantity),
            "source_unit": self.source_unit,
            "unit": self.unit,
            "measure_kind": self.measure_kind,
            "quantity_mode": self.quantity_mode,
            "unit_price": float(self.unit_price),
            "subtotal_amount": float(self.subtotal_amount),
            "remark": self.remark,
        }


@dataclass
class SchoolQuoteImportGroup:
    department: str
    items: list[SchoolQuoteImportItem] = field(default_factory=list)

    @property
    def subtotal_amount(self) -> Decimal:
        return sum((item.subtotal_amount for item in self.items), Decimal("0")).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

    def to_preview_dict(self) -> dict[str, Any]:
        unit_counts: dict[str, int] = {}
        for item in self.items:
            unit_counts[item.unit] = unit_counts.get(item.unit, 0) + 1
        return {
            "department": self.department,
            "item_count": len(self.items),
            "area_item_count": sum(item.measure_kind == "area" for item in self.items),
            "subtotal_amount": float(self.subtotal_amount),
            "unit_counts": unit_counts,
            "items": [item.to_preview_dict() for item in self.items],
        }


@dataclass
class SchoolQuoteImportPreview:
    preview_id: str
    source_sha256: str
    customer_name: str
    project_name: str
    groups: list[SchoolQuoteImportGroup]
    skipped_rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def school_count(self) -> int:
        return len(self.groups)

    @property
    def item_count(self) -> int:
        return sum(len(group.items) for group in self.groups)

    @property
    def total_amount(self) -> Decimal:
        return sum((group.subtotal_amount for group in self.groups), Decimal("0")).quantize(
            MONEY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

    @property
    def valid(self) -> bool:
        return not self.errors and bool(self.groups)

    def to_response(self) -> dict[str, Any]:
        return {
            "preview_id": self.preview_id,
            "source_sha256": self.source_sha256,
            "customer_name": self.customer_name,
            "project_name": self.project_name,
            "valid": self.valid,
            "school_count": self.school_count,
            "item_count": self.item_count,
            "total_amount": float(self.total_amount),
            "skipped_rows": self.skipped_rows,
            "errors": self.errors,
            "warnings": self.warnings,
            "schools": [group.to_preview_dict() for group in self.groups],
        }


def _merged_column_values(ws, column_index: int) -> dict[int, str]:
    values: dict[int, str] = {}
    for merged in ws.merged_cells.ranges:
        if merged.min_col > column_index or merged.max_col < column_index:
            continue
        value = _clean_detail_text(ws.cell(merged.min_row, column_index).value)
        if not value:
            continue
        for row_number in range(merged.min_row, merged.max_row + 1):
            values[row_number] = value
    return values


def parse_school_quote_workbook(
    file_bytes: bytes,
    *,
    customer_name: str,
    project_name: str,
) -> SchoolQuoteImportPreview:
    customer_name = _clean_scalar(customer_name)
    project_name = _clean_scalar(project_name)
    if not customer_name:
        raise SchoolQuoteImportFormatError("客户名称不能为空")
    if not project_name:
        raise SchoolQuoteImportFormatError("项目名称不能为空")

    try:
        workbook = load_workbook(BytesIO(file_bytes), data_only=True, read_only=False)
    except Exception as exc:
        raise SchoolQuoteImportFormatError("无法读取 Excel 文件") from exc

    try:
        worksheet = workbook.active
        if worksheet is None:
            raise SchoolQuoteImportFormatError("Excel 文件为空")
        headers = [_clean_scalar(cell.value) for cell in worksheet[1]]
        header_index = {header: index + 1 for index, header in enumerate(headers) if header}
        missing = [header for header in REQUIRED_HEADERS if header not in header_index]
        if missing:
            raise SchoolQuoteImportFormatError(f"缺少必填列: {', '.join(missing)}")

        remark_column = header_index.get("备注")
        merged_remarks = _merged_column_values(worksheet, remark_column) if remark_column else {}
        subtotal_column = header_index.get("小计")
        groups: OrderedDict[str, SchoolQuoteImportGroup] = OrderedDict()
        skipped_rows: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        for row_number in range(2, worksheet.max_row + 1):
            def cell(header: str) -> Any:
                return worksheet.cell(row_number, header_index[header]).value

            department = _clean_scalar(cell("部门/科室"))
            item_name = _clean_scalar(cell("项目内容"))
            if not department and not item_name and all(
                worksheet.cell(row_number, column).value is None
                for column in range(1, worksheet.max_column + 1)
            ):
                skipped_rows.append({"row": row_number, "reason": "空行"})
                continue
            if item_name == "合计" and not department:
                skipped_rows.append({"row": row_number, "reason": "汇总行"})
                continue

            row_errors: list[str] = []
            if not department:
                row_errors.append("部门/科室不能为空")
            if not item_name:
                row_errors.append("项目内容不能为空")
            raw_unit = _clean_scalar(cell("单位"))
            if not raw_unit:
                row_errors.append("单位不能为空")

            try:
                quantity = _parse_decimal(cell("数量"), row=row_number, field_name="数量")
            except ValueError as exc:
                quantity = None
                row_errors.append(str(exc))
            if quantity is None:
                row_errors.append("数量不能为空")
            elif quantity <= 0:
                row_errors.append("数量必须大于 0")

            try:
                unit_price = _parse_decimal(cell("单价"), row=row_number, field_name="单价")
            except ValueError as exc:
                unit_price = None
                row_errors.append(str(exc))
            if unit_price is None:
                row_errors.append("单价不能为空")
            elif unit_price < 0:
                row_errors.append("单价不能为负数")

            if row_errors:
                errors.append({"row": row_number, "message": "；".join(dict.fromkeys(row_errors))})
                continue

            display_unit, measure_kind = _normalize_unit(raw_unit)
            quantity_mode = "area" if measure_kind == "area" else "piece"
            subtotal_amount = (quantity * unit_price).quantize(
                MONEY_QUANTUM,
                rounding=ROUND_HALF_UP,
            )
            if subtotal_column:
                try:
                    source_subtotal = _parse_decimal(
                        worksheet.cell(row_number, subtotal_column).value,
                        row=row_number,
                        field_name="小计",
                    )
                except ValueError as exc:
                    warnings.append({"row": row_number, "message": str(exc)})
                else:
                    if source_subtotal is not None:
                        source_subtotal = source_subtotal.quantize(
                            MONEY_QUANTUM,
                            rounding=ROUND_HALF_UP,
                        )
                        if source_subtotal != subtotal_amount:
                            warnings.append({
                                "row": row_number,
                                "message": f"原始小计 {source_subtotal} 与数量×单价 {subtotal_amount} 不一致，已按数量×单价重算",
                            })

            remark = _clean_detail_text(cell("备注")) if remark_column else ""
            if not remark and row_number in merged_remarks:
                remark = merged_remarks[row_number]
            item = SchoolQuoteImportItem(
                row_number=row_number,
                item_name=item_name,
                material_process=_clean_detail_text(cell("产品/材质/工艺")),
                quantity=quantity,
                source_unit=raw_unit,
                unit=display_unit,
                measure_kind=measure_kind,
                quantity_mode=quantity_mode,
                unit_price=unit_price,
                remark=remark or None,
                subtotal_amount=subtotal_amount,
            )
            groups.setdefault(department, SchoolQuoteImportGroup(department=department)).items.append(item)

        if not groups and not errors:
            errors.append({"row": 0, "message": "未找到有效学校明细"})

        source_sha256 = sha256(file_bytes).hexdigest()
        return SchoolQuoteImportPreview(
            preview_id=_preview_id(file_bytes, customer_name, project_name),
            source_sha256=source_sha256,
            customer_name=customer_name,
            project_name=project_name,
            groups=list(groups.values()),
            skipped_rows=skipped_rows,
            errors=errors,
            warnings=warnings,
        )
    finally:
        workbook.close()


async def resolve_customer_id(db: AsyncSession, customer_name: str):
    result = await db.execute(
        select(Customer.id)
        .where(Customer.name == customer_name, Customer.deleted_at.is_(None))
        .order_by(Customer.created_at.asc())
    )
    customer_ids = list(result.scalars().all())
    if len(customer_ids) > 1:
        raise ValueError("客户名称匹配到多个客户档案，请先合并客户档案后再导入")
    return customer_ids[0] if customer_ids else None


async def find_existing_school_quotes(
    db: AsyncSession,
    *,
    customer_name: str,
    customer_id,
    project_name: str,
    departments: list[str],
) -> list[dict[str, Any]]:
    customer_match = BusinessDocument.customer_name == customer_name
    if customer_id:
        customer_match = or_(
            BusinessDocument.customer_id == customer_id,
            BusinessDocument.customer_name == customer_name,
        )
    result = await db.execute(
        select(BusinessDocument)
        .where(
            BusinessDocument.doc_type == "quote",
            BusinessDocument.deleted_at.is_(None),
            BusinessDocument.project_name == project_name,
            BusinessDocument.department.in_(departments),
            customer_match,
        )
        .order_by(BusinessDocument.department, BusinessDocument.created_at),
    )
    return [
        {
            "id": str(quote.id),
            "quote_no": quote.doc_no,
            "department": quote.department,
            "total_amount": float(quote.total_amount or 0),
        }
        for quote in result.scalars().all()
    ]


async def commit_school_quote_preview(
    db: AsyncSession,
    preview: SchoolQuoteImportPreview,
    *,
    customer_id=None,
) -> list[dict[str, Any]]:
    if not preview.valid:
        raise ValueError("清单预览存在错误，不能提交")
    service = BusinessDocumentService(db, doc_type="quote")
    created: list[dict[str, Any]] = []
    for group in preview.groups:
        quote_data: dict[str, Any] = {
            "customer_id": str(customer_id) if customer_id else None,
            "customer_name": None if customer_id else preview.customer_name,
            "project_name": preview.project_name,
            "department": group.department,
            "discount_amount": Decimal("0"),
            "tax_rate": Decimal("0"),
            "items": [item.to_quote_item() for item in group.items],
        }
        quote = await service.create(quote_data)
        created.append({
            "id": str(quote["id"]),
            "quote_no": quote["quote_no"],
            "department": group.department,
            "item_count": len(group.items),
            "total_amount": float(quote["total_amount"]),
        })
    return created
