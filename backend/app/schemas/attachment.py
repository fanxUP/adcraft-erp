from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AttachmentCreate(BaseModel):
    filename: str
    file_path: str
    file_size: int | None = None
    file_type: str | None = None
    category: str | None = None
    remark: str | None = None


class AttachmentResponse(BaseModel):
    id: str
    related_type: str
    related_id: str
    filename: str
    file_path: str
    file_size: int | None = None
    file_type: str | None = None
    category: str | None = None
    uploaded_by: str | None = None
    remark: str | None = None
    created_at: str | None = None
