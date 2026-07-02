"""add chat tables

Revision ID: a32c1ade8b8e
Revises: 2254fcfe9080
Create Date: 2026-07-02 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a32c1ade8b8e'
down_revision: Union[str, None] = '2254fcfe9080'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建会话表
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('type', sa.String(20), nullable=False, server_default='private'),
        sa.Column('name', sa.String(128), nullable=True),
        sa.Column('avatar', sa.String(512), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_content', sa.String(256), nullable=True),
        sa.Column('last_message_sender_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_conversations_owner_id', 'conversations', ['owner_id'])
    op.create_index('ix_conversations_last_message_at', 'conversations', ['last_message_at'])

    # 创建会话成员表
    op.create_table(
        'conversation_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('nickname', sa.String(64), nullable=True),
        sa.Column('muted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_read_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_conversation_members_conversation_id', 'conversation_members', ['conversation_id'])
    op.create_index('ix_conversation_members_user_id', 'conversation_members', ['user_id'])
    op.create_unique_constraint('uq_conversation_member', 'conversation_members', ['conversation_id', 'user_id'])

    # 创建消息表
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('reply_to_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id'), nullable=True),
        sa.Column('mentions', postgresql.JSON(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # 创建已读回执表
    op.create_table(
        'message_read_receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_message_read_receipts_message_id', 'message_read_receipts', ['message_id'])
    op.create_index('ix_message_read_receipts_user_id', 'message_read_receipts', ['user_id'])
    op.create_unique_constraint('uq_message_read_receipt', 'message_read_receipts', ['message_id', 'user_id'])

    # 创建用户在线状态表
    op.create_table(
        'user_presence',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='offline'),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('user_presence')
    op.drop_table('message_read_receipts')
    op.drop_table('messages')
    op.drop_table('conversation_members')
    op.drop_table('conversations')
