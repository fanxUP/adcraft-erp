"""第七阶段：订单明细级并行进度契约测试。"""

from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.workflows import DESIGN_TASK_WORKFLOW, INSTALLATION_TASK_WORKFLOW
from app.models.task_order_item_link import TaskOrderItemLink
from app.schemas.order import OrderItemResponse
from app.schemas.task import (
    DesignTaskCreate,
    DesignTaskResponse,
    TaskItemAction,
    TaskItemRollbackRequest,
    TaskStatusChange,
    TaskOrderItemOption,
    TaskQueueItem,
)
from app.services.task_service import (
    DesignTaskService,
    InstallationTaskService,
    _aggregate_task_status,
    _apply_task_item_status_change,
    _blocking_outsource_map,
    _ensure_task_order_item_links,
    _get_or_create_rollback_target_task,
    _materialize_legacy_task_scope,
    _resolve_order_item_stage,
    _rollback_task_items,
    _sync_task_order_item_links,
    _task_item_actions,
    _task_order_item_option_map,
    _validate_order_item_id,
    _validate_order_item_ids,
)
from app.services.task_history_service import task_history_snapshot
from tests.conftest import make_mock_design_task, make_mock_installation_task


ORDER_ID = "33333333-3333-3333-3333-333333333333"
ITEM_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ITEM_UUID = UUID(ITEM_ID)
SECOND_ITEM_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SECOND_ITEM_UUID = UUID(SECOND_ITEM_ID)


def test_task_contract_carries_order_item_identity():
    create = DesignTaskCreate(order_id=ORDER_ID, order_item_id=ITEM_ID)
    assert create.order_item_id == ITEM_ID

    queue_item = TaskQueueItem(
        id="task-id",
        task_type="design",
        stage="design",
        task_no="D20260907-0001",
        document_id=ORDER_ID,
        order_item_id=ITEM_ID,
        item_name="前台发光字",
        project_name="门头项目",
        status="designing",
        progress_pct=60,
    )
    assert queue_item.order_item_id == ITEM_ID
    assert queue_item.item_name == "前台发光字"


def test_task_responses_expose_nullable_order_item_identity():
    response_fields = DesignTaskResponse.model_fields
    assert "order_item_id" in response_fields
    assert "item_name" in response_fields


def test_task_order_item_option_exposes_stage_and_selectability():
    option_fields = TaskOrderItemOption.model_fields

    assert "stage" in option_fields
    assert "stage_label" in option_fields
    assert "can_select" in option_fields
    assert "disabled_reason" in option_fields
    assert "outsource_blocked" in option_fields
    assert "outsource_status" in option_fields
    assert "outsource_status_label" in option_fields
    assert "outsource_task_count" in option_fields
    assert "outsource_task_nos" in option_fields
    assert "actions" in option_fields


def test_task_item_actions_use_single_item_plain_language_commands():
    actions = _task_item_actions(
        "production",
        "in_progress",
        can_operate=True,
        is_linked=True,
        disabled_reason=None,
        outsource_blocked=False,
    )

    assert [action["to_status"] for action in actions] == [
        "completed",
        "rework",
        "pending",
        "rolled_back",
    ]
    assert actions[0]["label"] == "完成制作"
    assert actions[2]["label"] == "退回待制作"
    assert all(action["allowed"] for action in actions)


def test_task_item_actions_use_stage_rollback_instead_of_item_cancellation():
    actions = _task_item_actions(
        "production",
        "in_progress",
        can_operate=True,
        is_linked=True,
        disabled_reason=None,
        outsource_blocked=False,
    )

    rollback = next(action for action in actions if action["key"] == "rollback_stage")
    assert rollback["to_status"] == "rolled_back"
    assert rollback["label"] == "退回设计"
    assert rollback["operation"] == "rollback"
    assert rollback["target_stage"] == "design"
    assert all(action["to_status"] != "cancelled" for action in actions)


def test_design_item_actions_never_offer_cancellation():
    actions = _task_item_actions(
        "design",
        "designing",
        can_operate=True,
        is_linked=True,
        disabled_reason=None,
        outsource_blocked=False,
    )

    assert all(action["to_status"] != "cancelled" for action in actions)
    assert not any(action.get("operation") == "rollback" for action in actions)


@pytest.mark.parametrize(
    ("task_type", "target_stage", "label"),
    [
        ("production", "design", "恢复到设计"),
        ("installation", "production", "恢复到制作"),
    ],
)
def test_historical_cancelled_item_can_be_explicitly_restored(
    task_type,
    target_stage,
    label,
):
    actions = _task_item_actions(
        task_type,
        "cancelled",
        can_operate=True,
        is_linked=True,
        disabled_reason="该明细历史上已取消，只能查看",
        outsource_blocked=False,
    )

    rollback = next(action for action in actions if action["key"] == "rollback_stage")
    assert rollback["label"] == label
    assert rollback["target_stage"] == target_stage
    assert rollback["allowed"] is True
    assert all(action["to_status"] != "cancelled" for action in actions)


