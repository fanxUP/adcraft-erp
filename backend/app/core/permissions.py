"""Permission code constants and RBAC dependency factories.

Usage in route definitions:

    from app.core.permissions import require_permission, PERM_BACKUP_CREATE

    @router.post("/create")
    async def create_backup(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_permission(PERM_BACKUP_CREATE)),
    ):
        ...

For admin-only endpoints:

    from app.core.permissions import require_role

    @router.delete("/{user_id}")
    async def delete_user(
        ...,
        current_user: User = Depends(require_role("admin")),
    ):
        ...
"""

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User

# ── Permission code constants ──────────────────────────────────────────────

# System
PERM_SYSTEM_LOGS = "system:logs"

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
PERM_ORDER_VIEW_PRICE = "order:view_price"
PERM_ORDER_ITEM_VIEW_PRICE = "order_item:view_price"

# Price and financial visibility.  These are deliberately separate from
# module read permissions: being able to process a task does not imply being
# able to see the commercial value of the order or its line items.
PERM_CATALOG_VIEW_PRICE = "catalog:view_price"
PERM_FINANCE_VIEW_COST = "finance:view_cost"
PERM_REPORT_VIEW_FINANCIAL = "report:view_financial"

# Design Task
PERM_DESIGN_TASK_READ = "design_task:read"
PERM_DESIGN_TASK_CREATE = "design_task:create"
PERM_DESIGN_TASK_UPDATE = "design_task:update"
PERM_DESIGN_TASK_CHANGE_STATUS = "design_task:change_status"

# Production Task
PERM_PRODUCTION_TASK_READ = "production_task:read"
PERM_PRODUCTION_TASK_CREATE = "production_task:create"
PERM_PRODUCTION_TASK_UPDATE = "production_task:update"
PERM_PRODUCTION_TASK_CHANGE_STATUS = "production_task:change_status"

# Installation Task
PERM_INSTALLATION_TASK_READ = "installation_task:read"
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

# Inventory
PERM_INVENTORY_READ = "inventory:read"
PERM_INVENTORY_CREATE = "inventory:create"
PERM_INVENTORY_UPDATE = "inventory:update"
PERM_INVENTORY_STOCK_IN = "inventory:stock_in"
PERM_INVENTORY_STOCK_OUT = "inventory:stock_out"

# Outsource
PERM_OUTSOURCE_READ = "outsource:read"
PERM_OUTSOURCE_CREATE = "outsource:create"
PERM_OUTSOURCE_UPDATE = "outsource:update"
PERM_OUTSOURCE_DELETE = "outsource:delete"
PERM_OUTSOURCE_PAYMENT_READ = "outsource_payment:read"
PERM_OUTSOURCE_PAYMENT_CREATE = "outsource_payment:create"

# Report
PERM_REPORT_READ = "report:read"

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
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_CREATE,
    PERM_DESIGN_TASK_UPDATE,
    PERM_DESIGN_TASK_CHANGE_STATUS,
    PERM_DESIGN_TASK_DELETE,
    PERM_PRODUCTION_TASK_READ,
    PERM_PRODUCTION_TASK_CREATE,
    PERM_PRODUCTION_TASK_UPDATE,
    PERM_PRODUCTION_TASK_CHANGE_STATUS,
    PERM_PRODUCTION_TASK_DELETE,
    PERM_INSTALLATION_TASK_READ,
    PERM_INSTALLATION_TASK_CREATE,
    PERM_INSTALLATION_TASK_UPDATE,
    PERM_INSTALLATION_TASK_CHANGE_STATUS,
    PERM_INSTALLATION_TASK_DELETE,
})


