"""CPB-P01: completed project board scope and response-contract tests."""

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.api import tasks
from app.core.permissions import (
    PERM_DESIGN_TASK_READ,
    PERM_PRODUCTION_TASK_READ,
    PERM_TASK_COMPLETION_READ,
)
from app.services.completed_project_board_service import (
    aggregate_completed_project_cards,
    CompletedProjectBoardService,
    CompletedProjectNotFound,
    build_completed_project_detail,
    serialize_completed_project_resources,
)
from app.services.task_completion_metrics_service import CompletionEvent


PROJECT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ITEM_A = UUID("11111111-1111-1111-1111-111111111111")
ITEM_B = UUID("22222222-2222-2222-2222-222222222222")
TASK_A = UUID("33333333-3333-3333-3333-333333333333")
USER_ME = UUID("44444444-4444-4444-4444-444444444444")
USER_OTHER = UUID("55555555-5555-5555-5555-555555555555")


def _document(project_id: UUID, *, amount: str = "1200.00"):
    return SimpleNamespace(
        id=project_id,
        doc_no=f"O-{str(project_id)[:4]}",
        project_name=f"项目-{str(project_id)[:4]}",
        customer_name="测试客户",
        department="设计部",
        total_amount=amount,
    )


def _event(
    project_id: UUID,
    item_id: UUID,
    *,
    assignee_user_id: UUID | None,
    task_type: str = "design",
    completed_at: datetime = datetime(2026, 9, 10, 10),
    item_name: str = "门头字",
):
    return CompletionEvent(
        id=TASK_A,
        task_type=task_type,
        task_id=TASK_A,
        document_id=project_id,
        order_item_id=item_id,
        to_status="confirmed" if task_type == "design" else "completed",
        operated_at=completed_at,
        assignee_user_id=assignee_user_id,
        project_no=f"O-{str(project_id)[:4]}",
        project_name=f"项目-{str(project_id)[:4]}",
        item_name=item_name,
        task_no="D20260910-0001",
        assignee_name="本人" if assignee_user_id == USER_ME else "其他员工",
    )


def _item(
    item_id: UUID,
    *,
    name: str,
    sort_order: int,
    material_process: str = "铝板彩印",
    length: str | None = "1.2",
    length_unit: str = "m",
    width: str | None = "0.8",
    width_unit: str = "m",
    height: str | None = None,
    height_unit: str = "m",
    quantity: str = "3",
    unit: str = "个",
):
    return SimpleNamespace(
        id=item_id,
        item_name=name,
        material_process=material_process,
        length=length,
        length_unit=length_unit,
        width=width,
        width_unit=width_unit,
        height=height,
        height_unit=height_unit,
        quantity=quantity,
        unit=unit,
        sort_order=sort_order,
    )


def test_employee_cards_are_limited_to_own_completed_work_units():
    documents = [_document(PROJECT_A), _document(PROJECT_B)]
    events = [
        _event(PROJECT_A, ITEM_A, assignee_user_id=USER_OTHER),
        _event(PROJECT_B, ITEM_B, assignee_user_id=USER_ME),
    ]

    rows = aggregate_completed_project_cards(
        documents,
        {PROJECT_A: datetime(2026, 9, 10, 12), PROJECT_B: datetime(2026, 9, 11, 12)},
        events,
        scope="own",
        include_amount=False,
        owner_user_id=USER_ME,
    )

    assert [row["project_id"] for row in rows] == [str(PROJECT_B)]
    assert rows[0]["completed_detail_count"] == 1
    assert "total_amount" not in rows[0]


def test_admin_cards_include_legacy_completed_project_without_item_events():
    rows = aggregate_completed_project_cards(
        [_document(PROJECT_A)],
        {PROJECT_A: datetime(2026, 9, 10, 12)},
        [],
        scope="all",
        include_amount=True,
    )

    assert len(rows) == 1
    assert rows[0]["completed_detail_count"] == 0
    assert rows[0]["completed_work_unit_count"] == 0
    assert rows[0]["total_amount"] == 1200.0


def test_project_detail_exposes_only_the_events_in_the_resolved_scope():
    event = _event(PROJECT_B, ITEM_B, assignee_user_id=USER_ME)

    detail = build_completed_project_detail(
        _document(PROJECT_B),
        datetime(2026, 9, 11, 12),
        [event],
        scope="own",
        include_amount=False,
        owner_user_id=USER_ME,
    )

    assert detail["project_id"] == str(PROJECT_B)
    assert [item["order_item_id"] for item in detail["items"]] == [str(ITEM_B)]
    assert detail["items"][0]["stages"]["design"]["employee_name"] == "本人"
    assert "total_amount" not in detail
    assert not {"unit_price", "subtotal_amount", "cost_amount", "gross_profit"}.intersection(detail)


