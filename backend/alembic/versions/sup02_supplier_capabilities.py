"""Add multiple supplier roles and external-service capabilities, preserving IDs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "sup02_supplier_capabilities"
down_revision = "obd01_order_business_date"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("outsource_vendors", sa.Column("supplier_types", JSONB(), nullable=True))
    op.add_column("outsource_vendors", sa.Column("service_types", JSONB(), nullable=True))
    # Unknown legacy service text remains in service_type. Unspecified old
    # capabilities retain all supported choices, preserving previous eligibility.
    op.execute("""
        UPDATE outsource_vendors v SET
          supplier_types = jsonb_build_array(v.supplier_type),
          service_types = CASE WHEN v.supplier_type <> 'outsource' THEN '[]'::jsonb
            WHEN v.service_type IN ('production','installation','design','transport')
              THEN (SELECT jsonb_agg(DISTINCT capability ORDER BY capability) FROM (
                SELECT v.service_type AS capability UNION
                SELECT t.task_type FROM outsource_tasks t WHERE t.vendor_id = v.id
                  AND t.task_type IN ('production','installation','design','transport')
              ) capabilities)
            ELSE '["production","installation","design","transport"]'::jsonb END
    """)
    for name in ("supplier_types", "service_types"):
        op.alter_column("outsource_vendors", name, nullable=False)
        op.create_index(f"ix_outsource_vendors_{name}", "outsource_vendors", [name], postgresql_using="gin")
    op.create_check_constraint("ck_supplier_roles", "outsource_vendors",
        "jsonb_typeof(supplier_types) = 'array' AND jsonb_array_length(supplier_types) > 0 "
        "AND supplier_types <@ '[\"outsource\",\"material\",\"equipment\",\"transport\",\"service\",\"other\"]'::jsonb")
    op.create_check_constraint("ck_supplier_services", "outsource_vendors",
        "jsonb_typeof(service_types) = 'array' "
        "AND service_types <@ '[\"production\",\"installation\",\"design\",\"transport\"]'::jsonb "
        "AND (supplier_types @> '[\"outsource\"]'::jsonb OR service_types = '[]'::jsonb)")


def downgrade():
    # An old single-choice schema cannot represent multi-role records safely.
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM outsource_vendors WHERE jsonb_array_length(supplier_types) > 1
        OR jsonb_array_length(service_types) > 1) THEN
        RAISE EXCEPTION 'Multi-role supplier data exists; export new data and use a coordinated backup recovery';
      END IF;
    END $$""")
    for name in ("ck_supplier_services", "ck_supplier_roles"):
        op.drop_constraint(name, "outsource_vendors", type_="check")
    for name in ("service_types", "supplier_types"):
        op.drop_index(f"ix_outsource_vendors_{name}", table_name="outsource_vendors")
        op.drop_column("outsource_vendors", name)
