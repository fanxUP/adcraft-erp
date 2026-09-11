#!/usr/bin/env bash
# AdCraft ERP — GitHub + 原生服务/Docker Compose 部署入口
#
# 这个脚本只负责发布应用代码和启动应用：
# - 代码唯一来源是固定的 GitHub 仓库；
# - .env、uploads、backups、logs 和 Docker 数据卷不加入 Git，也不由本脚本删除；
# - 数据恢复请使用系统内的备份管理功能；
# - 已存在的原生 systemd 服务自动复用，Docker Compose 只在 Docker 已启动时使用；
# - 不执行 docker compose down -v、git clean 或自动 restore。
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
REPO_URL="https://github.com/fanxUP/adcraft-erp.git"
REMOTE_NAME="origin"
BRANCH="${DEPLOY_BRANCH:-master}"
EXPECTED_COMMIT=""
HEALTH_URL="${DEPLOY_HEALTH_URL:-http://127.0.0.1/health}"
NATIVE_HEALTH_URL="${DEPLOY_NATIVE_HEALTH_URL:-http://127.0.0.1:8000/api/v1/health}"
HEALTH_TIMEOUT_SECONDS="${DEPLOY_HEALTH_TIMEOUT_SECONDS:-90}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE_NAME="${DEPLOY_SERVICE_NAME:-adcraft-backend}"
DEPLOY_MODE="${DEPLOY_MODE:-auto}"

usage() {
  cat <<'EOF'
AdCraft ERP GitHub 部署

首次部署（推荐）：
  sudo ./install-ubuntu.sh

已有项目更新：
  sudo ./deploy.sh
  sudo ./deploy.sh --branch master --commit <完整提交哈希>

脚本固定从以下 GitHub 仓库拉取代码：
  https://github.com/fanxUP/adcraft-erp.git

脚本会自动识别原生服务和 Docker Compose：
  - 已存在并运行 adcraft-backend.service 时，复用原生 systemd/Nginx；
  - 全新 Ubuntu 安装 Docker 并启动 Docker 时，使用 Docker Compose。

部署不会自动备份、同步或恢复业务数据，也不会删除 .env、上传文件、备份文件
或 Docker 数据卷。数据恢复请在系统内通过备份管理完成。
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir)
      PROJECT_DIR="${2:?缺少项目目录}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:?缺少分支名称}"
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

