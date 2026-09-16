"""统一供应商主数据 API。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    PERM_SUPPLIER_CENTER_READ,
    PERM_SUPPLIER_CREATE,
    PERM_SUPPLIER_READ,
    PERM_SUPPLIER_UPDATE,
    require_all_permissions,
)
from app.models.user import User
from app.schemas.common import error, success, success_paginated
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.operation_log_service import (
    ACTION_CREATE,
    ACTION_UPDATE,
    OBJ_SUPPLIER,
    log_operation,
)
from app.services.supplier_service import SupplierService


router = APIRouter(prefix="/suppliers", tags=["Suppliers"])
_READ = require_all_permissions(PERM_SUPPLIER_CENTER_READ, PERM_SUPPLIER_READ)
_CREATE = require_all_permissions(PERM_SUPPLIER_CENTER_READ, PERM_SUPPLIER_CREATE)
_UPDATE = require_all_permissions(PERM_SUPPLIER_CENTER_READ, PERM_SUPPLIER_UPDATE)


@router.get("/")
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    supplier_type: str | None = None,
    is_active: bool | None = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_READ),
):
    try:
        rows, total = await SupplierService(db, viewer=current_user).list_suppliers(
            page,
            page_size,
            keyword=keyword,
            supplier_type=supplier_type,
            is_active=is_active,
        )
    except ValueError as exc:
        return error(40001, str(exc))
    return success_paginated(rows, total, page, page_size)


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_READ),
):
    supplier = await SupplierService(db, viewer=current_user).get_supplier(supplier_id)
    if supplier is None:
        return error(40401, "供应商不存在")
    return success(supplier)

@router.post("/")
async def create_supplier(
    data: SupplierCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_CREATE),
):
    try:
        supplier = await SupplierService(db, viewer=current_user).create_supplier(data.model_dump())
    except ValueError as exc:
        return error(40001, str(exc))
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        OBJ_SUPPLIER,
        UUID(supplier["id"]),
        ACTION_CREATE,
        ip_address=request.client.host if request.client else None,
        after_data={"vendor_no": supplier["vendor_no"], "name": supplier["name"]},
    )
    return success(supplier)


@router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: UUID,
    data: SupplierUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_UPDATE),
):
    try:
        supplier = await SupplierService(db, viewer=current_user).update_supplier(
            supplier_id,
            data.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        return error(40001, str(exc))
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        OBJ_SUPPLIER,
        supplier_id,
        ACTION_UPDATE,
        ip_address=request.client.host if request.client else None,
    )
    return success(supplier)


@router.post("/{supplier_id}/deactivate")
async def deactivate_supplier(
    supplier_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_UPDATE),
):
    try:
        supplier = await SupplierService(db, viewer=current_user).deactivate_supplier(supplier_id)
    except ValueError as exc:
        return error(40001, str(exc))
    await log_operation(
        db,
        current_user.id,
        current_user.real_name or current_user.username,
        OBJ_SUPPLIER,
        supplier_id,
        ACTION_UPDATE,
        ip_address=request.client.host if request.client else None,
        after_data={"is_active": False},
    )
    return success(supplier)
