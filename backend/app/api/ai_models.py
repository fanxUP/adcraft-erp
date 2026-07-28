"""API routes for AI Model management."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ai_model import AIModelCreate, AIModelUpdate
from app.schemas.common import success, success_paginated, error
from app.services.ai_model_service import AIModelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/models", tags=["AI Models"])


@router.get("/")
async def list_models(
    page: int = 1,
    page_size: int = 100,
    provider_id: str | None = None,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AIModelService(db)
    provider_uuid = UUID(provider_id) if provider_id else None
    items, total = await service.list_models(
        page=page, page_size=page_size, provider_id=provider_uuid, enabled_only=enabled_only
    )
    return success_paginated(items, total, page, page_size)


@router.get("/{model_id}")
async def get_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AIModelService(db)
    model = await service.get_model(model_id)
    if not model:
        return error(404, "模型不存在")
    return success(model)


@router.post("/")
async def create_model(
    data: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new AI model under a provider."""
    service = AIModelService(db)
    try:
        model = await service.create_model(data.model_dump(exclude_none=True))
        return success(model)
    except IntegrityError as e:
        await db.rollback()
        if "uq_ai_models" in str(e.orig):
            return error(409, f"模型代码 '{data.upstream_model_code}' 在该供应商下已存在")
        return error(500, "创建模型失败: 数据冲突")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create model")
        return error(500, f"创建模型失败: {str(e)}")


@router.patch("/{model_id}")
async def update_model(
    model_id: UUID,
    data: AIModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AIModelService(db)
    try:
        model = await service.update_model(model_id, data.model_dump(exclude_none=True))
        if not model:
            return error(404, "模型不存在")
        return success(model)
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update model")
        return error(500, f"更新模型失败: {str(e)}")


@router.delete("/{model_id}")
async def delete_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AIModelService(db)
    deleted = await service.delete_model(model_id)
    if not deleted:
        return error(404, "模型不存在")
    return success({"deleted": True})
