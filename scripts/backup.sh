#!/bin/bash
# AdCraft ERP Backup Script
# Usage: ./scripts/backup.sh
# Creates separate SQL and verified attachment archives.

set -euo pipefail
# Backups are private to the application account and its service group. The
# group bit is needed when the scheduled backup runs as root while the API
# lists/downloads the resulting archive as adcraft.
umask 007

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Configuration
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
BACKUP_SQL="${BACKUP_DIR}/${BACKUP_NAME}.sql"
LOCK_DIR="${BACKUP_DIR}/.${BACKUP_NAME}.lock"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"
chmod 2770 "$BACKUP_DIR"
if [ -e "$BACKUP_FILE" ] || [ -e "$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz" ]; then
  echo "同一时间的备份已存在，请稍后重试，原备份保留。" >&2
  exit 1
fi
if ! mkdir "$LOCK_DIR"; then
  echo "已有备份正在执行，请稍后重试。" >&2
  exit 1
fi
trap 'rm -f "$BACKUP_SQL" "${BACKUP_FILE}.tmp"; rmdir "$LOCK_DIR"' EXIT

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup..."

# 1. Dump PostgreSQL database
echo "  -> Dumping PostgreSQL database"
PROJECT_DIR="$PROJECT_DIR" \
  python3 "$SCRIPT_DIR/postgres_cli.py" dump --file "$BACKUP_SQL"
echo "  -> Database dump size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}.sql" | cut -f1)"

# 2. Keep the narrow SQL archive format used by the existing restore API.
echo "  -> Archiving database dump only..."
tar -czf "${BACKUP_FILE}.tmp" -C "$BACKUP_DIR" "${BACKUP_NAME}.sql"
mv "${BACKUP_FILE}.tmp" "$BACKUP_FILE"
chmod 660 "$BACKUP_FILE"

# 3. Clean up temporary SQL dump
rm -f "${BACKUP_DIR}/${BACKUP_NAME}.sql"

# Resolve the application's actual upload root, including native backend cwd.
UPLOAD_ROOT=$(PROJECT_DIR="$PROJECT_DIR" python3 - "$SCRIPT_DIR" <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from postgres_cli import _read_env_file
project = Path(os.environ["PROJECT_DIR"])
env = _read_env_file(project / ".env")
configured = os.environ.get("LOCAL_UPLOAD_DIR") or env.get("LOCAL_UPLOAD_DIR")
if configured:
    root = Path(configured)
    if not root.is_absolute():
        root = (project / "backend" if (project / "backend/.venv").is_dir() else project) / root
else:
    root = project / "uploads"
print(root.resolve())
PY
)
UPLOAD_BACKUP="$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz"
python3 "$SCRIPT_DIR/uploads_backup.py" create "$UPLOAD_BACKUP" --root "$UPLOAD_ROOT"
python3 - "$BACKUP_FILE" "$UPLOAD_BACKUP" <<'PY'
import hashlib, sys
from pathlib import Path
for name in sys.argv[1:]:
    path = Path(name)
    with path.open('rb') as source:
        checksum = hashlib.file_digest(source, 'sha256').hexdigest()
    path.with_name(path.name + '.sha256').write_text(f'{checksum}  {path.name}\n')
PY

# 4. Clean up old backups (keep RETENTION_DAYS)
echo "  -> Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "uploads_*.tar.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_DIR" -name "*.sha256" -type f -mtime "+${RETENTION_DAYS}" -delete

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f | wc -l | tr -d ' ')
BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: ${BACKUP_FILE} (${BACKUP_SIZE})"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Total backups on disk: ${BACKUP_COUNT}"

SYNC_REMOTE=$(PROJECT_DIR="$PROJECT_DIR" python3 - "$SCRIPT_DIR" <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from postgres_cli import _read_env_file
env = _read_env_file(Path(os.environ["PROJECT_DIR"]) / ".env")
print(os.environ.get("RCLONE_REMOTE") or env.get("RCLONE_REMOTE", ""))
PY
)
BACKUP_DIR="$BACKUP_DIR" RCLONE_REMOTE="$SYNC_REMOTE" bash "$SCRIPT_DIR/backup_sync.sh"

exit 0
