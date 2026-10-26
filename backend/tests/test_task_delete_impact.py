"""Task deletion previews must describe the existing cascade and reject stale confirmation."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api import tasks as api
from app.models.acceptance import AcceptanceForm
from app.models.business_document import BusinessDocument
from app.models.outsource import OutsourceTask
from app.models.task import DesignTask, ProductionTask, InstallationTask
from app.models.task_order_item_link import TaskOrderItemLink
from app.services.task_service import get_task_delete_impact, validate_task_delete_impact

MODELS = {"design": DesignTask, "production": ProductionTask, "installation": InstallationTask}
NUMBERS = {"design": "design_no", "production": "production_no", "installation": "installation_no"}


@pytest.fixture
def graph():
    order = SimpleNamespace(id=uuid4(), doc_type="order", doc_no="O-001", status="in_installation", updated_at=datetime(2026, 10, 27))
    tasks = {}
    links = []
    for kind in MODELS:
        task = SimpleNamespace(id=uuid4(), document_id=order.id, status="in_progress", updated_at=order.updated_at,
                               created_at=order.updated_at, order_item_id=None, scope_status="active", attachments=[])
        setattr(task, NUMBERS[kind], f"{kind}-001")
        tasks[kind] = task
        links.append(SimpleNamespace(id=uuid4(), task_type=kind, task_id=task.id, order_item_id=uuid4(), item_status="pending",
                                     item_progress_pct=0, assignee_user_id=None, planned_quantity=10, completed_quantity=None, link_status="active"))
    order.items = [SimpleNamespace(id=link.order_item_id, item_name=f"{link.task_type}明细", quantity=10,
                                   updated_at=order.updated_at, lifecycle_status="active") for link in links]
    acceptance = SimpleNamespace(id=uuid4(), acceptance_no="A-001", status="draft", updated_at=order.updated_at)
    external = [SimpleNamespace(id=uuid4(), task_no=f"OT-{kind}", status="pending", updated_at=order.updated_at,
                                deleted_at=None, source_task_type=kind, source_task_id=task.id) for kind, task in tasks.items()]
    db = AsyncMock()
    db.get.return_value = order
    statements = []

    async def execute(statement):
        statements.append(statement)
        entity = statement.column_descriptions[0]["entity"]
        params = statement.compile().params
        if entity in MODELS.values():
            rows = [task for kind, task in tasks.items() if MODELS[kind] == entity]
        elif entity == TaskOrderItemLink:
            rows = [link for link in links if link.task_type == params["task_type_1"] and link.task_id == params["task_id_1"]]
        elif entity == AcceptanceForm:
            rows = [acceptance]
        elif entity == OutsourceTask:
            source_ids = [value for key, value in params.items() if key.startswith("source_task_id_")]
            rows = [row for row in external if row.source_task_id in source_ids]
        else:
            raise AssertionError(f"Unexpected preview query: {entity}")
        result = MagicMock()
        result.scalar_one_or_none.return_value = rows[0] if rows else None
        result.scalars.return_value.all.return_value = rows
        return result

    db.execute.side_effect = execute
    return SimpleNamespace(db=db, order=order, tasks=tasks, links=links, acceptance=acceptance, external=external, statements=statements)


async def preview(graph, kind="design", **kwargs):
    with patch("app.services.task_service.get_visible_task", AsyncMock(return_value=graph.tasks[kind])):
        return await get_task_delete_impact(graph.db, kind, graph.tasks[kind].id, None, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,status,deleted,target,reopened", [
    ("design", "confirmed", 1, None, 0),
    ("design", "designing", 3, "confirmed", 0),
    ("design", "in_installation", 3, "confirmed", 0),
    ("production", "designing", 1, None, 0),
    ("production", "in_production", 2, "designing", 1),
    ("production", "in_installation", 2, "designing", 1),
    ("installation", "in_production", 1, None, 0),
    ("installation", "in_installation", 1, "in_production", 1),
    ("installation", "completed", 1, None, 0),
])
async def test_preview_matches_conditional_cascade(graph, kind, status, deleted, target, reopened):
    graph.order.status = status
    result = await preview(graph, kind)
    effects = [entry["effect"] for entry in result["entries"]]
    assert effects.count("delete_task") == deleted
    assert effects.count("unlink_outsource") == deleted
    assert effects.count("recycle_acceptance") == bool(target)
    assert effects.count("reopen_task") == reopened
    assert result["target_order_status"] == target
    assert len(result["plan_hash"]) == 64
    assert next(entry for entry in result["entries"] if entry["id"] == str(graph.tasks[kind].id))["items"] == [f"{kind}明细"]
    graph.db.delete.assert_not_awaited()
    graph.db.flush.assert_not_awaited()
    assert graph.order.status == status


@pytest.mark.asyncio
async def test_fingerprint_detects_item_assignment_and_downstream_changes(graph):
    initial = await preview(graph)
    assert (await preview(graph))["plan_hash"] == initial["plan_hash"]
    graph.links[1].assignee_user_id = uuid4()
    assigned = await preview(graph)
    assert assigned["plan_hash"] != initial["plan_hash"]
    graph.tasks["installation"].status = "completed"
    assert (await preview(graph))["plan_hash"] != assigned["plan_hash"]


@pytest.mark.asyncio
async def test_stale_confirmation_is_rejected_and_snapshot_is_locked(graph):
    initial = await preview(graph)
    graph.order.status = "completed"
    with patch("app.services.task_service.get_visible_task", AsyncMock(return_value=graph.tasks["design"])):
        with pytest.raises(ValueError, match="关联数据已变化"):
            await validate_task_delete_impact(graph.db, "design", graph.tasks["design"].id, None, initial["plan_hash"])
    assert graph.db.get.call_args.kwargs["with_for_update"] is True
    assert any(statement._for_update_arg is not None for statement in graph.statements)
    graph.db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_or_invisible_task_is_not_previewed(graph):
    with patch("app.services.task_service.get_visible_task", AsyncMock(return_value=None)):
        with pytest.raises(ValueError, match="任务不存在或没有访问权限"):
            await get_task_delete_impact(graph.db, "design", uuid4(), None)
    graph.db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_related_record_labels_are_hidden_without_module_read_permission(graph):
    viewer = SimpleNamespace(id=uuid4())
    with patch("app.services.task_service.get_visible_task", AsyncMock(return_value=graph.tasks["design"])), \
         patch("app.services.task_service.user_has_permission", return_value=False), \
         patch("app.services.task_service.can_view_outsource_tasks", return_value=False):
        result = await get_task_delete_impact(graph.db, "design", graph.tasks["design"].id, viewer)
    labels = " ".join(entry["label"] for entry in result["entries"])
    assert "design-001" in labels
    assert "production-001" not in labels
    assert "installation-001" not in labels
    assert "OT-design" not in labels
    assert "A-001" not in labels
    assert "无详情查看权限" in labels


@pytest.mark.asyncio
async def test_preview_requires_permission_for_requested_task_type(graph):
    with patch("app.api.tasks._user_has_permission", return_value=False), \
         patch("app.api.tasks.get_task_delete_impact", AsyncMock()) as get_impact:
        with pytest.raises(HTTPException) as error:
            await api.preview_task_delete(task_type="installation", task_id=str(uuid4()), db=graph.db, current_user=SimpleNamespace())
    assert error.value.status_code == 403
    get_impact.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["design", "production", "installation"])
async def test_stale_confirmation_never_calls_delete_service(graph, kind):
    method = getattr(api, f"delete_{kind}_task")
    service_class = {"design": "DesignTaskService", "production": "ProductionTaskService", "installation": "InstallationTaskService"}[kind]
    with patch(f"app.api.tasks.{service_class}") as service, \
         patch("app.api.tasks.validate_task_delete_impact", AsyncMock(side_effect=ValueError("关联数据已变化"))):
        service.return_value.delete_task = AsyncMock()
        result = await method(task_id=str(graph.tasks[kind].id), plan_hash="a" * 64, db=graph.db, current_user=SimpleNamespace())
    assert result["code"] == 40001
    service.return_value.delete_task.assert_not_awaited()
