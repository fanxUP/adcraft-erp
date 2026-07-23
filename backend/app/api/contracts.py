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
    exclude_contract_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ContractService(db)
    contracts, total = await service.list_contracts(page, page_size, status, keyword, customer_id, contract_type, exclude_contract_type)
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
    customer_id: str | None = None,
    contract_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return orders and quotes not yet linked to any contract (including framework contract projects).
    If contract_id is provided (editing), also include resources already linked to that contract.
    If customer_id is provided, only return resources for that customer."""
    from sqlalchemy import select, not_
    from app.models.business_document import BusinessDocument
    from app.models.contract import ContractDocument
    from app.models.framework_contract import FrameworkContractProjectDocument

    # Documents already in any contract (exclude current if editing)
    used_sub = select(ContractDocument.document_id)
    if contract_id:
        used_sub = used_sub.where(ContractDocument.contract_id != UUID(contract_id))

    # Also exclude docs in framework contract projects
    fw_sub = select(FrameworkContractProjectDocument.document_id)

    # Single unified query
    q = select(BusinessDocument).where(
        BusinessDocument.deleted_at.is_(None),
        BusinessDocument.doc_type.in_(["order", "quote"]),
        not_(BusinessDocument.id.in_(used_sub)),
        not_(BusinessDocument.id.in_(fw_sub)),
    )
    # Exclude cancelled/converted quotes
    q = q.where(
        ~((BusinessDocument.doc_type == "quote") & BusinessDocument.status.in_(["converted", "cancelled"]))
    )
    if customer_id:
        q = q.where(BusinessDocument.customer_id == UUID(customer_id))
    result = await db.execute(q.order_by(BusinessDocument.created_at.desc()).limit(500))
    docs = result.scalars().all()

    from app.services.business_document_service import BusinessDocumentService

    # Split into orders/quotes for frontend compatibility
    orders_list, quotes_list = [], []
    for d in docs:
        item = BusinessDocumentService._to_ref(d)
        # available-resources 额外携带 customer_id
        item["customer_id"] = str(d.customer_id) if d.customer_id else None
        if d.doc_type == "order":
            orders_list.append(item)
        else:
            quotes_list.append(item)

    # Used project names
    from app.models.contract import Contract as ContractModel
    used_q = select(ContractModel.project_name).where(
        ContractModel.deleted_at.is_(None),
        ContractModel.project_name.isnot(None),
        ContractModel.project_name != "",
    )
    if contract_id:
        used_q = used_q.where(ContractModel.id != UUID(contract_id))
    if customer_id:
        used_q = used_q.where(ContractModel.customer_id == UUID(customer_id))
    used_result = await db.execute(used_q)
    used_project_names = list({row[0] for row in used_result.all()})

    return success({
        "orders": orders_list,
        "quotes": quotes_list,
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
