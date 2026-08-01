"""remove_customer_agreements_and_price_rules

删除客户协议价与定价规则集——只保留产品/材质/工艺定价

Revision ID: a7b8c9d0e1f2
Revises: f2a3b4c5d6e7f809
Create Date: 2026-08-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f2a3b4c5d6e7f809'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # quote_versions.pricing_rule_set_id 引用 price_rule_sets，须先删
    op.drop_column("quote_versions", "pricing_rule_set_id")
    op.drop_table("customer_price_agreements")
    op.drop_table("cdr_price_rules")
    op.drop_table("price_rule_sets")


def downgrade() -> None:
    # 从 97d60c4ad1c9_add_cdr_quote_tables 复制原始表定义
    op.create_table("price_rule_sets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(32), server_default=sa.text("'draft'"), nullable=False, comment="draft | published | archived"),
        sa.Column("effective_from", sa.String(32), nullable=True, comment="YYYY-MM-DD"),
        sa.Column("effective_to", sa.String(32), nullable=True, comment="YYYY-MM-DD"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table("cdr_price_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("rule_set_id", UUID(as_uuid=True), sa.ForeignKey("price_rule_sets.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("conditions_json", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False, comment="触发条件列表"),
        sa.Column("actions_json", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False, comment="计算动作列表"),
        sa.Column("conflict_policy", sa.String(32), server_default=sa.text("'higher_priority_wins'"), nullable=False, comment="冲突策略"),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table("customer_price_agreements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=True),
        sa.Column("process_id", UUID(as_uuid=True), sa.ForeignKey("processes.id"), nullable=True),
        sa.Column("pricing_method", sa.String(32), nullable=False, comment="area | length | quantity | fixed"),
        sa.Column("price_value", sa.Numeric(14, 4), nullable=False),
        sa.Column("minimum_charge", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("discount_rate", sa.Numeric(8, 4), server_default=sa.text("1.0"), nullable=False, comment="折扣率：0.8=打8折"),
        sa.Column("effective_from", sa.String(32), nullable=False, comment="YYYY-MM-DD"),
        sa.Column("effective_to", sa.String(32), nullable=True, comment="YYYY-MM-DD"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.add_column("quote_versions",
        sa.Column("pricing_rule_set_id", UUID(as_uuid=True), sa.ForeignKey("price_rule_sets.id"), nullable=True)
    )
