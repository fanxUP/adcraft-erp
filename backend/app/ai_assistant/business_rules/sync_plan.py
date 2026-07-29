"""Pure synchronization planning for source and persisted business rules."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import BusinessRuleSpec


@dataclass(frozen=True)
class PersistedRuleState:
    key: str
    version: int
    content_hash: str


@dataclass(frozen=True)
class PlannedRuleVersion:
    rule: BusinessRuleSpec
    version: int


@dataclass(frozen=True)
class RuleSyncPlan:
    added: tuple[PlannedRuleVersion, ...]
    updated: tuple[PlannedRuleVersion, ...]
    retired: tuple[PersistedRuleState, ...]
    unchanged: tuple[PersistedRuleState, ...]

    @property
    def in_sync(self) -> bool:
        return not (self.added or self.updated or self.retired)


def build_sync_plan(
    source_rules: tuple[BusinessRuleSpec, ...],
    persisted_rules: tuple[PersistedRuleState, ...],
) -> RuleSyncPlan:
    """Compare source rules with the currently active database rules."""
    source_by_key = {rule.key: rule for rule in source_rules}
    persisted_by_key = {rule.key: rule for rule in persisted_rules}

    added = tuple(
        PlannedRuleVersion(rule=source_by_key[key], version=1)
        for key in sorted(source_by_key.keys() - persisted_by_key.keys())
    )
    updated = tuple(
        PlannedRuleVersion(
            rule=source_by_key[key],
            version=persisted_by_key[key].version + 1,
        )
        for key in sorted(source_by_key.keys() & persisted_by_key.keys())
        if source_by_key[key].content_hash != persisted_by_key[key].content_hash
    )
    retired = tuple(
        persisted_by_key[key]
        for key in sorted(persisted_by_key.keys() - source_by_key.keys())
    )
    unchanged = tuple(
        persisted_by_key[key]
        for key in sorted(source_by_key.keys() & persisted_by_key.keys())
        if source_by_key[key].content_hash == persisted_by_key[key].content_hash
    )
    return RuleSyncPlan(
        added=added,
        updated=updated,
        retired=retired,
        unchanged=unchanged,
    )
