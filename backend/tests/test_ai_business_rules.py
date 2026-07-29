from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai_assistant.business_rules.catalog import (
    BusinessRuleSpec,
    build_business_rule_catalog,
    render_business_rules_context,
)
from app.ai_assistant.business_rules.service import (
    BusinessRuleSyncService,
    build_page_contract_status,
)
from app.ai_assistant.business_rules.sync_plan import (
    PersistedRuleState,
    build_sync_plan,
)
from app.ai_assistant.models import AiBusinessRule, AiBusinessRuleSyncLog
from app.ai_assistant.orchestrator import AiOrchestrator
from app.ai_assistant.prompt_builder import PromptBuilder


def test_business_rule_catalog_is_derived_from_canonical_workflows():
    rules = {rule.key: rule for rule in build_business_rule_catalog()}

    order_rule = rules["workflow.order"]
    assert order_rule.rule_type == "workflow"
    assert order_rule.payload["transitions"]["pending_confirm"] == [
        "confirmed",
        "cancelled",
    ]
    assert len(order_rule.content_hash) == 64


def test_sync_plan_adds_updates_retires_and_keeps_unchanged_rules():
    current_rules = (
        BusinessRuleSpec(
            key="workflow.order",
            title="订单流程",
            rule_type="workflow",
            payload={"transitions": {"draft": ["confirmed"]}},
        ),
        BusinessRuleSpec(
            key="workflow.production_task",
            title="制作任务流程",
            rule_type="workflow",
            payload={"transitions": {"pending": ["in_progress"]}},
        ),
        BusinessRuleSpec(
            key="policy.safe_write",
            title="安全写入规则",
            rule_type="policy",
            payload={"requires_confirmation": True},
        ),
    )
    persisted_rules = (
        PersistedRuleState(
            key="workflow.order",
            version=2,
            content_hash="outdated",
        ),
        PersistedRuleState(
            key="workflow.design_task",
            version=1,
            content_hash="removed",
        ),
        PersistedRuleState(
            key="policy.safe_write",
            version=3,
            content_hash=current_rules[2].content_hash,
        ),
    )

    plan = build_sync_plan(current_rules, persisted_rules)

    assert [(item.rule.key, item.version) for item in plan.added] == [
        ("workflow.production_task", 1),
    ]
    assert [(item.rule.key, item.version) for item in plan.updated] == [
        ("workflow.order", 3),
    ]
    assert [item.key for item in plan.retired] == ["workflow.design_task"]
    assert [item.key for item in plan.unchanged] == ["policy.safe_write"]


def test_prompt_prefers_published_business_rule_context():
    published_context = (
        "## 已发布业务规则（数据库）\n"
        "规则库指纹：abc123\n"
        "【订单流程】\n"
        "- pending_confirm → confirmed"
    )

    prompt = PromptBuilder().build_system_prompt(
        SimpleNamespace(username="admin", real_name="管理员", roles=[]),
        None,
        [],
        business_rules_context=published_context,
    )

    assert published_context in prompt
    assert "pending_confirm → confirmed / cancelled" not in prompt


def test_prompt_context_includes_only_current_page_operation_semantics():
    context = render_business_rules_context(
        build_business_rule_catalog(),
        page_key="order_detail",
        business_type="order",
    )

    assert "当前页面：订单详情" in context
    assert "查看订单信息、交付任务、验收与收款进度" in context
    assert "order-status-confirmed" in context
    assert "确认订单进入正式交付流程" in context
    assert "order:change_status" in context
    assert "quote-status-confirmed" not in context


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_initial_sync_publishes_catalog_and_records_audit_log():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarRows([]))
    db.flush = AsyncMock()
    db.add = MagicMock()

    result = await BusinessRuleSyncService(db).synchronize()

    catalog_size = len(build_business_rule_catalog())
    added_models = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], AiBusinessRule)
    ]
    audit_models = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], AiBusinessRuleSyncLog)
    ]
    assert result["added_count"] == catalog_size
    assert result["updated_count"] == 0
    assert result["retired_count"] == 0
    assert len(added_models) == catalog_size
    assert all(rule.status == "active" and rule.version == 1 for rule in added_models)
    assert len(audit_models) == 1
    assert audit_models[0].status == "success"


