"""后台管理 API — 仅显式 system:super_admin 能力可访问。"""

import logging
import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permission_catalog import permission_pack_definitions
from app.core.permissions import PERM_SYSTEM_SUPER_ADMIN, require_permission
from app.models.user import User
from app.schemas.admin import RoleCreate, RoleUpdate, RolePermissionUpdate, SettingsUpdate
from app.schemas.common import success, error
from app.services.branding_service import (
    admin_branding_payload,
    get_branding,
    remove_logo,
    replace_logo,
)
from app.services.role_service import RoleService
from app.services.operation_log_service import (
    log_operation,
    ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE,
)

logger = logging.getLogger(__name__)


def _resolve_settings_env_path() -> str:
    """Resolve the configuration file used by the current runtime.

    Native systemd and Docker both keep the deployment .env at the project
    root.  The old upward search stopped at ``backend/.env`` when that stale
    compatibility file happened to exist, which made the save endpoint write
    to a protected source directory instead of the file actually loaded by
    the service.  An explicit override keeps packaged/custom deployments
    deterministic; the ordered fallbacks preserve local development support.
    """
    configured_path = os.environ.get("ADCRAFT_ENV_FILE", "").strip()
    if configured_path:
        return os.path.abspath(os.path.expanduser(configured_path))

    module_path = Path(__file__).resolve()
    project_root = module_path.parents[3]
    project_env = project_root / ".env"
    candidates = (
        project_env,
        Path("/app/.env"),
        Path.cwd() / ".env",
        module_path.parents[2] / ".env",
    )
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            return normalized
    return str(project_env)


def _rewrite_env_file(env_path: str, env_lines: dict) -> None:
    """Rewrite a .env file, preserving comments/order, overriding keys in env_lines."""
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    else:
        lines = []
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


router = APIRouter(prefix="/admin", tags=["Admin"])

OBJ_ROLE = "role"
OBJ_PERMISSION = "permission"
OBJ_SETTINGS = "settings"


# ── Roles ──────────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    service = RoleService(db)
    return success(await service.list_roles())


@router.post("/roles")
async def create_role(
    data: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
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
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
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
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
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
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    service = RoleService(db)
    try:
        role_before = await service.repo.get_by_id(UUID(role_id))
        before_codes = [permission.code for permission in getattr(role_before, "permissions", ()) or ()] if role_before else []
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
            before_data={"permissions": before_codes},
            after_data={
                "permissions": [permission["code"] for permission in result.get("permissions", [])],
                "added_permissions": result.get("added_permissions", []),
                "removed_permissions": result.get("removed_permissions", []),
            },
        )
    except Exception:
        logger.warning("Failed to log set_role_permissions operation", exc_info=True)
    return success(result)


