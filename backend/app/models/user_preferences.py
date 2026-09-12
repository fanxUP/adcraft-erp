"""Per-user UI preferences.

These values are deliberately kept separate from the user identity and
password fields.  The server only accepts the small allow-listed set exposed
by the authentication API; the browser cache is never the source of truth.
"""

import uuid

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    # A primary key also enforces the one-to-one relationship with users.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    theme: Mapped[str] = mapped_column(String(32), nullable=False, default="light-blue")
    font_size: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=14)
    font_weight: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=400)

    user = relationship("User", back_populates="preferences", lazy="selectin")
