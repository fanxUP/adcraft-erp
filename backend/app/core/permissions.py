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


# ── Role name constants ───────────────────────────────────────────────────

ROLE_ADMIN = "admin"
ROLE_SALES = "sales"
ROLE_DESIGNER = "designer"
ROLE_PRODUCTION = "production"
ROLE_INSTALLER = "installer"
ROLE_FINANCE = "finance"


# ── Dependency factories ──────────────────────────────────────────────────

def require_permission(permission_code: str):
    """FastAPI dependency: require the current user to have a specific permission.

    The user's roles are checked (via the role_permissions join table).
    If none of the user's roles grant the required permission, a 403 is raised.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        for role in current_user.roles:
            for perm in role.permissions:
                if perm.code == permission_code:
                    return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足: 需要「{permission_code}」权限",
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
