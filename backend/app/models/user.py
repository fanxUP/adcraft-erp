import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Table, Column, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # Built-in defaults are applied once by the bootstrap script.  A later
    # seed refreshes the permission catalog but never overwrites a role that
    # has already been initialized or customized.
    permission_seed_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, lazy="selectin")
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles", lazy="selectin")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # Structured authorization metadata.  The stable code remains the
    # compatibility identifier; these fields drive grouping, dependency
    # validation and sensitivity-aware admin UI.
    module: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    resource: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(64), nullable=False, default="read")
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="action")
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="JWT token 版本号")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="首次登录需强制改密")

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")
    preferences: Mapped["UserPreference | None"] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )


# Register the related model whenever the user model is imported.  The
# relationship uses a string target to avoid a circular import in the model
# modules, while Alembic still receives the table through env.py.
from app.models.user_preferences import UserPreference  # noqa: E402,F401
