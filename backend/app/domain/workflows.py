"""跨模块共享的业务状态机定义（兼容导出层）。"""

from app.domain.workflow_registry import (
    WORKFLOW_REGISTRY,
    Workflow,
    WorkflowDefinition,
    get_workflow_definition,
)


# Existing callers still receive mapping-shaped objects.  The mappings are
# immutable views owned by the registry, so no caller can silently alter the
# process policy for the rest of the application.
ORDER_WORKFLOW: Workflow = get_workflow_definition("order").transitions
QUOTE_WORKFLOW: Workflow = get_workflow_definition("quote").transitions
CONTRACT_WORKFLOW: Workflow = get_workflow_definition("contract").transitions
ACCEPTANCE_WORKFLOW: Workflow = get_workflow_definition("acceptance").transitions
DESIGN_TASK_WORKFLOW: Workflow = get_workflow_definition("design_task").transitions
PRODUCTION_TASK_WORKFLOW: Workflow = get_workflow_definition("production_task").transitions
INSTALLATION_TASK_WORKFLOW: Workflow = get_workflow_definition("installation_task").transitions
OUTSOURCE_TASK_WORKFLOW: Workflow = get_workflow_definition("outsource_task").transitions


def allowed_targets(
    workflow: Workflow | WorkflowDefinition,
    current_status: str,
) -> tuple[str, ...]:
    if isinstance(workflow, WorkflowDefinition):
        return workflow.allowed_targets(current_status)
    return workflow.get(current_status, ())


def ensure_transition(
    workflow: Workflow | WorkflowDefinition,
    current_status: str,
    target_status: str,
) -> None:
    if isinstance(workflow, WorkflowDefinition):
        workflow.ensure_transition(current_status, target_status)
        return
    if target_status not in allowed_targets(workflow, current_status):
        raise ValueError(f"不允许从 {current_status} 流转到 {target_status}")
