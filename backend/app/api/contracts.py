import logging
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_any_role
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractUpdate, ContractStatusChange
from app.schemas.common import success, success_paginated
from app.services.contract_service import ContractService
from app.services.operation_log_service import (
    log_operation, OBJ_CONTRACT, ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE,
)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("/")
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    customer_id: str | None = None,
    contract_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ContractService(db)
    contracts, total = await service.list_contracts(page, page_size, status, keyword, customer_id, contract_type)
    return success_paginated(contracts, total, page, page_size)


@router.post("/")
async def create_contract(
    data: ContractCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = ContractService(db)
    contract = await service.create_contract(data.model_dump())
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, UUID(contract["id"]), ACTION_CREATE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"contract_no": contract["contract_no"], "project_name": contract["project_name"]})
    return success(contract)


@router.get("/available-resources")
async def get_available_resources(
    contract_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return orders and quotes not yet linked to any contract.
    If contract_id is provided (editing), also include resources already linked to that contract."""
    from sqlalchemy import select, not_
    from app.models.order import Order as OrderModel
    from app.models.quote import Quote as QuoteModel
    from app.models.contract import ContractOrder, ContractQuote

    # Build subquery: order_ids that are in any contract (excluding current one if editing)
    co_sub = select(ContractOrder.order_id)
    if contract_id:
        co_sub = co_sub.where(ContractOrder.contract_id != UUID(contract_id))

    # Available orders: not deleted AND not in any other contract
    orders_result = await db.execute(
        select(OrderModel)
        .where(
            OrderModel.deleted_at.is_(None),
            not_(OrderModel.id.in_(co_sub)),
        )
        .order_by(OrderModel.created_at.desc())
        .limit(500)
    )
    orders = orders_result.scalars().all()

    # Same for quotes
    cq_sub = select(ContractQuote.quote_id)
    if contract_id:
        cq_sub = cq_sub.where(ContractQuote.contract_id != UUID(contract_id))

    quotes_result = await db.execute(
        select(QuoteModel)
        .where(
            QuoteModel.deleted_at.is_(None),
            QuoteModel.status != "converted",
            not_(QuoteModel.id.in_(cq_sub)),
        )
        .order_by(QuoteModel.created_at.desc())
        .limit(500)
    )
    quotes = quotes_result.scalars().all()

    # Query project_names already used by other contracts
    from app.models.contract import Contract as ContractModel
    used_q = select(ContractModel.project_name).where(
        ContractModel.deleted_at.is_(None),
        ContractModel.project_name.isnot(None),
        ContractModel.project_name != "",
    )
    if contract_id:
        used_q = used_q.where(ContractModel.id != UUID(contract_id))
    used_result = await db.execute(used_q)
    used_project_names = list({row[0] for row in used_result.all()})

    return success({
        "orders": [
            {
                "id": str(o.id),
                "order_no": o.order_no,
                "project_name": o.project_name,
                "customer_id": str(o.customer_id) if o.customer_id else None,
                "customer_name": o.customer.name if o.customer else None,
            }
            for o in orders
        ],
        "quotes": [
            {
                "id": str(q.id),
                "quote_no": q.quote_no,
                "project_name": q.project_name,
                "customer_id": str(q.customer_id) if q.customer_id else None,
                "customer_name": q.customer_name,
            }
            for q in quotes
        ],
        "used_project_names": used_project_names,
    })


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ContractService(db)
    contract = await service.get_contract(UUID(contract_id))
    if not contract:
        return {"code": 40401, "message": "合同不存在", "data": None}
    return success(contract)


@router.put("/{contract_id}")
async def update_contract(
    contract_id: str,
    data: ContractUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = ContractService(db)
    cid = UUID(contract_id)
    before = await service.get_contract(cid)
    contract = await service.update_contract(cid, data.model_dump(exclude_none=True))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, cid, ACTION_UPDATE,
                        ip_address=request.client.host if request.client else None,
                        before_data=before, after_data=contract)
    return success(contract)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = ContractService(db)
    cid = UUID(contract_id)
    before = await service.get_contract(cid)
    ok = await service.delete_contract(cid)
    if not ok:
        return {"code": 40401, "message": "合同不存在", "data": None}
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, cid, ACTION_DELETE,
                        ip_address=request.client.host if request.client else None,
                        before_data=before)
    return success(None)


@router.post("/{contract_id}/status")
async def change_contract_status(
    contract_id: str,
    data: ContractStatusChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = ContractService(db)
    cid = UUID(contract_id)
    before = await service.get_contract(cid)
    contract = await service.change_status(cid, data.to_status, data.reason)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, cid, "change_status",
                        ip_address=request.client.host if request.client else None,
                        before_data=before, after_data=contract)
    return success(contract)


@router.post("/{contract_id}/upload")
async def upload_contract_attachment(
    contract_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ContractService(db)
    cid = UUID(contract_id)
    contract = await service.get_contract(cid)
    if not contract:
        return {"code": 40401, "message": "合同不存在", "data": None}

    upload_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, "contracts")
    os.makedirs(upload_dir, exist_ok=True)
    # Delete old file if exists
    if contract.get("attachment_path"):
        old_path = os.path.join(settings.LOCAL_UPLOAD_DIR, contract["attachment_path"])
        if os.path.isfile(old_path):
            os.remove(old_path)

    ts = str(int(time.time()))
    safe_name = f"{contract_id}_{ts}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_name)
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    rel_path = f"contracts/{safe_name}"
    updated = await service.update_attachment(cid, rel_path, file.filename)
    return success(updated)


@router.get("/{contract_id}/attachment")
async def download_contract_attachment(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ContractService(db)
    contract = await service.get_contract(UUID(contract_id))
    if not contract or not contract.get("attachment_path"):
        return {"code": 40401, "message": "附件不存在", "data": None}

    file_path = os.path.join(settings.LOCAL_UPLOAD_DIR, contract["attachment_path"])
    if not os.path.isfile(file_path):
        return {"code": 40401, "message": "附件文件不存在", "data": None}

    return FileResponse(file_path, filename=contract.get("attachment_name") or "")


@router.delete("/{contract_id}/attachment")
async def delete_contract_attachment(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ContractService(db)
    cid = UUID(contract_id)
    contract = await service.get_contract(cid)
    if not contract:
        return {"code": 40401, "message": "合同不存在", "data": None}

    if contract.get("attachment_path"):
        file_path = os.path.join(settings.LOCAL_UPLOAD_DIR, contract["attachment_path"])
        if os.path.isfile(file_path):
            os.remove(file_path)

    await service.update_attachment(cid, None, None)
    return success(None)
