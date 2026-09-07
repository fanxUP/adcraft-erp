from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import CoercedModel


TaskType = Literal["design", "production", "installation"]
DependencyType = Literal["finish_to_start"]


class TaskDependencyCreate(BaseModel):
    predecessor_task_type: TaskType
    predecessor_task_id: str
    successor_task_type: TaskType
    successor_task_id: str
    dependency_type: DependencyType = "finish_to_start"


class TaskDependencyTaskSummary(CoercedModel):
    model_config = {"from_attributes": True}

    task_type: TaskType
    task_id: str
    task_no: str
    order_id: str | None = None
    project_name: str
    status: str
    progress_pct: int = Field(0, ge=0, le=100)


class TaskDependencyResponse(CoercedModel):
    model_config = {"from_attributes": True}

    id: str
    dependency_type: DependencyType
    predecessor: TaskDependencyTaskSummary
    successor: TaskDependencyTaskSummary
    is_satisfied: bool
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
