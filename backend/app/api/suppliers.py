"""统一供应商主数据 API。"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import (
    PERM_SUPPLIER_CENTER_READ,
    user_has_permission,
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


def require_supplier_action(action):
    required = (PERM_SUPPLIER_CENTER_READ, f"supplier:{action}")
    legacy = ("outsource_center:read", f"outsource_vendor:{action}")

    async def dependency(current_user: User = Depends(get_current_user)):
        if any(all(user_has_permission(current_user, code) for code in group) for group in (required, legacy)):
            return current_user
        raise HTTPException(403, "权限不足：需要供应商或外协商管理权限")
    return dependency


_READ = require_supplier_action("read")
_CREATE = require_supplier_action("create")
_UPDATE = require_supplier_action("update")


@router.get("/")
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    supplier_type: str | None = None,
    is_active: bool | None = True,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_READ),
):
    try:
        rows, total = await SupplierService(db, viewer=current_user).list_suppliers(
            page,
            page_size,
            keyword=keyword,
            supplier_type=supplier_type,
            is_active=None if include_inactive else is_active,
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
    try:
        supplier = await SupplierService(db, viewer=current_user).get_supplier(supplier_id)
    except ValueError as exc:
        return error(40001, str(exc))
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
        supplier = await SupplierService(db, viewer=current_user).create_supplier(data.model_dump(exclude_unset=True))
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
