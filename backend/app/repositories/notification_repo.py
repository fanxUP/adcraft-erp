import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: uuid.UUID) -> Optional[Notification]:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        user_id: uuid.UUID,
        type_filter: Optional[str] = None,
        is_read: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        count_query = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id
        )

        if type_filter:
            query = query.where(Notification.type == type_filter)
            count_query = count_query.where(Notification.type == type_filter)
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
            count_query = count_query.where(Notification.is_read == is_read)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Notification.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar() or 0

    async def mark_read(self, notification_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_read=True, read_at=func.now())
        )
        return result.rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=func.now())
        )
        return result.rowcount

    async def delete(self, notification_id: uuid.UUID) -> bool:
        notification = await self.get_by_id(notification_id)
        if not notification:
            return False
        await self.db.delete(notification)
        return True

    async def get_recent(self, user_id: uuid.UUID, limit: int = 10) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
