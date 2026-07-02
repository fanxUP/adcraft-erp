import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Conversation(Base, TimestampMixin):
    """会话表 - 支持私聊和群聊"""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="private")  # 'private' | 'group'
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 群聊名称
    avatar: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # 群头像
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 群主
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 最后消息时间
    last_message_content: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # 最后消息预览
    last_message_sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    last_message_sender = relationship("User", foreign_keys=[last_message_sender_id], lazy="selectin")
    members = relationship("ConversationMember", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan")


class ConversationMember(Base):
    """会话成员表"""
    __tablename__ = "conversation_members"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conversation_member"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")  # 'owner' | 'admin' | 'member'
    nickname: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 群内昵称
    muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 免打扰
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 最后阅读时间

    # Relationships
    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User", lazy="selectin")


class Message(Base, SoftDeleteMixin):
    """消息表"""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")  # 'text'|'image'|'file'|'system'|'reply'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reply_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    mentions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # @的用户ID列表
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)  # 扩展信息
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], lazy="selectin")
    reply_to = relationship("Message", remote_side=[id], lazy="selectin")


class MessageReadReceipt(Base):
    """已读回执表"""
    __tablename__ = "message_read_receipts"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_read_receipt"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    message = relationship("Message", lazy="selectin")
    user = relationship("User", lazy="selectin")


class UserPresence(Base):
    """用户在线状态表"""
    __tablename__ = "user_presence"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")  # 'online'|'away'|'busy'|'offline'
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", lazy="selectin")
