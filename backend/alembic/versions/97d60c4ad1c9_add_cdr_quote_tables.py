"""add_cdr_quote_tables

增强产品/材料/工艺模型 + 新增 CDR 智能报价领域表

Revision ID: 97d60c4ad1c9
Revises: e5f6g7h8vehicle
Create Date: 2026-07-27 12:23:49.775745
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = '97d60c4ad1c9'
down_revision: Union[str, None] = 'e5f6g7h8vehicle'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. 增强 products 表 ──
    op.add_column("products", sa.Column("requires_geometry", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否需要 CDR 几何数据"))
    op.add_column("products", sa.Column("needs_installation", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否需要安装"))
    op.add_column("products", sa.Column("allows_outsource", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否允许外协"))
    op.add_column("products", sa.Column("needs_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否需要审批"))
    op.add_column("products", sa.Column("default_loss_rate", sa.Numeric(8, 4), server_default=sa.text("0"), nullable=False, comment="默认损耗率"))
    op.add_column("products", sa.Column("standard_lead_days", sa.Integer(), nullable=True, comment="标准交期（天）"))

    # ── 2. 增强 materials 表 ──
    op.add_column("materials", sa.Column("category", sa.String(64), nullable=True, comment="材料分类：板材/卷材/辅材等"))
    op.add_column("materials", sa.Column("thickness_mm", sa.Numeric(8, 2), nullable=True, comment="厚度(mm)"))
    op.add_column("materials", sa.Column("sheet_width_mm", sa.Numeric(10, 2), nullable=True, comment="单张/单卷宽度(mm)"))
    op.add_column("materials", sa.Column("sheet_height_mm", sa.Numeric(10, 2), nullable=True, comment="单张/单卷高度(mm)"))
    op.add_column("materials", sa.Column("purchase_unit", sa.String(32), nullable=True, comment="采购单位"))
    op.add_column("materials", sa.Column("min_purchase_qty", sa.Numeric(14, 3), server_default=sa.text("0"), nullable=False, comment="最小采购量"))
    op.add_column("materials", sa.Column("supplier", sa.String(255), nullable=True, comment="默认供应商"))
    op.add_column("materials", sa.Column("price_updated_at", sa.String(32), nullable=True, comment="上次调价时间"))

    # ── 3. 增强 processes 表 ──
    op.add_column("processes", sa.Column("billing_basis", sa.String(32), server_default=sa.text("'fixed'"), nullable=False, comment="计价基准: area/length/quantity/hours/fixed"))
    op.add_column("processes", sa.Column("machine_type", sa.String(64), nullable=True, comment="设备类型"))
    op.add_column("processes", sa.Column("startup_fee", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False, comment="开机费"))
    op.add_column("processes", sa.Column("min_charge", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False, comment="最低收费"))
    op.add_column("processes", sa.Column("standard_hours", sa.Numeric(8, 2), nullable=True, comment="标准人工工时"))

    # ── 4. 材料价格版本 ──
    op.create_table("material_price_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("supplier", sa.String(255), nullable=True),
        sa.Column("price_type", sa.String(32), server_default=sa.text("'purchase'"), nullable=False, comment="purchase|sale"),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("tax_included", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("tax_rate", sa.Numeric(8, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("effective_from", sa.String(32), nullable=False, comment="YYYY-MM-DD"),
        sa.Column("effective_to", sa.String(32), nullable=True, comment="YYYY-MM-DD"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 5. 定价规则集 ──
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

    # ── 6. CDR 定价规则 ──
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

    # ── 7. 客户协议价 ──
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

    # ── 8. 报价版本（先删除旧表如果存在，使用新结构） ──
    op.execute("DROP TABLE IF EXISTS quote_versions CASCADE")
    op.create_table("quote_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("business_documents.id"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("pricing_rule_set_id", UUID(as_uuid=True), sa.ForeignKey("price_rule_sets.id"), nullable=True),
        sa.Column("status", sa.String(32), server_default=sa.text("'draft'"), nullable=False, comment="draft | review | approved | rejected"),
        sa.Column("subtotal_amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("discount_amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("tax_rate", sa.Numeric(8, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_profit", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_margin", sa.Numeric(8, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("snapshot_json", JSONB(), nullable=True, comment="报价快照"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 9. 报价明细行 ──
    op.create_table("quote_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("version_id", UUID(as_uuid=True), sa.ForeignKey("quote_versions.id"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("width_mm", sa.Numeric(12, 3), nullable=True),
        sa.Column("height_mm", sa.Numeric(12, 3), nullable=True),
        sa.Column("length_m", sa.Numeric(12, 3), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), server_default=sa.text("1"), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("pieces", sa.Numeric(10, 2), nullable=True, comment="件数"),
        sa.Column("billable_quantity", sa.Numeric(14, 4), server_default=sa.text("0"), nullable=False, comment="计费数量（含损耗）"),
        sa.Column("unit_price", sa.Numeric(14, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("manual_adjustment", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("manual_reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), server_default=sa.text("'auto'"), nullable=False, comment="auto | manual"),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("pricing_trace_json", JSONB(), nullable=True, comment="规则执行过程"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 10. 报价行工艺明细 ──
    op.create_table("quote_line_processes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("line_id", UUID(as_uuid=True), sa.ForeignKey("quote_lines.id"), nullable=False),
        sa.Column("process_id", UUID(as_uuid=True), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("billing_quantity", sa.Numeric(14, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_amount", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("pricing_trace_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 11. 审批记录 ──
    op.create_table("quote_approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("business_documents.id"), nullable=False),
        sa.Column("quote_version_id", UUID(as_uuid=True), sa.ForeignKey("quote_versions.id"), nullable=True),
        sa.Column("approval_type", sa.String(32), nullable=False, comment="low_margin | over_discount | price_override | high_value"),
        sa.Column("requested_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approver_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(32), server_default=sa.text("'pending'"), nullable=False, comment="pending | approved | rejected"),
        sa.Column("reason", sa.Text(), nullable=True, comment="请求原因"),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 12. 审计日志 ──
    op.create_table("quote_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("business_documents.id"), nullable=False),
        sa.Column("quote_version_id", UUID(as_uuid=True), sa.ForeignKey("quote_versions.id"), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("before_json", JSONB(), nullable=True),
        sa.Column("after_json", JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("device_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── 13. CDR 设备 ──
    op.create_table("cdr_devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("device_code", sa.String(64), unique=True, nullable=False),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("machine_fingerprint_hash", sa.String(128), nullable=False),
        sa.Column("plugin_version", sa.String(32), nullable=True),
        sa.Column("bridge_version", sa.String(32), nullable=True),
        sa.Column("coreldraw_versions_json", JSONB(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(32), server_default=sa.text("'active'"), nullable=False, comment="active | revoked"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 14. CDR 采集会话 ──
    op.create_table("cdr_capture_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("session_code", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("cdr_devices.id"), nullable=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("document_name", sa.String(500), nullable=True),
        sa.Column("document_path_hash", sa.String(128), nullable=True),
        sa.Column("coreldraw_version", sa.String(32), nullable=True),
        sa.Column("page_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("page_name", sa.String(128), nullable=True),
        sa.Column("selection_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("drawing_fingerprint", sa.String(128), nullable=True),
        sa.Column("capture_payload_json", JSONB(), nullable=True),
        sa.Column("warnings_json", JSONB(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 15. 图稿快照 ──
    op.create_table("drawing_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_code", sa.String(64), unique=True, nullable=False),
        sa.Column("capture_session_id", UUID(as_uuid=True), sa.ForeignKey("cdr_capture_sessions.id"), nullable=True),
        sa.Column("quote_id", UUID(as_uuid=True), sa.ForeignKey("business_documents.id"), nullable=True),
        sa.Column("quote_version_id", UUID(as_uuid=True), sa.ForeignKey("quote_versions.id"), nullable=True),
        sa.Column("drawing_fingerprint", sa.String(128), nullable=True),
        sa.Column("geometry_summary_json", JSONB(), nullable=True, comment="几何摘要"),
        sa.Column("object_summary_json", JSONB(), nullable=True, comment="对象摘要"),
        sa.Column("preview_file_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ── 索引 ──
    op.create_index("ix_quote_versions_quote_id", "quote_versions", ["quote_id"])
    op.create_index("ix_quote_lines_version_id", "quote_lines", ["version_id"])
    op.create_index("ix_quote_line_processes_line_id", "quote_line_processes", ["line_id"])
    op.create_index("ix_quote_approvals_quote_id", "quote_approvals", ["quote_id"])
    op.create_index("ix_quote_audit_logs_quote_id", "quote_audit_logs", ["quote_id"])
    op.create_index("ix_cdr_capture_sessions_device_id", "cdr_capture_sessions", ["device_id"])
    op.create_index("ix_drawing_snapshots_quote_id", "drawing_snapshots", ["quote_id"])
    op.create_index("ix_drawing_snapshots_capture_session_id", "drawing_snapshots", ["capture_session_id"])
    op.create_index("ix_customer_price_agreements_customer_id", "customer_price_agreements", ["customer_id"])


def downgrade() -> None:
    # 删除索引
    op.drop_index("ix_customer_price_agreements_customer_id")
    op.drop_index("ix_drawing_snapshots_capture_session_id")
    op.drop_index("ix_drawing_snapshots_quote_id")
    op.drop_index("ix_cdr_capture_sessions_device_id")
    op.drop_index("ix_quote_audit_logs_quote_id")
    op.drop_index("ix_quote_approvals_quote_id")
    op.drop_index("ix_quote_line_processes_line_id")
    op.drop_index("ix_quote_lines_version_id")
    op.drop_index("ix_quote_versions_quote_id")

    # 删除表
    op.drop_table("drawing_snapshots")
    op.drop_table("cdr_capture_sessions")
    op.drop_table("cdr_devices")
    op.drop_table("quote_audit_logs")
    op.drop_table("quote_approvals")
    op.drop_table("quote_line_processes")
    op.drop_table("quote_lines")
    op.drop_table("quote_versions")
    op.drop_table("customer_price_agreements")
    op.drop_table("cdr_price_rules")
    op.drop_table("price_rule_sets")
    op.drop_table("material_price_versions")

    # 删除 processes 新增字段
    op.drop_column("processes", "standard_hours")
    op.drop_column("processes", "min_charge")
    op.drop_column("processes", "startup_fee")
    op.drop_column("processes", "machine_type")
    op.drop_column("processes", "billing_basis")

    # 删除 materials 新增字段
    op.drop_column("materials", "price_updated_at")
    op.drop_column("materials", "supplier")
    op.drop_column("materials", "min_purchase_qty")
    op.drop_column("materials", "purchase_unit")
    op.drop_column("materials", "sheet_height_mm")
    op.drop_column("materials", "sheet_width_mm")
    op.drop_column("materials", "thickness_mm")
    op.drop_column("materials", "category")

    # 删除 products 新增字段
    op.drop_column("products", "standard_lead_days")
    op.drop_column("products", "default_loss_rate")
    op.drop_column("products", "needs_approval")
    op.drop_column("products", "allows_outsource")
    op.drop_column("products", "needs_installation")
    op.drop_column("products", "requires_geometry")
