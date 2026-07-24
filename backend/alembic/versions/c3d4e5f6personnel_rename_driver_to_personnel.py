"""rename driver → personnel: tables, columns, indexes

Revision ID: c3d4e5f6personnel
Revises: a1b2c3d4aerial
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c3d4e5f6personnel'
down_revision = 'b2c3d4e5agent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Drop FKs referencing aerial_drivers ──
    op.execute("""
        DO $$
        DECLARE
            con record;
        BEGIN
            FOR con IN
                SELECT conrelid::regclass::text AS tbl, conname
                FROM pg_constraint
                WHERE confrelid = 'aerial_drivers'::regclass AND contype = 'f'
            LOOP
                EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', con.tbl, con.conname);
            END LOOP;
        END $$;
    """)

    # ── Step 2: Rename columns ──
    # aerial_drivers
    op.alter_column('aerial_drivers', 'driver_name', new_column_name='name')

    # aerial_vehicles
    op.alter_column('aerial_vehicles', 'default_driver_id', new_column_name='default_personnel_id')

    # aerial_daily_ledgers
    op.alter_column('aerial_daily_ledgers', 'driver_id', new_column_name='personnel_id')
    op.alter_column('aerial_daily_ledgers', 'driver_wage_amount', new_column_name='personnel_wage_amount')

    # aerial_driver_expenses (will be renamed later)
    op.alter_column('aerial_driver_expenses', 'driver_id', new_column_name='personnel_id')
    op.alter_column('aerial_driver_expenses', 'paid_by_driver', new_column_name='paid_by_personnel')

    # aerial_driver_wages (will be renamed later)
    op.alter_column('aerial_driver_wages', 'driver_id', new_column_name='personnel_id')

    # aerial_vehicle_costs
    op.alter_column('aerial_vehicle_costs', 'is_driver_advance', new_column_name='is_personnel_advance')

    # ── Step 3: Rename indexes before renaming tables ──
    op.execute("ALTER INDEX IF EXISTS ix_aerial_ledger_driver_id RENAME TO ix_aerial_ledger_personnel_id")
    op.execute("ALTER INDEX IF EXISTS ix_aerial_expense_driver_id RENAME TO ix_aerial_expense_personnel_id")
    op.execute("ALTER INDEX IF EXISTS ix_aerial_wage_driver_id RENAME TO ix_aerial_wage_personnel_id")

    # ── Step 4: Rename tables ──
    op.rename_table('aerial_drivers', 'aerial_personnel')
    op.rename_table('aerial_driver_expenses', 'aerial_personnel_expenses')
    op.rename_table('aerial_driver_wages', 'aerial_personnel_wages')

    # ── Step 5: Add personnel_type column ──
    op.add_column('aerial_personnel',
        sa.Column('personnel_type', sa.String(32), server_default='driver', nullable=False)
    )

    # ── Step 6: Recreate FKs ──
    op.create_foreign_key(None, 'aerial_vehicles', 'aerial_personnel',
                          ['default_personnel_id'], ['id'])
    op.create_foreign_key(None, 'aerial_daily_ledgers', 'aerial_personnel',
                          ['personnel_id'], ['id'])
    op.create_foreign_key(None, 'aerial_personnel_expenses', 'aerial_personnel',
                          ['personnel_id'], ['id'])
    op.create_foreign_key(None, 'aerial_personnel_wages', 'aerial_personnel',
                          ['personnel_id'], ['id'])


def downgrade() -> None:
    # ── Step 1: Drop FKs ──
    op.execute("""
        DO $$
        DECLARE
            con record;
        BEGIN
            FOR con IN
                SELECT conrelid::regclass::text AS tbl, conname
                FROM pg_constraint
                WHERE confrelid = 'aerial_personnel'::regclass AND contype = 'f'
            LOOP
                EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', con.tbl, con.conname);
            END LOOP;
        END $$;
    """)

    # ── Step 2: Drop personnel_type ──
    op.drop_column('aerial_personnel', 'personnel_type')

    # ── Step 3: Rename tables back ──
    op.rename_table('aerial_personnel', 'aerial_drivers')
    op.rename_table('aerial_personnel_expenses', 'aerial_driver_expenses')
    op.rename_table('aerial_personnel_wages', 'aerial_driver_wages')

    # ── Step 4: Rename indexes back ──
    op.execute("ALTER INDEX IF EXISTS ix_aerial_ledger_personnel_id RENAME TO ix_aerial_ledger_driver_id")
    op.execute("ALTER INDEX IF EXISTS ix_aerial_expense_personnel_id RENAME TO ix_aerial_expense_driver_id")
    op.execute("ALTER INDEX IF EXISTS ix_aerial_wage_personnel_id RENAME TO ix_aerial_wage_driver_id")

    # ── Step 5: Rename columns back ──
    op.alter_column('aerial_drivers', 'name', new_column_name='driver_name')
    op.alter_column('aerial_vehicles', 'default_personnel_id', new_column_name='default_driver_id')
    op.alter_column('aerial_daily_ledgers', 'personnel_id', new_column_name='driver_id')
    op.alter_column('aerial_daily_ledgers', 'personnel_wage_amount', new_column_name='driver_wage_amount')
    op.alter_column('aerial_driver_expenses', 'personnel_id', new_column_name='driver_id')
    op.alter_column('aerial_driver_expenses', 'paid_by_personnel', new_column_name='paid_by_driver')
    op.alter_column('aerial_driver_wages', 'personnel_id', new_column_name='driver_id')
    op.alter_column('aerial_vehicle_costs', 'is_personnel_advance', new_column_name='is_driver_advance')

    # ── Step 6: Recreate FKs ──
    op.create_foreign_key(None, 'aerial_vehicles', 'aerial_drivers',
                          ['default_driver_id'], ['id'])
    op.create_foreign_key(None, 'aerial_daily_ledgers', 'aerial_drivers',
                          ['driver_id'], ['id'])
    op.create_foreign_key(None, 'aerial_driver_expenses', 'aerial_drivers',
                          ['driver_id'], ['id'])
    op.create_foreign_key(None, 'aerial_driver_wages', 'aerial_drivers',
                          ['driver_id'], ['id'])
