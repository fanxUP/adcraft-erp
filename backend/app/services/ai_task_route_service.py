"""Business logic for AI Task Route management."""
from typing import Any, Optional
from uuid import UUID

from app.repositories.ai_task_route_repo import AITaskRouteRepository


class AITaskRouteService:
    def __init__(self, repo: AITaskRouteRepository):
        self.repo = repo

    async def create_route(
        self, tenant_id: UUID, data: dict, created_by: Optional[UUID] = None
    ) -> dict:
        """Create a new task route, converting JSON fields."""
        payload = self._prepare_payload(data)
        route = await self.repo.create(tenant_id, payload, created_by)
        return self._to_dict(route)

    async def update_route(self, route_id: UUID, data: dict) -> Optional[dict]:
        """Update a task route."""
        payload = self._prepare_payload(data)
        route = await self.repo.update(route_id, payload)
        if not route:
            return None
        return self._to_dict(route)

    async def get_route(self, route_id: UUID) -> Optional[dict]:
        route = await self.repo.get_by_id(route_id)
        if not route:
            return None
        return self._to_dict(route)

    async def get_route_by_code(self, tenant_id: UUID, task_code: str) -> Optional[dict]:
        route = await self.repo.get_by_code(tenant_id, task_code)
        if not route:
            return None
        return self._to_dict(route)

    async def list_routes(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        enabled_only: bool = False,
        search: Optional[str] = None,
    ) -> dict:
        routes, total = await self.repo.list_all(
            tenant_id, page=page, page_size=page_size,
            enabled_only=enabled_only, search=search,
        )
        return {
            "items": [self._to_dict(r) for r in routes],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def delete_route(self, route_id: UUID) -> bool:
        return await self.repo.delete(route_id)

    def _prepare_payload(self, data: dict) -> dict:
        """Convert frontend-friendly fields to DB column names."""
        payload = {}
        field_map = {
            "task_code": "task_code",
            "task_name": "task_name",
            "description": "description",
            "primary_provider_id": "primary_provider_id",
            "primary_model_role": "primary_model_role",
            "timeout_seconds": "timeout_seconds",
            "max_output_tokens": "max_output_tokens",
            "temperature": "temperature",
            "enabled": "enabled",
        }
        for frontend_key, db_key in field_map.items():
            if frontend_key in data:
                payload[db_key] = data[frontend_key]

        # JSON fields
        if "fallback_chain" in data and data["fallback_chain"] is not None:
            payload["fallback_chain_json"] = [
                {"provider_id": str(f["provider_id"]), "model_role": f.get("model_role", "standard")}
                for f in data["fallback_chain"]
            ]
        if "required_capabilities" in data and data["required_capabilities"] is not None:
            payload["required_capabilities_json"] = data["required_capabilities"]
        if "budget_policy_json" in data and data["budget_policy_json"] is not None:
            payload["budget_policy_json"] = data["budget_policy_json"]
        if "data_policy_json" in data and data["data_policy_json"] is not None:
            payload["data_policy_json"] = data["data_policy_json"]
        if "circuit_breaker" in data and data["circuit_breaker"] is not None:
            payload["circuit_breaker_json"] = data["circuit_breaker"]

        return payload

    def _to_dict(self, route) -> dict:
        return {
            "id": str(route.id),
            "tenant_id": str(route.tenant_id),
            "task_code": route.task_code,
            "task_name": route.task_name,
            "description": route.description,
            "primary_provider_id": str(route.primary_provider_id) if route.primary_provider_id else None,
            "primary_model_role": route.primary_model_role,
            "fallback_chain_json": route.fallback_chain_json or [],
            "required_capabilities_json": route.required_capabilities_json or {},
            "timeout_seconds": route.timeout_seconds,
            "max_output_tokens": route.max_output_tokens,
            "temperature": route.temperature,
            "circuit_breaker_json": route.circuit_breaker_json or {},
            "enabled": route.enabled,
            "version": route.version,
            "created_at": route.created_at.isoformat() if route.created_at else None,
            "updated_at": route.updated_at.isoformat() if route.updated_at else None,
        }
