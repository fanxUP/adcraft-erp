#!/bin/bash
# Seed script: create default roles.
# Admin creation is handled by backend/scripts/init_app.py and requires the
# explicitly configured ADMIN_INIT_PASSWORD environment variable.

set -e

HOST="${DB_HOST:-postgres}"
PORT="${DB_PORT:-5432}"
DB="${POSTGRES_DB:-adcraft_erp}"
USER="${POSTGRES_USER:-adcraft}"
PASSWORD="${POSTGRES_PASSWORD:-}"

SQL="
INSERT INTO roles (id, name, description) VALUES
  (gen_random_uuid(), 'admin', '系统管理员，拥有所有权限'),
  (gen_random_uuid(), 'sales', '销售员，管理客户和报价'),
  (gen_random_uuid(), 'designer', '设计师，处理设计任务'),
  (gen_random_uuid(), 'production', '制作人员，处理制作任务'),
  (gen_random_uuid(), 'installer', '安装人员，处理安装任务'),
  (gen_random_uuid(), 'finance', '财务人员，管理收款和对账')
ON CONFLICT (name) DO NOTHING;

"

echo "Seeding database..."
echo "$SQL" | PGPASSWORD="$PASSWORD" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB"
echo "Role seed complete. Admin creation is handled by backend/scripts/init_app.py."