def test_business_rule_models_preserve_versions_and_sync_history():
    rule_columns = AiBusinessRule.__table__.columns
    sync_columns = AiBusinessRuleSyncLog.__table__.columns

    assert {
        "rule_key",
        "version",
        "content_hash",
        "payload_json",
        "status",
        "source",
    } <= set(rule_columns.keys())
    assert {
        "catalog_digest",
        "added_count",
        "updated_count",
        "retired_count",
        "details_json",
    } <= set(sync_columns.keys())


def test_page_contract_health_reports_database_version_and_target_drift():
    source_rules = build_business_rule_catalog()
    source_contract = next(
        rule
        for rule in source_rules
        if rule.key == "contract.page_capabilities"
    )
    persisted_targets = [
        target
        for target in source_contract.payload["target_keys"]
        if target != "installation-draft"
    ]
    persisted_targets.append("retired-control")
    active_rows = [
        SimpleNamespace(
            rule_key="contract.page_capabilities",
            version=3,
            content_hash="outdated",
            payload_json={
                "version": 1,
                "target_keys": persisted_targets,
            },
        )
    ]

    status = build_page_contract_status(source_rules, active_rows)

    assert status["source_version"] == 2
    assert status["active_rule_version"] == 3
    assert status["database_contract_version"] == 1
    assert status["in_sync"] is False
    assert status["added_targets"] == ["installation-draft"]
    assert status["retired_targets"] == ["retired-control"]


@pytest.mark.asyncio
async def test_rule_status_includes_contract_health_and_recent_sync_history():
    source_rules = build_business_rule_catalog()
    active_rows = [
        SimpleNamespace(
            rule_key=rule.key,
            version=1,
            content_hash=rule.content_hash,
            payload_json=rule.payload,
        )
        for rule in source_rules
    ]
    latest_sync = SimpleNamespace(
        status="success",
        catalog_digest="abc123",
        added_count=1,
        updated_count=0,
        retired_count=0,
        unchanged_count=len(source_rules) - 1,
        created_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarRows(active_rows),
            _ScalarRows([latest_sync]),
        ]
    )

    status = await BusinessRuleSyncService(db).build_status()

    assert status["in_sync"] is True
    assert status["contract"]["in_sync"] is True
    assert status["contract"]["semantic_complete_count"] == 33
    assert status["last_sync"]["catalog_digest"] == "abc123"
    assert len(status["recent_syncs"]) == 1


@pytest.mark.asyncio
async def test_orchestrator_loads_published_rules_once_per_tool_loop():
    orchestrator = AiOrchestrator(MagicMock())
    orchestrator.memory_service.get_history_messages = AsyncMock(return_value=[])
    orchestrator.llm_client.chat_completion = AsyncMock(return_value="已完成")
    orchestrator.prompt_builder.build_system_prompt = MagicMock(
        return_value="system prompt"
    )
    orchestrator.business_rule_service.get_prompt_context = AsyncMock(
        return_value="published rules"
    )

    reply, tool_results, pending = await orchestrator._tool_loop(
        user=SimpleNamespace(id="user-1", username="admin", roles=[]),
        session=SimpleNamespace(id="session-1"),
        message="下一步做什么",
        context=None,
        user_msg_id="message-1",
    )

    assert reply == "已完成"
    assert tool_results == []
    assert pending is None
    orchestrator.business_rule_service.get_prompt_context.assert_awaited_once()
    orchestrator.business_rule_service.get_prompt_context.assert_awaited_once_with(
        page_key=None,
        business_type=None,
    )
    assert (
        orchestrator.prompt_builder.build_system_prompt.call_args.kwargs[
            "business_rules_context"
        ]
        == "published rules"
    )
