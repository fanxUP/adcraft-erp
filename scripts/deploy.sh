#!/usr/bin/env bash
# 兼容旧入口：统一转到仓库根目录的 GitHub + Docker Compose 部署脚本。
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../deploy.sh" "$@"
