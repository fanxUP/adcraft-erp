#!/bin/bash
# Seed script: create admin user and default roles

set -e

HOST="${DB_HOST:-postgres}"
PORT="${DB_PORT:-5432}"
DB="${POSTGRES_DB:-adcraft_erp}"
USER="${POSTGRES_USER:-adcraft}"
PASSWORD="${POSTGRES_PASSWORD:-adcraft_dev_password}"

SQL="
INSERT INTO roles (id, name, description) VALUES
  (gen_random_uuid(), 'admin', '系统管理员，拥有所有权限'),
  (gen_random_uuid(), 'sales', '销售员，管理客户和报价'),
  (gen_random_uuid(), 'designer', '设计师，处理设计任务'),
  (gen_random_uuid(), 'production', '制作人员，处理制作任务'),
  (gen_random_uuid(), 'installer', '安装人员，处理安装任务'),
  (gen_random_uuid(), 'finance', '财务人员，管理收款和对账')
ON CONFLICT (name) DO NOTHING;

INSERT INTO users (id, username, password_hash, real_name, is_active) VALUES
  (gen_random_uuid(), 'admin', '\$2b\$12\$CssbSpQCObmbmkgCzolCkuZbDBRHjoz9ykY/3V6A8EYND3hSaOZQ2', '系统管理员', TRUE)
ON CONFLICT (username) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.username = 'admin' AND r.name = 'admin'
ON CONFLICT DO NOTHING;
"

echo "Seeding database..."
echo "$SQL" | PGPASSWORD="$PASSWORD" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB"
echo "Seed complete."
