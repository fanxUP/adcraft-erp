"""Permission code constants and RBAC dependency factories.

Usage in route definitions:

    from app.core.permissions import require_permission, PERM_BACKUP_CREATE

    @router.post("/create")
    async def create_backup(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_permission(PERM_BACKUP_CREATE)),
    ):
        ...

For system-management endpoints, use the explicit super-admin capability:

    from app.core.permissions import PERM_SYSTEM_SUPER_ADMIN, require_permission

    @router.delete("/{user_id}")
    async def delete_user(
        ...,
        current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
    ):
        ...
"""

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.core.permission_catalog import (
    RESOURCE_CENTER_PERMISSIONS,
    SENSITIVE_PERMISSIONS,
    TASK_MUTATION_PERMISSIONS,
)
from app.models.user import User

# ── Permission code constants ──────────────────────────────────────────────

# System
PERM_SYSTEM_LOGS = "system:logs"
PERM_SYSTEM_SUPER_ADMIN = "system:super_admin"

# Backup
PERM_BACKUP_CREATE = "backup:create"
PERM_BACKUP_READ = "backup:read"
PERM_BACKUP_RESTORE = "backup:restore"
PERM_BACKUP_DELETE = "backup:delete"

# User management
PERM_USER_READ = "user:read"
PERM_USER_CREATE = "user:create"
PERM_USER_UPDATE = "user:update"
PERM_USER_DELETE = "user:delete"

# Customer
PERM_CUSTOMER_READ = "customer:read"
PERM_CUSTOMER_CREATE = "customer:create"
PERM_CUSTOMER_UPDATE = "customer:update"
PERM_CUSTOMER_DELETE = "customer:delete"

# Product / Material / Process
PERM_PRODUCT_READ = "product:read"
PERM_PRODUCT_CREATE = "product:create"
PERM_PRODUCT_UPDATE = "product:update"
PERM_PRODUCT_DELETE = "product:delete"
PERM_MATERIAL_READ = "material:read"
PERM_MATERIAL_CREATE = "material:create"
PERM_MATERIAL_UPDATE = "material:update"
PERM_MATERIAL_DELETE = "material:delete"
PERM_PROCESS_READ = "process:read"
PERM_PROCESS_CREATE = "process:create"
PERM_PROCESS_UPDATE = "process:update"
PERM_PROCESS_DELETE = "process:delete"

# Quote
PERM_QUOTE_READ = "quote:read"
PERM_QUOTE_CREATE = "quote:create"
PERM_QUOTE_UPDATE = "quote:update"
PERM_QUOTE_DELETE = "quote:delete"
PERM_QUOTE_CONFIRM = "quote:confirm"
PERM_QUOTE_CONVERT = "quote:convert"

# Order
PERM_ORDER_READ = "order:read"
PERM_ORDER_CREATE = "order:create"
PERM_ORDER_UPDATE = "order:update"
PERM_ORDER_DELETE = "order:delete"
PERM_ORDER_CHANGE_STATUS = "order:change_status"
PERM_ORDER_CHANGE_DATE = "order:change_date"
PERM_ORDER_VIEW_PRICE = "order:view_price"
PERM_ORDER_ITEM_VIEW_PRICE = "order_item:view_price"
# 订单任务分配只管理“哪些员工能看到订单任务”，不授予订单价格或订单编辑权限。
PERM_ORDER_TASK_ASSIGN = "order:task_assign"

# Price and financial visibility.  These are deliberately separate from
# module read permissions: being able to process a task does not imply being
# able to see the commercial value of the order or its line items.
PERM_CATALOG_VIEW_PRICE = "catalog:view_price"
PERM_FINANCE_VIEW_COST = "finance:view_cost"
PERM_REPORT_VIEW_FINANCIAL = "report:view_financial"

# Task queue / task list / task assignment
PERM_TASK_QUEUE_READ = "task_queue:read"
# A read-only organization-wide scope for managers and similar operational
# roles.  This is deliberately separate from ``order:task_assign``: seeing
# every task must not allow changing who can see an order's tasks.
PERM_TASK_QUEUE_VIEW_ALL = "task_queue:view_all"

