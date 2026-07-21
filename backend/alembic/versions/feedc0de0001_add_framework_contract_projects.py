"""add framework contract projects

Revision ID: feedc0de0001
Revises: fa0b1c2d3e4f
Create Date: 2026-07-21 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'feedc0de0001'
down_revision: Union[str, None] = 'fa0b1c2d3e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 框架合同项目表
    op.create_table(
        'framework_contract_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contracts.id'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('project_name', sa.String(255), nullable=False),
        sa.Column('project_amount', sa.Numeric(14, 2), default=0),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('attachment_path', sa.String(500), nullable=True, comment='附件存储路径'),
        sa.Column('attachment_name', sa.String(255), nullable=True, comment='附件文件名'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

    # 框架合同项目-订单关联表
    op.create_table(
        'framework_contract_project_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('framework_contract_projects.id'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 框架合同项目-报价关联表
    op.create_table(
        'framework_contract_project_quotes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('framework_contract_projects.id'), nullable=False),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quotes.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('framework_contract_project_quotes')
    op.drop_table('framework_contract_project_orders')
    op.drop_table('framework_contract_projects')