@pytest.mark.asyncio
async def test_historical_cancelled_option_exposes_enabled_restore_action():
    db = AsyncMock()
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            doc_type="order",
            deleted_at=None,
            status="in_production",
        )
    )
    db.execute = AsyncMock(return_value=_mock_result([_mock_order_item()]))
    link = TaskOrderItemLink(
        task_type="production",
        task_id=UUID("22222222-2222-2222-2222-222222222222"),
        order_item_id=ITEM_UUID,
        item_status="cancelled",
        item_progress_pct=100,
    )

    with (
        patch(
            "app.services.task_service._task_stage_states_by_item",
            new=AsyncMock(return_value=({}, {})),
        ),
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[link]),
        ),
        patch(
            "app.services.task_service._blocking_outsource_map",
            new=AsyncMock(return_value={}),
        ),
    ):
        options = await _task_order_item_option_map(
            db,
            UUID(ORDER_ID),
            "production",
            task_id=link.task_id,
        )

    option = options[ITEM_UUID]
    restore = next(action for action in option["actions"] if action["key"] == "rollback_stage")
    assert option["can_select"] is False
    assert restore["label"] == "恢复到设计"
    assert restore["allowed"] is True


def test_rollback_request_requires_explicit_item_ids_and_optional_reason():
    request = TaskItemRollbackRequest(
        order_item_ids=[ITEM_ID],
        reason="尺寸需要重新确认",
    )

    assert request.order_item_ids == [ITEM_ID]
    assert request.reason == "尺寸需要重新确认"


def test_task_item_action_contract_exposes_cross_stage_operation():
    action = TaskItemAction(
        key="rollback_stage",
        to_status="rolled_back",
        label="退回设计",
        allowed=True,
        operation="rollback",
        target_stage="design",
    )

    assert action.operation == "rollback"
    assert action.target_stage == "design"


def test_task_item_actions_disable_completion_when_outsource_is_active():
    actions = _task_item_actions(
        "installation",
        "in_progress",
        can_operate=True,
        is_linked=True,
        disabled_reason=None,
        outsource_blocked=True,
        outsource_reason="外协任务进行中，外协完成后才能完成安装任务",
    )

    completed = next(action for action in actions if action["to_status"] == "completed")
    assert completed["allowed"] is False
    assert completed["disabled_reason"] == "外协任务进行中，外协完成后才能完成安装任务"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_type", "message"),
    [
        ("design", "设计明细不能单独取消"),
        ("production", "制作明细不能取消"),
        ("installation", "安装明细不能取消"),
    ],
)
async def test_delivery_item_cancellation_is_rejected_with_plain_language(
    task_type,
    message,
):
    db = AsyncMock()
    task = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        document_id=UUID(ORDER_ID),
    )

    with pytest.raises(ValueError, match=message):
        await _apply_task_item_status_change(
            db,
            task_type,
            task,
            "cancelled",
            [ITEM_ID],
        )


@pytest.mark.asyncio
async def test_retried_item_rollback_is_a_safe_noop():
    db = AsyncMock()
    task = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        document_id=UUID(ORDER_ID),
        order_item_id=None,
        status="rolled_back",
        progress_pct=0,
    )
    link = TaskOrderItemLink(
        task_type="production",
        task_id=task.id,
        order_item_id=ITEM_UUID,
        item_status="rolled_back",
        item_progress_pct=0,
    )

    with patch(
        "app.services.task_service._task_order_item_link_rows",
        new=AsyncMock(return_value=[link]),
    ):
        changed = await _rollback_task_items(
            db,
            "production",
            task,
            [ITEM_ID],
            reason=None,
            viewer=None,
            operated_by=None,
        )

    assert changed == []
    assert link.item_status == "rolled_back"
    db.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_historical_cancelled_item_can_be_restored_to_previous_stage():
    db = MagicMock()
    db.flush = AsyncMock()
    task = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        document_id=UUID(ORDER_ID),
        order_item_id=None,
        status="pending",
        progress_pct=33,
    )
    link = TaskOrderItemLink(
        task_type="production",
        task_id=task.id,
        order_item_id=ITEM_UUID,
        item_status="cancelled",
        item_progress_pct=100,
    )
    target_task = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
    )

    with (
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[link]),
        ),
        patch(
            "app.services.task_service._blocking_outsource_map",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.services.task_service._get_or_create_rollback_target_task",
            new=AsyncMock(return_value=(target_task, "confirmed")),
        ),
        patch(
            "app.services.task_service._refresh_task_aggregate",
            new=AsyncMock(),
        ),
        patch(
            "app.services.task_service._reconcile_order_stage_after_item_rollback",
            new=AsyncMock(),
        ),
    ):
        changed = await _rollback_task_items(
            db,
            "production",
            task,
            [ITEM_ID],
            reason="历史任务恢复",
            viewer=None,
            operated_by=None,
        )

    assert changed == [ITEM_UUID]
    assert link.item_status == "rolled_back"
    assert link.item_progress_pct == 0
    assert link.assignee_user_id is None
    db.add_all.assert_called_once()


