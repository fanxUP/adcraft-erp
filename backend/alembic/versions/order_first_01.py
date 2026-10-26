"""Unified order creation, reconciliation work and immutable fund reversals.

Revision ID: order_first_01
Revises: fcr01_finance_recon
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "order_first_01"
down_revision = "fcr01_finance_recon"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("customer_statements", sa.Column("snapshot_json", pg.JSONB(), nullable=True))
    op.add_column("business_documents", sa.Column("creation_request_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_business_documents_creation_request_id", "business_documents", ["creation_request_id"])
    op.add_column("business_documents", sa.Column("settlement_adjustment", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("record_type", sa.String(16), nullable=False, server_default="receipt"))
    op.add_column("payments", sa.Column("reference_payment_id", pg.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=True))
    op.create_index("ix_payments_reference_payment_id", "payments", ["reference_payment_id"])
    op.add_column("payments", sa.Column("request_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_payments_request_id", "payments", ["request_id"])
    # Allocation reversals are signed ledger entries. The original entries
    # remain unchanged; all existing readers already aggregate their net sum.
    op.drop_constraint("ck_payment_allocations_amount_positive", "payment_allocations", type_="check")
    op.create_check_constraint("ck_payment_allocations_amount_positive", "payment_allocations", "allocated_amount <> 0")
    for name in ("planned_quantity", "completed_quantity"):
        op.add_column("task_order_item_links", sa.Column(name, sa.Numeric(14, 3), nullable=True))
    op.add_column("task_order_item_links", sa.Column("scope_snapshot", pg.JSONB(), nullable=True))
    op.create_table(
        "order_change_actions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", pg.UUID(as_uuid=True), sa.ForeignKey("business_documents.id"), nullable=False),
        sa.Column("batch_id", sa.String(64), nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("record_key", sa.String(128), nullable=False),
        sa.Column("record_no", sa.String(128)),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("assigned_to", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("context", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "batch_id", "module", "record_key", "action_type", name="uq_order_change_action_source"),
        sa.CheckConstraint("status IN ('pending', 'resolved')", name="ck_order_change_action_status"),
    )
    op.create_index("ix_order_change_actions_document_id", "order_change_actions", ["document_id"])


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT EXISTS (SELECT 1 FROM payment_allocations WHERE allocated_amount < 0) OR EXISTS (SELECT 1 FROM payments WHERE record_type = 'refund') OR EXISTS (SELECT 1 FROM order_change_actions) OR EXISTS (SELECT 1 FROM customer_statements WHERE snapshot_json IS NOT NULL) OR EXISTS (SELECT 1 FROM business_documents WHERE creation_request_id IS NOT NULL) OR EXISTS (SELECT 1 FROM task_order_item_links WHERE scope_snapshot IS NOT NULL OR completed_quantity IS NOT NULL)")).scalar():
        raise RuntimeError("已有订单变更或资金冲回记录；请使用兼容代码回滚，禁止删除真实业务记录")
    op.drop_column("customer_statements", "snapshot_json")
    op.drop_table("order_change_actions")
    for name in ("scope_snapshot", "completed_quantity", "planned_quantity"):
        op.drop_column("task_order_item_links", name)
    op.drop_constraint("ck_payment_allocations_amount_positive", "payment_allocations", type_="check")
    op.create_check_constraint("ck_payment_allocations_amount_positive", "payment_allocations", "allocated_amount > 0")
    op.drop_constraint("uq_payments_request_id", "payments", type_="unique")
    op.drop_column("payments", "request_id")
    op.drop_index("ix_payments_reference_payment_id", table_name="payments")
    op.drop_column("payments", "reference_payment_id")
    op.drop_column("payments", "record_type")
    op.drop_column("business_documents", "settlement_adjustment")
    op.drop_constraint("uq_business_documents_creation_request_id", "business_documents", type_="unique")
    op.drop_column("business_documents", "creation_request_id")
