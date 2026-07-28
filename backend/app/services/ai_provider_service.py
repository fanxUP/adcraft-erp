"""Service layer for AI Provider management."""
import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.security.secret_store import decrypt_api_key, encrypt_api_key, mask_api_key
from app.models.ai_model import AIModel
from app.repositories.ai_provider_repo import AIProviderRepository

logger = logging.getLogger(__name__)


class AIProviderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIProviderRepository(db)

    async def _count_models(self, provider_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(AIModel.id)).where(AIModel.provider_id == provider_id)
        )
        return result.scalar() or 0

    def _to_response(self, provider) -> dict:
        encrypted_key = provider.credential_reference or ""
        has_key = bool(encrypted_key)
        return {
            "id": str(provider.id),
            "provider_code": provider.provider_code,
            "provider_name": provider.provider_name,
            "provider_type": provider.provider_type,
            "protocol": provider.protocol,
            "base_url": provider.base_url,
            "full_url_mode": provider.full_url_mode,
            "endpoint_url": provider.endpoint_url,
            "api_key_display": mask_api_key(encrypted_key) if has_key else None,
            "has_api_key": has_key,
            "auth_header": provider.auth_header,
            "auth_prefix": provider.auth_prefix,
            "custom_headers_json": provider.custom_headers_json or {},
            "proxy_config_json": provider.proxy_config_json or {},
            "timeout_seconds": provider.timeout_seconds,
            "retry_count": provider.retry_count,
            "tls_verify": provider.tls_verify,
            "enabled": provider.enabled,
            "priority": provider.priority,
            "health_status": provider.health_status,
            "health_score": float(provider.health_score) if provider.health_score else None,
            "last_health_check_at": provider.last_health_check_at,
            "model_count": 0,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        }

    async def _enrich(self, items: list[dict]) -> list[dict]:
        for item in items:
            item["model_count"] = await self._count_models(UUID(item["id"]))
        return items

    async def list_providers(
        self, page: int = 1, page_size: int = 50, enabled_only: bool = False
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        providers, total = await self.repo.list_all(
            skip=skip, limit=page_size, enabled_only=enabled_only
        )
        items = [self._to_response(p) for p in providers]
        items = await self._enrich(items)
        return items, total

    async def get_provider(self, provider_id: UUID) -> dict | None:
        provider = await self.repo.get_by_id(provider_id)
        if not provider:
            return None
        resp = self._to_response(provider)
        resp["model_count"] = await self._count_models(provider_id)
        return resp

    async def create_provider(self, data: dict) -> dict:
        api_key = data.pop("api_key", None)
        if api_key:
            data["credential_reference"] = encrypt_api_key(api_key)
        if "tenant_id" not in data:
            data["tenant_id"] = "00000000-0000-0000-0000-000000000001"
        provider = await self.repo.create(data)
        return self._to_response(provider)

    async def update_provider(self, provider_id: UUID, data: dict) -> dict | None:
        api_key = data.pop("api_key", None)
        if api_key:
            data["credential_reference"] = encrypt_api_key(api_key)
        elif api_key is not None:
            data["credential_reference"] = None
        provider = await self.repo.update(provider_id, data)
        if not provider:
            return None
        return self._to_response(provider)

    async def delete_provider(self, provider_id: UUID) -> bool:
        return await self.repo.delete(provider_id)

    async def duplicate_provider(self, provider_id: UUID, new_code: str, new_name: str) -> dict | None:
        provider = await self.repo.get_by_id(provider_id)
        if not provider:
            return None
        data = {
            "provider_code": new_code,
            "provider_name": new_name,
            "provider_type": provider.provider_type,
            "protocol": provider.protocol,
            "base_url": provider.base_url,
            "full_url_mode": provider.full_url_mode,
            "endpoint_url": provider.endpoint_url,
            "auth_header": provider.auth_header,
            "auth_prefix": provider.auth_prefix,
            "custom_headers_json": provider.custom_headers_json,
            "proxy_config_json": provider.proxy_config_json,
            "timeout_seconds": provider.timeout_seconds,
            "retry_count": provider.retry_count,
            "tls_verify": provider.tls_verify,
            "enabled": False,
            "priority": provider.priority + 10,
            "tenant_id": provider.tenant_id,
        }
        new_provider = await self.repo.create(data)
        return self._to_response(new_provider)

    async def get_api_key(self, provider_id: UUID) -> str | None:
        provider = await self.repo.get_by_id(provider_id)
        if not provider or not provider.credential_reference:
            return None
        try:
            return decrypt_api_key(provider.credential_reference)
        except Exception:
            logger.error(f"Failed to decrypt API key for provider {provider_id}")
            return None
