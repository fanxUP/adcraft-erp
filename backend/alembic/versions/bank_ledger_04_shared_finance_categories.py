"""Link manual bank ledger entries and project costs to shared categories.

Existing free-text values are preserved as category names, except for the two
approved legacy labels which are normalized through explicit aliases.
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "bank_ledger_04"
down_revision = "bank_ledger_03"
branch_labels = None
depends_on = None


DEFAULT_CATEGORIES = (
    "张江",
    "过账",
    "高空作业车",
    "员工社保",
    "员工工资",
    "居间费",
    "手续费",
    "餐费/交通费",
    "车辆加油/维修",
    "房租",
    "水电",
    "材料采购",
    "外协加工安装",
    "运输/物流费",
    "办公",
    "制作标书",
    "投标保证金",
    "工资",
    "税费",
    "还款",
    "其他支出",
    "租赁费",
    "安装杂费",
    "差旅费",
    "人工/工时费",
    "材料费",
    "办公费",
    "其他",
)

ALIASES = {
    "外协加工": "外协加工安装",
    "运输": "运输/物流费",
}


def _canonical_category_sql(column: str) -> str:
    cases = " ".join(f"WHEN '{old}' THEN '{new}'" for old, new in ALIASES.items())
    return f"CASE btrim({column}) {cases} ELSE btrim({column}) END"


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _backfill_table(connection, table_name: str, scope: str = "TRUE") -> None:
    canonical_category = _canonical_category_sql("entry.category")
    connection.execute(sa.text(
        f"UPDATE {table_name} AS entry "
        f"SET category = {canonical_category}, category_id = category_ref.id "
        f"FROM finance_categories AS category_ref "
        f"WHERE ({scope}) AND entry.category IS NOT NULL AND btrim(entry.category) <> '' "
        f"AND category_ref.name = {canonical_category}"
    ))


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "finance_categories",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_finance_categories"),
        sa.UniqueConstraint("name", name="uq_finance_categories_name"),
        sa.UniqueConstraint("code", name="uq_finance_categories_code"),
    )
    op.create_index("ix_finance_categories_sort", "finance_categories", ["sort_order", "name"])
    op.create_table(
        "finance_category_aliases",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.String(length=64), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["finance_categories.id"],
            name="fk_finance_category_aliases_category", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_finance_category_aliases"),
        sa.UniqueConstraint("alias", name="uq_finance_category_aliases_alias"),
    )
    op.create_index(
        "ix_finance_category_aliases_category",
        "finance_category_aliases",
        ["category_id"],
    )

    op.add_column("bank_ledger_entries", sa.Column("category_id", UUID(as_uuid=True), nullable=True))
    op.add_column("project_costs", sa.Column("category_id", UUID(as_uuid=True), nullable=True))

    connection = op.get_bind()
    for position, name in enumerate(DEFAULT_CATEGORIES):
        category_id = uuid4()
        code = "bank_fee" if name == "手续费" else f"finance_category_{position + 1:03d}"
        op.execute(
            "INSERT INTO finance_categories (id, name, code, sort_order) "
            f"VALUES ('{category_id}', {_sql_literal(name)}, {_sql_literal(code)}, {position})"
        )

    # Discover legacy labels in SQL so this migration can be inspected and
    # rendered with Alembic's offline SQL mode as well as run online.
    ledger_names = _canonical_category_sql("category")
    cost_names = _canonical_category_sql("category")
    connection.execute(sa.text(
        "WITH existing_names AS ("
        f"SELECT {ledger_names} AS name FROM bank_ledger_entries "
        "WHERE entry_type = 'manual' AND direction = 'expense' "
        "AND category IS NOT NULL AND btrim(category) <> '' "
        "UNION "
        f"SELECT {cost_names} AS name FROM project_costs "
        "WHERE category IS NOT NULL AND btrim(category) <> ''"
        "), unseeded_names AS ("
        "SELECT existing_names.name FROM existing_names "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM finance_categories WHERE finance_categories.name = existing_names.name"
        ")"
        ") INSERT INTO finance_categories (id, name, code, sort_order) "
        "SELECT gen_random_uuid(), unseeded_names.name, 'legacy_' || md5(unseeded_names.name), "
        "1000 + row_number() OVER (ORDER BY unseeded_names.name) "
        "FROM unseeded_names"
    ))

    _backfill_table(
        connection,
        "bank_ledger_entries",
        "entry.entry_type = 'manual' AND entry.direction = 'expense'",
    )
    _backfill_table(connection, "project_costs")

    for alias, canonical_name in ALIASES.items():
        op.execute(
            "INSERT INTO finance_category_aliases (id, alias, category_id) "
            f"SELECT '{uuid4()}', {_sql_literal(alias)}, id FROM finance_categories "
            f"WHERE name = {_sql_literal(canonical_name)}"
        )

    op.create_foreign_key(
        "fk_bank_ledger_entries_category",
        "bank_ledger_entries",
        "finance_categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_project_costs_category",
        "project_costs",
        "finance_categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_bank_ledger_entries_category_id", "bank_ledger_entries", ["category_id"])
    op.create_index("ix_project_costs_category_id", "project_costs", ["category_id"])


def downgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The original text columns remain populated and canonicalized, so older
    # application code can continue reading them after this additive rollback.
    op.drop_index("ix_project_costs_category_id", table_name="project_costs")
    op.drop_index("ix_bank_ledger_entries_category_id", table_name="bank_ledger_entries")
    op.drop_constraint("fk_project_costs_category", "project_costs", type_="foreignkey")
    op.drop_constraint("fk_bank_ledger_entries_category", "bank_ledger_entries", type_="foreignkey")
    op.drop_column("project_costs", "category_id")
    op.drop_column("bank_ledger_entries", "category_id")
    op.drop_index("ix_finance_category_aliases_category", table_name="finance_category_aliases")
    op.drop_table("finance_category_aliases")
    op.drop_index("ix_finance_categories_sort", table_name="finance_categories")
    op.drop_table("finance_categories")
