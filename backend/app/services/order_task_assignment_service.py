"""Order-scoped visibility and employee assignment rules for delivery tasks."""

from __future__ import annotations

import inspect
from uuid import UUID

from sqlalchemy import exists, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    PERM_DESIGN_TASK_ASSIGN,
    PERM_INSTALLATION_TASK_ASSIGN,
    PERM_ORDER_TASK_ASSIGN,
    PERM_PRODUCTION_TASK_ASSIGN,
    PERM_TASK_QUEUE_VIEW_ALL,
    user_has_permission,
)
from app.models.business_document import BusinessDocument
from app.models.employee import Employee
from app.models.order_task_assignee import OrderTaskAssignee
from app.models.user import User
from app.repositories.order_task_assignee_repo import OrderTaskAssigneeRepository


TASK_ASSIGN_PERMISSION_BY_TYPE = {
    "design": PERM_DESIGN_TASK_ASSIGN,
    "production": PERM_PRODUCTION_TASK_ASSIGN,
    "installation": PERM_INSTALLATION_TASK_ASSIGN,
}


def can_assign_task(task_type: str, viewer: User | None) -> bool:
    """Whether a viewer may choose or change a task-level assignee."""
    if viewer is None:
        return True
    permission = TASK_ASSIGN_PERMISSION_BY_TYPE.get(task_type)
    return permission is not None and user_has_permission(viewer, permission)


def can_manage_order_task_assignments(viewer: User | None) -> bool:
    return viewer is None or user_has_permission(viewer, PERM_ORDER_TASK_ASSIGN)


def can_view_all_task_scope(viewer: User | None) -> bool:
    """Whether a viewer may see every task without managing assignments."""
    return (
        viewer is None
        or can_manage_order_task_assignments(viewer)
        or user_has_permission(viewer, PERM_TASK_QUEUE_VIEW_ALL)
    )


def order_task_visibility_clause(model, viewer: User | None):
    """Return the SQL predicate for a task visible to ``viewer``.

    No rows in ``order_task_assignees`` means unrestricted visibility. Once an
    order has one or more rows, only an active employee bound to the current
    login may see its tasks. Users with either the assignment-management
    permission or the separate read-only all-scope permission bypass the row
    filter; only the former may maintain assignments.
    """
    if can_view_all_task_scope(viewer):
        return true()

    task_table = getattr(model, "__table__", model)
    assignee_table = OrderTaskAssignee.__table__
    employee_table = Employee.__table__
    document_id = task_table.c.document_id
    assignment_exists = exists(
        select(assignee_table.c.id).where(
            assignee_table.c.document_id == document_id,
        )
    )
    viewer_assignment_exists = exists(
        select(assignee_table.c.id)
        .select_from(assignee_table.join(employee_table, employee_table.c.id == assignee_table.c.employee_id))
        .where(
            assignee_table.c.document_id == document_id,
            employee_table.c.user_id == viewer.id,
            employee_table.c.is_active.is_(True),
            employee_table.c.employment_status == "active",
            employee_table.c.deleted_at.is_(None),
        )
    )
    return or_(~assignment_exists, viewer_assignment_exists)


def task_visibility_clause(model, viewer: User | None):
    """Backward-friendly alias for repositories and attachment checks."""
    return order_task_visibility_clause(model, viewer)


async def get_visible_task(
    db: AsyncSession,
    model,
    task_id: UUID,
    viewer: User | None,
):
    result = await db.execute(
        select(model).where(
            model.id == task_id,
            task_visibility_clause(model, viewer),
        )
    )
    row = result.scalar_one_or_none()
    if inspect.isawaitable(row):
        row = await row
    return row


def _employee_is_active_clause():
    return (
        Employee.is_active.is_(True),
        Employee.employment_status == "active",
        Employee.deleted_at.is_(None),
        Employee.user_id.is_not(None),
    )


def _employee_payload(employee: Employee) -> dict[str, str | None]:
    return {
        "id": str(employee.id),
        "name": employee.name,
        "employee_no": employee.employee_no,
        "user_id": str(employee.user_id) if employee.user_id else None,
    }


