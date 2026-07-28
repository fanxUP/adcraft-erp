"""API routes for AI Provider management - the core of the Model Center."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.providers.base import ModelConfig, ProviderConfig, TestConfig
from app.ai.gateway.providers.openai_chat import OpenAICompatibleAdapter
from app.ai.gateway.security.ssrf_guard import validate_url
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate
from app.schemas.common import success, success_paginated, error
from app.services.ai_provider_service import AIProviderService
from app.services.ai_model_service import AIModelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/providers", tags=["AI Providers"])


@router.get("/")
async def list_providers(
    page: int = 1,
    page_size: int = 50,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all AI providers with pagination."""
    service = AIProviderService(db)
    items, total = await service.list_providers(
        page=page, page_size=page_size, enabled_only=enabled_only
    )
    return success_paginated(items, total, page, page_size)


@router.post("/")
async def create_provider(
    data: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new AI provider (model service supplier)."""
    service = AIProviderService(db)
    try:
        provider = await service.create_provider(data.model_dump(exclude_none=True))
        return success(provider)
    except IntegrityError as e:
        await db.rollback()
        if "uq_ai_providers" in str(e.orig):
            return error(409, f"供应商代码 '{data.provider_code}' 已存在")
        return error(500, "创建供应商失败: 数据冲突")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create provider")
        return error(500, f"创建供应商失败: {str(e)}")


@router.get("/{provider_id}")
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get provider details by ID."""
    service = AIProviderService(db)
    provider = await service.get_provider(provider_id)
    if not provider:
        return error(404, "供应商不存在")
    return success(provider)


@router.patch("/{provider_id}")
async def update_provider(
    provider_id: UUID,
    data: AIProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update provider configuration."""
    service = AIProviderService(db)
    try:
        provider = await service.update_provider(provider_id, data.model_dump(exclude_none=True))
        if not provider:
            return error(404, "供应商不存在")
        return success(provider)
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update provider")
        return error(500, f"更新供应商失败: {str(e)}")


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a provider and all its models."""
    service = AIProviderService(db)
    deleted = await service.delete_provider(provider_id)
    if not deleted:
        return error(404, "供应商不存在")
    return success({"deleted": True})


@router.post("/{provider_id}/duplicate")
async def duplicate_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    new_code: str = "",
    new_name: str = "",
):
    """Duplicate a provider configuration (API key not copied)."""
    if not new_code or not new_name:
        return error(400, "请提供新供应商代码和名称")
    service = AIProviderService(db)
    provider = await service.duplicate_provider(provider_id, new_code, new_name)
    if not provider:
        return error(404, "原供应商不存在")
    return success(provider)


@router.post("/{provider_id}/enable")
async def enable_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enable a provider."""
    service = AIProviderService(db)
    provider = await service.update_provider(provider_id, {"enabled": True})
    if not provider:
        return error(404, "供应商不存在")
    return success(provider)


@router.post("/{provider_id}/disable")
async def disable_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disable a provider."""
    service = AIProviderService(db)
    provider = await service.update_provider(provider_id, {"enabled": False})
    if not provider:
        return error(404, "供应商不存在")
    return success(provider)


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    test_type: str = "connection",
    model_code: str = "",
):
    """Test provider connectivity using a specific model."""
    provider_service = AIProviderService(db)
    provider = await provider_service.get_provider(provider_id)
    if not provider:
        return error(404, "供应商不存在")

    api_key = await provider_service.get_api_key(provider_id)
    if not api_key:
        return error(400, "未配置API密钥，请先设置")

    config = ProviderConfig(
        base_url=provider.get("base_url", ""),
        full_url_mode=provider.get("full_url_mode", False),
        endpoint_url=provider.get("endpoint_url"),
        auth_header=provider.get("auth_header", "Authorization"),
        auth_prefix=provider.get("auth_prefix", "Bearer"),
        api_key=api_key,
        custom_headers=provider.get("custom_headers_json", {}),
        timeout_seconds=provider.get("timeout_seconds", 60),
        retry_count=provider.get("retry_count", 2),
        tls_verify=provider.get("tls_verify", True),
    )

    target = config.endpoint_url if config.full_url_mode else config.base_url
    if target:
        try:
            validate_url(target)
        except Exception as e:
            return error(400, f"URL安全检查未通过: {str(e)}")

    model_svc = AIModelService(db)
    models, _ = await model_svc.list_models(page=1, page_size=50, provider_id=provider_id)
    target_model = None
    if model_code:
        for m in models:
            if m.get("upstream_model_code") == model_code:
                target_model = m
                break
    if not target_model and models:
        target_model = models[0]

    if not target_model:
        return error(400, "请在供应商下至少添加一个模型才能测试")

    model_config = ModelConfig(
        upstream_model_code=target_model["upstream_model_code"],
        max_output_tokens=target_model.get("max_output_tokens"),
        supports_streaming=target_model.get("supports_streaming", False),
        supports_tools=target_model.get("supports_tools", False),
        supports_json_schema=target_model.get("supports_json_schema", False),
        supports_vision=target_model.get("supports_vision", False),
    )

    try:
        adapter = OpenAICompatibleAdapter()
        test_cfg = TestConfig(
            test_type=test_type,
            prompt="回复一句话：你好，连接测试成功。",
            max_tokens=50,
            temperature=0.1,
        )
        result = await adapter.test_connection(config, model_config, test_cfg)

        if result.success:
            await provider_service.update_provider(provider_id, {"health_status": "healthy"})
        else:
            await provider_service.update_provider(provider_id, {"health_status": "degraded"})

        return success({
            "success": result.success,
            "status_code": result.status_code,
            "latency_ms": result.latency_ms,
            "first_token_latency_ms": result.first_token_latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "output_text": result.output_text,
            "error_code": result.error_code,
            "error_message": result.error_message,
        })
    except Exception as e:
        logger.exception(f"Provider test failed: {e}")
        await provider_service.update_provider(provider_id, {"health_status": "degraded"})
        return error(500, f"测试失败: {str(e)}")