@pytest.mark.asyncio
async def test_existing_completed_previous_stage_link_is_reset_when_restoring():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    source_task = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        document_id=UUID(ORDER_ID),
    )
    target_task = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        document_id=UUID(ORDER_ID),
        status="confirmed",
    )
    db.execute.return_value = _mock_result([target_task])
    target_link = TaskOrderItemLink(
        task_type="design",
        task_id=target_task.id,
        order_item_id=ITEM_UUID,
        item_status="confirmed",
        item_progress_pct=100,
        item_completed_at=SimpleNamespace(),
        assignee_user_id=UUID("44444444-4444-4444-4444-444444444444"),
    )

    with (
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[target_link]),
        ),
        patch(
            "app.services.task_service._refresh_task_aggregate",
            new=AsyncMock(),
        ),
    ):
        target, previous_status = await _get_or_create_rollback_target_task(
            db,
            source_task,
            "production",
            ITEM_UUID,
            operated_by=None,
        )

    assert target is target_task
    assert previous_status == "confirmed"
    assert target_link.item_status == "pending"
    assert target_link.item_progress_pct == 0
    assert target_link.item_completed_at is None
    assert target_link.assignee_user_id is None


def _mock_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _mock_outsource_task(
    *,
    item_id=ITEM_UUID,
    status="in_progress",
    task_no="OT20260908-0001",
    deleted_at=None,
    task_type="production",
):
    return SimpleNamespace(
        order_item_id=item_id,
        status=status,
        task_no=task_no,
        deleted_at=deleted_at,
        task_type=task_type,
    )


def _mock_order_item(item_id=ITEM_ID, name="前台发光字"):
    return OrderItemResponse(
        id=item_id,
        item_name=name,
        quantity=1,
        unit_price=100,
        subtotal_amount=100,
    )


def test_status_change_contract_requires_checked_order_items():
    with pytest.raises(ValidationError):
        TaskStatusChange(to_status="completed")

    change = TaskStatusChange(
        to_status="completed",
        order_item_ids=[ITEM_ID],
    )
    assert change.order_item_ids == [ITEM_ID]


def test_status_change_contract_can_carry_the_selected_assignee():
    change = TaskStatusChange(
        to_status="in_progress",
        order_item_ids=[ITEM_ID],
        assigned_to="66666666-6666-6666-6666-666666666666",
    )

    assert change.assigned_to == "66666666-6666-6666-6666-666666666666"


def test_mixed_item_status_uses_unfinished_state_for_task_summary():
    assert _aggregate_task_status("design", ["confirmed", "designing"]) == "designing"
    assert _aggregate_task_status("production", ["completed", "in_progress"]) == "in_progress"
    assert _aggregate_task_status("installation", ["completed", "assigned"]) == "assigned"


def test_rolled_back_item_is_not_counted_as_completed_work():
    assert _aggregate_task_status("production", ["completed", "rolled_back"]) == "completed"
    assert _aggregate_task_status("production", ["in_progress", "rolled_back"]) == "in_progress"
    assert _aggregate_task_status("production", ["rolled_back"]) == "rolled_back"
    assert _aggregate_task_status("production", ["completed", "cancelled"]) == "completed"
    assert _aggregate_task_status("production", ["cancelled"]) == "cancelled"


