from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import DesignTask, InstallationTask, ProductionTask
from app.models.task_dependency import TaskDependency
from app.schemas.task_dependency import (
    TaskDependencyCreate,
    TaskDependencyResponse,
    TaskDependencyTaskSummary,
)


TASK_MODELS = {
    "design": DesignTask,
    "production": ProductionTask,
    "installation": InstallationTask,
}

TASK_NO_FIELDS = {
    "design": "design_no",
    "production": "production_no",
    "installation": "installation_no",
}

SUCCESS_STATUSES = {
    "design": {"confirmed", "completed"},
    "production": {"completed"},
    "installation": {"completed"},
}

PROGRESSION_STATUSES = {
    "design": {"designing", "pending_review", "confirmed"},
    "production": {"in_progress", "completed"},
    "installation": {"in_progress", "pending_acceptance", "completed"},
}


def _task_key(task_type: str, task_id: str | UUID) -> tuple[str, str]:
    return task_type, str(task_id)


def _task_model(task_type: str):
    try:
        return TASK_MODELS[task_type]
    except KeyError as exc:
        raise ValueError(f"不支持的任务类型：{task_type}") from exc


def dependency_edge_would_cycle(
    edges: set[tuple[tuple[str, str], tuple[str, str]]],
    predecessor: tuple[str, str],
    successor: tuple[str, str],
) -> bool:
    """Return whether adding predecessor -> successor would create a cycle."""
    adjacency: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for edge_predecessor, edge_successor in edges:
        adjacency[edge_predecessor].add(edge_successor)

    pending = [successor]
    visited: set[tuple[str, str]] = set()
    while pending:
        current = pending.pop()
        if current == predecessor:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, ()))
    return False


def dependency_status_is_satisfied(task_type: str, status: str) -> bool:
    return status in SUCCESS_STATUSES.get(task_type, set())


def progression_statuses_for(task_type: str) -> set[str]:
    return set(PROGRESSION_STATUSES.get(task_type, set()))


async def _get_task(db: AsyncSession, task_type: str, task_id: UUID):
    return await db.get(_task_model(task_type), task_id)


def _task_summary(task_type: str, task) -> dict:
    task_no = getattr(task, TASK_NO_FIELDS[task_type])
    document_id = getattr(task, "document_id", None)
    return {
        "task_type": task_type,
        "task_id": str(task.id),
        "task_no": task_no,
        "order_id": str(document_id) if document_id else None,
        "project_name": task.project_name,
        "status": task.status,
        "progress_pct": int(task.progress_pct or 0),
    }


def _missing_task_summary(task_type: str, task_id: UUID) -> dict:
    return {
        "task_type": task_type,
        "task_id": str(task_id),
        "task_no": str(task_id),
        "order_id": None,
        "project_name": "任务已删除",
        "status": "deleted",
        "progress_pct": 0,
    }


async def get_task_dependency_state(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
) -> dict:
    """Compute the current blocking state from incoming dependency edges."""
    result = await db.execute(
        select(TaskDependency).where(
            TaskDependency.successor_task_type == task_type,
            TaskDependency.successor_task_id == task_id,
        )
    )
    dependencies = list(result.scalars().all())
    blocking_tasks: list[dict] = []
    for dependency in dependencies:
        if not isinstance(dependency, TaskDependency):
            # Keeps the helper tolerant of lightweight repository mocks and
            # legacy adapters that return scalar IDs for unrelated queries.
            continue
        predecessor = await _get_task(
            db,
            dependency.predecessor_task_type,
            dependency.predecessor_task_id,
        )
        summary = (
            _task_summary(dependency.predecessor_task_type, predecessor)
            if predecessor
            else _missing_task_summary(
                dependency.predecessor_task_type,
                dependency.predecessor_task_id,
            )
        )
        if not predecessor or not dependency_status_is_satisfied(
            dependency.predecessor_task_type,
            predecessor.status,
        ):
            blocking_tasks.append(summary)

    if not blocking_tasks:
        return {
            "is_blocked": False,
            "blocked_reason": None,
            "blocking_tasks": [],
        }

    task_numbers = "、".join(item["task_no"] for item in blocking_tasks)
    return {
        "is_blocked": True,
        "blocked_reason": f"前置任务未完成或已取消：{task_numbers}",
        "blocking_tasks": blocking_tasks,
    }


async def enrich_task_dict_with_dependency_state(
    db: AsyncSession,
    task_type: str,
    task_dict: dict,
) -> dict:
    task_id = task_dict.get("id")
    if not task_id:
        task_dict.update(
            {"is_blocked": False, "blocked_reason": None, "blocking_tasks": []}
        )
        return task_dict
    state = await get_task_dependency_state(db, task_type, UUID(str(task_id)))
    task_dict.update(state)
    return task_dict


