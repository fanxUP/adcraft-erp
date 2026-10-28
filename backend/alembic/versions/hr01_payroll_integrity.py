"""Preserve payroll snapshots and effective-dated rules without rewriting facts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "hr01_payroll_integrity"
down_revision = "cca01_company_accounts"
branch_labels = None
depends_on = None

HR_PERMISSIONS = {
    "employee:read": "查看员工档案", "employee:manage": "维护员工档案", "employee:private": "查看员工私密资料",
    "attendance:read": "查看考勤", "attendance:manage": "维护考勤和规则",
    "leave:read": "查看请假", "leave:manage": "登记维护请假", "leave:approve": "审批撤销请假",
    "salary:read": "查看工资", "salary:calculate": "核算工资和维护标准", "salary:pay": "登记工资发放",
    "department:read": "查看部门", "department:manage": "维护部门",
}


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    # Explicitly fail rather than discarding or guessing duplicate business facts.
    for table, keys in (("salary_records", "employee_id, month"), ("attendance_records", "employee_id, date")):
        op.execute(f"""DO $$ BEGIN IF EXISTS (SELECT 1 FROM {table} GROUP BY {keys} HAVING count(*) > 1) THEN
            RAISE EXCEPTION 'Duplicate rows in {table}; reconcile explicitly before HR migration';
            END IF; END $$""")
    op.add_column("leave_requests", sa.Column("cancelled_by", UUID(as_uuid=True), nullable=True))
    op.add_column("leave_requests", sa.Column("cancelled_at", sa.DateTime, nullable=True))
    op.add_column("leave_requests", sa.Column("cancellation_reason", sa.Text, nullable=True))
    op.create_foreign_key("fk_leave_cancelled_by", "leave_requests", "users", ["cancelled_by"], ["id"])
    op.add_column("employment_histories", sa.Column("is_automatic", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("salary_records", sa.Column("snapshot", JSONB, nullable=True))
    op.add_column("salary_records", sa.Column("expense_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_salary_expense", "salary_records", "expenses", ["expense_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_salary_expense", "salary_records", ["expense_id"])
    op.create_unique_constraint("uq_salary_employee_month", "salary_records", ["employee_id", "month"])
    op.create_unique_constraint("uq_attendance_employee_date", "attendance_records", ["employee_id", "date"])
    op.drop_constraint("uq_salary_rules_employee", "salary_rules", type_="unique")
    op.create_unique_constraint("uq_salary_rules_employee_date", "salary_rules", ["employee_id", "effective_date"])
    for code, name in HR_PERMISSIONS.items():
        module, action = code.split(":")
        op.execute(sa.text("""INSERT INTO permissions
            (id, code, name, module, resource, action, kind, sensitivity, status, sort_order)
            VALUES (gen_random_uuid(), :code, :name, :module, :module, :action, 'action', :sensitivity, 'active', 0)
            ON CONFLICT (code) DO NOTHING""").bindparams(code=code, name=name, module=module, action=action,
                sensitivity="financial" if module == "salary" else "security" if code == "employee:private" else "normal"))
    # Retain department codes already used in HR instead of changing employees.
    op.execute("""INSERT INTO departments (id, code, name, is_active, sort_order, created_at, updated_at)
        SELECT gen_random_uuid(), codes.code,
            CASE codes.code WHEN 'design' THEN '设计部' WHEN 'production' THEN '生产部' WHEN 'installation' THEN '安装部'
            WHEN 'sales' THEN '销售部' WHEN 'finance' THEN '财务部' WHEN 'admin' THEN '行政部' ELSE codes.code END,
            true, 0, now(), now()
        FROM (SELECT department AS code FROM employees WHERE department IS NOT NULL AND department <> ''
              UNION SELECT department FROM attendance_rules WHERE department IS NOT NULL AND department <> '') codes
        WHERE NOT EXISTS (SELECT 1 FROM departments d WHERE d.code = codes.code)
        ON CONFLICT DO NOTHING""")
    # Preserve access for capability-based super administrators only. No normal role gets new HR access.
    op.execute("""INSERT INTO role_permissions (role_id, permission_id)
        SELECT DISTINCT old.role_id, p.id FROM role_permissions old
        JOIN permissions super ON super.id = old.permission_id AND super.code = 'system:super_admin'
        CROSS JOIN permissions p WHERE p.code IN (%s)
        ON CONFLICT DO NOTHING""" % ",".join("'%s'" % code for code in HR_PERMISSIONS))


def downgrade():
    # Application rollback keeps this additive schema; never destroy payment links/snapshots.
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM employment_histories WHERE is_automatic = true)
           OR EXISTS (SELECT 1 FROM leave_requests WHERE cancelled_at IS NOT NULL)
           OR EXISTS (SELECT 1 FROM salary_records WHERE snapshot IS NOT NULL OR expense_id IS NOT NULL)
           OR EXISTS (SELECT 1 FROM salary_rules GROUP BY employee_id HAVING count(*) > 1) THEN
            RAISE EXCEPTION 'HR history exists; retain schema during application rollback';
        END IF;
    END $$""")
    op.drop_constraint("uq_salary_rules_employee_date", "salary_rules", type_="unique")
    op.create_unique_constraint("uq_salary_rules_employee", "salary_rules", ["employee_id"])
    op.drop_constraint("uq_attendance_employee_date", "attendance_records", type_="unique")
    op.drop_constraint("uq_salary_employee_month", "salary_records", type_="unique")
    op.drop_constraint("uq_salary_expense", "salary_records", type_="unique")
    op.drop_constraint("fk_salary_expense", "salary_records", type_="foreignkey")
    op.drop_column("salary_records", "expense_id")
    op.drop_column("salary_records", "snapshot")
    op.drop_column("employment_histories", "is_automatic")
    op.drop_constraint("fk_leave_cancelled_by", "leave_requests", type_="foreignkey")
    for name in ("cancelled_by", "cancelled_at", "cancellation_reason"):
        op.drop_column("leave_requests", name)
    # Keep department master records and permissions for older applications.
    # Retain permission records to preserve custom role configuration across application rollbacks.