async def list_task_assignee_options(db: AsyncSession) -> list[dict[str, str | None]]:
    """List only active employees that can actually own a task."""
    result = await db.execute(
        select(Employee)
        .where(*_employee_is_active_clause())
        .order_by(Employee.name, Employee.employee_no)
    )
    return [_employee_payload(employee) for employee in result.scalars().all()]


async def resolve_current_employee_user_id(db: AsyncSession, viewer: User) -> UUID:
    """Resolve the login to an active employee for ordinary status changes."""
    viewer_id = getattr(viewer, "id", None)
    if viewer_id is None:
        raise ValueError("当前登录账号未绑定在职员工，无法变更任务状态，请联系管理员完善员工绑定")

    result = await db.execute(
        select(Employee).where(
            Employee.user_id == viewer_id,
            *_employee_is_active_clause(),
        )
    )
    employee = result.scalar_one_or_none()
    if inspect.isawaitable(employee):
        employee = await employee
    if employee is None or employee.user_id is None:
        raise ValueError("当前登录账号未绑定在职员工，无法变更任务状态，请联系管理员完善员工绑定")
    return employee.user_id


async def validate_task_assignee(
    db: AsyncSession,
    raw_assigned_to,
) -> UUID | None:
    """Validate a privileged task assignment against an active employee binding."""
    if raw_assigned_to in (None, ""):
        return None
    try:
        assigned_to = raw_assigned_to if isinstance(raw_assigned_to, UUID) else UUID(str(raw_assigned_to))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("分配人无效，请重新选择") from exc

    result = await db.execute(
        select(User)
        .join(Employee, Employee.user_id == User.id)
        .where(
            User.id == assigned_to,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            *_employee_is_active_clause(),
        )
    )
    user = result.scalar_one_or_none()
    if inspect.isawaitable(user):
        user = await user
    if user is None:
        raise ValueError("所选分配人不存在或已停用，请重新选择")
    return assigned_to


async def _ensure_order(db: AsyncSession, order_id: UUID) -> BusinessDocument:
    order = await db.get(BusinessDocument, order_id)
    if (
        order is None
        or order.doc_type != "order"
        or order.deleted_at is not None
    ):
        raise ValueError("订单不存在或已删除")
    return order


async def get_order_task_assignees(
    db: AsyncSession,
    order_id: UUID,
) -> dict:
    await _ensure_order(db, order_id)
    repo = OrderTaskAssigneeRepository(db)
    rows = await repo.list_for_order_with_employees(order_id)
    employees = [_employee_payload(employee) for _, employee in rows]
    return {
        "order_id": str(order_id),
        "employee_ids": [entry["id"] for entry in employees],
        "employees": employees,
        "is_restricted": bool(employees),
    }


async def replace_order_task_assignees(
    db: AsyncSession,
    order_id: UUID,
    raw_employee_ids: list[str | UUID],
    assigned_by: UUID | None,
) -> dict:
    await _ensure_order(db, order_id)

    employee_ids: list[UUID] = []
    seen: set[UUID] = set()
    for raw_employee_id in raw_employee_ids:
        try:
            employee_id = raw_employee_id if isinstance(raw_employee_id, UUID) else UUID(str(raw_employee_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("员工编号格式不正确，请重新选择") from exc
        if employee_id in seen:
            raise ValueError("分配员工不能重复")
        seen.add(employee_id)
        employee_ids.append(employee_id)

    if employee_ids:
        result = await db.execute(
            select(Employee).where(
                Employee.id.in_(employee_ids),
                *_employee_is_active_clause(),
            )
        )
        employees = list(result.scalars().all())
        employee_map = {employee.id: employee for employee in employees}
        missing = [employee_id for employee_id in employee_ids if employee_id not in employee_map]
        if missing:
            raise ValueError("只能分配给已绑定登录账号的在职员工")

    repo = OrderTaskAssigneeRepository(db)
    await repo.replace(order_id, employee_ids, assigned_by)
    return await get_order_task_assignees(db, order_id)
