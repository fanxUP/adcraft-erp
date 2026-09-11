"""订单明细执行归属和岗位操作边界回归测试。"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.models.task_order_item_link import TaskOrderItemLink
from app.models.task import DesignTask
from app.repositories.task_repo import _item_assignee_filter
from app.schemas.task import TaskOrderItemOption
from app.services.task_service import (
    DesignTaskService,
    _apply_task_item_status_change,
    _reject_legacy_task_assignee_input,
    _resolve_status_assignee,
)


ITEM_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ITEM_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TASK_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
ORDER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _worker_viewer(permission: str = "design_task:change_status"):
    read_permission = {
        "design_task:change_status": "design_task:read",
        "design_task:assign": "design_task:read",
        "production_task:change_status": "production_task:read",
        "production_task:assign": "production_task:read",
        "installation_task:change_status": "installation_task:read",
        "installation_task:assign": "installation_task:read",
    }.get(permission)
    permissions = [permission, read_permission] if read_permission else [permission]
    return SimpleNamespace(
        id=ACTOR_ID,
        is_active=True,
        deleted_at=None,
        is_superuser=False,
        roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in permissions])],
    )


def _link(item_id: UUID, assignee_user_id: UUID | None = None):
    return SimpleNamespace(
        id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        task_type="design",
        task_id=TASK_ID,
        order_item_id=item_id,
        position=0,
        item_status="designing",
        item_progress_pct=50,
        item_completed_at=None,
        assignee_user_id=assignee_user_id,
    )


def test_task_item_link_has_independent_assignee_field():
    assert "assignee_user_id" in TaskOrderItemLink.__table__.c
    assert TaskOrderItemLink.__table__.c.assignee_user_id.nullable is True


def test_task_order_item_option_exposes_item_assignee_contract():
    fields = TaskOrderItemOption.model_fields

    assert "assignee_user_id" in fields
    assert "assignee_name" in fields
    assert "assignee_state" in fields


def test_task_list_assignee_filter_uses_item_executor_not_legacy_task_owner():
    expression = str(_item_assignee_filter(DesignTask, "design", str(ACTOR_ID)))

    assert "task_order_item_links.assignee_user_id" in expression
    assert "design_tasks.assigned_to" not in expression


def test_status_log_backfill_does_not_copy_legacy_whole_task_owner():
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "tcd01_task_item_status_logs.py"
    ).read_text()

    assert "t.assigned_to" not in migration
    assert "tio01_task_item_assignees" not in migration


def test_authenticated_task_mutations_reject_legacy_whole_task_owner_input():
    with pytest.raises(ValueError, match="整张设计任务负责人已停用"):
        _reject_legacy_task_assignee_input(
            {"assigned_to": str(OTHER_ID)},
            "design",
            _worker_viewer("design_task:assign"),
        )


@pytest.mark.asyncio
async def test_claiming_one_item_does_not_assign_the_other_item():
    db = AsyncMock()
    task = SimpleNamespace(
        id=TASK_ID,
        document_id=ORDER_ID,
        status="designing",
        progress_pct=50,
        completed_at=None,
    )
    first = _link(ITEM_A)
    second = _link(ITEM_B, OTHER_ID)
    states = {
        ITEM_A: ("designing", 50),
        ITEM_B: ("designing", 50),
    }

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_A]),
        ),
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[first, second]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value=states),
        ),
        patch("app.services.task_service.TaskItemStatusLog"),
    ):
        selected, updated = await _apply_task_item_status_change(
            db,
            "design",
            task,
            "pending_review",
            [str(ITEM_A)],
            viewer=_worker_viewer(),
            assignee_user_id=ACTOR_ID,
            operated_by=ACTOR_ID,
        )

    assert selected == [ITEM_A]
    assert updated[ITEM_A][0] == "pending_review"
    assert first.assignee_user_id == ACTOR_ID
    assert second.assignee_user_id == OTHER_ID


@pytest.mark.asyncio
async def test_worker_cannot_change_another_workers_claimed_item():
    db = AsyncMock()
    task = SimpleNamespace(
        id=TASK_ID,
        document_id=ORDER_ID,
        status="designing",
        progress_pct=50,
        completed_at=None,
    )
    states = {ITEM_B: ("designing", 50)}

    with (
        patch(
            "app.services.task_service._prepare_status_item_ids",
            new=AsyncMock(return_value=[ITEM_B]),
        ),
        patch(
            "app.services.task_service._task_order_item_link_rows",
            new=AsyncMock(return_value=[_link(ITEM_B, OTHER_ID)]),
        ),
        patch(
            "app.services.task_service._task_item_state_map",
            new=AsyncMock(return_value=states),
        ),
        patch("app.services.task_service.TaskItemStatusLog"),
    ):
        with pytest.raises(ValueError, match="由其他员工负责"):
            await _apply_task_item_status_change(
                db,
                "design",
                task,
                "pending_review",
                [str(ITEM_B)],
                viewer=_worker_viewer(),
                assignee_user_id=ACTOR_ID,
                operated_by=ACTOR_ID,
            )


@pytest.mark.asyncio
async def test_worker_cannot_change_a_different_stage_from_the_service_layer():
    with pytest.raises(ValueError, match="只能查看制作流程，不能变更状态"):
        await _apply_task_item_status_change(
            AsyncMock(),
            "production",
            SimpleNamespace(id=TASK_ID, document_id=ORDER_ID, status="pending"),
            "in_progress",
            [str(ITEM_A)],
            viewer=_worker_viewer("design_task:change_status"),
            assignee_user_id=ACTOR_ID,
            operated_by=ACTOR_ID,
        )


@pytest.mark.asyncio
async def test_status_request_cannot_choose_a_whole_task_owner():
    with pytest.raises(ValueError, match="不再设置整张任务负责人"):
        await _resolve_status_assignee(
            AsyncMock(),
            SimpleNamespace(assigned_to=OTHER_ID),
            str(OTHER_ID),
            task_type="design",
            viewer=_worker_viewer(),
        )


@pytest.mark.asyncio
async def test_stage_manager_without_employee_binding_can_operate_without_claiming():
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    manager = _worker_viewer("design_task:assign")
    manager.roles[0].permissions.append(SimpleNamespace(code="design_task:change_status"))

    assignee = await _resolve_status_assignee(
        db,
        SimpleNamespace(assigned_to=None),
        None,
        task_type="design",
        viewer=manager,
    )

    assert assignee is None


@pytest.mark.asyncio
async def test_authenticated_status_change_does_not_mutate_legacy_task_owner():
    db = AsyncMock()
    old_owner = OTHER_ID
    task = SimpleNamespace(
        id=TASK_ID,
        document_id=None,
        status="designing",
        progress_pct=50,
        completed_at=None,
        assigned_to=old_owner,
        planned_start_at=None,
        planned_end_at=None,
    )
    service = DesignTaskService(db, _worker_viewer())
    service.repo = MagicMock()
    service.repo.get_by_id = AsyncMock(return_value=task)
    service._to_dict = AsyncMock(return_value={"status": "confirmed"})

    with (
        patch(
            "app.services.task_service._resolve_status_assignee",
            new=AsyncMock(return_value=ACTOR_ID),
        ),
        patch(
            "app.services.task_service._apply_task_item_status_change",
            new=AsyncMock(return_value=([ITEM_A], {ITEM_A: ("confirmed", 100)})),
        ),
        patch("app.services.task_service.record_task_event", new=AsyncMock()),
    ):
        await service.change_status(
            TASK_ID,
            "confirmed",
            order_item_ids=[str(ITEM_A)],
        )

    assert task.assigned_to == old_owner
