"""后台管理 API — 仅 admin 角色可访问。"""

import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.admin import RoleCreate, RoleUpdate, RolePermissionUpdate, SettingsUpdate
from app.schemas.common import success, error
from app.services.role_service import RoleService
from app.services.operation_log_service import (
    log_operation,
    ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

OBJ_ROLE = "role"
OBJ_PERMISSION = "permission"
OBJ_SETTINGS = "settings"


# ── Roles ──────────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = RoleService(db)
    return success(await service.list_roles())


@router.post("/roles")
async def create_role(
    data: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = RoleService(db)
    try:
        role = await service.create_role(data.name, data.description)
    except ValueError as e:
        return error(40001, str(e))
    try:
        await log_operation(
            db, current_user.id, current_user.real_name or current_user.username,
            OBJ_ROLE, None, ACTION_CREATE,
            ip_address=request.client.host if request.client else None,
            after_data=role,
        )
    except Exception:
        logger.warning("Failed to log create_role operation", exc_info=True)
    return success(role)


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    data: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = RoleService(db)
    try:
        role = await service.update_role(UUID(role_id), data.model_dump(exclude_none=True))
    except ValueError as e:
        return error(40401, str(e))
    try:
        await log_operation(
            db, current_user.id, current_user.real_name or current_user.username,
            OBJ_ROLE, UUID(role_id), ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            after_data=role,
        )
    except Exception:
        logger.warning("Failed to log update_role operation", exc_info=True)
    return success(role)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = RoleService(db)
    try:
        await service.delete_role(UUID(role_id))
    except ValueError as e:
        return error(40001, str(e))
    try:
        await log_operation(
            db, current_user.id, current_user.real_name or current_user.username,
            OBJ_ROLE, UUID(role_id), ACTION_DELETE,
            ip_address=request.client.host if request.client else None,
        )
    except Exception:
        logger.warning("Failed to log delete_role operation", exc_info=True)
    return success(None)


@router.put("/roles/{role_id}/permissions")
async def set_role_permissions(
    role_id: str,
    data: RolePermissionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = RoleService(db)
    try:
        result = await service.set_role_permissions(UUID(role_id), data.permission_ids)
    except ValueError as e:
        msg = str(e)
        # Distinguish "role not found" from invalid UUID input
        if "不存在" in msg:
            return error(40401, msg)
        return error(40001, msg)
    try:
        await log_operation(
            db, current_user.id, current_user.real_name or current_user.username,
            OBJ_PERMISSION, UUID(role_id), ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            after_data={"permission_count": len(result.get("permissions", []))},
        )
    except Exception:
        logger.warning("Failed to log set_role_permissions operation", exc_info=True)
    return success(result)


# ── Permissions ────────────────────────────────────────────────────────────

@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    service = RoleService(db)
    return success(await service.list_permissions())


# ── System Settings ────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    current_user: User = Depends(get_current_user),
):
    api_key = settings.AI_API_KEY
    masked_key = api_key[:8] + "****" + api_key[-4:] if api_key and len(api_key) > 12 else "未配置"
    return success({
        "APP_NAME": settings.APP_NAME,
        "COMPANY_NAME": settings.COMPANY_NAME,
        "JWT_EXPIRE_MINUTES": settings.JWT_EXPIRE_MINUTES,
        "UPLOAD_STORAGE": settings.UPLOAD_STORAGE,
        "LOCAL_UPLOAD_DIR": settings.LOCAL_UPLOAD_DIR,
        "AI_ENABLED": settings.AI_ENABLED,
        "AI_PROVIDER": settings.AI_PROVIDER,
        "AI_MODEL": settings.AI_MODEL,
        "AI_API_KEY": masked_key,
        "AI_API_BASE_URL": settings.AI_API_BASE_URL,
    })


@router.put("/settings")
async def update_settings(
    data: SettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    # admin.py is at backend/app/api/admin.py — go up 4 levels to project root (local dev).
    # In Docker the file is at /app/app/api/admin.py, so 4 levels hits / which is not writable.
    # Fall back to /app/.env in that case.
    _file_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_file_dir))))
    if _project_root in ("/", ""):
        _project_root = "/app"
    env_path = os.path.join(_project_root, ".env")

    # In Docker, the .env file may not exist (env vars come from compose).
    # If missing, create from current settings so it can be managed going forward.
    if not os.path.exists(env_path):
        lines = []
        env_lines = {}
    else:
        with open(env_path, "r") as f:
            lines = f.readlines()
        env_lines = {}
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0]
                env_lines[key] = line

    allowed_keys = {"APP_NAME", "COMPANY_NAME", "JWT_EXPIRE_MINUTES", "AI_ENABLED", "AI_PROVIDER", "AI_MODEL", "AI_API_KEY", "AI_API_BASE_URL"}
    updated = {}

    for key, value in data.model_dump(exclude_none=True).items():
        if key not in allowed_keys:
            continue
        str_val = str(value)
        env_lines[key] = f'{key}="{str_val}"\n' if " " in str_val else f"{key}={str_val}\n"
        updated[key] = str_val

    if not updated:
        return error(40001, "没有有效的配置项可更新")

    # Log first — if this fails, don't write the file
    try:
        await log_operation(
            db, current_user.id, current_user.real_name or current_user.username,
            OBJ_SETTINGS, None, ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            after_data=updated,
        )
    except Exception:
        logger.warning("Failed to log update_settings operation", exc_info=True)

    # Rewrite .env preserving comments and order
    with open(env_path, "w") as f:
        written = set()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0]
                if key in env_lines:
                    f.write(env_lines[key])
                    written.add(key)
            else:
                f.write(line)
        for key, line in env_lines.items():
            if key not in written:
                f.write(line)

    return success({"updated": updated, "message": "配置已更新，重启服务后生效"})