# Sensitive permissions are kept in one immutable set so role-management and
# response serializers can share the same security boundary.  The set is
# intentionally permission-code based rather than role-name based: custom
# business roles can still be evaluated consistently.
SENSITIVE_PERMISSION_CODES = frozenset({
    # Complete quote/contract capabilities are sensitive because their
    # normal read responses contain commercial amounts, even when a route is
    # not named ``view_price``.
    PERM_QUOTE_READ,
    PERM_QUOTE_CREATE,
    PERM_QUOTE_UPDATE,
    PERM_QUOTE_DELETE,
    PERM_QUOTE_CONFIRM,
    PERM_QUOTE_CONVERT,
    PERM_CONTRACT_READ,
    PERM_CONTRACT_CREATE,
    PERM_CONTRACT_UPDATE,
    PERM_CONTRACT_DELETE,
    PERM_CONTRACT_CHANGE_STATUS,
    # CDR quoting includes pricing rules, calculated totals and customer
    # agreements, so it must not be attached to an execution role either.
    PERM_CDR_QUOTE_READ,
    PERM_CDR_QUOTE_CREATE,
    PERM_CDR_QUOTE_UPDATE,
    PERM_CDR_QUOTE_DELETE,
    PERM_CDR_QUOTE_VIEW_COST,
    PERM_CDR_QUOTE_VIEW_PROFIT,
    PERM_CDR_QUOTE_ADJUST_PRICE,
    PERM_CDR_QUOTE_APPROVE,
    PERM_CDR_QUOTE_CONVERT,
    PERM_CDR_RULE_SET_PUBLISH,
    PERM_CDR_CUSTOMER_AGREEMENT_MANAGE,
    PERM_ORDER_VIEW_PRICE,
    PERM_ORDER_ITEM_VIEW_PRICE,
    PERM_CATALOG_VIEW_PRICE,
    PERM_FINANCE_VIEW_COST,
    PERM_REPORT_VIEW_FINANCIAL,
    PERM_REPORT_READ,
    PERM_PAYMENT_READ,
    PERM_PAYMENT_CREATE,
    PERM_PAYMENT_VOID,
    PERM_STATEMENT_READ,
    PERM_STATEMENT_CREATE,
    PERM_STATEMENT_CONFIRM,
    PERM_EXPENSE_READ,
    PERM_EXPENSE_CREATE,
    PERM_EXPENSE_UPDATE,
    PERM_EXPENSE_DELETE,
    PERM_OUTSOURCE_PAYMENT_READ,
    PERM_OUTSOURCE_PAYMENT_CREATE,
})

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

    granted = get_user_permission_codes(user)
    return {
        "view_order_price": PERM_ORDER_VIEW_PRICE in granted,
        "view_order_item_price": PERM_ORDER_ITEM_VIEW_PRICE in granted,
        "view_catalog_price": PERM_CATALOG_VIEW_PRICE in granted,
        "view_cost": PERM_FINANCE_VIEW_COST in granted,
        "view_financial_report": PERM_REPORT_VIEW_FINANCIAL in granted,
    }


def user_has_permission(user: User, permission_code: str) -> bool:
    """Return whether a database-loaded user has one explicit permission."""

    return permission_code in get_user_permission_codes(user)


def validate_role_sensitive_permissions(
    role_name: str,
    permission_codes: set[str] | list[str] | tuple[str, ...],
) -> None:
    """Prevent execution roles from being granted commercial permissions."""

    if role_name in {ROLE_ADMIN, *SENSITIVE_ROLE_NAMES}:
        return
    codes = set(permission_codes)
    execution_capable = (
        role_name in EXECUTION_ROLE_NAMES
        or bool(EXECUTION_PERMISSION_CODES.intersection(codes))
    )
    if execution_capable and SENSITIVE_PERMISSION_CODES.intersection(codes):
        raise ValueError("设计、制作、安装角色不能拥有价格或财务权限")


def validate_execution_role_combination(role_names: list[str] | tuple[str, ...]) -> None:
    """Prevent ordinary users from combining execution and sensitive roles."""

    names = set(role_names)
    if ROLE_ADMIN in names:
        return
    if EXECUTION_ROLE_NAMES.intersection(names) and SENSITIVE_ROLE_NAMES.intersection(names):
        raise ValueError("执行角色不能与销售或财务角色同时分配")


# ── Dependency factories ──────────────────────────────────────────────────

def require_permission(permission_code: str):
    """FastAPI dependency: require the current user to have a specific permission.

    The user's roles are checked (via the role_permissions join table).
    If none of the user's roles grant the required permission, a 403 is raised.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if user_has_permission(current_user, permission_code):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要「{permission_code}」权限",
        )

    return dependency


def require_any_permission(*permission_codes: str):
    """要求当前用户至少拥有一个指定权限。"""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        granted = {
            permission.code
            for role in current_user.roles
            for permission in role.permissions
        }
        if granted.intersection(permission_codes):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要以下任一权限「{'/'.join(permission_codes)}」",
        )

    return dependency


def require_role(role_name: str):
    """FastAPI dependency: require the current user to have a specific role.

    Simpler than require_permission — checks role name directly.
    Useful for broad admin/supervisor checks.
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
    """FastAPI dependency: require the current user to have at least one of the specified roles."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        for role in current_user.roles:
            if role.name in role_names:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要{'/'.join(role_names)}角色",
        )

    return dependency