# Design Task
PERM_DESIGN_TASK_READ = "design_task:read"
PERM_DESIGN_TASK_LIST = "design_task:list"
PERM_DESIGN_TASK_ASSIGN = "design_task:assign"
PERM_DESIGN_TASK_CREATE = "design_task:create"
PERM_DESIGN_TASK_UPDATE = "design_task:update"
PERM_DESIGN_TASK_CHANGE_STATUS = "design_task:change_status"

# Production Task
PERM_PRODUCTION_TASK_READ = "production_task:read"
PERM_PRODUCTION_TASK_LIST = "production_task:list"
PERM_PRODUCTION_TASK_ASSIGN = "production_task:assign"
PERM_PRODUCTION_TASK_CREATE = "production_task:create"
PERM_PRODUCTION_TASK_UPDATE = "production_task:update"
PERM_PRODUCTION_TASK_CHANGE_STATUS = "production_task:change_status"

# Installation Task
PERM_INSTALLATION_TASK_READ = "installation_task:read"
PERM_INSTALLATION_TASK_LIST = "installation_task:list"
PERM_INSTALLATION_TASK_ASSIGN = "installation_task:assign"
PERM_INSTALLATION_TASK_CREATE = "installation_task:create"
PERM_INSTALLATION_TASK_UPDATE = "installation_task:update"
PERM_INSTALLATION_TASK_CHANGE_STATUS = "installation_task:change_status"
PERM_INSTALLATION_TASK_DELETE = "installation_task:delete"

# Production Task Delete
PERM_PRODUCTION_TASK_DELETE = "production_task:delete"

# Design Task Delete
PERM_DESIGN_TASK_DELETE = "design_task:delete"

# Payment
PERM_PAYMENT_READ = "payment:read"
PERM_PAYMENT_CREATE = "payment:create"
PERM_PAYMENT_VOID = "payment:void"

# Statement
PERM_STATEMENT_READ = "statement:read"
PERM_STATEMENT_CREATE = "statement:create"
PERM_STATEMENT_CONFIRM = "statement:confirm"

# Expense
PERM_EXPENSE_READ = "expense:read"
PERM_EXPENSE_CREATE = "expense:create"
PERM_EXPENSE_UPDATE = "expense:update"
PERM_EXPENSE_DELETE = "expense:delete"

# Supplier master data. The module gate, ledger visibility and bank fields
# remain independently composable so an external-task manager can maintain
# supplier contacts without seeing financial or banking data.
PERM_SUPPLIER_CENTER_READ = "supplier_center:read"
PERM_SUPPLIER_READ = "supplier:read"
PERM_SUPPLIER_CREATE = "supplier:create"
PERM_SUPPLIER_UPDATE = "supplier:update"
PERM_SUPPLIER_LEDGER_READ = "supplier:ledger:read"
PERM_SUPPLIER_BANK_READ = "supplier:bank:view"
PERM_SUPPLIER_BANK_UPDATE = "supplier:bank:edit"

# Resource center / Inventory
PERM_RESOURCE_CENTER_READ = "resource_center:read"
PERM_INVENTORY_READ = "inventory:read"
PERM_INVENTORY_CREATE = "inventory:create"
PERM_INVENTORY_UPDATE = "inventory:update"
PERM_INVENTORY_STOCK_IN = "inventory:stock_in"
PERM_INVENTORY_STOCK_OUT = "inventory:stock_out"

# Outsource center.  The parent gate and the two business areas are kept
# separate so a user can manage vendors without seeing tasks, or handle
# payment reconciliation without receiving task write permissions.
PERM_OUTSOURCE_CENTER_READ = "outsource_center:read"
PERM_OUTSOURCE_VENDOR_READ = "outsource_vendor:read"
PERM_OUTSOURCE_VENDOR_CREATE = "outsource_vendor:create"
PERM_OUTSOURCE_VENDOR_UPDATE = "outsource_vendor:update"
PERM_OUTSOURCE_VENDOR_DELETE = "outsource_vendor:delete"
PERM_OUTSOURCE_TASK_READ = "outsource_task:read"
PERM_OUTSOURCE_TASK_CREATE = "outsource_task:create"
PERM_OUTSOURCE_TASK_UPDATE = "outsource_task:update"
PERM_OUTSOURCE_TASK_CHANGE_STATUS = "outsource_task:change_status"
PERM_OUTSOURCE_TASK_DELETE = "outsource_task:delete"
PERM_OUTSOURCE_PAYMENT_READ = "outsource_payment:read"
PERM_OUTSOURCE_PAYMENT_CREATE = "outsource_payment:create"

