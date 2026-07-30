#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/adcraft}"
SERVICE_NAME="${SERVICE_NAME:-adcraft-backend}"
BRANCH="${DEPLOY_BRANCH:-master}"
BUNDLE=""
DIST_ARCHIVE=""
EXPECTED_COMMIT=""

usage() {
  cat <<'EOF'
AdCraft ERP 全量部署

用法：
  sudo ./deploy.sh
  sudo ./deploy.sh --bundle /tmp/adcraft.bundle \
    --dist /tmp/adcraft-dist.tar.gz \
    --commit <完整提交哈希>

默认从 origin/master 更新。服务器无法访问 GitHub 时，可上传 git bundle
和本地构建的前端 dist 压缩包后部署。

持久数据：
  .env、backend/uploads、backups、backend/.venv

程序目录会强制与目标 Git 提交一致，服务器上的临时代码改动会被清理。
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bundle)
      BUNDLE="${2:?缺少 bundle 路径}"
      shift 2
      ;;
    --dist)
      DIST_ARCHIVE="${2:?缺少 dist 压缩包路径}"
      shift 2
      ;;
    --commit)
      EXPECTED_COMMIT="${2:?缺少提交哈希}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "请使用 sudo 运行部署脚本。" >&2
  exit 1
fi

cd "$PROJECT_DIR"

if [ ! -d .git ]; then
  echo "部署目录不是 Git 仓库：$PROJECT_DIR" >&2
  exit 1
fi

if [ -n "$BUNDLE" ]; then
  if [ ! -f "$BUNDLE" ] || [ -z "$EXPECTED_COMMIT" ]; then
    echo "bundle 部署必须同时提供有效的 --bundle 和 --commit。" >&2
    exit 1
  fi
  git fetch "$BUNDLE" "refs/heads/${BRANCH}"
  TARGET_COMMIT="$(git rev-parse FETCH_HEAD)"
else
  git fetch --prune origin "$BRANCH"
  TARGET_COMMIT="$(git rev-parse "origin/${BRANCH}")"
fi

if [ -n "$EXPECTED_COMMIT" ]; then
  RESOLVED_EXPECTED="$(git rev-parse "$EXPECTED_COMMIT")"
  if [ "$TARGET_COMMIT" != "$RESOLVED_EXPECTED" ]; then
    echo "提交校验失败：目标 $TARGET_COMMIT，期望 $RESOLVED_EXPECTED" >&2
    exit 1
  fi
fi

if [ -n "$BUNDLE" ]; then
  git update-ref "refs/remotes/origin/${BRANCH}" "$TARGET_COMMIT"
fi

echo "=== AdCraft ERP 全量部署 ==="
echo "目标提交：$TARGET_COMMIT"

# 仅备份数据库；代码由 Git 恢复，上传文件是独立持久数据。
BACKUP_TOOL_DIR="$(mktemp -d /tmp/adcraft-database-backup.XXXXXX)"
trap 'rm -rf "$BACKUP_TOOL_DIR"' EXIT
git archive "$TARGET_COMMIT" scripts/backup.sh scripts/postgres_cli.py \
  | tar -x -C "$BACKUP_TOOL_DIR"
chmod 700 "$BACKUP_TOOL_DIR/scripts/backup.sh"
PROJECT_DIR="$PROJECT_DIR" "$BACKUP_TOOL_DIR/scripts/backup.sh"
rm -rf "$BACKUP_TOOL_DIR"
trap - EXIT

git reset --hard "$TARGET_COMMIT"
git clean -ffdx \
  -e .env \
  -e .deployed-commit \
  -e backups \
  -e backend/.venv \
  -e backend/uploads

for PERSISTENT_PATH in .deployed-commit backend/uploads/; do
  if ! grep -Fqx "$PERSISTENT_PATH" .git/info/exclude; then
    printf '%s\n' "$PERSISTENT_PATH" >> .git/info/exclude
  fi
done

if [ ! -f .env ]; then
  echo "缺少生产环境配置：$PROJECT_DIR/.env" >&2
  exit 1
fi

if [ ! -x backend/.venv/bin/python ]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install --quiet --disable-pip-version-check -e backend

if [ -n "$DIST_ARCHIVE" ]; then
  if [ ! -f "$DIST_ARCHIVE" ]; then
    echo "前端构建包不存在：$DIST_ARCHIVE" >&2
    exit 1
  fi
  rm -rf frontend/dist
  mkdir -p frontend/dist
  tar --warning=no-unknown-keyword -xzf "$DIST_ARCHIVE" -C frontend/dist
else
  NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
  if [ "$NODE_MAJOR" -lt 20 ]; then
    echo "Node.js 版本过低，请提供 --dist 或升级到 Node.js 20+。" >&2
    exit 1
  fi
  (
    cd frontend
    HUSKY=0 npm ci
    npm run build
  )
fi
chmod -R a+rX frontend/dist

(
  cd backend
  PYTHONPATH=. .venv/bin/alembic upgrade head
  PYTHONPATH=. .venv/bin/python scripts/seed_permissions.py
)

python3 /opt/adcraft/backend/apply_hr_module.py 2>/dev/null || true
systemctl restart "$SERVICE_NAME"

for _ in $(seq 1 20); do
  if systemctl is-active --quiet "$SERVICE_NAME" \
    && curl --fail --silent --show-error \
      http://127.0.0.1:8000/api/openapi.json >/dev/null; then
    break
  fi
  sleep 1
done

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "服务启动失败：$SERVICE_NAME" >&2
  exit 1
fi
curl --fail --silent --show-error \
  http://127.0.0.1:8000/api/openapi.json >/dev/null

printf '%s\n' "$TARGET_COMMIT" > .deployed-commit

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "部署后检测到跟踪文件变化：" >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

echo "部署完成：$TARGET_COMMIT"