if [[ ! "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "分支名称包含非法字符：$BRANCH" >&2
  exit 1
fi

if [ ! -d "$PROJECT_DIR" ]; then
  echo "项目目录不存在：$PROJECT_DIR；首次部署请运行 ./install-ubuntu.sh。" >&2
  exit 1
fi
cd "$PROJECT_DIR"

if [ ! -d .git ]; then
  echo "项目目录不是 Git 仓库：$PROJECT_DIR；首次部署请运行 ./install-ubuntu.sh。" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "未安装 git；请运行 ./install-ubuntu.sh。" >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "未安装 curl。" >&2
  exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
  echo "未安装 systemctl；当前部署入口只支持 Ubuntu systemd 环境。" >&2
  exit 1
fi
if ! [[ "$HEALTH_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "健康检查超时时间必须是正整数：$HEALTH_TIMEOUT_SECONDS" >&2
  exit 1
fi

normalize_remote_url() {
  local url="$1"
  url="${url%/}"
  url="${url%.git}"
  printf '%s' "$url"
}

is_adcraft_github_remote() {
  case "$(normalize_remote_url "$1")" in
    https://github.com/fanxUP/adcraft-erp|\
    git@github.com:fanxUP/adcraft-erp|\
    ssh://git@github.com/fanxUP/adcraft-erp)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

ORIGIN_URL="$(git remote get-url "$REMOTE_NAME" 2>/dev/null || true)"
if [ -z "$ORIGIN_URL" ]; then
  git remote add "$REMOTE_NAME" "$REPO_URL"
  ORIGIN_URL="$REPO_URL"
fi
if ! is_adcraft_github_remote "$ORIGIN_URL"; then
  echo "远程 origin 不是 AdCraft GitHub 仓库：$ORIGIN_URL" >&2
  echo "请将 origin 指向 $REPO_URL 后再部署。" >&2
  exit 1
fi

TRACKED_CHANGES="$(git status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_CHANGES" ]; then
  echo "部署停止：工作区存在未提交的跟踪文件改动。" >&2
  echo "$TRACKED_CHANGES" >&2
  echo "请先提交这些代码，或恢复后再部署；脚本不会覆盖本地代码改动。" >&2
  exit 1
fi

has_native_runtime() {
  [ -x backend/.venv/bin/python ] \
    && systemctl cat "$SERVICE_NAME" >/dev/null 2>&1 \
    && systemctl is-active --quiet "$SERVICE_NAME"
}

has_compose_runtime() {
  command -v docker >/dev/null 2>&1 \
    && docker compose version >/dev/null 2>&1 \
    && systemctl is-active --quiet docker
}

case "$DEPLOY_MODE" in
  auto)
    if has_native_runtime; then
      DEPLOY_MODE="native"
    elif has_compose_runtime; then
      DEPLOY_MODE="compose"
    else
      echo "未检测到可用运行环境：请确保 $SERVICE_NAME 正在运行，或启动 Docker Compose。" >&2
      exit 1
    fi
    ;;
  native)
    if ! has_native_runtime; then
      echo "指定使用原生模式，但未检测到正在运行的 $SERVICE_NAME 服务。" >&2
      exit 1
    fi
    ;;
  compose)
    if ! has_compose_runtime; then
      echo "指定使用 Docker Compose，但 Docker 服务或 Compose 不可用。" >&2
      exit 1
    fi
    ;;
  *)
    echo "DEPLOY_MODE 只能是 auto、native 或 compose：$DEPLOY_MODE" >&2
    exit 1
    ;;
esac

echo "=== AdCraft ERP 部署 ==="
echo "代码源：$ORIGIN_URL"
echo "分支：$BRANCH"
echo "运行方式：$DEPLOY_MODE"
echo "正在从 GitHub 拉取代码..."
export GIT_TERMINAL_PROMPT=0
if ! git fetch --prune --no-tags "$REMOTE_NAME" \
  "refs/heads/$BRANCH:refs/remotes/$REMOTE_NAME/$BRANCH"; then
  echo "从 GitHub 拉取失败，部署已停止；不会使用旧代码继续运行。" >&2
  exit 1
fi

TARGET_COMMIT="$(git rev-parse "refs/remotes/$REMOTE_NAME/$BRANCH")"
if [ -n "$EXPECTED_COMMIT" ]; then
  RESOLVED_EXPECTED="$(git rev-parse "$EXPECTED_COMMIT^{commit}" 2>/dev/null || true)"
  if [ -z "$RESOLVED_EXPECTED" ] || [ "$TARGET_COMMIT" != "$RESOLVED_EXPECTED" ]; then
    echo "提交校验失败：GitHub 目标为 $TARGET_COMMIT，期望为 $EXPECTED_COMMIT。" >&2
    exit 1
  fi
fi

CURRENT_COMMIT="$(git rev-parse HEAD)"
# 只更新 Git 跟踪的程序代码；未跟踪的 .env、uploads、backups、logs 保留不动。
git reset --hard "$TARGET_COMMIT"

if [ ! -f .env ]; then
  echo "缺少 .env：请先执行 ./install-ubuntu.sh，或复制 config/env.example 后填写配置。" >&2
  exit 1
