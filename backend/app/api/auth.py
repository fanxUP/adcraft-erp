from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest
from app.schemas.common import success
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.authenticate(data)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user, token = result
    return success({
        "token": token,
        "username": user.username,
        "real_name": user.real_name,
    })


@router.get("/me")
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    profile = await service.get_profile(current_user.id)
    return success(profile)


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    ok = await service.change_password(current_user.id, data.old_password, data.new_password)
    if not ok:
        return {"code": 40101, "message": "原密码错误", "data": None}
    return success(None)
