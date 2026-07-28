"""API routes for Prompt Center - template management, versioning, and testing."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ai_prompt import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptVersionCreate,
    PromptVersionUpdate,
    PromptTestRequest,
)
from app.schemas.common import success, success_paginated, error
from app.services.ai_prompt_service import AIPromptService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/prompts", tags=["AI Prompts"])

_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _get_service(db: AsyncSession) -> AIPromptService:
    return AIPromptService(db, tenant_id=UUID(_TENANT_ID))


# ════════════════════════════════════════════
# Template CRUD
# ════════════════════════════════════════════


@router.get("/templates")
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all prompt templates with pagination."""
    svc = _get_service(db)
    items, total = await svc.list_templates(page=page, page_size=page_size, category=category, search=search)
    return success_paginated(items, total, page, page_size)


@router.post("/templates")
async def create_template(
    data: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new prompt template."""
    svc = _get_service(db)
    try:
        result = await svc.create_template(
            data.model_dump(exclude_none=True),
            created_by=current_user.id,
        )
        return success(result)
    except IntegrityError as e:
        await db.rollback()
        if "uq_prompt_template_per_tenant" in str(e.orig):
            return error(409, f"模板代码 '{data.template_code}' 已存在")
        return error(500, "创建模板失败: 数据冲突")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create template")
        return error(500, f"创建模板失败: {str(e)}")


@router.get("/templates/{template_id}")
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get template details by ID."""
    svc = _get_service(db)
    tpl = await svc.get_template(template_id)
    if not tpl:
        return error(404, "模板不存在")
    return success(tpl)


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: UUID,
    data: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update prompt template configuration."""
    svc = _get_service(db)
    try:
        tpl = await svc.update_template(template_id, data.model_dump(exclude_none=True))
        if not tpl:
            return error(404, "模板不存在")
        return success(tpl)
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update template")
        return error(500, f"更新模板失败: {str(e)}")


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a prompt template and all its versions."""
    svc = _get_service(db)
    deleted = await svc.delete_template(template_id)
    if not deleted:
        return error(404, "模板不存在")
    return success({"deleted": True})


# ════════════════════════════════════════════
# Version Management
# ════════════════════════════════════════════


@router.get("/templates/{template_id}/versions")
async def list_versions(
    template_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all versions of a template."""
    svc = _get_service(db)
    items, total = await svc.list_versions(template_id, page=page, page_size=page_size)
    return success_paginated(items, total, page, page_size)


@router.post("/templates/{template_id}/versions")
async def create_version(
    template_id: UUID,
    data: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new version of a prompt template."""
    svc = _get_service(db)
    try:
        result = await svc.create_version(
            template_id,
            data.model_dump(exclude_none=True),
            created_by=current_user.id,
        )
        return success(result)
    except ValueError as e:
        return error(404, str(e))
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create version")
        return error(500, f"创建版本失败: {str(e)}")


@router.get("/templates/{template_id}/versions/{version_id}")
async def get_version(
    template_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific version of a template."""
    svc = _get_service(db)
    ver = await svc.get_version(version_id)
    if not ver:
        return error(404, "版本不存在")
    return success(ver)


@router.post("/templates/{template_id}/versions/{version_id}/activate")
async def activate_version(
    template_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate a specific version of a template."""
    svc = _get_service(db)
    try:
        ver = await svc.activate_version(template_id, version_id)
        if not ver:
            return error(404, "版本不存在")
        return success(ver)
    except ValueError as e:
        return error(404, str(e))
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to activate version")
        return error(500, f"激活版本失败: {str(e)}")


# ════════════════════════════════════════════
# Test Execution
# ════════════════════════════════════════════


@router.post("/templates/{template_id}/test")
async def test_prompt(
    template_id: UUID,
    data: PromptTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test a prompt template by resolving variables and executing via AI."""
    svc = _get_service(db)
    try:
        result = await svc.execute_test(
            template_id,
            data.model_dump(exclude_none=True),
            user_id=str(current_user.id) if current_user.id else None,
        )
        return success(result)
    except ValueError as e:
        return error(400, str(e))
    except Exception as e:
        logger.exception("Prompt test failed")
        return error(500, f"测试执行失败: {str(e)}")


# ════════════════════════════════════════════
# Execution Logs
# ════════════════════════════════════════════


@router.get("/execution-logs")
async def list_execution_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    template_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List AI prompt test execution logs."""
    svc = _get_service(db)
    items, total = await svc.list_execution_logs(
        page=page, page_size=page_size, template_id=template_id,
    )
    return success_paginated(items, total, page, page_size)
