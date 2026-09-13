"""Structured permission catalog and composition policies.

The database still stores the historical permission codes.  This module adds
the semantic layer that makes those codes composable: module/resource/action
metadata, explicit dependencies, and security conflicts.  It intentionally
does not grant permissions by role name.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    module: str
    resource: str
    action: str
    kind: str = "action"
    sensitivity: str = "normal"
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class PermissionValidationIssue:
    kind: str
    code: str
    message: str
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PermissionPackDefinition:
    """A named configuration shortcut that expands to atomic permissions."""

    code: str
    name: str
    description: str
    permissions: tuple[str, ...]


# Dependencies are deliberately explicit.  A child permission never silently
# grants its parent; the role editor and the server validator must both show
# and validate the complete set.
PERMISSION_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    # Delivery task list/actions require detail read permission.
    "task_queue:view_all": ("task_queue:read",),
    "design_task:list": ("design_task:read",),
    "design_task:assign": ("design_task:read",),
    "design_task:create": ("design_task:read",),
    "design_task:update": ("design_task:read",),
    "design_task:change_status": ("design_task:read",),
    "design_task:delete": ("design_task:read",),
    "production_task:list": ("production_task:read",),
    "production_task:assign": ("production_task:read",),
    "production_task:create": ("production_task:read",),
    "production_task:update": ("production_task:read",),
    "production_task:change_status": ("production_task:read",),
    "production_task:delete": ("production_task:read",),
    "installation_task:list": ("installation_task:read",),
    "installation_task:assign": ("installation_task:read",),
    "installation_task:create": ("installation_task:read",),
    "installation_task:update": ("installation_task:read",),
    "installation_task:change_status": ("installation_task:read",),
    "installation_task:delete": ("installation_task:read",),
    # Order task visibility management is still an order operation.
    "order:task_assign": ("order:read",),
    # Price fields must never be readable without the corresponding object.
    "order:view_price": ("order:read",),
    "order_item:view_price": ("order:read",),
    # Resource-center children require its parent gate.
    "vehicle:read": ("resource_center:read",),
    "vehicle:create": ("resource_center:read",),
    "vehicle:update": ("resource_center:read",),
    "vehicle:delete": ("resource_center:read",),
    "aerial:read": ("resource_center:read",),
    "aerial:create": ("resource_center:read",),
    "aerial:update": ("resource_center:read",),
    "aerial:delete": ("resource_center:read",),
    "aerial:finance": ("resource_center:read",),
    "aerial:wage": ("resource_center:read",),
    "finance:review": ("resource_center:read",),
    # Outsource payment is intentionally independent from the task center.
    "outsource_vendor:read": ("outsource_center:read",),
    "outsource_vendor:create": ("outsource_center:read",),
    "outsource_vendor:update": ("outsource_center:read",),
    "outsource_vendor:delete": ("outsource_center:read",),
    "outsource_task:read": ("outsource_center:read",),
    "outsource_task:create": ("outsource_center:read", "outsource_task:read"),
    "outsource_task:update": ("outsource_center:read", "outsource_task:read"),
    "outsource_task:change_status": ("outsource_center:read", "outsource_task:read"),
    "outsource_task:delete": ("outsource_center:read", "outsource_task:read"),
    # Completion metrics are non-financial, but organization-wide visibility
    # must always include the personal read capability.
    "task_completion:view_all": ("task_completion:read",),
}


# These are the high-risk capabilities that must be reviewed together.  Read
# access to task details is not considered an execution role: sales users can
# read/assign tasks while still viewing commercial information.  Mutating a
# delivery task is the boundary that identifies an execution operator.
TASK_MUTATION_PERMISSIONS = frozenset({
    "design_task:create",
    "design_task:update",
    "design_task:change_status",
    "design_task:delete",
    "production_task:create",
    "production_task:update",
    "production_task:change_status",
    "production_task:delete",
    "installation_task:create",
    "installation_task:update",
    "installation_task:change_status",
    "installation_task:delete",
})

SENSITIVE_PERMISSIONS = frozenset({
    "quote:read",
    "quote:create",
    "quote:update",
    "quote:delete",
    "quote:confirm",
    "quote:convert",
    "contract:read",
    "contract:create",
    "contract:update",
    "contract:delete",
    "contract:change_status",
    "cdr_quote:read",
    "cdr_quote:create",
    "cdr_quote:update",
    "cdr_quote:delete",
    "cdr_quote:view_cost",
    "cdr_quote:view_profit",
    "cdr_quote:adjust_price",
    "cdr_quote:approve",
    "cdr_quote:convert",
    "cdr_rule_set:publish",
    "cdr_customer_agreement:manage",
    "order:view_price",
    "order_item:view_price",
    "catalog:view_price",
    "finance:view_cost",
    "report:view_financial",
    "payment:read",
    "payment:create",
    "payment:void",
    "statement:read",
    "statement:create",
    "statement:confirm",
    "expense:read",
    "expense:create",
    "expense:update",
    "expense:delete",
    "outsource_payment:read",
    "outsource_payment:create",
    # AI business tools may expose pricing, financial summaries or anomaly
    # details; treat their entry capabilities as sensitive as the data they
    # return, so a custom execution role cannot add them accidentally.
    "ai_quote:read",
    "ai_knowledge:read",
    "ai_report:read",
    "ai_anomaly:read",
})

RESOURCE_CENTER_PERMISSIONS = frozenset({
    "resource_center:read",
    "vehicle:read",
    "vehicle:create",
    "vehicle:update",
    "vehicle:delete",
    "finance:review",
    "aerial:read",
    "aerial:create",
    "aerial:update",
    "aerial:delete",
    "aerial:finance",
    "aerial:wage",
})

SENSITIVE_FIELD_ACTIONS = frozenset({"view_price", "view_cost", "view_profit"})
FINANCIAL_MODULES = frozenset({"payment", "statement", "expense", "report"})

CONFLICT_POLICIES: tuple[tuple[str, frozenset[str], frozenset[str], str], ...] = (
    (
        "execution_sensitive_conflict",
        TASK_MUTATION_PERMISSIONS,
        SENSITIVE_PERMISSIONS,
        "任务执行能力不能与价格或财务能力同时启用",
    ),
    (
        "execution_resource_conflict",
        TASK_MUTATION_PERMISSIONS,
        RESOURCE_CENTER_PERMISSIONS,
        "任务执行能力不能与资源中心车辆/高空车能力同时启用",
    ),
)


# Packs are editor shortcuts only. The role-permission join table stores the
# expanded atomic codes, so changing a pack never silently changes an already
# saved role.
PERMISSION_PACKS: tuple[PermissionPackDefinition, ...] = (
    PermissionPackDefinition(
        code="design_task_operator",
        name="设计任务处理",
        description="工作台与设计任务处理能力",
        permissions=(
            "task_queue:read",
            "design_task:read",
            "design_task:create",
            "design_task:update",
            "design_task:change_status",
        ),
    ),
    PermissionPackDefinition(
        code="production_task_operator",
        name="制作任务处理",
        description="工作台与制作任务处理能力",
        permissions=(
            "task_queue:read",
            "production_task:read",
            "production_task:create",
            "production_task:update",
            "production_task:change_status",
        ),
    ),
    PermissionPackDefinition(
        code="installation_task_operator",
        name="安装任务处理",
        description="工作台与安装任务处理能力",
        permissions=(
            "task_queue:read",
            "installation_task:read",
            "installation_task:create",
            "installation_task:update",
            "installation_task:change_status",
        ),
    ),
    PermissionPackDefinition(
        code="outsource_readonly",
        name="外协只读",
        description="查看外协商和外协任务，不包含编辑或付款",
        permissions=(
            "outsource_center:read",
            "outsource_vendor:read",
            "outsource_task:read",
        ),
    ),
    PermissionPackDefinition(
        code="resource_vehicle_manager",
        name="车辆资源管理",
        description="进入资源中心并管理公司车辆",
        permissions=(
            "resource_center:read",
            "vehicle:read",
            "vehicle:create",
            "vehicle:update",
            "vehicle:delete",
        ),
    ),
    PermissionPackDefinition(
        code="finance_viewer",
        name="财务查看",
        description="查看订单金额、成本和经营财务数据",
        permissions=(
            "order:read",
            "order:view_price",
            "order_item:view_price",
            "finance:view_cost",
            "report:read",
            "report:view_financial",
            "payment:read",
            "statement:read",
            "expense:read",
        ),
    ),
    PermissionPackDefinition(
        code="manager_operational_readonly",
        name="经理运营只读",
        description="查看经营驾驶舱、运营报表、项目进度和完成统计，不包含价格、成本、收付款或任务变更",
        permissions=(
            "dashboard:read",
            "report:read",
            "order:read",
            "task_queue:read",
            "task_queue:view_all",
            "design_task:read",
            "production_task:read",
            "installation_task:read",
            "task_completion:read",
            "task_completion:view_all",
        ),
    ),
)


def declared_permission_codes() -> frozenset[str]:
    """Return all permission constants without maintaining a second code list."""

    from app.core import permissions as permission_constants

    return frozenset(
        value
        for name, value in vars(permission_constants).items()
        if name.startswith("PERM_") and isinstance(value, str)
    )


def _split_permission_code(code: str) -> tuple[str, str, str]:
    parts = code.split(":")
    module = parts[0]
    if len(parts) == 2:
        resource, action = module, parts[1]
    else:
        resource, action = ":".join(parts[:2]), ":".join(parts[2:])
    return module, resource, action


def _build_definition(code: str) -> PermissionDefinition:
    module, resource, action = _split_permission_code(code)
    kind = "field" if action in SENSITIVE_FIELD_ACTIONS else "action"
    if action == "read" and module.endswith("_center"):
        kind = "module"

    if (
        action in {"view_price", "view_profit"}
        or module in {"quote", "contract", "cdr_quote"}
        or code in {"ai_quote:read", "ai_knowledge:read"}
    ):
        sensitivity = "price"
    elif (
        action == "view_cost"
        or (module in FINANCIAL_MODULES and code != "report:read")
        or module == "finance"
        or code in {"ai_report:read", "ai_anomaly:read"}
    ):
        sensitivity = "financial"
    elif module.startswith("outsource"):
        sensitivity = "external"
    elif module == "system" or module in {"backup", "user"}:
        sensitivity = "security"
    else:
        sensitivity = "normal"

    return PermissionDefinition(
        code=code,
        module=module,
        resource=resource,
        action=action,
        kind=kind,
        sensitivity=sensitivity,
        requires=PERMISSION_DEPENDENCIES.get(code, ()),
    )


def permission_definitions() -> tuple[PermissionDefinition, ...]:
    """Build deterministic metadata for every declared permission constant."""

    return tuple(_build_definition(code) for code in sorted(declared_permission_codes()))


def permission_pack_definitions() -> tuple[PermissionPackDefinition, ...]:
    """Return deterministic, server-owned editor shortcuts."""

    return PERMISSION_PACKS


def get_permission_pack(code: str) -> PermissionPackDefinition:
    for pack in PERMISSION_PACKS:
        if pack.code == code:
            return pack
    raise KeyError(f"未知权限包: {code}")


def get_permission_definition(code: str) -> PermissionDefinition:
    if code not in declared_permission_codes():
        raise KeyError(f"未知权限码: {code}")
    return _build_definition(code)


def get_permission_dependencies(code: str) -> tuple[str, ...]:
    return PERMISSION_DEPENDENCIES.get(code, ())


def validate_permission_catalog() -> tuple[str, ...]:
    """Validate the static catalog before it can be used by the application.

    Returning messages instead of raising makes the function useful in tests
    and release checks.  ``ensure_permission_catalog`` is the startup gate.
    """
    known = declared_permission_codes()
    errors: list[str] = []

    for code, dependencies in PERMISSION_DEPENDENCIES.items():
        if code not in known:
            errors.append(f"依赖规则引用未知权限主体: {code}")
        if code in dependencies:
            errors.append(f"权限不能依赖自身: {code}")
        for dependency in dependencies:
            if dependency not in known:
                errors.append(f"权限「{code}」依赖未知权限: {dependency}")

    # Detect dependency cycles with a small DFS so a future catalog edit cannot
    # make dependency expansion loop forever.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(code: str) -> None:
        if code in visited or code not in PERMISSION_DEPENDENCIES:
            return
        if code in visiting:
            errors.append(f"权限依赖存在循环: {code}")
            return
        visiting.add(code)
        for dependency in PERMISSION_DEPENDENCIES.get(code, ()):
            visit(dependency)
        visiting.remove(code)
        visited.add(code)

    for code in PERMISSION_DEPENDENCIES:
        visit(code)

    for name, left, right, _message in CONFLICT_POLICIES:
        if left.intersection(right):
            errors.append(f"冲突策略「{name}」存在自冲突权限")

    pack_codes = [pack.code for pack in PERMISSION_PACKS]
    if len(pack_codes) != len(set(pack_codes)):
        errors.append("权限包编码重复")
    for pack in PERMISSION_PACKS:
        for permission in pack.permissions:
            if permission not in known:
                errors.append(f"权限包「{pack.code}」引用未知权限: {permission}")

    return tuple(dict.fromkeys(errors))


def ensure_permission_catalog() -> None:
    errors = validate_permission_catalog()
    if errors:
        raise RuntimeError("权限目录校验失败：" + "；".join(errors))


def expand_permission_dependencies(permission_codes: set[str] | list[str] | tuple[str, ...]) -> frozenset[str]:
    """Return the requested permissions plus all transitive prerequisites."""

    expanded = set(permission_codes)
    pending = list(expanded)
    while pending:
        code = pending.pop()
        for required in get_permission_dependencies(code):
            if required not in expanded:
                expanded.add(required)
                pending.append(required)
    return frozenset(expanded)


def validate_permission_set(
    permission_codes: set[str] | list[str] | tuple[str, ...],
    *,
    allow_conflicts: bool = False,
) -> list[PermissionValidationIssue]:
    """Validate a complete permission composition before it is persisted.

    The validator deliberately reasons about capabilities, not role names.
    ``system:super_admin`` is an explicit, auditable bypass capability; a
    role merely named ``admin`` does not bypass these checks.
    """

    codes = frozenset(permission_codes)
    known = declared_permission_codes()
    issues: list[PermissionValidationIssue] = []

    for unknown in sorted(codes - known):
        issues.append(PermissionValidationIssue(
            kind="unknown_permission",
            code=unknown,
            message=f"权限目录中不存在「{unknown}」，无法保存",
            permissions=(unknown,),
        ))

    if "system:super_admin" in codes:
        return issues

    for code in sorted(codes & known):
        missing = tuple(required for required in get_permission_dependencies(code) if required not in codes)
        if missing:
            issues.append(PermissionValidationIssue(
                kind="missing_dependency",
                code=code,
                message=f"「{code}」缺少前置权限：{'、'.join(missing)}",
                permissions=(code, *missing),
            ))

    if not allow_conflicts:
        for policy_code, left_set, right_set, message in CONFLICT_POLICIES:
            left = codes & left_set
            right = codes & right_set
            if not left or not right:
                continue
            issues.append(PermissionValidationIssue(
                kind="conflict",
                code=policy_code,
                message=message,
                permissions=tuple(sorted(left | right)),
            ))

    return issues
