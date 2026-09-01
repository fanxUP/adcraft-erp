#!/bin/bash
# AdCraft ERP Restore Script
# Usage: ./scripts/restore.sh <backup_file>
# Restores a backup archive created by backup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$(cd "$PROJECT_DIR/backups" && pwd)"

if [ $# -ne 1 ]; then
  echo "Usage: $0 <backup_file>"
  echo "Example: $0 backups/backup_20260629_020000.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"
BACKUP_NAME="$(basename -- "$BACKUP_FILE")"

if [[ ! "$BACKUP_NAME" =~ ^backup_[0-9]{8}_[0-9]{6}\.tar\.gz$ ]]; then
  echo "Error: Invalid backup filename: $BACKUP_NAME"
  exit 1
fi

if [ -L "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

BACKUP_REALPATH="$(readlink -f -- "$BACKUP_FILE")"
if [ "$(dirname -- "$BACKUP_REALPATH")" != "$BACKUP_DIR" ]; then
  echo "Error: Backup file must be inside $BACKUP_DIR"
  exit 1
fi

python3 "$SCRIPT_DIR/validate_backup.py" "$BACKUP_REALPATH"
SQL_MEMBER="${BACKUP_NAME%.tar.gz}.sql"

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
tar -xzf "$BACKUP_REALPATH" --no-same-owner --no-same-permissions -C "$TMP_DIR" "$SQL_MEMBER"

SQL_FILE="$TMP_DIR/$SQL_MEMBER"
if [ ! -f "$SQL_FILE" ]; then
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