@pytest.mark.asyncio
async def test_stage_reentry_resets_only_the_reopened_item():
    """重入任务卡时不能把同卡其他明细一起清零或清除执行人。"""
    task_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    existing_first = TaskOrderItemLink(
        task_type="production",
        task_id=task_id,
        order_item_id=ITEM_UUID,
        position=0,
        item_status="completed",
        item_progress_pct=100,
        item_completed_at=datetime(2026, 9, 10, 10),
        assignee_user_id=UUID("11111111-1111-1111-1111-111111111111"),
    )
    existing_second = TaskOrderItemLink(
        task_type="production",
        task_id=task_id,
        order_item_id=SECOND_ITEM_UUID,
        position=1,
        item_status="rolled_back",
        item_progress_pct=0,
        item_completed_at=None,
        assignee_user_id=UUID("22222222-2222-2222-2222-222222222222"),
    )
    reopened_first = TaskOrderItemLink(
        task_type="production",
        task_id=task_id,
        order_item_id=ITEM_UUID,
        position=0,
        item_status="completed",
        item_progress_pct=100,
        item_completed_at=existing_first.item_completed_at,
        assignee_user_id=existing_first.assignee_user_id,
    )
    reopened_second = TaskOrderItemLink(
        task_type="production",
        task_id=task_id,
        order_item_id=SECOND_ITEM_UUID,
        position=1,
        item_status="pending",
        item_progress_pct=0,
        item_completed_at=None,
        assignee_user_id=None,
    )
    task = MagicMock(id=task_id, status="pending", progress_pct=50, order_item_id=None)
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[existing_first, existing_second])))),
            MagicMock(),
            MagicMock(),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[ITEM_UUID, SECOND_ITEM_UUID])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[reopened_first, reopened_second])))),
        ]
    )

    await _sync_task_order_item_links(
        db,
        "production",
        task,
        [ITEM_UUID, SECOND_ITEM_UUID],
        previous_legacy_item_id=ITEM_UUID,
        reopen_item_ids={SECOND_ITEM_UUID},
    )

    insert_payload = db.execute.await_args_list[2].args[1]
    assert insert_payload[0]["item_status"] == "completed"
    assert insert_payload[0]["item_progress_pct"] == 100
    assert insert_payload[0]["assignee_user_id"] == existing_first.assignee_user_id
    assert insert_payload[1]["item_status"] == "pending"
    assert insert_payload[1]["item_progress_pct"] == 0
    assert insert_payload[1]["assignee_user_id"] is None


def test_order_item_stage_resolver_supports_parallel_delivery_progress():
    assert _resolve_order_item_stage(
        "designing",
        {"designing": ["confirmed"]},
    ) == "in_production"
    assert _resolve_order_item_stage(
        "designing",
        {
            "designing": ["confirmed"],
            "in_production": ["in_progress"],
        },
    ) == "in_production"
    assert _resolve_order_item_stage(
        "in_production",
        {
            "designing": ["confirmed"],
            "in_production": ["completed"],
        },
    ) == "in_installation"
    assert _resolve_order_item_stage(
        "in_installation",
        {
            "designing": ["confirmed"],
            "in_production": ["completed"],
            "in_installation": ["completed"],
        },
    ) == "completed"


def test_order_item_stage_resolver_does_not_guess_unknown_state():
    assert _resolve_order_item_stage(
        "in_production",
        {"designing": ["legacy_unknown_status"]},
    ) == "not_ready"


def test_order_item_stage_resolver_uses_order_stage_when_item_has_no_tasks():
    assert _resolve_order_item_stage("designing", {}) == "designing"
    assert _resolve_order_item_stage("in_production", {}) == "in_production"
    assert _resolve_order_item_stage("in_installation", {}) == "in_installation"
    assert _resolve_order_item_stage("completed", {}) == "completed"


def test_task_contract_carries_multiple_order_item_identity():
    response = DesignTaskResponse(
        id="task-id",
        design_no="D20260907-0002",
        document_id=ORDER_ID,
        customer_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        project_name="门头项目",
        status="designing",
        order_item_id=ITEM_ID,
        order_item_ids=[ITEM_ID, SECOND_ITEM_ID],
        item_name="前台发光字、侧招字",
        item_names=["前台发光字", "侧招字"],
    )

    assert response.order_item_ids == [ITEM_ID, SECOND_ITEM_ID]
    assert response.item_names == ["前台发光字", "侧招字"]


def test_update_contract_accepts_multiple_order_item_ids():
    from app.schemas.task import DesignTaskUpdate

    update = DesignTaskUpdate(order_item_ids=[ITEM_ID, SECOND_ITEM_ID])

    assert update.order_item_ids == [ITEM_ID, SECOND_ITEM_ID]


def test_new_flow_can_finish_without_extra_review_step():
    assert "confirmed" in DESIGN_TASK_WORKFLOW["designing"]
    assert "completed" in INSTALLATION_TASK_WORKFLOW["in_progress"]


def test_order_item_link_migration_is_additive_and_nullable():
    migration = next(
        Path(__file__).parents[1].glob(
            "alembic/versions/o6p7q8r9s0t1_add_task_order_item_links.py"
        )
    )
    source = migration.read_text()
    assert "op.add_column" in source
    for table in ("design_tasks", "production_tasks", "installation_tasks"):
        assert table in source
        assert "ix_{table}_order_item_id" in source
        assert "fk_{table}_order_item_id" in source
    assert "nullable=True" in source
    assert "UPDATE " not in source


