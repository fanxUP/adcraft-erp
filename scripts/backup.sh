#!/bin/bash
# AdCraft ERP Backup Script
# Usage: ./scripts/backup.sh
# Creates a database-only backup archive.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Load .env if available
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$PROJECT_DIR/.env"
  set +a
fi

# Configuration
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
DB_HOST="${PGHOST:-127.0.0.1}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${POSTGRES_DB:-adcraft_erp}"
DB_USER="${POSTGRES_USER:-adcraft}"
DB_PASS="${POSTGRES_PASSWORD:-adcraft_dev_password}"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup..."

# 1. Dump PostgreSQL database
BACKUP_SQL="${BACKUP_DIR}/${BACKUP_NAME}.sql"
echo "  -> Dumping PostgreSQL database"
BACKUP_SQL="$BACKUP_SQL" \
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
        "pg_dump",
        "-h",
        host,
        "-p",
        port,
        "-U",
        user,
        "-d",
        database,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "-f",
        os.environ["BACKUP_SQL"],
    ],
    check=True,
    env=environment,
)
PY
echo "  -> Database dump size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}.sql" | cut -f1)"

# 2. Archive only the database dump. Program files are versioned in Git and
# uploads are persistent business files, so neither belongs in deployment
# backups.
echo "  -> Archiving database dump only..."
tar -czf "$BACKUP_FILE" -C "$BACKUP_DIR" "${BACKUP_NAME}.sql"

# 3. Clean up temporary SQL dump
rm -f "${BACKUP_DIR}/${BACKUP_NAME}.sql"

# 4. Clean up old backups (keep RETENTION_DAYS)
echo "  -> Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f | wc -l | tr -d ' ')
BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: ${BACKUP_FILE} (${BACKUP_SIZE})"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Total backups on disk: ${BACKUP_COUNT}"

exit 0
