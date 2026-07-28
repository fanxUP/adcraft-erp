"""Service layer for Prompt Center - templates, versions, testing."""
import logging
import re
import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.gateway import AIGateway
from app.repositories.ai_prompt_repo import (
    AIPromptTemplateRepository,
    AIPromptVersionRepository,
    AIPromptExecutionLogRepository,
)

logger = logging.getLogger(__name__)

_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class AIPromptService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.template_repo = AIPromptTemplateRepository(db)
        self.version_repo = AIPromptVersionRepository(db)
        self.exec_log_repo = AIPromptExecutionLogRepository(db)

    # ── Helpers ──

    def _template_to_dict(self, tpl: Any, version_count: int = 0) -> dict:
        active_ver = None
        if tpl.active_version_id:
            active_ver = self._get_active_version_number(tpl)

        return {
            "id": str(tpl.id),
            "template_code": tpl.template_code,
            "template_name": tpl.template_name,
            "description": tpl.description,
            "category": tpl.category,
            "tags": tpl.tags or [],
            "variables_json": tpl.variables_json or [],
            "active_version_id": str(tpl.active_version_id) if tpl.active_version_id else None,
            "active_version_number": active_ver,
            "enabled": tpl.enabled,
            "version": tpl.version,
            "version_count": version_count,
            "created_by": str(tpl.created_by) if tpl.created_by else None,
            "updated_by": str(tpl.updated_by) if tpl.updated_by else None,
            "created_at": tpl.created_at,
            "updated_at": tpl.updated_at,
        }

    def _version_to_dict(self, ver: Any) -> dict:
        return {
            "id": str(ver.id),
            "template_id": str(ver.template_id),
            "version_number": ver.version_number,
            "content": ver.content,
            "variables_defaults_json": ver.variables_defaults_json or {},
            "change_log": ver.change_log,
            "status": ver.status,
            "created_by": str(ver.created_by) if ver.created_by else None,
            "created_at": ver.created_at,
            "updated_at": ver.updated_at,
        }

    def _get_active_version_number(self, tpl: Any) -> Optional[int]:
        """Quick check for active version number without extra query."""
        if hasattr(tpl, "_active_version_number"):
            return tpl._active_version_number
        return None

    @staticmethod
    def resolve_variables(content: str, variables: dict[str, str]) -> str:
        """Replace {{var_name}} placeholders with provided values.
        Unresolved variables are left as-is.
        """
        def replace_match(m: re.Match) -> str:
            key = m.group(1)
            return variables.get(key, m.group(0))
        return _VARIABLE_PATTERN.sub(replace_match, content)

    # ── Templates ──

    async def list_templates(
        self, page: int = 1, page_size: int = 20, category: Optional[str] = None, search: Optional[str] = None
    ) -> tuple[list[dict], int]:
        templates, total = await self.template_repo.list_all(
            self.tenant_id, page=page, page_size=page_size, category=category, search=search,
        )
        items = []
        if templates:
            # Batch-fetch version counts for all templates in one query
            tpl_ids = [tpl.id for tpl in templates]
            from sqlalchemy import select, func
            from app.repositories.ai_prompt_repo import AIPromptVersion
            count_query = select(
                AIPromptVersion.template_id,
                func.count(),
            ).where(AIPromptVersion.template_id.in_(set(tpl_ids))
            ).group_by(AIPromptVersion.template_id)
            count_result = await self.db.execute(count_query)
            vcount_map = {row[0]: row[1] for row in count_result.all()}
        else:
            vcount_map = {}
        for tpl in templates:
            vcount = vcount_map.get(tpl.id, 0)
            items.append(self._template_to_dict(tpl, vcount))
        return items, total

    async def get_template(self, template_id: UUID) -> Optional[dict]:
        tpl = await self.template_repo.get_by_id(template_id)
        if not tpl:
            return None
        vcount = await self._count_versions(tpl.id)
        return self._template_to_dict(tpl, vcount)

    async def create_template(self, data: dict, created_by: Optional[UUID] = None) -> dict:
        # Map frontend-friendly field names to DB columns
        payload = {}
        for k in ("template_code", "template_name", "description", "category", "enabled"):
            if k in data:
                payload[k] = data[k]
        if "tags" in data:
            payload["tags"] = data["tags"]
        if "variables" in data:
            payload["variables_json"] = [v.model_dump() if hasattr(v, "model_dump") else v for v in data["variables"]]

        tpl = await self.template_repo.create(self.tenant_id, payload, created_by)
        return self._template_to_dict(tpl)

    async def update_template(self, template_id: UUID, data: dict) -> Optional[dict]:
        payload = {}
        for k in ("template_name", "description", "category", "tags", "enabled", "active_version_id"):
            if k in data:
                payload[k] = data[k]
        if "variables" in data:
            payload["variables_json"] = [v.model_dump() if hasattr(v, "model_dump") else v for v in data["variables"]]

        tpl = await self.template_repo.update(template_id, payload)
        if not tpl:
            return None
        return self._template_to_dict(tpl)

    async def delete_template(self, template_id: UUID) -> bool:
        return await self.template_repo.delete(template_id)

    async def _count_versions(self, template_id: UUID) -> int:
        _, total = await self.version_repo.list_by_template(template_id, page=1, page_size=1)
        return total

    # ── Versions ──

    async def list_versions(
        self, template_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        versions, total = await self.version_repo.list_by_template(template_id, page, page_size)
        items = [self._version_to_dict(v) for v in versions]
        return items, total

    async def get_version(self, version_id: UUID) -> Optional[dict]:
        ver = await self.version_repo.get_by_id(version_id)
        if not ver:
            return None
        return self._version_to_dict(ver)

    async def create_version(
        self, template_id: UUID, data: dict, created_by: Optional[UUID] = None
    ) -> dict:
        # Verify template exists
        tpl = await self.template_repo.get_by_id(template_id)
        if not tpl:
            raise ValueError("模板不存在")

        version_number = await self.version_repo.get_next_version_number(template_id)

        payload = {
            "version_number": version_number,
            "content": data.get("content", ""),
            "variables_defaults_json": data.get("variables_defaults", {}),
            "change_log": data.get("change_log"),
            "status": "active" if data.get("activate", False) else "draft",
        }

        ver = await self.version_repo.create(template_id, payload, created_by)

        # If activate requested, update template's active_version_id
        if data.get("activate", False):
            await self.template_repo.update(template_id, {"active_version_id": ver.id})
            # Deactivate other versions of this template
            versions, _ = await self.version_repo.list_by_template(template_id, page=1, page_size=999)
            for v in versions:
                if v.id != ver.id and v.status == "active":
                    await self.version_repo.update(v.id, {"status": "archived"})

        return self._version_to_dict(ver)

    async def activate_version(self, template_id: UUID, version_id: UUID) -> Optional[dict]:
        tpl = await self.template_repo.get_by_id(template_id)
        if not tpl:
            raise ValueError("模板不存在")

        ver = await self.version_repo.get_by_id(version_id)
        if not ver or ver.template_id != template_id:
            raise ValueError("版本不存在")

        # Update version status
        await self.version_repo.update(version_id, {"status": "active"})

        # Deactivate other active versions
        versions, _ = await self.version_repo.list_by_template(template_id, page=1, page_size=999)
        for v in versions:
            if v.id != ver.id and v.status == "active":
                await self.version_repo.update(v.id, {"status": "archived"})

        # Set as active version on template
        await self.template_repo.update(template_id, {"active_version_id": ver.id})

        return self._version_to_dict(ver)

    # ── Test Execution ──

    async def execute_test(
        self,
        template_id: UUID,
        test_data: dict,
        user_id: Optional[str] = None,
    ) -> dict:
        """Resolve a prompt template with variables and execute via AI Gateway."""
        tpl = await self.template_repo.get_by_id(template_id)
        if not tpl:
            raise ValueError("模板不存在")

        # Determine which version to use
        version_id_str = test_data.get("version_id")
        if version_id_str:
            ver = await self.version_repo.get_by_id(UUID(version_id_str))
            if not ver or ver.template_id != template_id:
                raise ValueError("版本不存在")
        else:
            # Use active version
            if not tpl.active_version_id:
                raise ValueError("模板没有激活的版本，请先创建并激活一个版本")
            ver = await self.version_repo.get_by_id(tpl.active_version_id)
            if not ver:
                raise ValueError("激活的版本不存在")

        # Resolve variables
        variables = dict(ver.variables_defaults_json or {})
        variables.update(test_data.get("variables", {}))

        resolved_content = self.resolve_variables(ver.content, variables)

        # Build messages for AI call
        extra_messages = test_data.get("messages", [])
        # Use resolved content as the system prompt if role is system, or first message
        try:
            import json
            # Check if resolved_content looks like it contains a system message
            messages = [
                {"role": "system", "content": resolved_content},
                *extra_messages,
            ]
            if not extra_messages:
                messages.append({"role": "user", "content": "请根据以上指令回应。"})

        except Exception:
            messages = [{"role": "user", "content": resolved_content}]

        # Execute via Gateway
        gateway = AIGateway(self.db, tenant_id=str(self.tenant_id))

        try:
            result = await gateway.execute(
                task_code="prompt_test",
                messages=messages,
                model_role="standard",
                temperature=test_data.get("temperature"),
                max_output_tokens=test_data.get("max_output_tokens"),
                user_id=user_id,
            )

            # Log execution
            log = await self.exec_log_repo.create({
                "template_id": template_id,
                "version_id": ver.id,
                "tenant_id": self.tenant_id,
                "resolved_content": resolved_content,
                "variables_used_json": variables,
                "input_tokens": result.usage.input_tokens if result.usage else None,
                "output_tokens": result.usage.output_tokens if result.usage else None,
                "latency_ms": result.latency_ms,
                "model_code": result.model_code,
                "model_role": "standard",
                "output_text": result.output_text,
                "status": "completed",
            })

            return {
                "output_text": result.output_text,
                "input_tokens": result.usage.input_tokens if result.usage else None,
                "output_tokens": result.usage.output_tokens if result.usage else None,
                "latency_ms": result.latency_ms,
                "model_code": result.model_code,
                "resolved_content": resolved_content,
                "log_id": str(log.id),
            }

        except Exception as e:
            logger.exception("Prompt test execution failed")

            # Log failure
            await self.exec_log_repo.create({
                "template_id": template_id,
                "version_id": ver.id,
                "tenant_id": self.tenant_id,
                "resolved_content": resolved_content,
                "variables_used_json": variables,
                "status": "error",
                "error_message": str(e),
            })

            raise

    # ── Execution Logs ──

    async def list_execution_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        template_id: Optional[UUID] = None,
    ) -> tuple[list[dict], int]:
        logs, total = await self.exec_log_repo.list_all(
            self.tenant_id, page=page, page_size=page_size, template_id=template_id,
        )
        items = []
        for log in logs:
            item = {
                "id": str(log.id),
                "template_id": str(log.template_id) if log.template_id else None,
                "template_code": None,
                "template_name": None,
                "version_id": str(log.version_id) if log.version_id else None,
                "version_number": None,
                "resolved_content": log.resolved_content,
                "variables_used_json": log.variables_used_json or {},
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "latency_ms": log.latency_ms,
                "model_code": log.model_code,
                "output_text": log.output_text,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at,
            }
            # Enrich with template info if available
            if log.template_id and hasattr(log, "_template_cache"):
                item["template_code"] = log._template_cache.template_code
                item["template_name"] = log._template_cache.template_name
            items.append(item)
        return items, total