@pytest.mark.asyncio
async def test_order_item_validation_rejects_an_item_from_another_order():
    db = AsyncMock()
    item = MagicMock(document_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
    item.lifecycle_status = "active"
    db.get = AsyncMock(return_value=item)

    with pytest.raises(ValueError, match="不属于当前订单"):
        await _validate_order_item_id(db, UUID(ORDER_ID), ITEM_ID)


@pytest.mark.asyncio
async def test_order_item_ids_validation_rejects_duplicate_ids():
    db = AsyncMock()

    with pytest.raises(ValueError, match="不能重复"):
        await _validate_order_item_ids(
            db,
            UUID(ORDER_ID),
            [ITEM_ID, ITEM_ID],
        )


@pytest.mark.asyncio
async def test_order_item_validation_rejects_item_outside_task_stage():
    db = AsyncMock()
    item = MagicMock(
        id=ITEM_UUID,
        document_id=UUID(ORDER_ID),
        lifecycle_status="active",
    )
    db.get = AsyncMock(return_value=item)

    with patch(
        "app.services.task_service._task_order_item_option_map",
        new=AsyncMock(
            return_value={
                ITEM_UUID: {
                    "stage": "in_production",
                    "stage_label": "制作中",
                    "can_select": False,
                    "disabled_reason": "当前处于制作中，不能关联设计任务",
                    "item_name": "前台发光字",
                },
            },
        ),
    ):
        with pytest.raises(ValueError, match="制作中"):
            await _validate_order_item_ids(
                db,
                UUID(ORDER_ID),
                [ITEM_ID],
                task_type="design",
            )


@pytest.mark.asyncio
async def test_blocking_outsource_map_only_keeps_active_pending_or_in_progress_tasks():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_mock_result(
            [
                _mock_outsource_task(status="pending", task_no="OT-PENDING"),
                _mock_outsource_task(status="in_progress", task_no="OT-RUNNING"),
                _mock_outsource_task(status="completed", task_no="OT-DONE"),
                _mock_outsource_task(status="settled", task_no="OT-SETTLED"),
                _mock_outsource_task(status="cancelled", task_no="OT-CANCELLED"),
                _mock_outsource_task(
                    status="in_progress",
                    task_no="OT-DELETED",
                    deleted_at=SimpleNamespace(),
                ),
            ]
        )
    )

    blocked = await _blocking_outsource_map(
        db,
        UUID(ORDER_ID),
        "production",
        [ITEM_UUID],
    )

    assert blocked[ITEM_UUID]["outsource_blocked"] is True
    assert blocked[ITEM_UUID]["outsource_status"] == "in_progress"
    assert blocked[ITEM_UUID]["outsource_status_label"] == "外协任务进行中"
    assert blocked[ITEM_UUID]["outsource_task_count"] == 2
    assert blocked[ITEM_UUID]["outsource_task_nos"] == ["OT-PENDING", "OT-RUNNING"]


@pytest.mark.asyncio
async def test_design_task_does_not_query_or_block_for_outsource_task():
    db = AsyncMock()

    blocked = await _blocking_outsource_map(
        db,
        UUID(ORDER_ID),
        "design",
        [ITEM_UUID],
    )

    assert blocked == {}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_production_option_disables_unlinked_item_with_active_outsource_task():
    db = AsyncMock()
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            doc_type="order",
            deleted_at=None,
            status="in_production",
        )
    )
    db.execute = AsyncMock(
        side_effect=[
            _mock_result([_mock_order_item()]),
            _mock_result([_mock_outsource_task(task_type="production")]),
        ]
    )

    with (
        patch(
            "app.services.task_service._task_stage_states_by_item",
            new=AsyncMock(return_value=({}, {})),
        ),
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[]),
        ),
    ):
        options = await _task_order_item_option_map(
            db,
            UUID(ORDER_ID),
            "production",
            task_id=UUID("99999999-9999-9999-9999-999999999999"),
        )

    option = options[ITEM_UUID]
    assert option["outsource_blocked"] is True
    assert option["outsource_status_label"] == "外协任务进行中"
    assert option["can_select"] is False
    assert "外协" in option["disabled_reason"]


@pytest.mark.asyncio
async def test_execution_viewer_gets_generic_block_reason_without_outsource_details():
    db = AsyncMock()
    db.get = AsyncMock(
        return_value=SimpleNamespace(
            doc_type="order",
            deleted_at=None,
            status="in_production",
        )
    )
    db.execute = AsyncMock(
        side_effect=[
            _mock_result([_mock_order_item()]),
            _mock_result([_mock_outsource_task(task_type="production")]),
        ]
    )
    viewer = SimpleNamespace(
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code="production_task:read")])]
    )

    with (
        patch(
            "app.services.task_service._task_stage_states_by_item",
            new=AsyncMock(return_value=({}, {})),
        ),
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[]),
        ),
    ):
        options = await _task_order_item_option_map(
            db,
            UUID(ORDER_ID),
            "production",
            task_id=UUID("99999999-9999-9999-9999-999999999999"),
            viewer=viewer,
        )

    option = options[ITEM_UUID]
    assert option["can_select"] is False
    assert option["outsource_blocked"] is False
    assert option.get("outsource_status_label") is None
    assert option["outsource_task_count"] == 0
    assert option.get("outsource_task_nos") == []
    assert "外协" not in option["disabled_reason"]
    assert "只能查看制作流程" in option["disabled_reason"]


