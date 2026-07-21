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
from app.schemas.framework_contract import (
    FrameworkContractProjectCreate,
    FrameworkContractProjectUpdate,
)
from app.schemas.common import success, success_paginated
from app.services.contract_service import ContractService
from app.services.framework_contract_service import FrameworkContractService
from app.services.operation_log_service import (
    log_operation,
    OBJ_CONTRACT,
    ACTION_CREATE,
    ACTION_UPDATE,
    ACTION_DELETE,
)

router = APIRouter(prefix="/framework-contracts", tags=["Framework Contracts"])


# ── 框架合同列表（委托 ContractService，ct = '框架合同'） ──

@router.get("/")
async def list_framework_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    customer_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ContractService(db)
    contracts, total = await service.list_contracts(
        page, page_size, status, keyword, customer_id,
        contract_type="框架合同",
    )
    return success_paginated(contracts, total, page, page_size)


# ── 可用资源（某客户下未关联到任何框架合同项目的订单/报价） ──

@router.get("/available-projects")
async def get_available_projects(
    customer_id: str,
    contract_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回该客户下未被任何框架合同项目关联的订单和报价"""
    from sqlalchemy import select, not_
    from app.models.order import Order as OrderModel
    from app.models.quote import Quote as QuoteModel
    from app.models.framework_contract import (
        FrameworkContractProjectOrder,
        FrameworkContractProjectQuote,
    )

    # 已被任何项目关联的订单 ID
    used_orders_sub = select(FrameworkContractProjectOrder.order_id)
    # 已被任何项目关联的报价 ID
    used_quotes_sub = select(FrameworkContractProjectQuote.quote_id)

    # 客户下未关联的订单
    orders_result = await db.execute(
        select(OrderModel)
        .where(
            OrderModel.deleted_at.is_(None),
            OrderModel.customer_id == UUID(customer_id),
            not_(OrderModel.id.in_(used_orders_sub)),
        )
        .order_by(OrderModel.created_at.desc())
        .limit(500)
    )
    orders = orders_result.scalars().all()

    # 客户下未关联的报价
    quotes_result = await db.execute(
        select(QuoteModel)
        .where(
            QuoteModel.deleted_at.is_(None),
            QuoteModel.customer_id == UUID(customer_id),
            QuoteModel.status != "converted",
            not_(QuoteModel.id.in_(used_quotes_sub)),
        )
        .order_by(QuoteModel.created_at.desc())
        .limit(500)
    )
    quotes = quotes_result.scalars().all()

    # 客户下已存在的 project_name 列表（用于项目名称下拉）
    from sqlalchemy import func as sa_func
    projects_result = await db.execute(
        select(sa_func.distinct(OrderModel.project_name))
        .where(
            OrderModel.deleted_at.is_(None),
            OrderModel.customer_id == UUID(customer_id),
            OrderModel.project_name.isnot(None),
            OrderModel.project_name != "",
        )
    )
    order_project_names = [row[0] for row in projects_result.all()]

    quotes_projects_result = await db.execute(
        select(sa_func.distinct(QuoteModel.project_name))
        .where(
            QuoteModel.deleted_at.is_(None),
            QuoteModel.customer_id == UUID(customer_id),
            QuoteModel.project_name.isnot(None),
            QuoteModel.project_name != "",
        )
    )
    quote_project_names = [row[0] for row in quotes_projects_result.all()]

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
        "project_names": sorted(list(set(order_project_names + quote_project_names))),
    })


# ── 框架合同项目 CRUD ──

@router.get("/{contract_id}/projects")
async def list_projects(
    contract_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FrameworkContractService(db)
    projects, total = await service.list_projects(UUID(contract_id), page, page_size)
    return success_paginated(projects, total, page, page_size)


@router.post("/{contract_id}/projects")
async def create_project(
    contract_id: str,
    data: FrameworkContractProjectCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = FrameworkContractService(db)
    payload = data.model_dump()
    payload["contract_id"] = contract_id
    project = await service.create_project(payload)
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, UUID(contract_id), "add_project",
                        ip_address=request.client.host if request.client else None,
                        after_data={"project_name": project["project_name"]})
    return success(project)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FrameworkContractService(db)
    project = await service.get_project(UUID(project_id))
    if not project:
        return {"code": 40401, "message": "项目不存在", "data": None}
    return success(project)


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    data: FrameworkContractProjectUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = FrameworkContractService(db)
    pid = UUID(project_id)
    before = await service.get_project(pid)
    project = await service.update_project(pid, data.model_dump(exclude_none=True))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, UUID(before["contract_id"]), "update_project",
                        ip_address=request.client.host if request.client else None,
                        before_data=before, after_data=project)
    return success(project)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = FrameworkContractService(db)
    pid = UUID(project_id)
    before = await service.get_project(pid)
    ok = await service.delete_project(pid)
    if not ok:
        return {"code": 40401, "message": "项目不存在", "data": None}
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_CONTRACT, UUID(before["contract_id"]) if before else UUID("00000000-0000-0000-0000-000000000000"),
                        "delete_project",
                        ip_address=request.client.host if request.client else None,
                        before_data=before)
    return success(None)


# ── 项目附件 ──

@router.post("/projects/{project_id}/upload")
async def upload_project_attachment(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FrameworkContractService(db)
    pid = UUID(project_id)
    project = await service.get_project(pid)
    if not project:
        return {"code": 40401, "message": "项目不存在", "data": None}

    upload_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, "framework-contract-projects")
    os.makedirs(upload_dir, exist_ok=True)
    if project.get("attachment_path"):
        old_path = os.path.join(settings.LOCAL_UPLOAD_DIR, project["attachment_path"])
        if os.path.isfile(old_path):
            os.remove(old_path)

    ts = str(int(time.time()))
    safe_name = f"{project_id}_{ts}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_name)
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    rel_path = f"framework-contract-projects/{safe_name}"
    updated = await service.update_attachment(pid, rel_path, file.filename)
    return success(updated)


@router.get("/projects/{project_id}/attachment")
async def download_project_attachment(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = FrameworkContractService(db)
    project = await service.get_project(UUID(project_id))
    if not project or not project.get("attachment_path"):
        return {"code": 40401, "message": "附件不存在", "data": None}

    file_path = os.path.join(settings.LOCAL_UPLOAD_DIR, project["attachment_path"])
    if not os.path.isfile(file_path):
        return {"code": 40401, "message": "附件文件不存在", "data": None}

    return FileResponse(file_path, filename=project.get("attachment_name") or "")


@router.delete("/projects/{project_id}/attachment")
async def delete_project_attachment(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FrameworkContractService(db)
    pid = UUID(project_id)
    project = await service.get_project(pid)
    if not project:
        return {"code": 40401, "message": "项目不存在", "data": None}

    if project.get("attachment_path"):
        file_path = os.path.join(settings.LOCAL_UPLOAD_DIR, project["attachment_path"])
        if os.path.isfile(file_path):
            os.remove(file_path)

    await service.update_attachment(pid, None, None)
    return success(None)
