"""Database synchronization and runtime access for AI business rules."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_assistant.models import AiBusinessRule, AiBusinessRuleSyncLog

from .catalog import (
    BusinessRuleSpec,
    build_business_rule_catalog,
    business_rule_catalog_digest,
    render_business_rules_context,
)
from .sync_plan import PersistedRuleState, RuleSyncPlan, build_sync_plan

logger = logging.getLogger(__name__)

_SYNC_LOCK_ID = 6_240_321_991


class BusinessRuleSyncService:
    """Synchronize source rules and ensure the AI never consumes stale versions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _active_rules(self) -> list[AiBusinessRule]:
        result = await self.db.execute(
            select(AiBusinessRule)
            .where(AiBusinessRule.status == "active")
            .order_by(AiBusinessRule.rule_key)
        )
        return list(result.scalars().all())

    @staticmethod
    def _states(rows: list[AiBusinessRule]) -> tuple[PersistedRuleState, ...]:
        return tuple(
            PersistedRuleState(
                key=row.rule_key,
                version=row.version,
                content_hash=row.content_hash,
            )
            for row in rows
        )

    async def build_status(self) -> dict[str, Any]:
        source_rules = build_business_rule_catalog()
        active_rows = await self._active_rules()
        plan = build_sync_plan(source_rules, self._states(active_rows))
        last_result = await self.db.execute(
            select(AiBusinessRuleSyncLog)
            .order_by(desc(AiBusinessRuleSyncLog.created_at))
            .limit(1)
        )
        last_sync = last_result.scalar_one_or_none()
        return {
            "catalog_digest": business_rule_catalog_digest(source_rules),
            "in_sync": plan.in_sync,
            "active_count": len(active_rows),
            "pending": self._plan_counts(plan),
            "last_sync": self._serialize_sync_log(last_sync),
        }

    async def synchronize(self) -> dict[str, Any]:
        """Publish added/changed rules and retire rules removed from source."""
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _SYNC_LOCK_ID},
        )
        source_rules = build_business_rule_catalog()
        active_rows = await self._active_rules()
        active_by_key = {row.rule_key: row for row in active_rows}
        plan = build_sync_plan(source_rules, self._states(active_rows))

        for item in plan.updated:
            active_by_key[item.rule.key].status = "superseded"
            self.db.add(self._new_rule_model(item.rule, item.version))
        for item in plan.added:
            self.db.add(self._new_rule_model(item.rule, item.version))
        for item in plan.retired:
            active_by_key[item.key].status = "retired"

        digest = business_rule_catalog_digest(source_rules)
        details = {
            "added": [item.rule.key for item in plan.added],
            "updated": [item.rule.key for item in plan.updated],
            "retired": [item.key for item in plan.retired],
        }
        counts = self._plan_counts(plan)
        self.db.add(
            AiBusinessRuleSyncLog(
                catalog_digest=digest,
                status="success",
                details_json=details,
                **counts,
            )
        )
        await self.db.flush()
        return {
            "catalog_digest": digest,
            "in_sync": True,
            **counts,
            "details": details,
        }

    async def get_prompt_context(self) -> str:
        """Return current rules; source fallback prevents stale database guidance."""
        source_rules = build_business_rule_catalog()
        active_rows = await self._active_rules()
        plan = build_sync_plan(source_rules, self._states(active_rows))
        if not plan.in_sync:
            logger.error(
                "AI business-rule database drift detected; using current source rules"
            )
            return render_business_rules_context(source_rules)

        published_rules = tuple(
            BusinessRuleSpec(
                key=row.rule_key,
                title=row.title,
                rule_type=row.rule_type,
                payload=row.payload_json,
                source=row.source,
            )
            for row in active_rows
        )
        return render_business_rules_context(
            published_rules,
            catalog_digest=business_rule_catalog_digest(published_rules),
        )

    @staticmethod
    def _new_rule_model(
        rule: BusinessRuleSpec,
        version: int,
    ) -> AiBusinessRule:
        return AiBusinessRule(
            rule_key=rule.key,
            version=version,
            title=rule.title,
            rule_type=rule.rule_type,
            payload_json=rule.payload,
            content_hash=rule.content_hash,
            source=rule.source,
            status="active",
        )

    @staticmethod
    def _plan_counts(plan: RuleSyncPlan) -> dict[str, int]:
        return {
            "added_count": len(plan.added),
            "updated_count": len(plan.updated),
            "retired_count": len(plan.retired),
            "unchanged_count": len(plan.unchanged),
        }

    @staticmethod
    def _serialize_sync_log(log: AiBusinessRuleSyncLog | None) -> dict | None:
        if not log:
            return None
        return {
            "status": log.status,
            "catalog_digest": log.catalog_digest,
            "added_count": log.added_count,
            "updated_count": log.updated_count,
            "retired_count": log.retired_count,
            "unchanged_count": log.unchanged_count,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
