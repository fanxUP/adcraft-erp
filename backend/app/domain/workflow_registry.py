"""Immutable registry for business workflow definitions.

The application historically imported plain ``dict`` objects from
``app.domain.workflows``.  This module owns the definitions and exposes richer
metadata while keeping the old mapping-shaped API available through that
compatibility module.

There is intentionally no database or framework dependency here.  A workflow
definition is a piece of domain policy and must be safe to use from HTTP
handlers, background jobs, tests and the AI guidance layer alike.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType


Workflow = Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class WorkflowState:
    """Metadata for one state in a workflow."""

    code: str
    label: str
    terminal: bool = False


@dataclass(frozen=True)
class WorkflowTransition:
    """A valid state transition with a stable command identifier."""

    workflow_key: str
    source: str
    target: str
    command: str
    label: str


@dataclass(frozen=True)
class WorkflowDefinition:
    """Complete, immutable domain description of one workflow."""

    key: str
    label: str
    states: Mapping[str, WorkflowState]
    transitions: Workflow
    transition_specs: Mapping[tuple[str, str], WorkflowTransition]

    def allowed_targets(self, current_status: str) -> tuple[str, ...]:
        return self.transitions.get(current_status, ())

    def get_transition(
        self,
        current_status: str,
        target_status: str,
    ) -> WorkflowTransition | None:
        return self.transition_specs.get((current_status, target_status))

    def ensure_transition(
        self,
        current_status: str,
        target_status: str,
    ) -> WorkflowTransition:
        transition = self.get_transition(current_status, target_status)
        if transition is None:
            # Keep this wording compatible with the existing API and UI error
            # handling.  A later command layer may add a more specific reason
            # code without changing this domain-level exception contract.
            raise ValueError(f"不允许从 {current_status} 流转到 {target_status}")
        return transition


class WorkflowRegistry:
    """Lookup service for all server-owned workflow definitions."""

    def __init__(self, definitions: Iterable[WorkflowDefinition]):
        items = tuple(definitions)
        keys = [definition.key for definition in items]
        if len(keys) != len(set(keys)):
            raise ValueError("工作流编码不能重复")
        self._definitions = MappingProxyType(
            {definition.key: definition for definition in items}
        )

    def get(self, key: str) -> WorkflowDefinition:
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise KeyError(f"未知工作流: {key}") from exc

    def __getitem__(self, key: str) -> WorkflowDefinition:
        return self.get(key)

    def __contains__(self, key: object) -> bool:
        return key in self._definitions

    def keys(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def all(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(self._definitions.values())

    def ensure_transition(
        self,
        workflow_key: str,
        current_status: str,
        target_status: str,
    ) -> WorkflowTransition:
        return self.get(workflow_key).ensure_transition(
            current_status,
            target_status,
        )


def _build_definition(
    key: str,
    label: str,
    transitions: Mapping[str, tuple[str, ...]],
    state_labels: Mapping[str, str],
) -> WorkflowDefinition:
    normalized_transitions = {
        source: tuple(targets)
        for source, targets in transitions.items()
    }
    state_codes = set(normalized_transitions)
    state_codes.update(
        target
        for targets in normalized_transitions.values()
        for target in targets
    )
    missing_labels = state_codes - set(state_labels)
    if missing_labels:
        raise ValueError(
            f"工作流 {key} 存在未命名状态: {'、'.join(sorted(missing_labels))}"
        )

    states = {
        code: WorkflowState(
            code=code,
            label=state_labels[code],
            terminal=not normalized_transitions.get(code, ()),
        )
        for code in sorted(state_codes)
    }
    transition_specs = {
        (source, target): WorkflowTransition(
            workflow_key=key,
            source=source,
            target=target,
            command=f"{key}.{source}.to.{target}",
            label=f"{state_labels[source]} → {state_labels[target]}",
        )
        for source, targets in normalized_transitions.items()
        for target in targets
    }
    return WorkflowDefinition(
        key=key,
        label=label,
        states=MappingProxyType(states),
        transitions=MappingProxyType(normalized_transitions),
        transition_specs=MappingProxyType(transition_specs),
    )


WORKFLOW_REGISTRY = WorkflowRegistry(
    (
        _build_definition(
            "order",
            "订单流程",
            {
                "pending_confirm": ("confirmed", "cancelled"),
                "confirmed": ("designing", "cancelled"),
                "designing": ("in_production", "in_installation", "cancelled"),
                "in_production": ("designing", "in_installation", "cancelled"),
                "in_installation": (
                    "designing",
                    "in_production",
                    "completed",
                    "cancelled",
                ),
                "completed": (),
                "cancelled": (),
            },
            {
                "pending_confirm": "待确认",
                "confirmed": "已确认",
                "designing": "设计中",
                "in_production": "制作中",
                "in_installation": "安装中",
                "completed": "已完成",
                "cancelled": "已取消",
            },
        ),
        _build_definition(
            "quote",
            "报价流程",
            {
                "draft": ("confirmed", "cancelled"),
                "confirmed": ("converted", "cancelled", "draft"),
                "cancelled": (),
                "converted": (),
            },
            {
                "draft": "草稿",
                "confirmed": "已确认",
                "converted": "已转订单",
                "cancelled": "已取消",
            },
        ),
        _build_definition(
            "contract",
            "合同流程",
            {
                "draft": ("active", "completed"),
                "active": ("draft", "completed"),
                "completed": (),
            },
            {
                "draft": "草稿",
                "active": "生效",
                "completed": "已完成",
            },
        ),
        _build_definition(
            "acceptance",
            "验收流程",
            {
                "draft": ("pending",),
                "pending": ("accepted", "rejected"),
                "rejected": ("draft",),
            },
            {
                "draft": "草稿",
                "pending": "待验收",
                "accepted": "已验收",
                "rejected": "已驳回",
            },
        ),
        _build_definition(
            "design_task",
            "设计任务流程",
            {
                "pending": ("designing",),
                "designing": ("confirmed", "pending_review", "pending"),
                "pending_review": ("confirmed", "revision"),
                "revision": ("designing", "pending_review"),
                "confirmed": (),
                "cancelled": (),
            },
            {
                "pending": "待分配",
                "designing": "设计中",
                "pending_review": "待审核",
                "revision": "需修改",
                "confirmed": "已完成",
                "cancelled": "已取消",
            },
        ),
        _build_definition(
            "production_task",
            "制作任务流程",
            {
                "pending": ("in_progress",),
                "in_progress": ("completed", "rework", "pending"),
                "rework": ("in_progress",),
                "completed": (),
                "cancelled": (),
            },
            {
                "pending": "待制作",
                "in_progress": "制作中",
                "rework": "返工",
                "completed": "已完成",
                "cancelled": "已取消",
            },
        ),
        _build_definition(
            "installation_task",
            "安装任务流程",
            {
                "pending": ("assigned", "in_progress"),
                "assigned": ("in_progress", "pending"),
                "in_progress": ("completed", "pending_acceptance", "pending"),
                "pending_acceptance": ("completed", "in_progress"),
                "completed": (),
                "cancelled": (),
            },
            {
                "pending": "待分配",
                "assigned": "已分配",
                "in_progress": "安装中",
                "pending_acceptance": "待处理",
                "completed": "已完成",
                "cancelled": "已取消",
            },
        ),
        _build_definition(
            "outsource_task",
            "外协任务流程",
            {
                "pending": ("in_progress",),
                "in_progress": ("completed",),
                "completed": (),
                "settled": (),
                "cancelled": (),
            },
            {
                "pending": "待处理",
                "in_progress": "进行中",
                "completed": "已完成",
                "settled": "已结算",
                "cancelled": "已取消",
            },
        ),
    )
)


def get_workflow_definition(key: str) -> WorkflowDefinition:
    """Return a server-owned workflow definition by stable key."""

    return WORKFLOW_REGISTRY.get(key)
