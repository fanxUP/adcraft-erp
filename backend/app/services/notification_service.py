import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepo
from app.schemas.notification import NotificationCreate, NotificationResponse

logger = logging.getLogger(__name__)

# WebSocket connection manager: user_id -> set of WebSocket connections
_ws_connections: dict[uuid.UUID, set] = {}


def register_ws(user_id: uuid.UUID, ws) -> None:
    """Register a WebSocket connection for a user."""
    if user_id not in _ws_connections:
        _ws_connections[user_id] = set()
    _ws_connections[user_id].add(ws)


def unregister_ws(user_id: uuid.UUID, ws) -> None:
    """Unregister a WebSocket connection."""
    if user_id in _ws_connections:
        _ws_connections[user_id].discard(ws)
        if not _ws_connections[user_id]:
            del _ws_connections[user_id]


async def broadcast_to_user(user_id: uuid.UUID, data: dict) -> None:
    """Send a message to all WebSocket connections of a specific user."""
    if user_id not in _ws_connections:
        return
    message = json.dumps(data, default=str)
    dead = set()
    for ws in _ws_connections[user_id]:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _ws_connections[user_id].discard(ws)
    if not _ws_connections.get(user_id):
        _ws_connections.pop(user_id, None)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepo(db)

    async def create_notification(self, data: NotificationCreate) -> Notification:
        notification = Notification(
            user_id=data.user_id,
            sender_id=data.sender_id,
            type=data.type,
            title=data.title,
            content=data.content,
            link=data.link,
        )
        notification = await self.repo.create(notification)
        await self.db.commit()

        # Broadcast via WebSocket
        resp = NotificationResponse.model_validate(notification).model_dump(mode="json")
        await broadcast_to_user(data.user_id, {"type": "new_notification", "data": resp})

        # Also broadcast updated unread count
        count = await self.repo.get_unread_count(data.user_id)
        await broadcast_to_user(data.user_id, {"type": "unread_count", "data": {"count": count}})

        return notification

    async def create_system_notification(
        self,
        user_id: uuid.UUID,
        type_: str,
        title: str,
        content: str,
        link: Optional[str] = None,
    ) -> Notification:
        return await self.create_notification(
            NotificationCreate(
                user_id=user_id,
                type=type_,
                title=title,
                content=content,
                link=link,
            )
        )

    async def send_user_message(
        self,
        sender_id: uuid.UUID,
        recipient_id: uuid.UUID,
        title: str,
        content: str,
        link: Optional[str] = None,
    ) -> Notification:
        return await self.create_notification(
            NotificationCreate(
                user_id=recipient_id,
                sender_id=sender_id,
                type="user_message",
                title=title,
                content=content,
                link=link,
            )
        )

    async def get_notifications(
        self,
        user_id: uuid.UUID,
        type_filter: Optional[str] = None,
        is_read: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[NotificationResponse], int]:
        items, total = await self.repo.get_list(
            user_id=user_id,
            type_filter=type_filter,
            is_read=is_read,
            page=page,
            page_size=page_size,
        )
        responses = []
        for item in items:
            resp = NotificationResponse.model_validate(item)
            if item.sender:
                resp.sender_name = item.sender.real_name or item.sender.username
            responses.append(resp)
        return responses, total

    async def get_recent(self, user_id: uuid.UUID, limit: int = 10) -> list[NotificationResponse]:
        items = await self.repo.get_recent(user_id, limit)
        responses = []
        for item in items:
            resp = NotificationResponse.model_validate(item)
            if item.sender:
                resp.sender_name = item.sender.real_name or item.sender.username
            responses.append(resp)
        return responses

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.get_unread_count(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        notification = await self.repo.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            return False
        result = await self.repo.mark_read(notification_id)
        if result:
            await self.db.commit()
            # Broadcast updated unread count
            count = await self.repo.get_unread_count(user_id)
            await broadcast_to_user(user_id, {"type": "unread_count", "data": {"count": count}})
        return result

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        count = await self.repo.mark_all_read(user_id)
        if count > 0:
            await self.db.commit()
            # Broadcast updated unread count
            await broadcast_to_user(user_id, {"type": "unread_count", "data": {"count": 0}})
        return count

    async def delete_notification(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        notification = await self.repo.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            return False
        result = await self.repo.delete(notification_id)
        if result:
            await self.db.commit()
        return result
