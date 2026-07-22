"""merge orders & quotes into business_documents

Revision ID: f0e1d2c3b4a5
Revises: feedc0de0001
Create Date: 2026-07-22 20:12:39.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f0e1d2c3b4a5'
down_revision: Union[str, None] = 'feedc0de0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── helpers ──

def _add_document_fk(table, old_col, nullable=False):
    """Add document_id column, backfill from old column, add FK, drop old column."""
    op.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN document_id UUID"))
    op.execute(sa.text(f"UPDATE {table} SET document_id = {old_col}"))
    if not nullable:
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN document_id SET NOT NULL"))
    op.execute(sa.text(
        f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_document "
        f"FOREIGN KEY (document_id) REFERENCES business_documents(id)"
    ))
    op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN {old_col}"))


def _merge_junction(old_order_table, old_quote_table, new_table, project_fk=None):
    """Merge order+quote junction tables into single document junction table."""
    pk_col = "project_id" if project_fk else "contract_id"
    fk_src = "framework_contract_projects" if project_fk else "contracts"
    op.create_table(
        new_table,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(pk_col, postgresql.UUID(as_uuid=True), sa.ForeignKey(f'{fk_src}.id'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    old_ref = "order_id" if "order" in old_order_table else "quote_id"
    op.execute(sa.text(f"""
        INSERT INTO {new_table} ({pk_col}, document_id, created_at, updated_at)
        SELECT {pk_col}, {old_ref}, created_at, updated_at FROM {old_order_table};
        INSERT INTO {new_table} ({pk_col}, document_id, created_at, updated_at)
        SELECT {pk_col}, quote_id, created_at, updated_at FROM {old_quote_table};
    """))
    op.drop_table(old_quote_table)
    op.drop_table(old_order_table)


def upgrade() -> None:
    # ══════════════════════════════════════════════════
    # STEP 1: Create new unified tables
    # ══════════════════════════════════════════════════

    op.create_table(
        'business_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('doc_type', sa.String(16), nullable=False),
        sa.Column('doc_no', sa.String(64), unique=True, nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('project_name', sa.String(255), nullable=False),
        sa.Column('sales_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.String(64), nullable=False),
        sa.Column('total_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('contact_person', sa.String(64), nullable=True),
        sa.Column('contact_phone', sa.String(32), nullable=True),
        # order-specific
        sa.Column('paid_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('unpaid_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('cost_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('gross_profit', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('delivery_deadline', sa.DateTime, nullable=True),
        sa.Column('installation_address', sa.Text, nullable=True),
        sa.Column('source_quote_id', postgresql.UUID(as_uuid=True), nullable=True),  # FK added after data
        # quote-specific
        sa.Column('subtotal_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('discount_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('tax_rate', sa.Numeric(8, 4), server_default=sa.text('0')),
        sa.Column('tax_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('valid_until', sa.Date, nullable=True),
        # timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'business_document_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=False),
        sa.Column('source_quote_item_id', postgresql.UUID(as_uuid=True), nullable=True),  # FK after data
        sa.Column('item_name', sa.String(255), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('materials.id'), nullable=True),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('processes.id'), nullable=True),
        sa.Column('length', sa.Numeric(12, 3), nullable=True),
        sa.Column('length_unit', sa.String(16), nullable=True, server_default=sa.text("'m'")),
        sa.Column('width', sa.Numeric(12, 3), nullable=True),
        sa.Column('width_unit', sa.String(16), nullable=True, server_default=sa.text("'m'")),
        sa.Column('height', sa.Numeric(12, 3), nullable=True),
        sa.Column('height_unit', sa.String(16), nullable=True, server_default=sa.text("'m'")),
        sa.Column('quantity', sa.Numeric(14, 3), server_default=sa.text('1')),
        sa.Column('unit', sa.String(32), nullable=True),
        sa.Column('use_area', sa.Boolean, server_default=sa.text('false')),
        sa.Column('quantity_mode', sa.String(16), server_default=sa.text("'piece'")),
        sa.Column('pieces', sa.Numeric(10, 2), nullable=True, server_default=sa.text('1')),
        sa.Column('area', sa.Numeric(14, 3), nullable=True),
        sa.Column('unit_price', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('process_fee', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('installation_fee', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('design_fee', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('transport_fee', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('other_fee', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('subtotal_amount', sa.Numeric(14, 2), server_default=sa.text('0')),
        sa.Column('remark', sa.Text, nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('sort_order', sa.Integer, server_default=sa.text('0')),
        sa.Column('group_name', sa.String(255), nullable=True),
        sa.Column('material_process', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'business_document_status_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=False),
        sa.Column('from_status', sa.String(64), nullable=True),
        sa.Column('to_status', sa.String(64), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('operated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('operated_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'business_document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('business_documents.id'), nullable=False),
        sa.Column('version_no', sa.Integer, nullable=False),
        sa.Column('snapshot', postgresql.JSONB, nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ══════════════════════════════════════════════════
    # STEP 2: Migrate orders → business_documents
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        INSERT INTO business_documents (
            id, doc_type, doc_no,
            customer_id, customer_name, project_name, sales_user_id,
            status, total_amount, remark,
            department, contact_person, contact_phone,
            paid_amount, unpaid_amount, cost_amount, gross_profit,
            delivery_deadline, installation_address,
            created_at, updated_at, deleted_at
        )
        SELECT
            id, 'order', order_no,
            customer_id, NULL, project_name, sales_user_id,
            status, total_amount, remark,
            department, contact_person, contact_phone,
            COALESCE(paid_amount, 0), COALESCE(unpaid_amount, 0),
            COALESCE(cost_amount, 0), COALESCE(gross_profit, 0),
            delivery_deadline, installation_address,
            created_at, updated_at, deleted_at
        FROM orders
    """))

    # ══════════════════════════════════════════════════
    # STEP 3: Migrate quotes → business_documents
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        INSERT INTO business_documents (
            id, doc_type, doc_no,
            customer_id, customer_name, project_name, sales_user_id,
            status, total_amount, remark,
            department, contact_person, contact_phone,
            subtotal_amount, discount_amount, tax_rate, tax_amount, valid_until,
            created_at, updated_at, deleted_at
        )
        SELECT
            id, 'quote', quote_no,
            customer_id, customer_name, project_name, sales_user_id,
            status, total_amount, remark,
            department, contact_person, contact_phone,
            COALESCE(subtotal_amount, 0), COALESCE(discount_amount, 0),
            COALESCE(tax_rate, 0), COALESCE(tax_amount, 0), valid_until,
            created_at, updated_at, deleted_at
        FROM quotes
    """))

    # ══════════════════════════════════════════════════
    # STEP 4: Backfill source_quote_id (orders.quote_id → self-referencing FK)
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        UPDATE business_documents bd
        SET source_quote_id = o.quote_id
        FROM orders o
        WHERE bd.id = o.id AND o.quote_id IS NOT NULL
    """))
    op.execute(sa.text("""
        ALTER TABLE business_documents
        ADD CONSTRAINT fk_bd_source_quote
            FOREIGN KEY (source_quote_id) REFERENCES business_documents(id)
    """))

    # ══════════════════════════════════════════════════
    # STEP 5: Migrate items
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        INSERT INTO business_document_items (
            id, document_id,
            item_name, product_id, material_id, process_id,
            length, length_unit, width, width_unit, height, height_unit,
            quantity, unit, use_area, quantity_mode, pieces, area,
            unit_price, process_fee, installation_fee, design_fee,
            transport_fee, other_fee, subtotal_amount,
            remark, image_url, sort_order, group_name, material_process,
            created_at, updated_at
        )
        SELECT
            id, order_id,
            item_name, product_id, material_id, process_id,
            length, length_unit, width, width_unit, height, height_unit,
            quantity, unit, use_area, quantity_mode, pieces, area,
            unit_price, process_fee, installation_fee, design_fee,
            transport_fee, other_fee, subtotal_amount,
            remark, image_url, sort_order, group_name, material_process,
            created_at, updated_at
        FROM order_items
        UNION ALL
        SELECT
            id, quote_id,
            item_name, product_id, material_id, process_id,
            length, length_unit, width, width_unit, height, height_unit,
            quantity, unit, use_area, quantity_mode, pieces, area,
            unit_price, process_fee, installation_fee, design_fee,
            transport_fee, other_fee, subtotal_amount,
            remark, image_url, sort_order, group_name, material_process,
            created_at, updated_at
        FROM quote_items
    """))

    # Backfill source_quote_item_id (order_items.source_quote_item_id → self-referencing)
    op.execute(sa.text("""
        UPDATE business_document_items bdi
        SET source_quote_item_id = oi.source_quote_item_id
        FROM order_items oi
        WHERE bdi.id = oi.id AND oi.source_quote_item_id IS NOT NULL
    """))
    op.execute(sa.text("""
        ALTER TABLE business_document_items
        ADD CONSTRAINT fk_bdi_source_quote_item
            FOREIGN KEY (source_quote_item_id) REFERENCES business_document_items(id)
    """))

    # ══════════════════════════════════════════════════
    # STEP 6: Migrate status logs
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        INSERT INTO business_document_status_logs
            (id, document_id, from_status, to_status, reason, operated_by, operated_at)
        SELECT id, order_id, from_status, to_status, reason, operated_by, operated_at
        FROM order_status_logs
    """))

    # ══════════════════════════════════════════════════
    # STEP 7: Migrate versions
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        INSERT INTO business_document_versions
            (id, document_id, version_no, snapshot, created_by, created_at, updated_at)
        SELECT id, quote_id, version_no, snapshot, created_by, created_at, updated_at
        FROM quote_versions
    """))

    # ══════════════════════════════════════════════════
    # STEP 8: Update all referencing tables
    # ══════════════════════════════════════════════════

    # acceptance_forms: order_id + quote_id → document_id (has TWO old columns)
    op.execute(sa.text("""
        ALTER TABLE acceptance_forms ADD COLUMN document_id UUID;
        UPDATE acceptance_forms SET document_id = COALESCE(order_id, quote_id);
        ALTER TABLE acceptance_forms ADD CONSTRAINT fk_acceptance_forms_document
            FOREIGN KEY (document_id) REFERENCES business_documents(id);
        ALTER TABLE acceptance_forms DROP COLUMN order_id;
        ALTER TABLE acceptance_forms DROP COLUMN quote_id;
    """))

    # acceptance_items: order_item_id → document_item_id
    op.execute(sa.text("""
        ALTER TABLE acceptance_items ADD COLUMN document_item_id UUID;
        UPDATE acceptance_items SET document_item_id = order_item_id;
        ALTER TABLE acceptance_items ADD CONSTRAINT fk_acceptance_items_doc_item
            FOREIGN KEY (document_item_id) REFERENCES business_document_items(id);
        ALTER TABLE acceptance_items DROP COLUMN order_item_id;
    """))

    # project_costs: 4 FK columns → 2
    op.execute(sa.text("""
        ALTER TABLE project_costs ADD COLUMN document_id UUID;
        UPDATE project_costs SET document_id = COALESCE(order_id, quote_id);
        ALTER TABLE project_costs ADD CONSTRAINT fk_project_costs_document
            FOREIGN KEY (document_id) REFERENCES business_documents(id);
        ALTER TABLE project_costs ADD COLUMN document_item_id UUID;
        UPDATE project_costs SET document_item_id = COALESCE(order_item_id, quote_item_id);
        ALTER TABLE project_costs ADD CONSTRAINT fk_project_costs_doc_item
            FOREIGN KEY (document_item_id) REFERENCES business_document_items(id) ON DELETE SET NULL;
        ALTER TABLE project_costs DROP COLUMN order_id;
        ALTER TABLE project_costs DROP COLUMN quote_id;
        ALTER TABLE project_costs DROP COLUMN order_item_id;
        ALTER TABLE project_costs DROP COLUMN quote_item_id;
        ALTER TABLE project_costs DROP COLUMN source_type;
    """))

    # outsource_tasks: drop redundant order_id, keep related_doc_id + related_doc_type
    op.execute(sa.text("ALTER TABLE outsource_tasks DROP COLUMN IF EXISTS order_id"))

    # design_tasks, production_tasks, installation_tasks: order_id → document_id (NOT NULL)
    _add_document_fk('design_tasks', 'order_id', nullable=False)
    _add_document_fk('production_tasks', 'order_id', nullable=False)
    _add_document_fk('installation_tasks', 'order_id', nullable=False)

    # stock_records: order_id → document_id
    _add_document_fk('stock_records', 'order_id', nullable=True)

    # payments: order_id → document_id (NOT NULL)
    _add_document_fk('payments', 'order_id', nullable=False)

    # contract junction tables: merge contract_orders + contract_quotes → contract_documents
    _merge_junction('contract_orders', 'contract_quotes', 'contract_documents')

    # framework contract junction tables
    _merge_junction(
        'framework_contract_project_orders',
        'framework_contract_project_quotes',
        'framework_contract_project_documents',
        project_fk=True,
    )

    # ══════════════════════════════════════════════════
    # STEP 9: Drop legacy tables
    # ══════════════════════════════════════════════════
    # Order of drops matters for FK dependencies
    op.drop_table('order_status_logs')
    op.drop_table('quote_versions')
    op.drop_table('order_items')
    op.drop_table('quote_items')
    op.drop_table('orders')
    op.drop_table('quotes')

    # ══════════════════════════════════════════════════
    # STEP 10: Performance indexes
    # ══════════════════════════════════════════════════
    op.execute(sa.text("""
        CREATE INDEX idx_bd_type ON business_documents(doc_type);
        CREATE INDEX idx_bd_customer ON business_documents(customer_id) WHERE customer_id IS NOT NULL;
        CREATE INDEX idx_bd_status ON business_documents(status);
        CREATE INDEX idx_bd_deleted ON business_documents(deleted_at) WHERE deleted_at IS NULL;
    """))


def downgrade() -> None:
    """Downgrade is NOT supported — restore from backup if needed."""
    raise NotImplementedError("Downgrade not supported. Restore from pg_dump backup.")