@pytest.mark.asyncio
async def test_installation_completion_is_blocked_before_link_status_update():
    db = AsyncMock()
    task = make_mock_installation_task(status="pending_acceptance")
    task.order_item_id = ITEM_UUID
    states = {ITEM_UUID: ("pending_acceptance", 75)}
    db.execute = AsyncMock(
        return_value=_mock_result([_mock_outsource_task(task_type="installation")])
    )

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_UUID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value=states),
        ),
    ):
        with pytest.raises(ValueError, match="外协任务"):
            await _apply_task_item_status_change(
                db,
                "installation",
                task,
                "completed",
                [ITEM_ID],
            )

    assert task.status == "pending_acceptance"
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_execution_status_error_hides_outsource_task_reference():
    db = AsyncMock()
    task = SimpleNamespace(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        document_id=UUID(ORDER_ID),
        order_item_id=ITEM_UUID,
        status="in_progress",
        progress_pct=50,
        completed_at=None,
    )
    db.execute = AsyncMock(
        side_effect=[
            _mock_result([_mock_outsource_task(task_type="installation", task_no="OT-PRIVATE")]),
        ]
    )
    viewer = SimpleNamespace(
        roles=[SimpleNamespace(permissions=[
            SimpleNamespace(code="installation_task:read"),
            SimpleNamespace(code="installation_task:change_status"),
        ])]
    )

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_UUID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value={ITEM_UUID: ("pending_acceptance", 75)}),
        ),
    ):
        with pytest.raises(ValueError) as exc_info:
            await _apply_task_item_status_change(
                db,
                "installation",
                task,
                "completed",
                [ITEM_ID],
                viewer=viewer,
            )

    assert "外协" not in str(exc_info.value)
    assert "OT-PRIVATE" not in str(exc_info.value)
    assert "前置事项" in str(exc_info.value)


@pytest.mark.asyncio
async def test_production_completion_is_allowed_after_outsource_task_is_completed():
    db = AsyncMock()
    task = SimpleNamespace(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        document_id=UUID(ORDER_ID),
        order_item_id=ITEM_UUID,
        status="in_progress",
        progress_pct=50,
        completed_at=None,
    )
    states = {ITEM_UUID: ("in_progress", 50)}
    db.execute = AsyncMock(
        side_effect=[
            _mock_result([_mock_outsource_task(status="completed")]),
            MagicMock(),
        ]
    )

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_UUID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value=states),
        ),
    ):
        selected, updated = await _apply_task_item_status_change(
            db,
            "production",
            task,
            "completed",
            [ITEM_ID],
        )

    assert selected == [ITEM_UUID]
    assert updated[ITEM_UUID] == ("completed", 100)
    assert task.status == "completed"
    assert db.execute.await_count == 2


def test_many_order_item_link_migration_copies_legacy_links_without_guessing():
    migration = next(
        Path(__file__).parents[1].glob(
            "alembic/versions/p7q8r9s0t1u2_add_task_order_item_many_links.py"
        )
    )
    source = migration.read_text()

    assert 'op.create_table("task_order_item_links"' in source
    assert "task_type" in source
    assert "position" in source
    assert "UNION ALL" in source
    assert "WHERE order_item_id IS NOT NULL" in source


def test_item_state_migration_adds_state_columns_and_removes_dependency_graph():
    migration = next(
        Path(__file__).parents[1].glob(
            "alembic/versions/q8r9s0t1u2v3_add_item_state_remove_task_dependencies.py"
        )
    )
    source = migration.read_text()

    for column in ("item_status", "item_progress_pct", "item_completed_at"):
        assert column in source
    assert "DROP TABLE IF EXISTS task_dependencies" in source
    assert 'down_revision: Union[str, None] = "p7q8r9s0t1u2"' in source


