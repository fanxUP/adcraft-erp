#!/bin/bash
# AdCraft ERP Restore Script
# Usage: ./scripts/restore.sh <backup_file>
# Restores a backup archive created by backup.sh

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_file>"
  echo "Example: $0 backups/backup_2026_06_29_020000.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env if available
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$PROJECT_DIR/.env"
  set +a
fi

DB_HOST="${PGHOST:-127.0.0.1}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${POSTGRES_DB:-adcraft_erp}"
DB_USER="${POSTGRES_USER:-adcraft}"
DB_PASS="${POSTGRES_PASSWORD:-adcraft_dev_password}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting restore from: ${BACKUP_FILE}"
echo "  -> Target database: configured production database"
echo ""
echo "WARNING: This will OVERWRITE the current database!"
read -r -p "Are you sure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Restore cancelled."
  exit 1
fi

# Create temp directory
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "  -> Extracting backup archive..."
tar -xzf "$BACKUP_FILE" -C "$TMP_DIR"

# Find SQL dump
SQL_FILE=$(find "$TMP_DIR" -name "backup_*.sql" -type f | head -1)
if [ -z "$SQL_FILE" ]; then
  echo "Error: No SQL dump found in backup archive"
  exit 1
fi

# Restore PostgreSQL database
echo "  -> Restoring database..."
SQL_FILE="$SQL_FILE" \
DB_HOST="$DB_HOST" \
DB_PORT="$DB_PORT" \
DB_NAME="$DB_NAME" \
DB_USER="$DB_USER" \
DB_PASS="$DB_PASS" \
python3 - <<'PY'
import os
import re
import subprocess
from urllib.parse import unquote, urlsplit

database_url = os.environ.get("DATABASE_URL_SYNC", "")
if database_url:
    normalized_url = re.sub(
        r"^postgresql\+[^:]+://",
        "postgresql://",
        database_url,
        count=1,
    )
    parsed = urlsplit(normalized_url)
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 5432)
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    database = unquote(parsed.path.lstrip("/"))
else:
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASS"]
    database = os.environ["DB_NAME"]

environment = os.environ.copy()
environment["PGPASSWORD"] = password
subprocess.run(
    [
        "psql",
        "-h",
        host,
        "-p",
        port,
        "-U",
        user,
        "-d",
        database,
        "-f",
        os.environ["SQL_FILE"],
    ],
    check=True,
    env=environment,
)
PY
echo "  -> Database restore complete"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restore complete!"
exit 0
