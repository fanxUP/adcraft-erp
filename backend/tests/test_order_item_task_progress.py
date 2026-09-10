"""第七阶段：订单明细级并行进度契约测试。"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.workflows import DESIGN_TASK_WORKFLOW, INSTALLATION_TASK_WORKFLOW
from app.schemas.order import OrderItemResponse
from app.schemas.task import (
    DesignTaskCreate,
    DesignTaskResponse,
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
    _materialize_legacy_task_scope,
    _resolve_order_item_stage,
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
        from app.services.task_service import _task_order_item_option_map

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