# Report
PERM_DASHBOARD_READ = "dashboard:read"
PERM_REPORT_READ = "report:read"

# Delivery completion metrics.  These permissions are deliberately separate
# from financial reports: execution staff can see their own work results
# without gaining access to order prices, costs or profit.
PERM_TASK_COMPLETION_READ = "task_completion:read"
PERM_TASK_COMPLETION_VIEW_ALL = "task_completion:view_all"

# AI Features
PERM_AI_QUOTE_READ = "ai_quote:read"
PERM_AI_ANOMALY_READ = "ai_anomaly:read"
PERM_AI_KNOWLEDGE_READ = "ai_knowledge:read"
PERM_AI_REPORT_READ = "ai_report:read"

# Chat / Messaging
PERM_CHAT_READ = "chat:read"
PERM_CHAT_CREATE = "chat:create"
PERM_CHAT_DELETE = "chat:delete"
PERM_CHAT_GROUP_CREATE = "chat:group:create"
PERM_CHAT_GROUP_MANAGE = "chat:group:manage"

# Contract
PERM_CONTRACT_READ = "contract:read"
PERM_CONTRACT_CREATE = "contract:create"
PERM_CONTRACT_UPDATE = "contract:update"
PERM_CONTRACT_DELETE = "contract:delete"
PERM_CONTRACT_CHANGE_STATUS = "contract:change_status"

# Acceptance
PERM_ACCEPTANCE_READ = "acceptance:read"
PERM_ACCEPTANCE_CREATE = "acceptance:create"
PERM_ACCEPTANCE_UPDATE = "acceptance:update"
PERM_ACCEPTANCE_DELETE = "acceptance:delete"
PERM_ACCEPTANCE_CHANGE_STATUS = "acceptance:change_status"

# Vehicle
PERM_VEHICLE_READ = "vehicle:read"
PERM_VEHICLE_CREATE = "vehicle:create"
PERM_VEHICLE_UPDATE = "vehicle:update"
PERM_VEHICLE_DELETE = "vehicle:delete"

# Finance review (for fuel/maintenance expense review)
PERM_FINANCE_REVIEW = "finance:review"

# Aerial work platform
PERM_AERIAL_READ = "aerial:read"
PERM_AERIAL_CREATE = "aerial:create"
PERM_AERIAL_UPDATE = "aerial:update"
PERM_AERIAL_DELETE = "aerial:delete"
PERM_AERIAL_FINANCE = "aerial:finance"
PERM_AERIAL_WAGE = "aerial:wage"

# The parent gate is intentionally separate from the vehicle/aerial action
# permissions. A user must have both the module entry permission and the
# relevant child permission before a resource-center route is usable.
# Compatibility export. The catalog is the single source of truth for this
# security classification; callers should prefer its semantic name.
RESOURCE_CENTER_PERMISSION_CODES = RESOURCE_CENTER_PERMISSIONS

# CDR 智能报价
PERM_CDR_QUOTE_READ = "cdr_quote:read"
PERM_CDR_QUOTE_CREATE = "cdr_quote:create"
PERM_CDR_QUOTE_UPDATE = "cdr_quote:update"
PERM_CDR_QUOTE_DELETE = "cdr_quote:delete"
PERM_CDR_QUOTE_VIEW_COST = "cdr_quote:view_cost"
PERM_CDR_QUOTE_VIEW_PROFIT = "cdr_quote:view_profit"
PERM_CDR_QUOTE_ADJUST_PRICE = "cdr_quote:adjust_price"
PERM_CDR_QUOTE_APPROVE = "cdr_quote:approve"
PERM_CDR_QUOTE_CONVERT = "cdr_quote:convert"
PERM_CDR_RULE_SET_PUBLISH = "cdr_rule_set:publish"
PERM_CDR_DEVICE_MANAGE = "cdr_device:manage"
PERM_CDR_CUSTOMER_AGREEMENT_MANAGE = "cdr_customer_agreement:manage"


