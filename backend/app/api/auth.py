from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, UserPreferencesUpdate
from app.schemas.common import success
from app.services.auth_service import AuthService
from app.api.files import FILE_COOKIE, set_file_cookie
from app.core.deps import security_scheme

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def login(data: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.authenticate(data)
    if not result:
        raise HTTPException(status_code=401, detail="工号或密码错误")
    user, token = result
    set_file_cookie(response, request, token)
    return success({
        "token": token,
        "username": user.username,
        "real_name": user.real_name,
        "must_change_password": user.must_change_password,
    })


@router.get("/me")
async def me(request: Request, response: Response, credentials=Depends(security_scheme), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if credentials:
        set_file_cookie(response, request, credentials.credentials)
    service = AuthService(db)
    profile = await service.get_profile(current_user.id)
    return success(profile)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(FILE_COOKIE, path="/uploads", httponly=True, samesite="strict")
    return success(None)


@router.patch("/preferences")
async def update_preferences(
    data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    preferences = await service.update_preferences(
        current_user.id,
        data.model_dump(exclude_none=True),
    )
    if preferences is None:
        return {"code": 40401, "message": "当前用户不存在", "data": None}
    return success(preferences)


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