@router.post("/roles/{role_id}/permissions/preview")
async def preview_role_permissions(
    role_id: str,
    data: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    """Dry-run a complete permission composition without persisting it."""
    service = RoleService(db)
    try:
        result = await service.preview_role_permissions(UUID(role_id), data.permission_ids)
    except ValueError as e:
        msg = str(e)
        if "不存在" in msg:
            return error(40401, msg)
        return error(40001, msg)
    return success(result)


# ── Permissions ────────────────────────────────────────────────────────────

@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    service = RoleService(db)
    return success(await service.list_permissions())


@router.get("/permission-packs")
async def list_permission_packs(
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    """Return editor shortcuts; roles persist the expanded permission IDs."""
    return success([
        {
            "code": pack.code,
            "name": pack.name,
            "description": pack.description,
            "permissions": list(pack.permissions),
        }
        for pack in permission_pack_definitions()
    ])


# ── System Settings ────────────────────────────────────────────────────────

@router.post("/force-relogin")
async def force_relogin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    """递增所有活跃用户的令牌版本，使现有 JWT 在下次请求时失效。"""
    await db.execute(
        update(User)
        .where(User.deleted_at.is_(None), User.is_active.is_(True))
        .values(token_version=User.token_version + 1)
    )
    await db.commit()
    return success({"message": "已强制所有用户重新登录"})

@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    api_key = settings.AI_API_KEY
    masked_key = api_key[:8] + "****" + api_key[-4:] if api_key and len(api_key) > 12 else "未配置"
    branding = admin_branding_payload(settings.APP_NAME, await get_branding(db))
    return success({
        "APP_NAME": settings.APP_NAME,
        "COMPANY_NAME": settings.COMPANY_NAME,
        "COMPANY_PHONE": settings.COMPANY_PHONE,
        "JWT_EXPIRE_MINUTES": settings.JWT_EXPIRE_MINUTES,
        "UPLOAD_STORAGE": settings.UPLOAD_STORAGE,
        "LOCAL_UPLOAD_DIR": settings.LOCAL_UPLOAD_DIR,
        "AI_ENABLED": settings.AI_ENABLED,
        "AI_PROVIDER": settings.AI_PROVIDER,
        "AI_MODEL": settings.AI_MODEL,
        "AI_API_KEY": masked_key,
        "AI_API_BASE_URL": settings.AI_API_BASE_URL,
        "BRANDING": branding,
    })


@router.post("/settings/logo")
async def upload_system_logo(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    try:
        branding = await replace_logo(db, file, current_user.id, settings.APP_NAME)
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))

    try:
        await log_operation(
            db,
            current_user.id,
            current_user.real_name or current_user.username,
            OBJ_SETTINGS,
            None,
            ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            after_data={
                "logo_filename": branding["logo_filename"],
                "logo_content_type": branding["logo_content_type"],
                "logo_size": branding["logo_size"],
                "logo_version": branding["logo_version"],
            },
        )
    except Exception:
        logger.warning("Failed to log upload_system_logo operation", exc_info=True)
    return success({"branding": branding, "message": "logo 已更新"})


@router.delete("/settings/logo")
async def delete_system_logo(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    branding = await remove_logo(db, current_user.id, settings.APP_NAME)
    try:
        await log_operation(
            db,
            current_user.id,
            current_user.real_name or current_user.username,
            OBJ_SETTINGS,
            None,
            ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            after_data={"logo_version": branding["logo_version"], "restored_default": True},
        )
    except Exception:
        logger.warning("Failed to log delete_system_logo operation", exc_info=True)
    return success({"branding": branding, "message": "logo 已恢复默认"})


@router.put("/settings")
async def update_settings(
    data: SettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    env_path = _resolve_settings_env_path()

    # In Docker, the .env file may not exist (env vars come from compose).
    # If missing, create from current settings so it can be managed going forward.
    try:
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
    except OSError:
        logger.exception("Failed to read system settings from %s", env_path)
        return error(50002, "系统设置保存失败，请联系管理员检查配置文件权限")

    allowed_keys = {"APP_NAME", "COMPANY_NAME", "COMPANY_PHONE", "JWT_EXPIRE_MINUTES", "AI_ENABLED", "AI_PROVIDER", "AI_MODEL", "AI_API_KEY", "AI_API_BASE_URL"}
    updated = {}

    for key, value in data.model_dump(exclude_none=True).items():
        if key not in allowed_keys:
            continue
        str_val = str(value)
        escaped_val = str_val.replace("\\", "\\\\").replace('"', '\\"')
        env_lines[key] = f'{key}="{escaped_val}"\n'
        updated[key] = str_val

    if not updated:
        return error(40001, "没有有效的配置项可更新")

    # Write first.  A failed persistence must not leave an operation log that
    # claims the setting changed when the file was never updated.
    try:
        _rewrite_env_file(env_path, env_lines)
    except OSError:
        logger.exception("Failed to persist system settings to %s", env_path)
        return error(50002, "系统设置保存失败，请联系管理员检查配置文件权限")

    # Also update in-memory settings so changes take effect immediately
    for key, value in data.model_dump(exclude_none=True).items():
        if key in allowed_keys and hasattr(settings, key):
            setattr(settings, key, value)

    # Never place an API key in the operation log.  The log records the fact
    # that it changed while the secret remains only in the protected config.
    audit_data = dict(updated)
    if "AI_API_KEY" in audit_data:
        audit_data["AI_API_KEY"] = "***已更新***"
    try:
        await log_operation(
            db, current_user.id, current_user.real_name or current_user.username,
            OBJ_SETTINGS, None, ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            after_data=audit_data,
        )
    except Exception:
        logger.warning("Failed to log update_settings operation", exc_info=True)

    response_updated = dict(updated)
    if "AI_API_KEY" in response_updated:
        response_updated["AI_API_KEY"] = "***已更新***"
    return success({"updated": response_updated, "message": "配置已更新"})
