"""Exercise the finance reconciliation migration in a disposable schema."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


pytestmark = pytest.mark.skipif(
    not os.getenv("FINANCE_RECON_MIGRATION_TEST_URL"),
    reason="requires explicitly isolated PostgreSQL",
)


def test_finance_reconciliation_migration_upgrades_and_downgrades_in_isolated_schema():
    engine = sa.create_engine(os.environ["FINANCE_RECON_MIGRATION_TEST_URL"])
    schema = "finance_recon_migration_" + uuid4().hex
    path = Path(__file__).parents[1] / "alembic/versions/fcr01_finance_reconciliation.py"
    spec = importlib.util.spec_from_file_location("finance_reconciliation_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            conn.execute(sa.text("CREATE TABLE users (id uuid PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE project_costs (id uuid PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE outsource_tasks (id uuid PRIMARY KEY)"))
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()

            inspector = sa.inspect(conn)
            assert {
                "finance_payment_date_reconciliations",
                "finance_cost_overlap_reviews",
            }.issubset(set(inspector.get_table_names()))
            payment_columns = {
                column["name"]: column for column in inspector.get_columns("finance_payment_date_reconciliations")
            }
            assert payment_columns["created_at"]["nullable"] is False
            assert payment_columns["updated_at"]["nullable"] is False
            indexes = inspector.get_indexes("finance_payment_date_reconciliations")
            active_unique = next(
                index for index in indexes
                if index["name"] == "uq_finance_payment_recon_active_outsource_payment"
            )
            assert active_unique["unique"] is True
            assert "outsource_payment" in active_unique["dialect_options"]["postgresql_where"]

            reconciliation_id, source_id = uuid4(), uuid4()
            conn.execute(sa.text("""INSERT INTO finance_payment_date_reconciliations
                (id, source_type, source_id, amount, paid_at, evidence_type, evidence_reference)
                VALUES (:id, 'outsource_payment', :source_id, 10, now(), 'bank_statement', 'bank-001')"""),
                {"id": reconciliation_id, "source_id": source_id})
            with pytest.raises(sa.exc.IntegrityError):
                with conn.begin_nested():
                    conn.execute(sa.text("""INSERT INTO finance_payment_date_reconciliations
                        (id, source_type, source_id, amount, paid_at, evidence_type, evidence_reference)
                        VALUES (:id, 'outsource_payment', :source_id, 10, now(), 'bank_statement', 'bank-002')"""),
                        {"id": uuid4(), "source_id": source_id})

            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
            assert "finance_payment_date_reconciliations" not in sa.inspect(conn).get_table_names()
            assert "finance_cost_overlap_reviews" not in sa.inspect(conn).get_table_names()
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
