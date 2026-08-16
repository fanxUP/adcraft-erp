#!/usr/bin/env bash
# AdCraft 备份异地同步：将本地备份目录同步到 S3 兼容对象存储（MinIO/AWS S3 等），需 rclone
set -u

BACKUP_DIR="${BACKUP_DIR:-/opt/adcraft/backups}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"   # 例: minio:adcraft-backups（先 rclone config 配置）

if [ -z "$RCLONE_REMOTE" ]; then
  echo "未配置 RCLONE_REMOTE，跳过异地同步（配置后自动启用）"
  exit 0
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "未安装 rclone，跳过异地同步（apt install rclone）" >&2
  exit 0
fi

rclone sync "$BACKUP_DIR" "$RCLONE_REMOTE" --transfers 4 --checkers 8 2>&1 | tail -5
echo "备份已同步到 $RCLONE_REMOTE"
