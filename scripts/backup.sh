#!/bin/bash
# AdCraft ERP Backup Script
# Usage: ./scripts/backup.sh
# Creates a database-only backup archive.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Configuration
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup..."

# 1. Dump PostgreSQL database
BACKUP_SQL="${BACKUP_DIR}/${BACKUP_NAME}.sql"
echo "  -> Dumping PostgreSQL database"
PROJECT_DIR="$PROJECT_DIR" \
  python3 "$SCRIPT_DIR/postgres_cli.py" dump --file "$BACKUP_SQL"
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
