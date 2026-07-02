import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.schemas.notification import SendMessageRequest
from app.services.notification_service import (
    NotificationService,
    broadcast_to_user,
    register_ws,
    unregister_ws,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    type: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    items, total = await service.get_notifications(
        user_id=current_user.id,
        type_filter=type,
        is_read=is_read,
        page=page,
        page_size=page_size,
    )
    items_data = [item.model_dump(mode="json") for item in items]
    return success_paginated(items_data, total, page, page_size)


@router.get("/recent")
async def recent_notifications(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    items = await service.get_recent(current_user.id, limit)
    return success([item.model_dump(mode="json") for item in items])


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return success({"count": count})


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    result = await service.mark_read(notification_id, current_user.id)
    if not result:
        raise ValueError("通知不存在")
    return success()


@router.put("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    count = await service.mark_all_read(current_user.id)
    return success({"marked": count})


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    result = await service.delete_notification(notification_id, current_user.id)
    if not result:
        raise ValueError("通知不存在")
    return success()


@router.post("/send")
async def send_message(
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to another user."""
    service = NotificationService(db)
    notification = await service.send_user_message(
        sender_id=current_user.id,
        recipient_id=body.user_id,
        title=body.title,
        content=body.content,
        link=body.link,
    )
    return success({"id": str(notification.id)})


# WebSocket endpoint for real-time notifications
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for real-time notification push."""
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from jose import JWTError, jwt

    # Validate token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4001, reason="Invalid token")
            return
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    register_ws(user_id, websocket)

    # Send current unread count on connect
    try:
        async with AsyncSessionLocal() as db:
            service = NotificationService(db)
            count = await service.get_unread_count(user_id)
            await websocket.send_json({"type": "unread_count", "data": {"count": count}})
    except Exception as e:
        logger.warning(f"Failed to send initial unread count: {e}")

    try:
        while True:
            # Keep connection alive, wait for client messages (ping/pong)
            data = await websocket.receive_text()
            # Client can send "ping" to keep alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(user_id, websocket)
