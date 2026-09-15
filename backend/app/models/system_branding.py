"""Persisted application branding shared by the login and authenticated UI."""

import uuid

from sqlalchemy import Integer, LargeBinary, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


SYSTEM_BRANDING_ID = 1


class SystemBranding(Base, TimestampMixin):
    """The single editable visual identity for the application.

    The logo bytes live in the database rather than the uploads directory so
    the existing database-only backup/restore workflow also preserves the
    branding configuration.
    """

    __tablename__ = "system_branding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    logo_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    logo_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logo_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
