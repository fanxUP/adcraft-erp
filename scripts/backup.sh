#!/bin/bash
# AdCraft ERP Backup Script
# Usage: ./scripts/backup.sh
# Creates a timestamped backup of PostgreSQL database + uploads

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env if available
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$PROJECT_DIR/.env"
  set +a
fi

# Configuration
BACKUP_DIR="${PROJECT_DIR}/backups"
UPLOADS_DIR="${PROJECT_DIR}/uploads"
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
echo "  -> Dumping database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
export PGPASSWORD="$DB_PASS"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --clean --if-exists --no-owner --no-privileges \
  -f "${BACKUP_DIR}/${BACKUP_NAME}.sql"
unset PGPASSWORD
echo "  -> Database dump size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}.sql" | cut -f1)"

# 2. Create archive (DB dump + uploads)
echo "  -> Archiving database dump and uploads..."
tar -czf "$BACKUP_FILE" \
  -C "$BACKUP_DIR" "${BACKUP_NAME}.sql" \
  -C "$PROJECT_DIR" "uploads" 2>/dev/null || {
    # If uploads doesn't exist, create archive with just the SQL file
    tar -czf "$BACKUP_FILE" -C "$BACKUP_DIR" "${BACKUP_NAME}.sql"
  }

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
