from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission, require_role, PERM_USER_READ, PERM_USER_CREATE, PERM_USER_UPDATE, PERM_USER_DELETE
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.common import success, success_paginated
from app.services.user_service import UserService


class ResetPasswordRequest(BaseModel):
    new_password: str

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/all")
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有活跃用户（会话列表用）"""
    from app.repositories.user_repo import UserRepository
    repo = UserRepository(db)
    users = await repo.get_all_active_users(exclude_user_id=current_user.id)
    return success([{
        "id": str(u.id),
        "username": u.username,
        "real_name": u.real_name,
        "avatar": getattr(u, "avatar", None),
        "role": u.roles[0].name if u.roles else "",
    } for u in users])


@router.get("/")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USER_READ)),
):
    service = UserService(db)
    users, total = await service.list_users(page, page_size, keyword)
    return success_paginated(users, total, page, page_size)


@router.post("/")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USER_CREATE)),
):
    service = UserService(db)
    user = await service.create_user(data.model_dump())
    return success(user)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USER_READ)),
):
    service = UserService(db)
    user = await service.get_user(UUID(user_id))
    if not user:
        return {"code": 40401, "message": "用户不存在", "data": None}
    return success(user)


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USER_UPDATE)),
):
    service = UserService(db)
    user = await service.update_user(UUID(user_id), data.model_dump(exclude_none=True))
    return success(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USER_DELETE)),
):
    service = UserService(db)
    ok = await service.delete_user(UUID(user_id))
    if not ok:
        return {"code": 40401, "message": "用户不存在", "data": None}
    return success(None)


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USER_UPDATE)),
):
    service = UserService(db)
    ok = await service.reset_password(UUID(user_id), data.new_password)
    if not ok:
        return {"code": 40401, "message": "用户不存在", "data": None}
    return success(None)
