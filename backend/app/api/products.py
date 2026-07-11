import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.services.number_generator import generate_supplier_no
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.product import (
    ProductCategoryCreate, ProductCreate, ProductUpdate,
    MaterialCreate, MaterialUpdate,
    ProcessCreate, ProcessUpdate,
    SupplierCreate, SupplierUpdate,
)
from app.schemas.common import success, success_paginated
from app.services.product_service import ProductService
from app.utils.excel_import import ExcelImportResult, parse_excel, format_value, parse_number

router = APIRouter(prefix="/products", tags=["Products"])
cat_router = APIRouter(prefix="/product-categories", tags=["Product Categories"])
mat_router = APIRouter(prefix="/materials", tags=["Materials"])
proc_router = APIRouter(prefix="/processes", tags=["Processes"])
supplier_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


# Product Categories
@cat_router.get("/")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    cats = await service.list_categories()
    return success(cats)


@cat_router.post("/")
async def create_category(
    data: ProductCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    cat = await service.create_category(data.model_dump(exclude_none=True))
    return success(cat)


@cat_router.delete("/{cat_id}")
async def delete_category(
    cat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = ProductService(db)
    ok = await service.delete_category(UUID(cat_id))
    if not ok:
        return {"code": 40401, "message": "分类不存在", "data": None}
    return success(None)


# Products
@router.get("/")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    category_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    cid = UUID(category_id) if category_id else None
    products, total = await service.list_products(page, page_size, keyword, cid)
    return success_paginated(products, total, page, page_size)


@router.post("/")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    product = await service.create_product(data.model_dump())
    return success(product)


PRODUCT_COLUMN_MAP = {
    "产品名称": "name",
    "单位": "unit",
    "计价方式": "pricing_method",
    "默认价格": "default_price",
    "最低收费": "min_charge",
    "备注": "remark",
}
PRODUCT_REQUIRED = ["产品名称"]


@router.post("/import")
async def import_products(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch import products from Excel file."""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return {"code": 40001, "message": "请上传 .xlsx 或 .xls 格式的 Excel 文件", "data": None}

    content = await file.read()
    rows, header_errors = parse_excel(content, PRODUCT_REQUIRED, PRODUCT_COLUMN_MAP)
    if header_errors:
        return {"code": 40002, "message": "文件格式错误", "data": {"errors": header_errors}}

    result = ExcelImportResult()
    result.total_rows = len(rows)
    service = ProductService(db)

    for row in rows:
        try:
            name = format_value(row.get("name"))
            if not name:
                result.failed += 1
                result.errors.append({"row": row["_excel_row"], "message": "产品名称不能为空"})
                continue

            unit = format_value(row.get("unit")) or "项"
            pricing_method = format_value(row.get("pricing_method")) or "quantity"
            if pricing_method not in ("area", "quantity", "length", "word_count"):
                result.failed += 1
                result.errors.append({"row": row["_excel_row"], "message": f"无效的计价方式: {pricing_method}（可选: area/quantity/length/word_count）"})
                continue

            data = {
                "name": name,
                "unit": unit,
                "pricing_method": pricing_method,
                "default_price": parse_number(row.get("default_price")),
                "min_charge": parse_number(row.get("min_charge")),
                "remark": format_value(row.get("remark")),
            }
            await service.create_product(data)
            result.succeeded += 1
        except Exception as e:
            logger.exception("Product import failed for row %s: %s", row.get("_excel_row", "?"), e)
            result.failed += 1
            result.errors.append({"row": row.get("_excel_row", "?"), "message": str(e)})

    return success(result.to_dict())


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    product = await service.get_product(UUID(product_id))
    if not product:
        return {"code": 40401, "message": "产品不存在", "data": None}
    return success(product)


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    product = await service.update_product(UUID(product_id), data.model_dump(exclude_none=True))
    return success(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = ProductService(db)
    ok = await service.delete_product(UUID(product_id))
    if not ok:
        return {"code": 40401, "message": "产品不存在", "data": None}
    return success(None)


# Materials
@mat_router.get("/")
async def list_materials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    materials, total = await service.list_materials(page, page_size, keyword)
    return success_paginated(materials, total, page, page_size)


@mat_router.post("/")
async def create_material(
    data: MaterialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    material = await service.create_material(data.model_dump())
    return success(material)


MATERIAL_COLUMN_MAP = {
    "材质名称": "name",
    "规格": "spec",
    "单位": "unit",
    "采购价": "purchase_price",
    "销售价": "sale_price",
    "损耗率": "loss_rate",
    "安全库存": "safe_stock",
    "备注": "remark",
}
MATERIAL_REQUIRED = ["材质名称"]


@mat_router.post("/import")
async def import_materials(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch import materials from Excel file."""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return {"code": 40001, "message": "请上传 .xlsx 或 .xls 格式的 Excel 文件", "data": None}

    content = await file.read()
    rows, header_errors = parse_excel(content, MATERIAL_REQUIRED, MATERIAL_COLUMN_MAP)
    if header_errors:
        return {"code": 40002, "message": "文件格式错误", "data": {"errors": header_errors}}

    result = ExcelImportResult()
    result.total_rows = len(rows)
    service = ProductService(db)

    for row in rows:
        try:
            name = format_value(row.get("name"))
            if not name:
                result.failed += 1
                result.errors.append({"row": row["_excel_row"], "message": "材质名称不能为空"})
                continue

            data = {
                "name": name,
                "spec": format_value(row.get("spec")),
                "unit": format_value(row.get("unit")) or "张",
                "purchase_price": parse_number(row.get("purchase_price")),
                "sale_price": parse_number(row.get("sale_price")),
                "loss_rate": parse_number(row.get("loss_rate")),
                "safe_stock": parse_number(row.get("safe_stock")),
                "remark": format_value(row.get("remark")),
            }
            await service.create_material(data)
            result.succeeded += 1
        except Exception as e:
            logger.exception("Material import failed for row %s: %s", row.get("_excel_row", "?"), e)
            result.failed += 1
            result.errors.append({"row": row.get("_excel_row", "?"), "message": str(e)})

    return success(result.to_dict())


@mat_router.get("/{material_id}")
async def get_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    material = await service.get_material(UUID(material_id))
    if not material:
        return {"code": 40401, "message": "材质不存在", "data": None}
    return success(material)


@mat_router.put("/{material_id}")
async def update_material(
    material_id: str,
    data: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    material = await service.update_material(UUID(material_id), data.model_dump(exclude_none=True))
    return success(material)


@mat_router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = ProductService(db)
    ok = await service.delete_material(UUID(material_id))
    if not ok:
        return {"code": 40401, "message": "材质不存在", "data": None}
    return success(None)


# Processes
@proc_router.get("/")
async def list_processes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    processes, total = await service.list_processes(page, page_size, keyword)
    return success_paginated(processes, total, page, page_size)


@proc_router.post("/")
async def create_process(
    data: ProcessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    process = await service.create_process(data.model_dump())
    return success(process)


@proc_router.get("/{process_id}")
async def get_process(
    process_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    process = await service.get_process(UUID(process_id))
    if not process:
        return {"code": 40401, "message": "工艺不存在", "data": None}
    return success(process)


@proc_router.put("/{process_id}")
async def update_process(
    process_id: str,
    data: ProcessUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    process = await service.update_process(UUID(process_id), data.model_dump(exclude_none=True))
    return success(process)


@proc_router.delete("/{process_id}")
async def delete_process(
    process_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = ProductService(db)
    ok = await service.delete_process(UUID(process_id))
    if not ok:
        return {"code": 40401, "message": "工艺不存在", "data": None}
    return success(None)


# Suppliers
@supplier_router.get("/")
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    suppliers, total = await service.list_suppliers(page, page_size, keyword)
    return success_paginated(suppliers, total, page, page_size)


@supplier_router.post("/")
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    payload = data.model_dump()
    payload["supplier_no"] = await generate_supplier_no(db)
    supplier = await service.create_supplier(payload)
    return success(supplier)


@supplier_router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    supplier = await service.get_supplier(UUID(supplier_id))
    if not supplier:
        return {"code": 40401, "message": "供应商不存在", "data": None}
    return success(supplier)


@supplier_router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductService(db)
    supplier = await service.update_supplier(UUID(supplier_id), data.model_dump(exclude_none=True))
    return success(supplier)


@supplier_router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = ProductService(db)
    ok = await service.delete_supplier(UUID(supplier_id))
    if not ok:
        return {"code": 40401, "message": "供应商不存在", "data": None}
    return success(None)
