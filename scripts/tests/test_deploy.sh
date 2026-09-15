#!/usr/bin/env bash
# Lightweight regression checks for the single GitHub deployment path.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

bash -n "$ROOT_DIR/deploy.sh"
bash -n "$ROOT_DIR/install-ubuntu.sh"
bash -n "$ROOT_DIR/scripts/deploy.sh"

deploy_help="$($ROOT_DIR/deploy.sh --help)"
[[ "$deploy_help" == *"固定从以下 GitHub 仓库拉取代码"* ]]
[[ "$deploy_help" == *"不会自动备份、同步或恢复业务数据"* ]]
if ! [[ "$deploy_help" == *"自动识别原生服务和 Docker Compose"* ]]; then
  echo "deploy script does not advertise automatic native/Compose detection" >&2
  exit 1
fi

install_help="$($ROOT_DIR/install-ubuntu.sh --help)"
[[ "$install_help" == *"全新 Ubuntu 安装"* ]]
[[ "$install_help" == *"不会导入、删除或覆盖业务数据库"* ]]

if grep -qE 'git pull .*\|\||使用当前代码继续' \
  "$ROOT_DIR/deploy.sh" "$ROOT_DIR/install-ubuntu.sh"; then
  echo "deployment scripts contain a forbidden fallback or destructive command" >&2
  exit 1
fi

if grep -qE '^[[:space:]]*(git clean|docker compose down -v)' \
  "$ROOT_DIR/deploy.sh" "$ROOT_DIR/install-ubuntu.sh"; then
  echo "deployment scripts contain a destructive data command" >&2
  exit 1
fi

grep -q 'https://github.com/fanxUP/adcraft-erp.git' "$ROOT_DIR/deploy.sh"
grep -q 'docker compose -f "\$COMPOSE_FILE" up -d --build' "$ROOT_DIR/deploy.sh"
grep -q 'git clone --origin origin --branch' "$ROOT_DIR/install-ubuntu.sh"
grep -q 'install -d -o "\$service_user" -g "\$service_group" -m 0750 "\$upload_dir"' "$ROOT_DIR/deploy.sh"
grep -q 'find "\$upload_dir" -xdev -type f' "$ROOT_DIR/deploy.sh"

echo "simple deployment tests passed"
