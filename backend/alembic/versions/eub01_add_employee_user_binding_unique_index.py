"""enforce one active employee record per login user

Revision ID: eub01_employee_user_binding
Revises: osa01_order_stage_attachments
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "eub01_employee_user_binding"
down_revision: Union[str, None] = "osa01_order_stage_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_employees_user_id_not_deleted"


def upgrade() -> None:
    # Do not silently choose a record if legacy data already violates the
    # intended one-to-one relationship.  The migration must be safe to rerun
    # only after the conflicting records have been reviewed by an operator.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT user_id
                    FROM employees
                    WHERE user_id IS NOT NULL
                      AND deleted_at IS NULL
                    GROUP BY user_id
                    HAVING COUNT(*) > 1
                ) THEN
                    RAISE EXCEPTION
                        '无法建立员工账号唯一约束：存在重复的未删除员工绑定，请先人工处理';
                END IF;
            END $$;
            """
        )
    )
    op.create_index(
        INDEX_NAME,
        "employees",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="employees")
