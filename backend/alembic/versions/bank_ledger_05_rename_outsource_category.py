"""Rename the shared outsourced processing category and align existing rows."""

from alembic import op


revision = "bank_ledger_05"
down_revision = "bank_ledger_04"
branch_labels = None
depends_on = None


OLD_NAME = "外协加工安装"
NEW_NAME = "外协加工/安装"
LEGACY_NAME = "外协加工"


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '30s'")
    op.execute(
        f"""
        DO $$
        DECLARE
            old_id uuid;
            new_id uuid;
            target_id uuid;
            alias_name text;
            alias_id uuid;
        BEGIN
            SELECT id INTO old_id FROM finance_categories WHERE name = '{OLD_NAME}' FOR UPDATE;
            SELECT id INTO new_id FROM finance_categories WHERE name = '{NEW_NAME}' FOR UPDATE;

            IF old_id IS NOT NULL AND new_id IS NOT NULL AND old_id <> new_id THEN
                RAISE EXCEPTION 'Cannot rename {OLD_NAME}: {NEW_NAME} already belongs to another category';
            END IF;

            target_id := COALESCE(old_id, new_id);
            IF target_id IS NULL THEN
                RAISE EXCEPTION 'Finance category not found: {OLD_NAME} / {NEW_NAME}';
            END IF;

            IF old_id IS NOT NULL THEN
                UPDATE finance_categories SET name = '{NEW_NAME}' WHERE id = target_id;
            END IF;

            FOREACH alias_name IN ARRAY ARRAY['{NEW_NAME}', '{OLD_NAME}', '{LEGACY_NAME}'] LOOP
                SELECT category_id INTO alias_id
                FROM finance_category_aliases WHERE alias = alias_name FOR UPDATE;
                IF alias_id IS NOT NULL AND alias_id <> target_id THEN
                    RAISE EXCEPTION 'Finance category alias already points elsewhere';
                END IF;
                IF alias_id IS NULL AND alias_name <> '{NEW_NAME}' THEN
                    INSERT INTO finance_category_aliases (id, alias, category_id)
                    VALUES (gen_random_uuid(), alias_name, target_id);
                ELSIF alias_name = '{NEW_NAME}' AND alias_id = target_id THEN
                    DELETE FROM finance_category_aliases
                    WHERE alias = alias_name AND category_id = target_id;
                END IF;
            END LOOP;
        END $$;
        """
    )
    op.execute(
        f"""
        UPDATE bank_ledger_entries AS entry
        SET category = '{NEW_NAME}', category_id = category_ref.id
        FROM finance_categories AS category_ref
        WHERE category_ref.name = '{NEW_NAME}'
          AND entry.entry_type = 'manual'
          AND entry.direction = 'expense'
          AND (
              entry.category_id = category_ref.id
              OR btrim(coalesce(entry.category, '')) IN ('{OLD_NAME}', '{LEGACY_NAME}', '{NEW_NAME}')
          )
        """
    )
    op.execute(
        f"""
        UPDATE project_costs AS cost
        SET category = '{NEW_NAME}', category_id = category_ref.id
        FROM finance_categories AS category_ref
        WHERE category_ref.name = '{NEW_NAME}'
          AND (
              cost.category_id = category_ref.id
              OR btrim(coalesce(cost.category, '')) IN ('{OLD_NAME}', '{LEGACY_NAME}', '{NEW_NAME}')
          )
        """
    )


def downgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '30s'")
    op.execute(
        f"""
        DO $$
        DECLARE
            new_id uuid;
            old_id uuid;
            target_id uuid;
        BEGIN
            SELECT id INTO new_id FROM finance_categories WHERE name = '{NEW_NAME}' FOR UPDATE;
            SELECT id INTO old_id FROM finance_categories WHERE name = '{OLD_NAME}' FOR UPDATE;
            IF new_id IS NOT NULL AND old_id IS NOT NULL AND new_id <> old_id THEN
                RAISE EXCEPTION 'Cannot restore {OLD_NAME}: name belongs to another category';
            END IF;

            target_id := COALESCE(new_id, old_id);
            IF target_id IS NULL THEN
                RAISE EXCEPTION 'Finance category not found: {NEW_NAME} / {OLD_NAME}';
            END IF;

            UPDATE bank_ledger_entries AS entry
            SET category = '{OLD_NAME}', category_id = target_id
            WHERE entry.entry_type = 'manual'
              AND entry.direction = 'expense'
              AND (
                  entry.category_id = target_id
                  OR btrim(coalesce(entry.category, '')) IN ('{NEW_NAME}', '{LEGACY_NAME}', '{OLD_NAME}')
              );

            UPDATE project_costs AS cost
            SET category = '{OLD_NAME}', category_id = target_id
            WHERE cost.category_id = target_id
               OR btrim(coalesce(cost.category, '')) IN ('{NEW_NAME}', '{LEGACY_NAME}', '{OLD_NAME}');

            IF new_id IS NOT NULL THEN
                UPDATE finance_categories SET name = '{OLD_NAME}' WHERE id = target_id;
            END IF;

            DELETE FROM finance_category_aliases
            WHERE alias = '{OLD_NAME}' AND category_id = target_id;
        END $$;
        """
    )
