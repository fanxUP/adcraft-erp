#!/usr/bin/env bash
# AdCraft ERP — GitHub + Docker Compose 部署入口
#
# 这个脚本只负责发布应用代码和启动容器：
# - 代码唯一来源是固定的 GitHub 仓库；
# - .env、uploads、backups、logs 和 Docker 数据卷不加入 Git，也不由本脚本删除；
# - 数据恢复请使用系统内的备份管理功能；
# - 不执行 docker compose down -v、git clean 或自动 restore。
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
REPO_URL="https://github.com/fanxUP/adcraft-erp.git"
REMOTE_NAME="origin"
BRANCH="${DEPLOY_BRANCH:-master}"
EXPECTED_COMMIT=""
HEALTH_URL="${DEPLOY_HEALTH_URL:-http://127.0.0.1/health}"
HEALTH_TIMEOUT_SECONDS="${DEPLOY_HEALTH_TIMEOUT_SECONDS:-90}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

usage() {
  cat <<'EOF'
AdCraft ERP Ubuntu/Docker Compose 部署

首次部署（推荐）：
  sudo ./install-ubuntu.sh

已有项目更新：
  sudo ./deploy.sh
  sudo ./deploy.sh --branch master --commit <完整提交哈希>

脚本固定从以下 GitHub 仓库拉取代码：
  https://github.com/fanxUP/adcraft-erp.git

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
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "未安装 Docker Compose；请运行 ./install-ubuntu.sh。" >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "未安装 curl；请运行 ./install-ubuntu.sh。" >&2
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

echo "=== AdCraft ERP 部署 ==="
echo "代码源：$ORIGIN_URL"
echo "分支：$BRANCH"
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

# 只更新 Git 跟踪的程序代码；未跟踪的 .env、uploads、backups、logs 保留不动。
git reset --hard "$TARGET_COMMIT"

if [ ! -f .env ]; then
  echo "缺少 .env：请先执行 ./install-ubuntu.sh，或复制 config/env.example 后填写配置。" >&2
  exit 1
fi
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "缺少 Compose 配置：$PROJECT_DIR/$COMPOSE_FILE" >&2
  exit 1
fi

mkdir -p uploads backups logs

echo "检查 Compose 配置..."
docker compose -f "$COMPOSE_FILE" config --quiet

echo "构建并启动服务..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "等待应用和数据库健康检查..."
HEALTH_OK=0
for _ in $(seq 1 "$HEALTH_TIMEOUT_SECONDS"); do
  HEALTH_RESPONSE="$(curl --fail --silent --show-error --max-time 5 "$HEALTH_URL" 2>/dev/null || true)"
  if [[ "$HEALTH_RESPONSE" == *'"database":"ok"'* ]]; then
    HEALTH_OK=1
    break
  fi
  sleep 1
done

if [ "$HEALTH_OK" -ne 1 ]; then
  echo "部署后健康检查失败：$HEALTH_URL" >&2
  docker compose -f "$COMPOSE_FILE" ps >&2 || true
  echo "请查看日志：docker compose logs --tail=100 backend nginx" >&2
  exit 1
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