# ── Role name constants ───────────────────────────────────────────────────

ROLE_ADMIN = "admin"
ROLE_SALES = "sales"
ROLE_DESIGNER = "designer"
ROLE_PRODUCTION = "production"
ROLE_INSTALLER = "installer"
ROLE_FINANCE = "finance"
ROLE_RESOURCE_MANAGER = "resource_manager"
ROLE_OUTSOURCE_MANAGER = "outsource_manager"
ROLE_MANAGER = "manager"

EXECUTION_ROLE_NAMES = frozenset({
    ROLE_DESIGNER,
    ROLE_PRODUCTION,
    ROLE_INSTALLER,
})
SENSITIVE_ROLE_NAMES = frozenset({ROLE_SALES, ROLE_FINANCE})

# A role is execution-capable when it can read or operate one of the three
# delivery task modules.  Keep this permission-based companion to
# ``EXECUTION_ROLE_NAMES`` so a custom role cannot bypass the safety rule by
# choosing a different display name.
EXECUTION_PERMISSION_CODES = frozenset({
    PERM_TASK_QUEUE_READ,
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_LIST,
    PERM_DESIGN_TASK_ASSIGN,
    PERM_PRODUCTION_TASK_READ,
    PERM_PRODUCTION_TASK_LIST,
    PERM_PRODUCTION_TASK_ASSIGN,
    PERM_INSTALLATION_TASK_READ,
    PERM_INSTALLATION_TASK_LIST,
    PERM_INSTALLATION_TASK_ASSIGN,
}) | TASK_MUTATION_PERMISSIONS


# Sensitive permissions are kept in one immutable set so role-management and
# response serializers can share the same security boundary.  The set is
# intentionally permission-code based rather than role-name based: custom
# business roles can still be evaluated consistently.
# Compatibility export. Keep the old import name while avoiding a second
# sensitive-permission list that could drift from the central catalog.
SENSITIVE_PERMISSION_CODES = SENSITIVE_PERMISSIONS

ORDER_PRICE_FIELDS = frozenset({
    "total_amount",
    "paid_amount",
    "unpaid_amount",
    "discount_amount",
    "tax_rate",
    "tax_amount",
    "cost_amount",
    "gross_profit",
    "profit_amount",
})

ORDER_ITEM_PRICE_FIELDS = frozenset({
    "unit_price",
    "process_fee",
    "installation_fee",
    "design_fee",
    "transport_fee",
    "other_fee",
    "subtotal_amount",
    "cost_amount",
    "gross_profit",
    "profit_amount",
})


def get_user_permission_codes(user: User) -> frozenset[str]:
    """Return the effective permission codes for a loaded user.

    This helper is intentionally pure and does not trust any client-provided
    role or permission value.  Route dependencies receive ``User`` from the
    database, so later field-level serializers can use the same calculation.
    """

    return frozenset(
        permission.code
        for role in getattr(user, "roles", ())
        for permission in getattr(role, "permissions", ())
    )


def get_user_capabilities(user: User) -> dict[str, bool]:
    """Expose non-sensitive capability flags for the authenticated client.

    These flags are for UI decisions only.  They never replace backend route
    authorization or field-level response filtering.
    """

    return {
        "view_order_price": user_has_permission(user, PERM_ORDER_VIEW_PRICE),
        "view_order_item_price": user_has_permission(user, PERM_ORDER_ITEM_VIEW_PRICE),
        "view_catalog_price": user_has_permission(user, PERM_CATALOG_VIEW_PRICE),
        "view_cost": user_has_permission(user, PERM_FINANCE_VIEW_COST),
        "view_financial_report": user_has_permission(user, PERM_REPORT_VIEW_FINANCIAL),
    }


