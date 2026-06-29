from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.common import success, success_paginated
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    users, total = await service.list_users(page, page_size, keyword)
    return success_paginated(users, total, page, page_size)


@router.post("/")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    user = await service.create_user(data.model_dump())
    return success(user)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    user = await service.update_user(UUID(user_id), data.model_dump(exclude_none=True))
    return success(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    ok = await service.delete_user(UUID(user_id))
    if not ok:
        return {"code": 40401, "message": "用户不存在", "data": None}
    return success(None)
