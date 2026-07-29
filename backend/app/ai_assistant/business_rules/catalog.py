"""Canonical business rules that are synchronized into the AI rule database."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.domain.workflows import (
    ACCEPTANCE_WORKFLOW,
    DESIGN_TASK_WORKFLOW,
    INSTALLATION_TASK_WORKFLOW,
    ORDER_WORKFLOW,
    OUTSOURCE_TASK_WORKFLOW,
    PRODUCTION_TASK_WORKFLOW,
    QUOTE_WORKFLOW,
)


@dataclass(frozen=True)
class BusinessRuleSpec:
    """A source-controlled business rule ready for deterministic versioning."""

    key: str
    title: str
    rule_type: str
    payload: dict[str, Any]
    source: str = "backend"

    @property
    def content_hash(self) -> str:
        content = {
            "key": self.key,
            "title": self.title,
            "rule_type": self.rule_type,
            "payload": self.payload,
            "source": self.source,
        }
        serialized = json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


_WORKFLOWS = (
    ("order", "订单流程", ORDER_WORKFLOW),
    ("quote", "报价流程", QUOTE_WORKFLOW),
    ("design_task", "设计任务流程", DESIGN_TASK_WORKFLOW),
    ("production_task", "制作任务流程", PRODUCTION_TASK_WORKFLOW),
    ("installation_task", "安装任务流程", INSTALLATION_TASK_WORKFLOW),
    ("acceptance", "验收流程", ACCEPTANCE_WORKFLOW),
    ("outsource_task", "外协任务流程", OUTSOURCE_TASK_WORKFLOW),
)


def build_business_rule_catalog() -> tuple[BusinessRuleSpec, ...]:
    """Build the current rule catalog directly from backend domain definitions."""
    workflow_rules = [
        BusinessRuleSpec(
            key=f"workflow.{key}",
            title=title,
            rule_type="workflow",
            source="app.domain.workflows",
            payload={
                "business_type": key,
                "transitions": {
                    current: list(targets)
                    for current, targets in workflow.items()
                },
            },
        )
        for key, title, workflow in _WORKFLOWS
    ]
    policy_rules = [
        BusinessRuleSpec(
            key="policy.safe_write",
            title="AI 安全写入规则",
            rule_type="policy",
            source="app.ai_assistant",
            payload={
                "requires_preview": True,
                "requires_user_confirmation": True,
                "forbidden_actions": [
                    "登记收款",
                    "修改已结清状态",
                    "修改订单金额",
                    "删除业务数据",
                ],
            },
        )
    ]
    return tuple(sorted((*workflow_rules, *policy_rules), key=lambda rule: rule.key))


def business_rule_catalog_digest(
    rules: tuple[BusinessRuleSpec, ...] | None = None,
) -> str:
    """Return one deploy-level fingerprint for the complete source catalog."""
    catalog = rules or build_business_rule_catalog()
    serialized = json.dumps(
        [(rule.key, rule.content_hash) for rule in catalog],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def render_business_rules_context(
    rules: tuple[BusinessRuleSpec, ...],
    *,
    catalog_digest: str | None = None,
) -> str:
    """Render published database rules as compact LLM context."""
    digest = catalog_digest or business_rule_catalog_digest(rules)
    lines = [
        "## 已发布业务规则（数据库）",
        f"规则库指纹：{digest}",
        "以下规则是当前唯一有效版本；不得引用已废弃或历史版本。",
    ]
    for rule in rules:
        lines.append(f"【{rule.title}】")
        if rule.rule_type == "workflow":
            for current, targets in rule.payload.get("transitions", {}).items():
                target_text = " / ".join(targets) if targets else "终态"
                lines.append(f"- {current} → {target_text}")
        elif rule.key == "policy.safe_write":
            lines.append("- 所有写操作先生成预览，并等待用户明确确认。")
            forbidden = "、".join(rule.payload.get("forbidden_actions", []))
            if forbidden:
                lines.append(f"- AI 禁止直接执行：{forbidden}。")
    return "\n".join(lines)