def user_has_permission(user: User, permission_code: str) -> bool:
    """Return whether a user can exercise one capability.

    This compatibility helper now delegates to the same evaluator used by
    FastAPI dependencies, including super-admin bypass, prerequisite checks
    and conflict blocking for sensitive fields.
    """

    from app.core.authorization import AuthorizationEvaluator

    return AuthorizationEvaluator(user).check(permission_code).allowed


def validate_role_sensitive_permissions(
    role_name: str,
    permission_codes: set[str] | list[str] | tuple[str, ...],
) -> None:
    """Compatibility wrapper for code-level permission composition validation.

    ``role_name`` is intentionally ignored.  The old signature is retained
    for third-party callers during migration, but a display name must never
    decide whether a capability combination is safe.
    """

    from app.core.permission_catalog import validate_permission_set

    issues = validate_permission_set(permission_codes)
    if issues:
        raise ValueError("；".join(dict.fromkeys(issue.message for issue in issues)))


def validate_role_resource_permissions(
    role_name: str,
    permission_codes: set[str] | list[str] | tuple[str, ...],
) -> None:
    """Compatibility wrapper; resource conflicts are validated by capability code."""

    from app.core.permission_catalog import validate_permission_set

    issues = validate_permission_set(permission_codes)
    if issues:
        raise ValueError("；".join(dict.fromkeys(issue.message for issue in issues)))


def validate_execution_role_combination(role_names: list[str] | tuple[str, ...]) -> None:
    """Deprecated role-name API kept as a no-op during the migration.

    Callers that need validation must pass the effective permission union to
    ``validate_permission_set``.  Role names are labels and cannot express a
    security boundary for arbitrary custom roles.
    """

    del role_names


# ── Dependency factories ──────────────────────────────────────────────────

def require_permission(permission_code: str):
    """FastAPI dependency: require the current user to have a specific permission.

    The user's roles are checked (via the role_permissions join table).
    If none of the user's roles grant the required permission, a 403 is raised.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        # Lazy import avoids a module cycle: the evaluator reuses the
        # historical permission-code constants from this module.
        from app.core.authorization import AuthorizationEvaluator

        decision = AuthorizationEvaluator(current_user).check(permission_code)
        if decision.allowed:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=decision.message or f"权限不足: 需要「{permission_code}」权限",
        )

    return dependency


def require_any_permission(*permission_codes: str):
    """要求当前用户至少拥有一个指定权限。"""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        from app.core.authorization import AuthorizationEvaluator

        decision = AuthorizationEvaluator(current_user).check_any(*permission_codes)
        if decision.allowed:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=decision.message or f"权限不足: 需要以下任一权限「{'/'.join(permission_codes)}」",
        )

    return dependency


def require_all_permissions(*permission_codes: str):
    """要求当前用户同时拥有所有指定权限。

    This is used for a module parent gate plus a concrete business action.
    Keeping the check as a dependency prevents a route from accidentally
    falling back to the old broad ``outsource:*`` permission.
    """

    required = tuple(dict.fromkeys(permission_codes))
    if not required:
        raise ValueError("至少需要一个权限码")

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        from app.core.authorization import AuthorizationEvaluator

        decision = AuthorizationEvaluator(current_user).check_all(*required)
        if decision.allowed:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=decision.message or f"权限不足：请联系管理员开通「{'、'.join(required)}」权限",
        )

    return dependency


def require_role(role_name: str):
    """Compatibility-only role-name dependency for unmigrated integrations.

    New business routes must use ``require_permission`` or one of its
    composition helpers.  Keeping this adapter temporarily avoids breaking
    external integrations, but role names are not a safe authorization model
    for new code because custom roles may carry the same capabilities.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        for role in current_user.roles:
            if role.name == role_name:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要「{role_name}」角色",
        )

    return dependency


def require_any_role(*role_names: str):
    """Compatibility-only role-name dependency for unmigrated integrations."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        for role in current_user.roles:
            if role.name in role_names:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要{'/'.join(role_names)}角色",
        )

    return dependency
