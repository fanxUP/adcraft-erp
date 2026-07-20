import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_any_role
from app.models.user import User
from app.schemas.common import success, success_paginated, error
from app.services.acceptance_service import AcceptanceService

router = APIRouter(prefix="/acceptances", tags=["验收单"])

UPLOAD_DIR = "uploads/acceptances"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class AcceptanceCreate(BaseModel):
    order_id: str
    accepted_by: str | None = None
    our_acceptor_id: str | None = None
    remark: str | None = None
    items: list[dict] = []


class AcceptanceUpdate(BaseModel):
    accepted_by: str | None = None
    our_acceptor_id: str | None = None
    remark: str | None = None
    items: list[dict] | None = None


class StatusChange(BaseModel):
    to_status: str
    reason: str | None = None
    accepted_by: str | None = None


@router.get("/available-orders")
async def list_available_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return orders that don't have an acceptance yet."""
    service = AcceptanceService(db)
    items = await service.list_available_orders()
    return success(items)


@router.get("/")
async def list_acceptances(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    status: str = "",
    order_id: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AcceptanceService(db)
    items, total = await service.list_acceptances(
        page, page_size, keyword=keyword, status=status, order_id=order_id
    )
    return success_paginated(items, total, page, page_size)


@router.get("/{acceptance_id}")
async def get_acceptance(
    acceptance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AcceptanceService(db)
    try:
        data = await service.get_detail(uuid.UUID(acceptance_id))
        return success(data)
    except ValueError as e:
        return error(40001, str(e))


@router.post("/")
async def create_acceptance(
    body: AcceptanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = AcceptanceService(db)
    try:
        data = await service.create_acceptance(body.model_dump())
        return success(data)
    except ValueError as e:
        return error(40001, str(e))


@router.put("/{acceptance_id}")
async def update_acceptance(
    acceptance_id: str,
    body: AcceptanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = AcceptanceService(db)
    try:
        data = await service.update_acceptance(uuid.UUID(acceptance_id), body.model_dump(exclude_unset=True))
        return success(data)
    except ValueError as e:
        return error(40001, str(e))


@router.delete("/{acceptance_id}")
async def delete_acceptance(
    acceptance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = AcceptanceService(db)
    try:
        await service.delete_acceptance(uuid.UUID(acceptance_id))
        return success(None)
    except ValueError as e:
        return error(40001, str(e))


@router.post("/{acceptance_id}/change-status")
async def change_status(
    acceptance_id: str,
    body: StatusChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    service = AcceptanceService(db)
    try:
        data = await service.change_status(
            uuid.UUID(acceptance_id), body.to_status,
            reason=body.reason, accepted_by=body.accepted_by
        )
        return success(data)
    except ValueError as e:
        return error(40001, str(e))


@router.post("/{acceptance_id}/attachments")
async def upload_attachment(
    acceptance_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    from app.repositories.acceptance_repo import AcceptanceRepository

    repo = AcceptanceRepository(db)
    form = await repo.get_by_id(uuid.UUID(acceptance_id))
    if not form:
        return error(40001, "验收单不存在")

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    att = await repo.add_attachment(
        acceptance_id=uuid.UUID(acceptance_id),
        filename=file.filename,
        filepath=filepath,
        filesize=len(content),
        upload_by=current_user.id,
    )
    return success({
        "id": str(att.id),
        "filename": att.filename,
        "filepath": att.filepath,
        "filesize": att.filesize,
    })


@router.delete("/{acceptance_id}/attachments/{att_id}")
async def delete_attachment(
    acceptance_id: str,
    att_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role("admin", "sales")),
):
    from app.repositories.acceptance_repo import AcceptanceRepository

    repo = AcceptanceRepository(db)
    att = await repo.get_attachment_by_id(uuid.UUID(att_id))
    if not att or str(att.acceptance_id) != acceptance_id:
        return error(40001, "附件不存在")

    if os.path.exists(att.filepath):
        os.remove(att.filepath)

    await repo.delete_attachment(att)
    return success(None)
