from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    sender_id: Optional[UUID] = None
    sender_name: Optional[str] = None
    type: str
    title: str
    content: str
    link: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    user_id: UUID
    sender_id: Optional[UUID] = None
    type: str = "system_message"
    title: str
    content: str = ""
    link: Optional[str] = None


class SendMessageRequest(BaseModel):
    user_id: UUID
    title: str
    content: str
    link: Optional[str] = None


class UnreadCountResponse(BaseModel):
    count: int