def test_project_detail_is_one_row_per_order_item_and_keeps_stage_owners_independent():
    document = _document(PROJECT_A)
    items = [
        _item(ITEM_B, name="节目单", sort_order=1),
        _item(ITEM_A, name="标识牌", sort_order=0, material_process="亚克力发光字"),
    ]
    design_event = _event(
        PROJECT_A,
        ITEM_A,
        assignee_user_id=USER_ME,
        task_type="design",
        item_name="标识牌",
    )
    design_event.task_no = "D-0001"
    production_event = _event(
        PROJECT_A,
        ITEM_A,
        assignee_user_id=USER_OTHER,
        task_type="production",
        item_name="标识牌",
    )
    production_event.task_no = "P-0001"
    detail = build_completed_project_detail(
        document,
        datetime(2026, 9, 10, 12),
        [production_event, design_event],
        scope="all",
        include_amount=False,
        order_items=items,
    )

    assert [row["item_name"] for row in detail["items"]] == ["标识牌", "节目单"]
    assert len(detail["items"]) == 2
    row = detail["items"][0]
    assert row["material_process"] == "亚克力发光字"
    assert row["specification"] == "1.2m × 0.8m"
    assert row["quantity"] == 3.0
    assert row["unit"] == "个"
    assert row["stages"]["design"]["employee_name"] == "本人"
    assert row["stages"]["production"]["employee_name"] == "其他员工"
    assert row["stages"]["design"]["task_no"] == "D-0001"
    assert row["stages"]["production"]["task_no"] == "P-0001"
    assert "task_type" not in row
    assert "employee_name" not in row


def test_employee_detail_does_not_expose_other_employee_stage_snapshot():
    document = _document(PROJECT_A)
    items = [_item(ITEM_A, name="标识牌", sort_order=0)]
    own_design = _event(PROJECT_A, ITEM_A, assignee_user_id=USER_ME, task_type="design")
    other_production = _event(PROJECT_A, ITEM_A, assignee_user_id=USER_OTHER, task_type="production")

    detail = build_completed_project_detail(
        document,
        datetime(2026, 9, 10, 12),
        [own_design, other_production],
        scope="own",
        include_amount=False,
        owner_user_id=USER_ME,
        order_items=items,
    )

    row = detail["items"][0]
    assert row["stages"]["design"]["employee_name"] == "本人"
    assert row["stages"]["production"] is None


def test_project_detail_resource_serializer_groups_tasks_and_filters_installation_to_media():
    task = SimpleNamespace(
        id=TASK_A,
        installation_no="I-0001",
        created_at=datetime(2026, 9, 10, 9),
    )
    photo = SimpleNamespace(
        id=UUID("66666666-6666-6666-6666-666666666666"),
        related_type="installation_task",
        related_id=TASK_A,
        filename="现场.jpg",
        file_path="202609/现场.jpg",
        file_size=120,
        file_type="image/jpeg",
        category="photo",
        uploaded_by=USER_ME,
        remark=None,
        created_at=datetime(2026, 9, 10, 10),
    )
    non_media = SimpleNamespace(
        id=UUID("77777777-7777-7777-7777-777777777777"),
        related_type="installation_task",
        related_id=TASK_A,
        filename="说明.pdf",
        file_path="202609/说明.pdf",
        file_size=120,
        file_type="application/pdf",
        category="pdf",
        uploaded_by=USER_ME,
        remark=None,
        created_at=datetime(2026, 9, 10, 10),
    )

    resources = serialize_completed_project_resources(
        "installation",
        [task],
        [photo, non_media],
    )

    assert resources["task_count"] == 1
    assert resources["attachment_count"] == 1
    assert resources["tasks"][0]["task_no"] == "I-0001"
    assert resources["tasks"][0]["attachments"][0]["filename"] == "现场.jpg"


def test_stage_visibility_is_the_intersection_of_composed_stage_permissions():
    viewer = SimpleNamespace(
        id=USER_ME,
        roles=[SimpleNamespace(permissions=[
            SimpleNamespace(code=PERM_DESIGN_TASK_READ),
            SimpleNamespace(code=PERM_PRODUCTION_TASK_READ),
        ])],
    )
    service = CompletedProjectBoardService(None, viewer)

    assert service.allowed_task_types() == ["design", "production"]
    assert service.allowed_task_types("design") == ["design"]
    assert service.allowed_task_types("installation") == []


def test_completed_project_routes_require_personal_completion_read_permission():
    routes = {
        route.path: route
        for route in tasks.queue_router.routes
        if route.path in {
            "/task-queue/completed-projects",
            "/task-queue/completed-projects/{project_id}",
        }
    }

    assert set(routes) == {
        "/task-queue/completed-projects",
        "/task-queue/completed-projects/{project_id}",
    }
    for route in routes.values():
        permissions = set()
        for dependency in route.dependant.dependencies:
            call = dependency.call
            closure = getattr(call, "__closure__", None)
            if getattr(call, "__name__", None) != "dependency" or not closure:
                continue
            for cell in closure:
                value = cell.cell_contents
                if isinstance(value, str) and ":" in value:
                    permissions.add(value)
        assert permissions == {PERM_TASK_COMPLETION_READ}


@pytest.mark.asyncio
async def test_non_super_admin_cannot_expand_scope_without_own_completion_event():
    """The service contract must keep an inaccessible project indistinguishable from missing."""
    service = object.__new__(CompletedProjectBoardService)
    service._resolved_scope = "own"
    service._resolved_owner_user_id = USER_ME

    with pytest.raises(CompletedProjectNotFound):
        service.ensure_project_in_scope(PROJECT_A, {PROJECT_B})