fi
wait_for_health() {
  local url="$1"
  local health_response

  for _ in $(seq 1 "$HEALTH_TIMEOUT_SECONDS"); do
    health_response="$(curl --fail --silent --show-error --max-time 5 "$url" 2>/dev/null || true)"
    if [[ "$health_response" == *'"database":"ok"'* ]]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

deploy_compose() {
  if [ ! -f "$COMPOSE_FILE" ]; then
    echo "缺少 Compose 配置：$PROJECT_DIR/$COMPOSE_FILE" >&2
    return 1
  fi

  mkdir -p uploads backups logs
  echo "检查 Compose 配置..."
  docker compose -f "$COMPOSE_FILE" config --quiet
  echo "构建并启动 Docker Compose 服务..."
  docker compose -f "$COMPOSE_FILE" up -d --build

  echo "等待应用和数据库健康检查..."
  if ! wait_for_health "$HEALTH_URL"; then
    echo "部署后健康检查失败：$HEALTH_URL" >&2
    docker compose -f "$COMPOSE_FILE" ps >&2 || true
    echo "请查看日志：docker compose logs --tail=100 backend nginx" >&2
    return 1
  fi
}

deploy_native() {
  local backend_changes frontend_changes nginx_changes

  if [ ! -x backend/.venv/bin/python ]; then
    echo "缺少生产 Python venv：$PROJECT_DIR/backend/.venv/bin/python" >&2
    return 1
  fi

  backend_changes="$(git diff --name-only "$CURRENT_COMMIT" "$TARGET_COMMIT" -- backend)"
  frontend_changes="$(git diff --name-only "$CURRENT_COMMIT" "$TARGET_COMMIT" -- frontend)"
  nginx_changes="$(git diff --name-only "$CURRENT_COMMIT" "$TARGET_COMMIT" -- nginx)"

  if [ -n "$backend_changes" ]; then
    if git diff --name-only "$CURRENT_COMMIT" "$TARGET_COMMIT" -- backend/pyproject.toml | grep -q . \
      && [ "${INSTALL_DEPENDENCIES:-0}" != "1" ]; then
      echo "检测到 Python 依赖变更；请在确认软件源可用后使用 INSTALL_DEPENDENCIES=1 重新部署。" >&2
      return 1
    fi
    if [ "${INSTALL_DEPENDENCIES:-0}" = "1" ]; then
      backend/.venv/bin/pip install --quiet --disable-pip-version-check --no-build-isolation -e backend
    fi
    backend/.venv/bin/python -c \
      'import alembic, asyncpg, fastapi, pydantic, sqlalchemy, uvicorn'
  fi

  if [ -n "$frontend_changes" ]; then
    if ! command -v npm >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
      echo "检测到前端变更，但服务器没有 Node.js/npm。" >&2
      return 1
    fi
    if [ "$(node -p 'Number(process.versions.node.split(".")[0])')" -lt 20 ]; then
      echo "Node.js 版本过低，需要 20+。" >&2
      return 1
    fi
    (
      cd frontend
      HUSKY=0 npm ci
      npm run build
    )
    chmod -R a+rX frontend/dist
  fi

  if [ -n "$nginx_changes" ]; then
    nginx -t
    systemctl reload nginx
  fi

  echo "重启原生服务：$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
  echo "等待应用和数据库健康检查..."
  if ! wait_for_health "$NATIVE_HEALTH_URL"; then
    echo "部署后健康检查失败：$NATIVE_HEALTH_URL" >&2
    systemctl status "$SERVICE_NAME" --no-pager --full >&2 || true
    journalctl -u "$SERVICE_NAME" -n 80 --no-pager >&2 || true
    return 1
  fi
}

if [ "$DEPLOY_MODE" = "native" ]; then
  deploy_native
else
  deploy_compose
fi

printf '%s\n' "$TARGET_COMMIT" > .deployed-commit
chmod 640 .deployed-commit

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "部署后检测到跟踪文件变化，已停止。" >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

echo "部署完成。"
echo "提交：$TARGET_COMMIT"
echo "访问地址：http://$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "数据请通过系统备份管理导入；本次部署未修改业务数据。"
