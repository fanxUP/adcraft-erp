from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.utils.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)
WEBSOCKET_AUTH_SUBPROTOCOL = "adcraft-auth"


def extract_websocket_token(websocket, query_token: str | None = None) -> tuple[str | None, str | None]:
    """Read a WebSocket token without putting the preferred token in the URL.

    ``Sec-WebSocket-Protocol`` is visible to the server during the handshake but
    is not normally included in reverse-proxy access logs. The query-string
    fallback keeps already deployed clients working during the frontend rollout;
    the WebSocket Nginx location disables access logging for that compatibility
    path.
    """
    protocol_header = websocket.headers.get("sec-websocket-protocol", "")
    protocols = [item.strip() for item in protocol_header.split(",") if item.strip()]
    if len(protocols) >= 2 and protocols[0] == WEBSOCKET_AUTH_SUBPROTOCOL:
        return protocols[1], WEBSOCKET_AUTH_SUBPROTOCOL

    token = query_token
    if token is None:
        token = websocket.query_params.get("token")
    return token, None


async def authenticate_websocket_token(db: AsyncSession, token: str | None) -> User | None:
    """Apply the same account lifecycle checks to realtime connections as HTTP."""
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        token_version = int(payload.get("token_version", 1))
    except (ValueError, KeyError, TypeError):
        return None

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    employee_result = await db.execute(
        select(Employee)
        .where(Employee.user_id == user.id)
        .order_by(Employee.deleted_at.is_not(None), Employee.created_at.desc())
        .limit(1)
    )
    employee = employee_result.scalar_one_or_none()
    if employee is not None and (
        employee.deleted_at is not None
        or employee.employment_status != "active"
        or employee.is_active is not True
    ):
        return None

    if token_version < int(getattr(user, "token_version", 1)):
        return None
    if getattr(user, "must_change_password", False):
        return None
    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    employee_result = await db.execute(
        select(Employee)
        .where(Employee.user_id == user.id)
        .order_by(Employee.deleted_at.is_not(None), Employee.created_at.desc())
        .limit(1)
    )
    employee = employee_result.scalar_one_or_none()
    if isinstance(employee, Employee) and (
        employee.deleted_at is not None
        or employee.employment_status != "active"
        or employee.is_active is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="员工已离职、停职或停用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 校验 token 版本号，如果用户 token_version 已升级则强制重新登录
    token_ver = payload.get("token_version", 1)
    if token_ver < user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 强制改密：初始密码未修改前，仅放行认证相关接口（/me、/change-password 等）
    if getattr(user, "must_change_password", False) and not request.url.path.startswith("/api/v1/auth/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先修改初始密码",
            headers={"X-Error-Code": "40300"},
        )
    return user
