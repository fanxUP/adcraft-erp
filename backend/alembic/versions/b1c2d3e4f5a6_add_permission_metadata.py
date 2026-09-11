"""add structured permission metadata

Revision ID: b1c2d3e4f5a6
Revises: tavp01_order_task_assignees
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "tavp01_order_task_assignees"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("roles", sa.Column("permission_seed_version", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE roles
            SET permission_seed_version = CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM role_permissions rp
                    WHERE rp.role_id = roles.id
                ) THEN 1
                ELSE 0
            END
            """
        )
    )
    op.alter_column(
        "roles",
        "permission_seed_version",
        nullable=False,
        server_default=sa.text("0"),
    )

    op.add_column("permissions", sa.Column("module", sa.String(length=64), nullable=True))
    op.add_column("permissions", sa.Column("resource", sa.String(length=128), nullable=True))
    op.add_column("permissions", sa.Column("action", sa.String(length=64), nullable=True))
    op.add_column("permissions", sa.Column("kind", sa.String(length=32), nullable=True))
    op.add_column("permissions", sa.Column("sensitivity", sa.String(length=32), nullable=True))
    op.add_column("permissions", sa.Column("status", sa.String(length=16), nullable=True))
    op.add_column("permissions", sa.Column("sort_order", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE permissions
            SET
                module = split_part(code, ':', 1),
                resource = CASE
                    WHEN code NOT LIKE '%:%:%' THEN split_part(code, ':', 1)
                    ELSE split_part(code, ':', 1) || ':' || split_part(code, ':', 2)
                END,
                action = regexp_replace(code, '^.*:', ''),
                kind = CASE
                    WHEN code ~ ':(view_price|view_cost|view_profit)$' THEN 'field'
                    WHEN code IN ('resource_center:read', 'outsource_center:read') THEN 'module'
                    ELSE 'action'
                END,
                sensitivity = CASE
                    WHEN code ~ ':(view_price|view_profit)$'
                         OR code LIKE 'quote:%'
                         OR code LIKE 'contract:%'
                         OR code LIKE 'cdr_quote:%'
                         OR code IN ('catalog:view_price', 'order:view_price', 'order_item:view_price')
                        THEN 'price'
                    WHEN code ~ ':(view_cost)$'
                         OR code LIKE 'payment:%'
                         OR code LIKE 'statement:%'
                         OR code LIKE 'expense:%'
                         OR code LIKE 'report:%'
                         OR code = 'finance:review'
                        THEN 'financial'
                    WHEN code LIKE 'outsource%:%' THEN 'external'
                    WHEN code LIKE 'system:%'
                         OR code LIKE 'backup:%'
                         OR code LIKE 'user:%'
                        THEN 'security'
                    ELSE 'normal'
                END,
                status = 'active',
                sort_order = 0
            """
        )
    )

    for column in ("module", "resource", "action", "kind", "sensitivity", "status", "sort_order"):
        default = {
            "module": "'system'",
            "resource": "'system'",
            "action": "'read'",
            "kind": "'action'",
            "sensitivity": "'normal'",
            "status": "'active'",
            "sort_order": "0",
        }[column]
        op.alter_column(
            "permissions",
            column,
            nullable=False,
            server_default=sa.text(default),
        )

    # The new admin route guard is capability-based.  Create the explicit
    # super-admin capability during the same migration so an existing admin
    # account is not locked out between schema upgrade and the next seed run.
    # This only touches the permission catalog and its admin association; no
    # business facts or custom-role associations are changed.
    op.execute(
        sa.text(
            """
            INSERT INTO permissions
                (id, code, name, description, module, resource, action, kind,
                 sensitivity, status, sort_order)
            SELECT
                gen_random_uuid(),
                'system:super_admin',
                '超级管理员',
                '管理所有模块、权限和系统安全设置',
                'system',
                'system',
                'super_admin',
                'action',
                'security',
                'active',
                1
            WHERE NOT EXISTS (
                SELECT 1 FROM permissions WHERE code = 'system:super_admin'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'admin' AND p.code = 'system:super_admin'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # Keep the explicit capability row and association on downgrade.  Older
    # application code ignores unknown permission codes, while deleting it
    # here could erase an intentional post-migration security assignment.
    op.drop_column("permissions", "sort_order")
    op.drop_column("permissions", "status")
    op.drop_column("permissions", "sensitivity")
    op.drop_column("permissions", "kind")
    op.drop_column("permissions", "action")
    op.drop_column("permissions", "resource")
    op.drop_column("permissions", "module")
    op.drop_column("roles", "permission_seed_version")
