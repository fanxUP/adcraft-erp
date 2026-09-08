"""Tests for DesignTaskService: status transitions, CRUD, validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from app.api import tasks as task_api
from app.schemas.task import (
    DesignTaskCreate,
    InstallationTaskCreate,
    ProductionTaskCreate,
)
from app.services.task_service import (
    DesignTaskService,
    InstallationTaskService,
    ProductionTaskService,
    _prepare_task_create_data,
)

from tests.conftest import (
    SAMPLE_ORDER_ITEM_ID,
    SAMPLE_TASK_ID,
    SAMPLE_USER_ID,
    make_mock_design_task,
    make_mock_installation_task,
    make_mock_production_task,
)


@pytest.fixture
def mock_repo():
    """Create a mock DesignTaskRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.create = AsyncMock()
    repo.list_tasks = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def service(mock_repo):
    """Create DesignTaskService with a mocked repository."""
    with patch("app.services.task_service.DesignTaskRepository") as MockRepoClass:
        MockRepoClass.return_value = mock_repo
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            document_id=UUID("33333333-3333-3333-3333-333333333333"),
            lifecycle_status="active",
        ))
        # Mock db.execute to return a result that supports .fetchone()
        mock_exec_result = MagicMock()
        mock_exec_result.fetchone.return_value = None
        db.execute.return_value = mock_exec_result
        svc = DesignTaskService(db)
        svc.repo = mock_repo
        yield svc


# --- Status Transition Tests ---