@pytest.mark.asyncio
async def test_item_scoped_design_can_finish_without_review_step():
    db = AsyncMock()
    db.get = AsyncMock(return_value=MagicMock(
        id=ITEM_UUID,
        document_id=UUID(ORDER_ID),
        lifecycle_status="active",
    ))
    task = make_mock_design_task(status="designing", assigned_to=UUID("11111111-1111-1111-1111-111111111111"))
    task.order_item_id = ITEM_UUID
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)
    service._to_dict = AsyncMock(side_effect=lambda value: {"status": value.status})

    with (
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
        patch("app.services.task_service._item_stage_tasks_completed", new=AsyncMock(return_value=False)),
        patch("app.services.task_service._maybe_complete_order", new=AsyncMock()),
    ):
        result = await service.change_status(task.id, "confirmed", order_item_ids=[ITEM_ID])

    assert result["status"] == "confirmed"


@pytest.mark.asyncio
async def test_item_scoped_installation_can_finish_without_acceptance_step():
    db = AsyncMock()
    db.get = AsyncMock(return_value=MagicMock(
        id=ITEM_UUID,
        document_id=UUID(ORDER_ID),
        lifecycle_status="active",
    ))
    task = make_mock_installation_task(status="in_progress", assigned_to=UUID("11111111-1111-1111-1111-111111111111"))
    task.order_item_id = ITEM_UUID
    service = InstallationTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)
    service._to_dict = AsyncMock(side_effect=lambda value: {"status": value.status})

    with (
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
        patch("app.services.task_service._maybe_complete_order", new=AsyncMock()),
    ):
        result = await service.change_status(task.id, "completed", order_item_ids=[ITEM_ID])

    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_status_change_does_not_keep_new_assignee_when_transition_fails():
    db = AsyncMock()
    old_assignee = UUID("11111111-1111-1111-1111-111111111111")
    new_assignee = UUID("66666666-6666-6666-6666-666666666666")
    task = make_mock_design_task(status="pending", assigned_to=old_assignee)
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)

    with patch(
        "app.services.task_service._apply_task_item_status_change",
        new=AsyncMock(side_effect=ValueError("状态不允许")),
    ):
        with pytest.raises(ValueError, match="状态不允许"):
            await service.change_status(
                task.id,
                "confirmed",
                order_item_ids=[ITEM_ID],
                assigned_to=str(new_assignee),
            )

    assert task.assigned_to == old_assignee


@pytest.mark.asyncio
async def test_status_change_restores_new_assignee_when_side_effect_fails():
    db = AsyncMock()
    old_assignee = UUID("11111111-1111-1111-1111-111111111111")
    new_assignee = UUID("66666666-6666-6666-6666-666666666666")
    task = make_mock_design_task(status="designing", assigned_to=old_assignee)
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)

    with (
        patch(
            "app.services.task_service._apply_task_item_status_change",
            new=AsyncMock(return_value=([ITEM_UUID], {ITEM_UUID: ("confirmed", 100)})),
        ),
        patch(
            "app.services.task_service.record_task_event",
            new=AsyncMock(side_effect=RuntimeError("写入任务历史失败")),
        ),
    ):
        with pytest.raises(RuntimeError, match="写入任务历史失败"):
            await service.change_status(
                task.id,
                "confirmed",
                order_item_ids=[ITEM_ID],
                assigned_to=str(new_assignee),
            )

    assert task.assigned_to == old_assignee


@pytest.mark.asyncio
async def test_status_change_only_updates_checked_item_and_keeps_other_item_state():
    db = AsyncMock()
    task = make_mock_design_task(status="designing", progress_pct=50)
    task.order_item_id = ITEM_UUID
    second_item = SECOND_ITEM_UUID
    states = {
        ITEM_UUID: ("designing", 50),
        second_item: ("designing", 50),
    }

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_UUID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value=states),
        ),
    ):
        selected, updated = await _apply_task_item_status_change(
            db,
            "design",
            task,
            "confirmed",
            [ITEM_ID],
        )

    assert selected == [ITEM_UUID]
    assert updated[ITEM_UUID] == ("confirmed", 100)
    assert updated[second_item] == ("designing", 50)
    assert task.status == "designing"
    assert task.progress_pct == 75
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_installation_status_change_keeps_unchecked_item_in_task_aggregate():
    db = AsyncMock()
    task = make_mock_installation_task(status="in_progress", progress_pct=50)
    task.order_item_id = ITEM_UUID
    states = {
        ITEM_UUID: ("in_progress", 50),
        SECOND_ITEM_UUID: ("in_progress", 50),
    }

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_UUID]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value=states),
        ),
    ):
        selected, updated = await _apply_task_item_status_change(
            db,
            "installation",
            task,
            "completed",
            [ITEM_ID],
        )

    assert selected == [ITEM_UUID]
    assert updated[ITEM_UUID] == ("completed", 100)
    assert updated[SECOND_ITEM_UUID] == ("in_progress", 50)
    assert task.status == "in_progress"
    assert task.progress_pct == 75


