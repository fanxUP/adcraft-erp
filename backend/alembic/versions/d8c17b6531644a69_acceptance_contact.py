"""acceptance_forms 增加自有联系人字段

Revision ID: d8c17b6531644a69
Revises: f2a3b4c5d6e7f809
Create Date: 2026-08-03

验收单联系人不再从关联订单/报价继承，改为验收单自己的字段，由验收方填写。
"""
from alembic import op
import sqlalchemy as sa

revision = "d8c17b6531644a69"
down_revision = "f2a3b4c5d6e7f809"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("acceptance_forms", sa.Column("contact_person", sa.String(128), nullable=True))
    op.add_column("acceptance_forms", sa.Column("contact_phone", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("acceptance_forms", "contact_phone")
    op.drop_column("acceptance_forms", "contact_person")
