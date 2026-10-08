"""Opt-in migration dry run against an isolated PostgreSQL instance."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


@pytest.mark.skipif(not os.getenv("SUPPLIER_MIGRATION_TEST_URL"), reason="requires isolated PostgreSQL")
def test_backfill_preserves_ids_references_and_multi_role_membership():
    engine = sa.create_engine(os.environ["SUPPLIER_MIGRATION_TEST_URL"])
    schema = "supplier_test_" + uuid4().hex
    path = Path(__file__).parents[1] / "alembic/versions/sup02_supplier_capabilities.py"
    spec = importlib.util.spec_from_file_location("supplier_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            conn.execute(sa.text("""CREATE TABLE outsource_vendors (
                id uuid PRIMARY KEY, supplier_type varchar NOT NULL, service_type varchar,
                is_active boolean NOT NULL, deleted_at timestamp)"""))
            conn.execute(sa.text("CREATE TABLE outsource_tasks (id uuid PRIMARY KEY, vendor_id uuid REFERENCES outsource_vendors(id), task_type varchar)"))
            conn.execute(sa.text("CREATE TABLE project_costs (id uuid PRIMARY KEY, supplier_id uuid REFERENCES outsource_vendors(id))"))
            conn.execute(sa.text("CREATE TABLE expenses (id uuid PRIMARY KEY, supplier_id uuid REFERENCES outsource_vendors(id))"))
            ids = [uuid4() for _ in range(4)]
            for supplier_id, role, service, active in zip(ids, ["outsource", "material", "outsource", "outsource"], ["production", None, "历史自定义", None], [True, True, False, True]):
                conn.execute(sa.text("INSERT INTO outsource_vendors VALUES (:id,:role,:service,:active,NULL)"),
                             dict(id=supplier_id, role=role, service=service, active=active))
            task_id, cost_id, expense_id = uuid4(), uuid4(), uuid4()
            conn.execute(sa.text("INSERT INTO outsource_tasks VALUES (:id,:vendor,'installation')"), dict(id=task_id, vendor=ids[0]))
            conn.execute(sa.text("INSERT INTO project_costs VALUES (:id,:vendor)"), dict(id=cost_id, vendor=ids[0]))
            conn.execute(sa.text("INSERT INTO expenses VALUES (:id,:vendor)"), dict(id=expense_id, vendor=ids[1]))
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
            rows = {row.id: row for row in conn.execute(sa.text("SELECT * FROM outsource_vendors"))}
            assert set(rows) == set(ids)
            assert rows[ids[0]].supplier_types == ["outsource"]
            assert rows[ids[0]].service_types == ["installation", "production"]
            assert rows[ids[1]].service_types == []
            assert set(rows[ids[2]].service_types) == {"production", "installation", "design", "transport"}
            assert rows[ids[2]].service_type == "历史自定义"
            assert rows[ids[2]].is_active is False
            for table, column, expected in [("outsource_tasks", "vendor_id", ids[0]), ("project_costs", "supplier_id", ids[0]), ("expenses", "supplier_id", ids[1])]:
                assert conn.execute(sa.text(f"SELECT {column} FROM {table}")).scalar_one() == expected
            conn.execute(sa.text("UPDATE outsource_vendors SET supplier_types='[\"material\",\"outsource\"]'::jsonb WHERE id=:id"), dict(id=ids[0]))
            eligible = conn.execute(sa.text("""SELECT id FROM outsource_vendors
                WHERE supplier_types @> '["outsource"]'::jsonb AND service_types @> '["installation"]'::jsonb AND is_active""")).scalars().all()
            assert ids[0] in eligible and ids[1] not in eligible and ids[2] not in eligible
            with pytest.raises(sa.exc.IntegrityError, match="ck_supplier_roles"):
                with conn.begin_nested():
                    conn.execute(sa.text("UPDATE outsource_vendors SET supplier_types='[]'::jsonb WHERE id=:id"), dict(id=ids[0]))
            with pytest.raises(sa.exc.IntegrityError, match="ck_supplier_services"):
                with conn.begin_nested():
                    conn.execute(sa.text("UPDATE outsource_vendors SET service_types='[\"invalid\"]'::jsonb WHERE id=:id"), dict(id=ids[0]))
            with pytest.raises(sa.exc.DBAPIError, match="Multi-role supplier data exists"):
                with conn.begin_nested():
                    with Operations.context(MigrationContext.configure(conn)):
                        migration.downgrade()
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
