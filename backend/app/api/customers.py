import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.common import success, success_paginated
from app.services.customer_service import CustomerService
from app.services.operation_log_service import log_operation, OBJ_CUSTOMER, ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE
from app.utils.excel_import import ExcelImportResult, parse_excel, format_value

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=9999),
    keyword: str | None = None,
    customer_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CustomerService(db)
    customers, total = await service.list_customers(page, page_size, keyword, customer_type)
    return success_paginated(customers, total, page, page_size)


@router.post("/")
async def create_customer(
    data: CustomerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CustomerService(db)
    customer = await service.create_customer(data.model_dump())
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CUSTOMER, UUID(customer["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"name": customer["name"], "customer_no": customer["customer_no"]})
    return success(customer)


CUSTOMER_COLUMN_MAP = {
    "客户名称": "name",
    "客户类型": "customer_type",
    "等级": "level",
    "电话": "phone",
    "微信": "wechat",
    "地址": "address",
    "备注": "remark",
}
CUSTOMER_REQUIRED = ["客户名称"]
CUSTOMER_TYPE_VALUES = {"直客", "代理", "同行"}
CUSTOMER_LEVEL_VALUES = {"A", "B", "C"}


@router.post("/import")
async def import_customers(
    file: UploadFile = File(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch import customers from Excel file."""
    ip_addr = request.client.host if request and request.client else None
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return {"code": 40001, "message": "请上传 .xlsx 或 .xls 格式的 Excel 文件", "data": None}

    content = await file.read()
    rows, header_errors = parse_excel(content, CUSTOMER_REQUIRED, CUSTOMER_COLUMN_MAP)
    if header_errors:
        return {"code": 40002, "message": "文件格式错误", "data": {"errors": header_errors}}

    result = ExcelImportResult()
    result.total_rows = len(rows)
    service = CustomerService(db)

    for row in rows:
        try:
            name = format_value(row.get("name"))
            if not name:
                result.failed += 1
                result.errors.append({"row": row["_excel_row"], "message": "客户名称不能为空"})
                continue

            customer_type = format_value(row.get("customer_type"))
            if customer_type and customer_type not in CUSTOMER_TYPE_VALUES:
                result.failed += 1
                result.errors.append({"row": row["_excel_row"], "message": f"无效的客户类型: {customer_type}（可选: 直客/代理/同行）"})
                continue

            level = format_value(row.get("level"))
            if level and level not in CUSTOMER_LEVEL_VALUES:
                result.failed += 1
                result.errors.append({"row": row["_excel_row"], "message": f"无效的等级: {level}（可选: A/B/C）"})
                continue

            data = {
                "name": name,
                "customer_type": customer_type,
                "level": level,
                "phone": format_value(row.get("phone")),
                "wechat": format_value(row.get("wechat")),
                "address": format_value(row.get("address")),
                "remark": format_value(row.get("remark")),
            }
            customer = await service.create_customer(data)
            await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                                OBJ_CUSTOMER, UUID(customer["id"]), ACTION_CREATE,
                                ip_address=ip_addr,
                                after_data={"name": customer["name"], "customer_no": customer["customer_no"]})
            result.succeeded += 1
        except Exception as e:
            logger.exception("Customer import failed for row %s: %s", row.get("_excel_row", "?"), e)
            result.failed += 1
            result.errors.append({"row": row.get("_excel_row", "?"), "message": str(e)})

    return success(result.to_dict())


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CustomerService(db)
    customer = await service.get_customer(UUID(customer_id))
    if not customer:
        return {"code": 40401, "message": "客户不存在", "data": None}
    return success(customer)


@router.put("/{customer_id}")
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CustomerService(db)
    cid = UUID(customer_id)
    before = await service.get_customer(cid)
    customer = await service.update_customer(cid, data.model_dump(exclude_none=True))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CUSTOMER, cid, ACTION_UPDATE,
                        ip_address=request.client.host if request.client else None,
                        before_data=before, after_data=customer)
    return success(customer)


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = CustomerService(db)
    cid = UUID(customer_id)
    before = await service.get_customer(cid)
    ok = await service.delete_customer(cid)
    if not ok:
        return {"code": 40401, "message": "客户不存在", "data": None}
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CUSTOMER, cid, ACTION_DELETE,
                        ip_address=request.client.host if request.client else None,
                        before_data=before)
    return success(None)
