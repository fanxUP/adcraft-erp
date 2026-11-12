"""Merge retired shared finance categories into their canonical names."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "bank_ledger_06"
down_revision = "bank_ledger_05"
branch_labels = None
depends_on = None


BACKUP_TABLE = "finance_category_merge_backup_06"
MERGES = (
    ("人工/工时费", "外协加工/安装"),
    ("其他", "其他支出"),
    ("材料费", "材料采购"),
    ("办公", "办公费"),
    ("工资", "员工工资"),
    ("房租", "房租/水电"),
    ("水电", "房租/水电"),
)
NEW_CATEGORIES = (
    ("房租/水电", "bank_ledger_06_rent_water", 0),
    ("利息", "bank_ledger_06_interest", 1),
    ("设备/工具", "bank_ledger_06_equipment_tool", 2),
    ("车辆保险", "bank_ledger_06_vehicle_insurance", 3),
)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _merge_values_sql() -> str:
    return ", ".join(
        f"({_sql_literal(source)}, {_sql_literal(target)})"
        for source, target in MERGES
    )


def _source_values_sql() -> str:
    return ", ".join(f"({_sql_literal(source)})" for source, _ in MERGES)


def _new_category_values_sql() -> str:
    return ", ".join(
        f"({_sql_literal(name)}, {_sql_literal(code)}, {priority})"
        for name, code, priority in NEW_CATEGORIES
    )


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '30s'")
    op.create_table(
        BACKUP_TABLE,
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("old_category", sa.String(length=64), nullable=True),
        sa.Column("old_category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("entity_type", "entity_id", name="pk_finance_category_merge_backup_06"),
    )
    op.execute(
        "LOCK TABLE finance_categories, finance_category_aliases, "
        "bank_ledger_entries, project_costs IN SHARE ROW EXCLUSIVE MODE"
    )
    op.execute(
        "CREATE TEMPORARY TABLE finance_category_merge_map_06 ("
        "source_name VARCHAR(64) PRIMARY KEY, target_name VARCHAR(64) NOT NULL"
        ") ON COMMIT DROP"
    )
    op.execute(
        "INSERT INTO finance_category_merge_map_06 (source_name, target_name) VALUES "
        + _merge_values_sql()
    )

    # Reject alias/name/code collisions before changing any existing rows.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM finance_category_merge_map_06 AS mapping
                LEFT JOIN finance_categories AS target
                  ON target.name = mapping.target_name
                JOIN finance_category_aliases AS alias_ref
                  ON alias_ref.alias = mapping.target_name
                WHERE target.id IS NULL OR alias_ref.category_id <> target.id
            ) THEN
                RAISE EXCEPTION 'Finance category target name is already mapped as a conflicting alias';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM finance_category_merge_map_06 AS mapping
                LEFT JOIN finance_categories AS source
                  ON source.name = mapping.source_name
                LEFT JOIN finance_categories AS target
                  ON target.name = mapping.target_name
                JOIN finance_category_aliases AS alias_ref
                  ON alias_ref.alias = mapping.source_name
                WHERE alias_ref.category_id IS DISTINCT FROM source.id
                  AND alias_ref.category_id IS DISTINCT FROM target.id
            ) THEN
                RAISE EXCEPTION 'Finance category source alias already points elsewhere';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM (VALUES { _new_category_values_sql() }) AS definition(name, code, priority)
                JOIN finance_categories AS existing ON existing.code = definition.code
                WHERE existing.name <> definition.name
            ) THEN
                RAISE EXCEPTION 'Finance category code is already used by another category';
            END IF;
        END $$;
        """
    )

    # Create the new combined category and added expense categories. Preserve
    # the previous rent/water position where possible and record newly created
    # rows so downgrade can remove them safely.
    op.execute(
        f"""
        WITH definitions(name, code, priority) AS (
            VALUES {_new_category_values_sql()}
        ), bounds AS (
            SELECT
                COALESCE(MAX(sort_order), 0) AS max_order,
                MIN(sort_order) FILTER (WHERE name IN ('房租', '水电')) AS rent_water_order
            FROM finance_categories
        ), created AS (
            INSERT INTO finance_categories (id, name, code, sort_order)
            SELECT
                gen_random_uuid(),
                definition.name,
                definition.code,
                CASE
                    WHEN definition.priority = 0
                        THEN COALESCE(bounds.rent_water_order, bounds.max_order + 1)
                    ELSE bounds.max_order + definition.priority + 1
                END
            FROM definitions AS definition
            CROSS JOIN bounds
            WHERE NOT EXISTS (
                SELECT 1 FROM finance_categories AS existing
                WHERE existing.name = definition.name
            )
            RETURNING *
        )
        INSERT INTO {BACKUP_TABLE} (entity_type, entity_id, old_category, payload)
        SELECT 'created_category', id, name, to_jsonb(created) FROM created
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM finance_category_merge_map_06 AS mapping
                LEFT JOIN finance_categories AS target
                  ON target.name = mapping.target_name
                WHERE target.id IS NULL
            ) THEN
                RAISE EXCEPTION 'A canonical finance category target is missing';
            END IF;
        END $$;
        """
    )

    # Detect rows whose text label and linked category ID would map to
    # different canonical categories; abort rather than choose one silently.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM bank_ledger_entries AS entry
                JOIN finance_categories AS category_ref ON category_ref.id = entry.category_id
                JOIN finance_category_merge_map_06 AS id_mapping
                  ON id_mapping.source_name = category_ref.name
                JOIN finance_category_merge_map_06 AS text_mapping
                  ON text_mapping.source_name = btrim(coalesce(entry.category, ''))
                WHERE id_mapping.target_name <> text_mapping.target_name
            ) OR EXISTS (
                SELECT 1
                FROM project_costs AS cost
                JOIN finance_categories AS category_ref ON category_ref.id = cost.category_id
                JOIN finance_category_merge_map_06 AS id_mapping
                  ON id_mapping.source_name = category_ref.name
                JOIN finance_category_merge_map_06 AS text_mapping
                  ON text_mapping.source_name = btrim(coalesce(cost.category, ''))
                WHERE id_mapping.target_name <> text_mapping.target_name
            ) THEN
                RAISE EXCEPTION 'Finance category text and category ID map to different targets';
            END IF;
        END $$;
        """
    )

    # Save only category fields and category metadata, not financial amounts.
    op.execute(
        f"""
        INSERT INTO {BACKUP_TABLE} (entity_type, entity_id, old_category, payload)
        SELECT 'category', category_ref.id, category_ref.name, to_jsonb(category_ref)
        FROM finance_categories AS category_ref
        JOIN finance_category_merge_map_06 AS mapping
          ON mapping.source_name = category_ref.name
        """
    )
    op.execute(
        f"""
        INSERT INTO {BACKUP_TABLE} (entity_type, entity_id, old_category, old_category_id, payload)
        SELECT 'alias', alias_ref.id, alias_ref.alias, alias_ref.category_id, to_jsonb(alias_ref)
        FROM finance_category_aliases AS alias_ref
        WHERE alias_ref.category_id IN (
            SELECT category_ref.id
            FROM finance_categories AS category_ref
            JOIN finance_category_merge_map_06 AS mapping
              ON mapping.source_name = category_ref.name
        )
        OR alias_ref.alias IN (
            SELECT source_name FROM finance_category_merge_map_06
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO {BACKUP_TABLE} (entity_type, entity_id, old_category, old_category_id)
        SELECT 'bank_ledger_entry', entry.id, entry.category, entry.category_id
        FROM bank_ledger_entries AS entry
        WHERE entry.category_id IN (
            SELECT category_ref.id
            FROM finance_categories AS category_ref
            JOIN finance_category_merge_map_06 AS mapping
              ON mapping.source_name = category_ref.name
        )
        OR btrim(coalesce(entry.category, '')) IN (
            SELECT source_name FROM finance_category_merge_map_06
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO {BACKUP_TABLE} (entity_type, entity_id, old_category, old_category_id)
        SELECT 'project_cost', cost.id, cost.category, cost.category_id
        FROM project_costs AS cost
        WHERE cost.category_id IN (
            SELECT category_ref.id
            FROM finance_categories AS category_ref
            JOIN finance_category_merge_map_06 AS mapping
              ON mapping.source_name = category_ref.name
        )
        OR btrim(coalesce(cost.category, '')) IN (
            SELECT source_name FROM finance_category_merge_map_06
        )
        """
    )

    for table, row_alias in (("bank_ledger_entries", "entry"), ("project_costs", "cost")):
        op.execute(
            f"""
            UPDATE {table} AS {row_alias}
            SET category = mapping.target_name, category_id = target.id
            FROM finance_categories AS source
            JOIN finance_category_merge_map_06 AS mapping
              ON mapping.source_name = source.name
            JOIN finance_categories AS target
              ON target.name = mapping.target_name
            WHERE {row_alias}.category_id = source.id
            """
        )
        op.execute(
            f"""
            UPDATE {table} AS {row_alias}
            SET category = mapping.target_name, category_id = target.id
            FROM finance_category_merge_map_06 AS mapping
            JOIN finance_categories AS target
              ON target.name = mapping.target_name
            WHERE btrim(coalesce({row_alias}.category, '')) = mapping.source_name
            """
        )

    op.execute(
        """
        UPDATE finance_category_aliases AS alias_ref
        SET category_id = target.id
        FROM finance_categories AS source
        JOIN finance_category_merge_map_06 AS mapping
          ON mapping.source_name = source.name
        JOIN finance_categories AS target
          ON target.name = mapping.target_name
        WHERE alias_ref.category_id = source.id
        """
    )
    op.execute(
        """
        INSERT INTO finance_category_aliases (id, alias, category_id)
        SELECT gen_random_uuid(), mapping.source_name, target.id
        FROM finance_category_merge_map_06 AS mapping
        JOIN finance_categories AS target ON target.name = mapping.target_name
        ON CONFLICT (alias) DO UPDATE SET category_id = EXCLUDED.category_id
        """
    )
    op.execute(
        """
        DELETE FROM finance_categories
        WHERE name IN (SELECT source_name FROM finance_category_merge_map_06)
        """
    )


def downgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '30s'")
    op.execute(
        "LOCK TABLE finance_categories, finance_category_aliases, "
        "bank_ledger_entries, project_costs IN SHARE ROW EXCLUSIVE MODE"
    )
    op.execute(
        f"""
        INSERT INTO finance_categories (id, name, code, sort_order, created_at, updated_at)
        SELECT
            (payload->>'id')::uuid,
            payload->>'name',
            payload->>'code',
            (payload->>'sort_order')::integer,
            (payload->>'created_at')::timestamp,
            (payload->>'updated_at')::timestamp
        FROM {BACKUP_TABLE}
        WHERE entity_type = 'category'
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            code = EXCLUDED.code,
            sort_order = EXCLUDED.sort_order,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at
        """
    )
    op.execute(
        f"""
        DELETE FROM finance_category_aliases AS alias_ref
        WHERE alias_ref.alias IN (VALUES {_source_values_sql()})
          AND NOT EXISTS (
              SELECT 1 FROM {BACKUP_TABLE} AS backup
              WHERE backup.entity_type = 'alias' AND backup.entity_id = alias_ref.id
          )
        """
    )
    op.execute(
        f"""
        INSERT INTO finance_category_aliases (id, alias, category_id, created_at, updated_at)
        SELECT
            (payload->>'id')::uuid,
            payload->>'alias',
            (payload->>'category_id')::uuid,
            (payload->>'created_at')::timestamp,
            (payload->>'updated_at')::timestamp
        FROM {BACKUP_TABLE}
        WHERE entity_type = 'alias'
        ON CONFLICT (id) DO UPDATE SET
            alias = EXCLUDED.alias,
            category_id = EXCLUDED.category_id,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at
        """
    )
    for table, row_alias, entity_type in (
        ("bank_ledger_entries", "entry", "bank_ledger_entry"),
        ("project_costs", "cost", "project_cost"),
    ):
        op.execute(
            f"""
            UPDATE {table} AS {row_alias}
            SET category = backup.old_category, category_id = backup.old_category_id
            FROM {BACKUP_TABLE} AS backup
            WHERE backup.entity_type = '{entity_type}'
              AND backup.entity_id = {row_alias}.id
            """
        )
    op.execute(
        f"""
        DELETE FROM finance_categories AS category_ref
        USING {BACKUP_TABLE} AS backup
        WHERE backup.entity_type = 'created_category'
          AND backup.entity_id = category_ref.id
        """
    )
    op.execute(f"DROP TABLE {BACKUP_TABLE}")
