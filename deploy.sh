#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/adcraft}"
SERVICE_NAME="${SERVICE_NAME:-adcraft-backend}"
DEPLOY_OWNER="${DEPLOY_OWNER:-root}"
DEPLOY_GROUP="${DEPLOY_GROUP:-adcraft}"
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

程序目录会与目标 Git 提交一致；发现服务器有未提交的跟踪文件改动时会停止，
  不会自动使用 git clean 删除未知文件。代码最终归 ${DEPLOY_OWNER}:${DEPLOY_GROUP}，
  运行数据仍由服务账号维护。

默认复用服务器现有的 Python venv，不访问公网安装依赖。依赖有明确变更时，
在已确认服务器可访问软件源或已准备离线包后显式设置：
  INSTALL_DEPENDENCIES=1 sudo -E ./deploy.sh ...

首次接管已有临时覆盖代码时，可在确认代码已备份后使用：
  ALLOW_DIRTY_WORKTREE=1 sudo -E ./deploy.sh ...
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

if ! id "$DEPLOY_OWNER" >/dev/null 2>&1; then
  echo "部署代码所有者不存在：$DEPLOY_OWNER" >&2
  exit 1
fi
if ! getent group "$DEPLOY_GROUP" >/dev/null 2>&1; then
  echo "部署代码组不存在：$DEPLOY_GROUP" >&2
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

CURRENT_TRACKED_CHANGES="$(git status --porcelain --untracked-files=no)"
if [ -n "$CURRENT_TRACKED_CHANGES" ] && [ "${ALLOW_DIRTY_WORKTREE:-0}" != "1" ]; then
  echo "部署停止：服务器工作区存在未提交的跟踪文件改动。" >&2
  echo "$CURRENT_TRACKED_CHANGES" >&2
  echo "请先确认这些改动已经进入 Git，或在确认备份后使用 ALLOW_DIRTY_WORKTREE=1。" >&2
  exit 1
fi

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

if [ ! -f .env ]; then
  echo "缺少生产环境配置：$PROJECT_DIR/.env" >&2
  exit 1
fi

if [ ! -x backend/.venv/bin/python ]; then
  echo "缺少生产 Python venv：$PROJECT_DIR/backend/.venv/bin/python" >&2
  echo "请先在服务器准备依赖，或按维护窗口单独初始化 venv。" >&2
  exit 1
fi
if [ "${INSTALL_DEPENDENCIES:-0}" = "1" ]; then
  backend/.venv/bin/pip install --quiet --disable-pip-version-check --no-build-isolation -e backend
else
  echo "跳过 Python 依赖安装（使用服务器现有 venv）"
fi
backend/.venv/bin/python -c \
  'import alembic, asyncpg, fastapi, pydantic, sqlalchemy, uvicorn'

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

normalize_deploy_permissions() {
  local relative path

  # The project root and Git metadata must be usable by the deploy account.
  chown "$DEPLOY_OWNER:$DEPLOY_GROUP" "$PROJECT_DIR" "$PROJECT_DIR/.git"
  chmod 750 "$PROJECT_DIR" "$PROJECT_DIR/.git"
  chown -R "$DEPLOY_OWNER:$DEPLOY_GROUP" "$PROJECT_DIR/.git"
  chmod -R u+rwX,g+rX,o-rwx "$PROJECT_DIR/.git"

  # Only normalize source/generated-code paths. Persistent runtime data is
  # deliberately excluded so the adcraft service keeps ownership of it.
  for relative in \
    .github \
    .husky \
    architecture \
    backend/app \
    backend/alembic \
    backend/scripts \
    cdr-bridge \
    cdr-plugin \
    config \
    docs \
    frontend/src \
    frontend/public \
    frontend/dist \
    nginx \
    prompts \
    schema \
    scripts \
    templates; do
    path="$PROJECT_DIR/$relative"
    if [ -e "$path" ]; then
      chown -R "$DEPLOY_OWNER:$DEPLOY_GROUP" "$path"
      chmod -R u+rwX,g+rX,o-rwx "$path"
    fi
  done

  for relative in backend frontend nginx scripts; do
    path="$PROJECT_DIR/$relative"
    if [ -d "$path" ]; then
      chown "$DEPLOY_OWNER:$DEPLOY_GROUP" "$path"
      chmod 750 "$path"
    fi
  done

  # Root-level tracked files (compose files, deploy entrypoint, etc.) are
  # writable by the deploy owner but keep their existing executable bit.
  while IFS= read -r -d '' relative; do
    case "$relative" in
      .env|backend/uploads/*|backend/logs/*|backups/*)
        continue
        ;;
    esac
    path="$PROJECT_DIR/$relative"
    [ -f "$path" ] && chown "$DEPLOY_OWNER:$DEPLOY_GROUP" "$path"
  done < <(git ls-files -z)

  if [ -f "$PROJECT_DIR/.deployed-commit" ]; then
    chown "$DEPLOY_OWNER:$DEPLOY_GROUP" "$PROJECT_DIR/.deployed-commit"
    chmod 640 "$PROJECT_DIR/.deployed-commit"
  fi
}

normalize_deploy_permissions
systemctl restart "$SERVICE_NAME"

for _ in $(seq 1 20); do
  if systemctl is-active --quiet "$SERVICE_NAME" \
    && curl --fail --silent --show-error \
      http://127.0.0.1:8000/api/v1/health >/dev/null; then
    break
  fi
  sleep 1
done

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "服务启动失败：$SERVICE_NAME" >&2
  exit 1
fi
curl --fail --silent --show-error \
  http://127.0.0.1:8000/api/v1/health >/dev/null

printf '%s\n' "$TARGET_COMMIT" > .deployed-commit
chown "$DEPLOY_OWNER:$DEPLOY_GROUP" .deployed-commit
chmod 640 .deployed-commit

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "部署后检测到跟踪文件变化：" >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

echo "部署完成：$TARGET_COMMIT"
