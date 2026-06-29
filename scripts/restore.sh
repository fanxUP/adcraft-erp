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
echo "  -> Target database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo ""
echo "WARNING: This will OVERWRITE the current database and upload files!"
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
export PGPASSWORD="$DB_PASS"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE"
unset PGPASSWORD
echo "  -> Database restore complete"

# Restore uploads if present
if [ -d "$TMP_DIR/uploads" ] && [ "$(ls -A "$TMP_DIR/uploads")" ]; then
  echo "  -> Restoring uploads..."
  UPLOADS_DIR="${PROJECT_DIR}/uploads"
  mkdir -p "$UPLOADS_DIR"
  cp -r "$TMP_DIR/uploads/"* "$UPLOADS_DIR/" 2>/dev/null || true
  echo "  -> Uploads restore complete"
else
  echo "  -> No uploads found in backup (skipped)"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restore complete!"
exit 0