@pytest.mark.asyncio
async def test_legacy_whole_order_task_materializes_all_current_stage_items():
    db = AsyncMock()
    task = make_mock_installation_task(status="pending_acceptance", progress_pct=75)
    task.order_item_id = None

    with (
        patch(
            "app.services.task_service._linked_order_item_ids",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.task_service._task_order_item_option_map",
            new=AsyncMock(
                return_value={
                    ITEM_UUID: {
                        "stage": "in_installation",
                        "can_select": True,
                    },
                    SECOND_ITEM_UUID: {
                        "stage": "in_installation",
                        "can_select": True,
                    },
                },
            ),
        ),
    ):
        item_ids = await _materialize_legacy_task_scope(
            db,
            "installation",
            task,
        )

    assert item_ids == [ITEM_UUID, SECOND_ITEM_UUID]
    insert_payload = db.execute.await_args.args[1]
    assert [row["order_item_id"] for row in insert_payload] == [
        ITEM_UUID,
        SECOND_ITEM_UUID,
    ]
    assert {row["item_status"] for row in insert_payload} == {"pending_acceptance"}
    assert {row["item_progress_pct"] for row in insert_payload} == {75}


@pytest.mark.asyncio
async def test_completed_task_new_item_reopens_with_nonterminal_state():
    db = AsyncMock()
    task = make_mock_installation_task(status="completed", progress_pct=100)
    task.order_item_id = ITEM_UUID

    with patch(
        "app.services.task_service._linked_order_item_ids",
        new=AsyncMock(return_value=[ITEM_UUID]),
    ):
        await _ensure_task_order_item_links(
            db,
            "installation",
            task,
            [ITEM_UUID, SECOND_ITEM_UUID],
        )

    insert_payload = db.execute.await_args.args[1]
    assert insert_payload[0]["order_item_id"] == SECOND_ITEM_UUID
    assert insert_payload[0]["item_status"] == "in_progress"
    assert insert_payload[0]["item_progress_pct"] == 50


@pytest.mark.asyncio
async def test_historical_task_can_be_manually_linked_and_audited():
    db = AsyncMock()
    item = MagicMock(document_id=UUID(ORDER_ID), lifecycle_status="active")
    db.get = AsyncMock(return_value=item)
    task = make_mock_design_task(status="confirmed")
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)

    async def apply_update(current, data):
        for key, value in data.items():
            setattr(current, key, value)
        return current

    service.repo.update = AsyncMock(side_effect=apply_update)
    service._to_dict = AsyncMock(
        side_effect=lambda value: {
            "order_item_id": str(value.order_item_id),
        }
    )

    with (
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
        patch(
            "app.services.task_service._task_order_item_option_map",
            new=AsyncMock(
                return_value={
                    ITEM_UUID: {
                        "stage": "designing",
                        "stage_label": "设计中",
                        "can_select": True,
                        "disabled_reason": None,
                    },
                },
            ),
        ),
    ):
        result = await service.update_task(task.id, {"order_item_id": ITEM_ID})

    assert task.order_item_id == ITEM_UUID
    assert result["order_item_id"] == ITEM_ID
    assert task_history_snapshot(task)["order_item_id"] == ITEM_ID


@pytest.mark.asyncio
async def test_historical_task_can_be_manually_linked_to_multiple_items():
    db = AsyncMock()
    first_item = MagicMock(document_id=UUID(ORDER_ID), lifecycle_status="active")
    second_item = MagicMock(document_id=UUID(ORDER_ID), lifecycle_status="active")
    db.get = AsyncMock(side_effect=[first_item, second_item])
    task = make_mock_design_task(status="confirmed")
    service = DesignTaskService(db)
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)

    async def apply_update(current, data):
        for key, value in data.items():
            setattr(current, key, value)
        return current

    service.repo.update = AsyncMock(side_effect=apply_update)
    service._to_dict = AsyncMock(
        side_effect=lambda value: {
            "order_item_id": str(value.order_item_id),
            "order_item_ids": [ITEM_ID, SECOND_ITEM_ID],
        }
    )

    with (
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
        patch(
            "app.services.task_service._task_order_item_option_map",
            new=AsyncMock(
                return_value={
                    ITEM_UUID: {
                        "stage": "designing",
                        "stage_label": "设计中",
                        "can_select": True,
                        "disabled_reason": None,
                    },
                    SECOND_ITEM_UUID: {
                        "stage": "designing",
                        "stage_label": "设计中",
                        "can_select": True,
                        "disabled_reason": None,
                    },
                },
            ),
        ),
    ):
        result = await service.update_task(
            task.id,
            {"order_item_ids": [ITEM_ID, SECOND_ITEM_ID]},
        )

    assert task.order_item_id == ITEM_UUID
    assert result["order_item_ids"] == [ITEM_ID, SECOND_ITEM_ID]
    assert db.execute.await_count >= 2
