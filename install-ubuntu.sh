#!/usr/bin/env bash
# AdCraft ERP — 全新 Ubuntu 服务器安装入口
#
# 作用：安装 Docker/Compose、从固定 GitHub 仓库克隆代码、生成 .env 的必要密钥，
# 然后调用根目录 deploy.sh 启动系统。数据库和业务文件由用户自行通过系统备份管理恢复。
set -Eeuo pipefail

REPO_URL="https://github.com/fanxUP/adcraft-erp.git"
PROJECT_DIR="${PROJECT_DIR:-/opt/adcraft}"
BRANCH="${DEPLOY_BRANCH:-master}"

usage() {
  cat <<'EOF'
AdCraft ERP 全新 Ubuntu 安装

用法：
  sudo ./install-ubuntu.sh
  sudo ./install-ubuntu.sh --project-dir /opt/adcraft --branch master

脚本会：
  1. 安装 git、curl、Docker Engine 和 Docker Compose；
  2. 从 https://github.com/fanxUP/adcraft-erp.git 拉取指定分支；
  3. 创建 .env（不会覆盖已有 .env）；
  4. 构建并启动 Docker Compose 服务；
  5. 用 /health 验证应用和数据库可用。

脚本不会导入、删除或覆盖业务数据库、上传文件和备份文件。
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
  echo "请使用 sudo 运行安装脚本。" >&2
  exit 1
fi
if [ ! -r /etc/os-release ]; then
  echo "无法识别操作系统；此入口只支持 Ubuntu。" >&2
  exit 1
fi
# shellcheck disable=SC1091
source /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then
  echo "当前系统不是 Ubuntu（检测到：${ID:-unknown}）。" >&2
  exit 1
fi
if [[ ! "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "分支名称包含非法字符：$BRANCH" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
echo "安装 Ubuntu 基础依赖..."
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git

install_official_docker() {
  local architecture codename
  architecture="$(dpkg --print-architecture)"
  codename="${VERSION_CODENAME:-}"
  if [ -z "$codename" ]; then
    echo "无法确定 Ubuntu 版本代号，不能添加 Docker 官方软件源。" >&2
    exit 1
  fi
  apt-get install -y --no-install-recommends ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl --fail --silent --show-error --location \
    https://download.docker.com/linux/ubuntu/gpg \
    --output /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$architecture" "$codename" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

if ! command -v docker >/dev/null 2>&1; then
  echo "安装 Docker..."
  if apt-cache show docker.io >/dev/null 2>&1 \
    && apt-cache show docker-compose-v2 >/dev/null 2>&1; then
    apt-get install -y docker.io docker-compose-v2
  else
    install_official_docker
  fi
elif ! docker compose version >/dev/null 2>&1; then
  echo "Docker 已存在，但缺少 Compose 插件，正在补齐..."
  if apt-cache show docker-compose-v2 >/dev/null 2>&1; then
    apt-get install -y docker-compose-v2
  else
    install_official_docker
  fi
fi

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose 安装失败。" >&2
  exit 1
fi
systemctl enable --now docker

if [ -e "$PROJECT_DIR" ] && [ ! -d "$PROJECT_DIR/.git" ]; then
  if [ -n "$(find "$PROJECT_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)" ]; then
    echo "目标目录已存在且不是空目录：$PROJECT_DIR" >&2
    echo "为避免覆盖文件，请清空目录或换一个 --project-dir。" >&2
    exit 1
  fi
fi

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "从 GitHub 克隆项目：$REPO_URL"
  mkdir -p "$(dirname -- "$PROJECT_DIR")"
  git clone --origin origin --branch "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
else
  cd "$PROJECT_DIR"
  ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
  case "${ORIGIN_URL%/}" in
    https://github.com/fanxUP/adcraft-erp|https://github.com/fanxUP/adcraft-erp.git|\
    git@github.com:fanxUP/adcraft-erp|git@github.com:fanxUP/adcraft-erp.git|\
    ssh://git@github.com/fanxUP/adcraft-erp|ssh://git@github.com/fanxUP/adcraft-erp.git)
      ;;
    "")
      git remote add origin "$REPO_URL"
      ;;
    *)
      echo "已有项目的 origin 不是 AdCraft GitHub 仓库：$ORIGIN_URL" >&2
      exit 1
      ;;
  esac
fi

cd "$PROJECT_DIR"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "项目工作区存在未提交的跟踪文件改动，停止以避免覆盖。" >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp config/env.example "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "已创建 .env；正在生成本机密钥。"
fi

random_hex() {
  od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]'
}

set_env_if_empty() {
  local key="$1"
  local value="$2"
  local current
  current="$(awk -F= -v wanted="$key" '$1 == wanted { print substr($0, index($0, "=") + 1); exit }' "$ENV_FILE")"
  if [ -n "$current" ]; then
    return 0
  fi
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s#^${key}=.*#${key}=${value}#" "$ENV_FILE"
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

set_env_if_empty SECRET_KEY "$(random_hex)"
set_env_if_empty POSTGRES_PASSWORD "$(random_hex)"
set_env_if_empty MINIO_ROOT_PASSWORD "$(random_hex)"
chmod 600 "$ENV_FILE"

mkdir -p uploads backups logs
chmod 750 uploads backups logs

echo "开始启动 AdCraft ERP..."
PROJECT_DIR="$PROJECT_DIR" DEPLOY_BRANCH="$BRANCH" \
  "$PROJECT_DIR/deploy.sh"

echo
echo "安装完成。"
echo "项目目录：$PROJECT_DIR"
echo "如需恢复历史数据，请登录系统后使用备份管理导入；本脚本没有自动恢复数据。"
if ! grep -q '^ADMIN_INIT_PASSWORD=.' "$ENV_FILE"; then
  echo "当前 .env 未设置 ADMIN_INIT_PASSWORD；如果没有导入历史数据，请手动设置后重启容器。"
fi
