"""后台管理 API — 仅 admin 角色可访问。"""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import require_role
from app.models.user import User, Role, Permission
from app.schemas.common import success
from app.repositories.user_repo import UserRepository

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Roles ──────────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    data = []
    for r in roles:
        data.append({
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "permissions": [{"id": str(p.id), "code": p.code, "name": p.name} for p in r.permissions],
        })
    return success(data)


@router.post("/roles")
async def create_role(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    name = data.get("name", "").strip()
    if not name:
        return {"code": 40001, "message": "角色名称不能为空", "data": None}
    existing = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if existing:
        return {"code": 40001, "message": "角色名称已存在", "data": None}
    role = Role(name=name, description=data.get("description"))
    db.add(role)
    await db.flush()
    return success({"id": str(role.id), "name": role.name, "description": role.description, "permissions": []})


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    role = (await db.execute(select(Role).where(Role.id == UUID(role_id)))).scalar_one_or_none()
    if not role:
        return {"code": 40401, "message": "角色不存在", "data": None}
    if "name" in data and data["name"]:
        role.name = data["name"].strip()
    if "description" in data:
        role.description = data["description"]
    await db.flush()
    return success({"id": str(role.id), "name": role.name, "description": role.description})


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    role = (await db.execute(select(Role).where(Role.id == UUID(role_id)))).scalar_one_or_none()
    if not role:
        return {"code": 40401, "message": "角色不存在", "data": None}
    if role.name == "admin":
        return {"code": 40001, "message": "不能删除 admin 角色", "data": None}
    await db.delete(role)
    await db.flush()
    return success(None)


@router.put("/roles/{role_id}/permissions")
async def set_role_permissions(
    role_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    role = (await db.execute(select(Role).where(Role.id == UUID(role_id)))).scalar_one_or_none()
    if not role:
        return {"code": 40401, "message": "角色不存在", "data": None}
    perm_ids = data.get("permission_ids", [])
    if perm_ids:
        perms = (await db.execute(select(Permission).where(Permission.id.in_([UUID(pid) for pid in perm_ids])))).scalars().all()
    else:
        perms = []
    role.permissions = list(perms)
    await db.flush()
    return success({"id": str(role.id), "name": role.name, "permissions": [{"id": str(p.id), "code": p.code, "name": p.name} for p in role.permissions]})


# ── Permissions ────────────────────────────────────────────────────────────

@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(Permission).order_by(Permission.code))
    perms = result.scalars().all()
    data = [{"id": str(p.id), "code": p.code, "name": p.name, "description": p.description} for p in perms]
    return success(data)


# ── System Settings ────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    current_user: User = Depends(require_role("admin")),
):
    api_key = settings.AI_API_KEY
    masked_key = api_key[:8] + "****" + api_key[-4:] if api_key and len(api_key) > 12 else "未配置"
    return success({
        "APP_NAME": settings.APP_NAME,
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
    data: dict,
    current_user: User = Depends(require_role("admin")),
):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if not os.path.exists(env_path):
        return {"code": 40001, "message": ".env 文件不存在", "data": None}

    allowed_keys = {"APP_NAME", "JWT_EXPIRE_MINUTES", "AI_ENABLED", "AI_PROVIDER", "AI_MODEL", "AI_API_KEY", "AI_API_BASE_URL"}
    updated = {}

    # Read current .env
    with open(env_path, "r") as f:
        lines = f.readlines()

    # Update existing keys or append new ones
    env_lines = {}
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            env_lines[key] = line

    for key, value in data.items():
        if key not in allowed_keys:
            continue
        str_val = str(value)
        if key in env_lines:
            env_lines[key] = f"{key}={str_val}\n"
        else:
            env_lines[key] = f"{key}={str_val}\n"
        updated[key] = str_val

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
