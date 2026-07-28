"""add quote_item_id to project_costs

Revision ID: cc23a92b0294
Revises: cc23a92b0293
Create Date: 2026-07-09 19:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cc23a92b0294"
down_revision: Union[str, None] = "cc23a92b0293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 部分环境的历史迁移未创建该字段，使用幂等 DDL 兼容新旧数据库。
    op.execute(
        sa.text(
            "ALTER TABLE project_costs "
            "ADD COLUMN IF NOT EXISTS quote_item_id UUID"
        )
    )


def downgrade() -> None:
    pass
