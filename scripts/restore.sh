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
PROJECT_DIR="$PROJECT_DIR" \
  python3 "$SCRIPT_DIR/postgres_cli.py" restore --file "$SQL_FILE"
echo "  -> Database restore complete"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restore complete!"
exit 0
