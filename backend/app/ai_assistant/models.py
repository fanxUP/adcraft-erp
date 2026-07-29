"""AI Assistant SQLAlchemy models."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AiChatSession(Base, TimestampMixin):
    """AI 会话表"""
    __tablename__ = "ai_chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_page: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    current_business_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_business_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("idx_ai_chat_sessions_user_id", "user_id"),
    )


class AiChatMessage(Base, TimestampMixin):
    """AI 消息表"""
    __tablename__ = "ai_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_chat_sessions.id"), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, comment="user/assistant/tool/system")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    __table_args__ = (
        Index("idx_ai_chat_messages_session_id", "session_id"),
        Index("idx_ai_chat_messages_role", "role"),
    )


class AiToolCallLog(Base, TimestampMixin):
    """AI 工具调用日志表"""
    __tablename__ = "ai_tool_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_args: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tool_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="level_1/level_2/level_3/level_4")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", comment="pending/running/success/failed/blocked/waiting_confirmation")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ai_tool_call_logs_user_id", "user_id"),
        Index("idx_ai_tool_call_logs_tool_name", "tool_name"),
        Index("idx_ai_tool_call_logs_status", "status"),
    )


class AiPendingAction(Base, TimestampMixin):
    """AI 待确认操作表"""
    __tablename__ = "ai_pending_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_chat_sessions.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_args: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    preview_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="waiting_confirmation",
                                         comment="waiting_confirmation/confirmed/executed/cancelled/expired/failed")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ai_pending_actions_user_id", "user_id"),
        Index("idx_ai_pending_actions_status", "status"),
    )


class AiOperationAuditLog(Base, TimestampMixin):
    """AI 操作审计日志表"""
    __tablename__ = "ai_operation_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    business_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    before_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ai_operation_audit_logs_user_id", "user_id"),
        Index("idx_ai_operation_audit_logs_business", "business_type", "business_id"),
    )


class AiBusinessRule(Base, TimestampMixin):
    """Source-controlled AI business rule with immutable version history."""

    __tablename__ = "ai_business_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    rule_key: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="active/superseded/retired",
    )

    __table_args__ = (
        UniqueConstraint(
            "rule_key",
            "version",
            name="uq_ai_business_rule_version",
        ),
        Index("idx_ai_business_rules_key_status", "rule_key", "status"),
    )


class AiBusinessRuleSyncLog(Base):
    """Append-only audit record for every business-rule synchronization."""

    __tablename__ = "ai_business_rule_sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    catalog_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    added_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retired_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "idx_ai_business_rule_sync_logs_created_at",
            "created_at",
        ),
    )