async def _dependency_to_dict(db: AsyncSession, dependency: TaskDependency) -> dict:
    predecessor = await _get_task(
        db,
        dependency.predecessor_task_type,
        dependency.predecessor_task_id,
    )
    successor = await _get_task(
        db,
        dependency.successor_task_type,
        dependency.successor_task_id,
    )
    if not predecessor or not successor:
        raise ValueError("依赖关系引用的任务不存在")
    data = {
        "id": str(dependency.id),
        "dependency_type": dependency.dependency_type,
        "predecessor": _task_summary(dependency.predecessor_task_type, predecessor),
        "successor": _task_summary(dependency.successor_task_type, successor),
        "is_satisfied": dependency_status_is_satisfied(
            dependency.predecessor_task_type,
            predecessor.status,
        ),
        "created_by": str(dependency.created_by) if dependency.created_by else None,
        "created_at": dependency.created_at.isoformat() if dependency.created_at else None,
        "updated_at": dependency.updated_at.isoformat() if dependency.updated_at else None,
    }
    return TaskDependencyResponse.model_validate(data).model_dump(mode="json")


async def list_task_dependencies(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
) -> list[dict]:
    _task_model(task_type)
    result = await db.execute(
        select(TaskDependency).where(
            or_(
                and_(
                    TaskDependency.predecessor_task_type == task_type,
                    TaskDependency.predecessor_task_id == task_id,
                ),
                and_(
                    TaskDependency.successor_task_type == task_type,
                    TaskDependency.successor_task_id == task_id,
                ),
            )
        ).order_by(TaskDependency.created_at.asc())
    )
    dependencies = []
    for dependency in result.scalars().all():
        try:
            dependencies.append(await _dependency_to_dict(db, dependency))
        except ValueError:
            # A deleted task is cleaned up transactionally; skip any legacy
            # dangling row instead of breaking the whole task detail page.
            continue
    return dependencies


async def create_task_dependency(
    db: AsyncSession,
    data: TaskDependencyCreate,
    created_by: UUID | None = None,
) -> dict:
    predecessor_id = UUID(str(data.predecessor_task_id))
    successor_id = UUID(str(data.successor_task_id))
    predecessor = await _get_task(db, data.predecessor_task_type, predecessor_id)
    successor = await _get_task(db, data.successor_task_type, successor_id)
    if not predecessor or not successor:
        raise ValueError("前置任务或后置任务不存在")
    if predecessor.id == successor.id and data.predecessor_task_type == data.successor_task_type:
        raise ValueError("任务不能依赖自身")
    if predecessor.document_id != successor.document_id:
        raise ValueError("只允许建立同一订单内的任务依赖")

    duplicate = await db.execute(
        select(TaskDependency).where(
            TaskDependency.predecessor_task_type == data.predecessor_task_type,
            TaskDependency.predecessor_task_id == predecessor_id,
            TaskDependency.successor_task_type == data.successor_task_type,
            TaskDependency.successor_task_id == successor_id,
        )
    )
    if duplicate.scalar_one_or_none():
        raise ValueError("该任务依赖已经存在")

    edge_result = await db.execute(
        select(
            TaskDependency.predecessor_task_type,
            TaskDependency.predecessor_task_id,
            TaskDependency.successor_task_type,
            TaskDependency.successor_task_id,
        )
    )
    edges = {
        (
            (row[0], str(row[1])),
            (row[2], str(row[3])),
        )
        for row in edge_result.all()
    }
    if dependency_edge_would_cycle(
        edges,
        _task_key(data.predecessor_task_type, predecessor_id),
        _task_key(data.successor_task_type, successor_id),
    ):
        raise ValueError("该依赖会形成环路，无法创建")

    dependency = TaskDependency(
        predecessor_task_type=data.predecessor_task_type,
        predecessor_task_id=predecessor_id,
        successor_task_type=data.successor_task_type,
        successor_task_id=successor_id,
        dependency_type=data.dependency_type,
        created_by=created_by,
    )
    db.add(dependency)
    await db.flush()
    return await _dependency_to_dict(db, dependency)


async def delete_task_dependency(db: AsyncSession, dependency_id: UUID) -> None:
    dependency = await db.get(TaskDependency, dependency_id)
    if not dependency:
        raise ValueError("任务依赖不存在")
    await db.delete(dependency)
    await db.flush()


async def clear_task_dependencies(
    db: AsyncSession,
    task_type: str,
    task_ids: list[UUID],
) -> None:
    if not task_ids:
        return
    await db.execute(
        delete(TaskDependency).where(
            or_(
                and_(
                    TaskDependency.predecessor_task_type == task_type,
                    TaskDependency.predecessor_task_id.in_(task_ids),
                ),
                and_(
                    TaskDependency.successor_task_type == task_type,
                    TaskDependency.successor_task_id.in_(task_ids),
                ),
            )
        )
    )


async def ensure_task_not_blocked(
    db: AsyncSession,
    task_type: str,
    task_id: UUID,
    to_status: str,
) -> None:
    if to_status not in PROGRESSION_STATUSES.get(task_type, set()):
        return
    state = await get_task_dependency_state(db, task_type, task_id)
    if state["is_blocked"]:
        raise ValueError(f"任务当前被阻塞：{state['blocked_reason']}")