TRANSITION_TABLE = [
    ("pending", "designing", True),
    ("pending", "pending_review", False),
    ("pending", "confirmed", False),
    ("designing", "pending_review", True),
    ("designing", "pending", True),
    ("designing", "confirmed", True),
    ("pending_review", "confirmed", True),
    ("pending_review", "revision", True),
    ("pending_review", "designing", False),
    ("revision", "designing", True),
    ("revision", "pending_review", True),
    ("revision", "confirmed", False),
    ("confirmed", "designing", False),
    ("confirmed", "pending", False),
    ("confirmed", "revision", False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status,should_succeed", TRANSITION_TABLE)
async def test_status_transitions(service, mock_repo, from_status, to_status, should_succeed):
    """Verify all allowed and forbidden status transitions."""
    task = make_mock_design_task(status=from_status)
    mock_repo.get_by_id.return_value = task

    if should_succeed:
        result = await service.change_status(
            SAMPLE_TASK_ID,
            to_status,
            SAMPLE_USER_ID,
            order_item_ids=[str(task.order_item_id)],
        )
        assert result["status"] == to_status
    else:
        with pytest.raises(ValueError):
            await service.change_status(
                SAMPLE_TASK_ID,
                to_status,
                SAMPLE_USER_ID,
                order_item_ids=[str(task.order_item_id)],
            )


@pytest.mark.asyncio
async def test_completed_sets_timestamp(service, mock_repo):
    """Transitioning to 'confirmed' sets the completed_at timestamp."""
    task = make_mock_design_task(status="pending_review")
    mock_repo.get_by_id.return_value = task

    result = await service.change_status(
        SAMPLE_TASK_ID,
        "confirmed",
        SAMPLE_USER_ID,
        order_item_ids=[str(task.order_item_id)],
    )

    assert result["status"] == "confirmed"
    assert result["completed_at"] is not None
    assert result["progress_pct"] == 100


@pytest.mark.asyncio
async def test_change_status_nonexistent_task(service, mock_repo):
    """Changing status on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="设计任务不存在"):
        await service.change_status(SAMPLE_TASK_ID, "designing", SAMPLE_USER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_class", "task_factory", "terminal_status", "next_status"),
    [
        (DesignTaskService, make_mock_design_task, "confirmed", "designing"),
        (ProductionTaskService, make_mock_production_task, "completed", "in_progress"),
        (InstallationTaskService, make_mock_installation_task, "completed", "in_progress"),
        (InstallationTaskService, make_mock_installation_task, "cancelled", "in_progress"),
    ],
)
async def test_terminal_unlinked_historical_task_cannot_change_status(
    service_class,
    task_factory,
    terminal_status,
    next_status,
):
    """终态且没有订单明细范围的历史任务只能查看，不能再次流转。"""
    db = AsyncMock()
    repo = MagicMock()
    task = task_factory(
        status=terminal_status,
        progress_pct=0 if terminal_status == "cancelled" else 100,
    )
    task.order_item_id = None
    repo.get_by_id = AsyncMock(return_value=task)

    service = service_class(db)
    service.repo = repo

    with (
        patch(
            "app.services.task_service._linked_order_item_ids",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.task_service._materialize_legacy_task_scope",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.task_service._validate_order_item_ids",
            new=AsyncMock(side_effect=ValueError("baseline status path")),
        ),
    ):
        with pytest.raises(
            ValueError,
            match="历史任务未关联订单明细，已结束任务仅可查看，不能变更状态",
        ):
            await service.change_status(
                SAMPLE_TASK_ID,
                next_status,
                SAMPLE_USER_ID,
                order_item_ids=[str(SAMPLE_ORDER_ITEM_ID)],
            )


# --- Get Task Tests ---

@pytest.mark.asyncio
async def test_get_task_found(service, mock_repo):
    """get_task returns correct data for an existing task."""
    task = make_mock_design_task()
    mock_repo.get_by_id.return_value = task

    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is not None
    assert result["id"] == str(SAMPLE_TASK_ID)
    assert result["design_no"] == "D20260629-0001"
    assert result["project_name"] == "测试设计任务"
    assert result["status"] == "pending"
    assert result["description"] == "这是一个测试设计任务"
    assert result["design_file_url"] is None
    assert result["client_comments"] is None


@pytest.mark.asyncio
async def test_get_task_not_found(service, mock_repo):
    """get_task returns None for a non-existent task."""
    mock_repo.get_by_id.return_value = None
    result = await service.get_task(SAMPLE_TASK_ID)
    assert result is None


# --- To Dict Serialization ---

@pytest.mark.asyncio
async def test_to_dict_includes_all_fields(service):
    """_to_dict properly serializes a design task object."""
    task = make_mock_design_task(
        task_id=SAMPLE_TASK_ID,
        design_no="D20260629-0042",
        status="designing",
        description="设计说明",
        design_file_url="https://example.com/design.pdf",
        client_comments="客户确认中",
        completed_at=None,
    )
    d = await service._to_dict(task)
    assert d["id"] == str(SAMPLE_TASK_ID)
    assert d["design_no"] == "D20260629-0042"
    assert d["status"] == "designing"
    assert d["description"] == "设计说明"
    assert d["design_file_url"] == "https://example.com/design.pdf"
    assert d["client_comments"] == "客户确认中"
    assert d["completed_at"] is None
    assert isinstance(d["attachments"], list)


@pytest.mark.asyncio
async def test_to_dict_with_attachments(service):
    """_to_dict serializes attachment objects."""
    att = MagicMock()
    att.id = "att-1"
    att.related_type = "design_task"
    att.related_id = SAMPLE_TASK_ID
    att.filename = "sketch.ai"
    att.file_path = "202606/sketch.ai"
    att.file_size = 2048
    att.file_type = "application/illustrator"
    att.category = "design"
    att.uploaded_by = SAMPLE_USER_ID
    att.remark = "初稿"
    att.created_at = datetime.now(timezone.utc)

    task = make_mock_design_task(attachments=[att])
    d = await service._to_dict(task)
    assert len(d["attachments"]) == 1
    assert d["attachments"][0]["filename"] == "sketch.ai"
    assert d["attachments"][0]["category"] == "design"


# --- List Tasks Tests ---

@pytest.mark.asyncio
async def test_list_tasks_empty(service, mock_repo):
    """list_tasks returns empty list when no tasks exist."""
    mock_repo.list_tasks.return_value = ([], 0)
    tasks, total = await service.list_tasks(page=1, page_size=20)
    assert tasks == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_tasks_with_results(service, mock_repo):
    """list_tasks returns serialized tasks and total count."""
    task1 = make_mock_design_task(task_id=SAMPLE_TASK_ID, project_name="项目A")
    task2 = make_mock_design_task(
        task_id=SAMPLE_USER_ID,
        design_no="D20260629-0002",
        project_name="项目B",
    )
    mock_repo.list_tasks.return_value = ([task1, task2], 2)

    with patch("app.services.task_service._enrich_task_order", side_effect=lambda db, d: d):
        tasks, total = await service.list_tasks(page=1, page_size=20)
    assert total == 2
    assert len(tasks) == 2
    assert tasks[0]["project_name"] == "项目A"
    assert tasks[1]["project_name"] == "项目B"


# --- Create Task Tests ---

@pytest.mark.asyncio
async def test_create_task(service, mock_repo):
    """create_task sets design_no, status, and returns serialized result."""
    order = MagicMock(
        doc_type="order",
        deleted_at=None,
        status="confirmed",
        customer_id=SAMPLE_USER_ID,
        project_name="订单项目",
    )
    item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=SAMPLE_TASK_ID,
        lifecycle_status="active",
    )
    service.db.get.side_effect = [order, item]

    async def create_side_effect(data):
        return make_mock_design_task(
            design_no="D20260629-0050",
            project_name=data.get("project_name", "默认"),
        )

    mock_repo.create.side_effect = create_side_effect

    with (
        patch("app.services.task_service.generate_design_no", AsyncMock(return_value="D20260629-0050")),
        patch(
            "app.services.task_service._task_order_item_option_map",
            AsyncMock(return_value={SAMPLE_ORDER_ITEM_ID: {"can_select": True}}),
        ),
    ):
        result = await service.create_task({
            "order_id": SAMPLE_TASK_ID,
            "order_item_id": SAMPLE_ORDER_ITEM_ID,
            "customer_id": SAMPLE_USER_ID,
            "project_name": "新设计",
        })

    assert result["design_no"] == "D20260629-0050"
    assert result["project_name"] == "新设计"
    created_data = mock_repo.create.await_args.args[0]
    assert created_data["document_id"] == SAMPLE_TASK_ID
    assert created_data["customer_id"] == SAMPLE_USER_ID
    assert "order_id" not in created_data


@pytest.mark.asyncio
async def test_create_task_rejects_order_outside_design_stage(service, mock_repo):
    service.db.get.return_value = MagicMock(
        doc_type="order",
        deleted_at=None,
        status="cancelled",
        customer_id=SAMPLE_USER_ID,
        project_name="已取消的订单",
    )

    with pytest.raises(ValueError, match="当前状态不能创建设计任务"):
        await service.create_task({"order_id": SAMPLE_TASK_ID})

    mock_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_task_create_data_requires_order_item(service):
    """New tasks must be scoped to at least one order detail."""
    service.db.get.return_value = MagicMock(
        doc_type="order",
        deleted_at=None,
        status="confirmed",
        customer_id=SAMPLE_USER_ID,
        project_name="订单项目",
    )

    with pytest.raises(ValueError, match="至少选择一条订单明细"):
        await _prepare_task_create_data(
            service.db,
            {"order_id": str(SAMPLE_TASK_ID)},
            allowed_order_statuses=("confirmed",),
            task_label="设计",
            task_type="design",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "service_name", "payload", "expected_key"),
    [
        (
            task_api.create_design_task,
            "DesignTaskService",
            DesignTaskCreate(
                order_id=str(SAMPLE_TASK_ID),
                order_item_id=str(SAMPLE_ORDER_ITEM_ID),
            ),
            "order_item_id",
        ),
        (
            task_api.create_production_task,
            "ProductionTaskService",
            ProductionTaskCreate(
                order_id=str(SAMPLE_TASK_ID),
                order_item_ids=[str(SAMPLE_ORDER_ITEM_ID)],
            ),
            "order_item_ids",
        ),
        (
            task_api.create_installation_task,
            "InstallationTaskService",
            InstallationTaskCreate(
                order_id=str(SAMPLE_TASK_ID),
                order_item_ids=[str(SAMPLE_ORDER_ITEM_ID)],
            ),
            "order_item_ids",
        ),
    ],
)
async def test_task_create_endpoint_omits_none_item_alias(
    endpoint,
    service_name,
    payload,
    expected_key,
):
    """Create endpoints must not pass the other optional item alias as null."""
    service = MagicMock()
    service.create_task = AsyncMock(return_value={"id": "task-id"})
    current_user = MagicMock(id=SAMPLE_USER_ID)

    with patch.object(task_api, service_name, return_value=service):
        await endpoint(payload, AsyncMock(), current_user)

    create_payload = service.create_task.await_args.args[0]
    assert expected_key in create_payload
    omitted_key = "order_item_ids" if expected_key == "order_item_id" else "order_item_id"
    assert omitted_key not in create_payload


# --- Update Task Tests ---

@pytest.mark.asyncio
async def test_update_task(service, mock_repo):
    """update_task modifies and returns updated task."""
    task = make_mock_design_task(project_name="旧名称")
    mock_repo.get_by_id.return_value = task
    mock_repo.update.return_value = make_mock_design_task(project_name="新名称")

    result = await service.update_task(SAMPLE_TASK_ID, {"project_name": "新名称"})
    assert result["project_name"] == "新名称"


@pytest.mark.asyncio
async def test_update_nonexistent_task(service, mock_repo):
    """update_task on a non-existent task raises ValueError."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(ValueError, match="设计任务不存在"):
        await service.update_task(SAMPLE_TASK_ID, {"project_name": "新名称"})


# --- is_outsourced 标识 ---

@pytest.mark.asyncio
async def test_list_tasks_marks_outsourced(service, mock_repo):
    """list_tasks 批量标记 is_outsourced：有未删除外协任务的为 True。"""
    from tests.conftest import MockResult
    task1 = make_mock_design_task(task_id=SAMPLE_TASK_ID, project_name="已外协")
    task2 = make_mock_design_task(task_id=SAMPLE_USER_ID, design_no="D20260629-0002", project_name="未外协")
    mock_repo.list_tasks.return_value = ([task1, task2], 2)
    # 外协表只返回 task1 的 id
    service.db.execute.return_value = MockResult(scalars_return=[SAMPLE_TASK_ID])
    with patch("app.services.task_service._enrich_task_order", side_effect=lambda db, d: d):
        tasks, total = await service.list_tasks(page=1, page_size=20)
    assert total == 2
    flags = {t["project_name"]: t["is_outsourced"] for t in tasks}
    assert flags["已外协"] is True
    assert flags["未外协"] is False


@pytest.mark.asyncio
async def test_list_tasks_outsourced_filter_passes_to_repo(service, mock_repo):
    """list_tasks 把 outsourced 过滤透传给 repo。"""
    mock_repo.list_tasks.return_value = ([], 0)
    await service.list_tasks(page=1, page_size=20, outsourced=True)
    assert mock_repo.list_tasks.call_args.kwargs["outsourced"] is True
