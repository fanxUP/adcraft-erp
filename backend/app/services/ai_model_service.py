"""Service layer for AI Model management."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider import AIProvider
from app.repositories.ai_model_repo import AIModelRepository


class AIModelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIModelRepository(db)

    async def _get_provider_name(self, provider_id: UUID) -> str:
        result = await self.db.execute(
            select(AIProvider.provider_name).where(AIProvider.id == provider_id)
        )
        row = result.scalar_one_or_none()
        return row or ""

    def _to_response(self, model) -> dict:
        return {
            "id": str(model.id),
            "provider_id": str(model.provider_id),
            "provider_name": "",
            "upstream_model_code": model.upstream_model_code,
            "display_name": model.display_name,
            "model_role": model.model_role,
            "model_type": model.model_type,
            "context_window": model.context_window,
            "max_output_tokens": model.max_output_tokens,
            "supports_streaming": model.supports_streaming,
            "supports_tools": model.supports_tools,
            "supports_json_schema": model.supports_json_schema,
            "supports_vision": model.supports_vision,
            "supports_embedding": model.supports_embedding,
            "pricing_json": model.pricing_json or {},
            "enabled": model.enabled,
            "priority": model.priority,
            "health_status": model.health_status,
            "health_score": float(model.health_score) if model.health_score else None,
            "last_verified_at": model.last_verified_at,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    async def _enrich_with_provider_name(self, items: list[dict]) -> list[dict]:
        for item in items:
            item["provider_name"] = await self._get_provider_name(UUID(item["provider_id"]))
        return items

    async def list_models(
        self, page: int = 1, page_size: int = 100,
        provider_id: UUID | None = None, enabled_only: bool = False
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        if provider_id:
            models, total = await self.repo.list_by_provider(provider_id, skip=skip, limit=page_size)
        else:
            models, total = await self.repo.list_all(skip=skip, limit=page_size, enabled_only=enabled_only)
        items = [self._to_response(m) for m in models]
        items = await self._enrich_with_provider_name(items)
        return items, total

    async def get_model(self, model_id: UUID) -> dict | None:
        model = await self.repo.get_by_id(model_id)
        if not model:
            return None
        resp = self._to_response(model)
        resp["provider_name"] = await self._get_provider_name(model.provider_id)
        return resp

    async def create_model(self, data: dict) -> dict:
        if "tenant_id" not in data:
            data["tenant_id"] = "00000000-0000-0000-0000-000000000001"
        if "pricing" in data:
            data["pricing_json"] = data.pop("pricing")
        if "declared_capabilities" in data:
            data["declared_capabilities_json"] = data.pop("declared_capabilities")
        model = await self.repo.create(data)
        resp = self._to_response(model)
        resp["provider_name"] = await self._get_provider_name(model.provider_id)
        return resp

    async def update_model(self, model_id: UUID, data: dict) -> dict | None:
        if "pricing" in data:
            data["pricing_json"] = data.pop("pricing")
        if "declared_capabilities" in data:
            data["declared_capabilities_json"] = data.pop("declared_capabilities")
        model = await self.repo.update(model_id, data)
        if not model:
            return None
        resp = self._to_response(model)
        resp["provider_name"] = await self._get_provider_name(model.provider_id)
        return resp

    async def delete_model(self, model_id: UUID) -> bool:
        return await self.repo.delete(model_id)
