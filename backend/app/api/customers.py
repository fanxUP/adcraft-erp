from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.common import success, success_paginated
from app.services.customer_service import CustomerService
from app.services.operation_log_service import log_operation, OBJ_CUSTOMER, ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    current_user: User = Depends(get_current_user),
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
