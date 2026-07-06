#!/bin/bash
# =============================================================================
# AdCraft ERP — 一键部署/升级脚本（在服务器上运行）
# 用法:
#   ./scripts/deploy.sh          # 从 GitHub 拉取最新代码并重新部署
#   ./scripts/deploy.sh --local  # 使用本地代码（在无 GitHub 访问时）
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================"
echo " AdCraft ERP — 部署/升级"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# ── 1. 更新代码 ──────────────────────────────────────────
if [ "$1" = "--local" ]; then
    echo "  → 跳过 git pull（使用本地代码）"
else
    echo "  → 拉取最新代码..."
    git pull origin "$(git rev-parse --abbrev-ref HEAD)" 2>/dev/null || {
        echo "  ⚠ GitHub 不可达，使用当前代码继续"
    }
fi

# ── 2. 检查变更 ──────────────────────────────────────────
BACKEND_CHANGED=$(git diff --name-only HEAD@{1} 2>/dev/null | grep -c '^backend/' || echo 0)
FRONTEND_CHANGED=$(git diff --name-only HEAD@{1} 2>/dev/null | grep -c '^frontend/' || echo 0)
DOCKERFILE_CHANGED=$(git diff --name-only HEAD@{1} 2>/dev/null | grep -c 'Dockerfile' || echo 0)

if [ "$BACKEND_CHANGED" -gt 0 ] || [ "$DOCKERFILE_CHANGED" -gt 0 ]; then
    echo "  → 后端代码有变更，将重新构建镜像"
    REBUILD_BACKEND="--build"
else
    REBUILD_BACKEND=""
fi

if [ "$FRONTEND_CHANGED" -gt 0 ] || [ "$DOCKERFILE_CHANGED" -gt 0 ]; then
    echo "  → 前端代码有变更，将重新构建镜像"
    REBUILD_FRONTEND="--build"
else
    REBUILD_FRONTEND=""
fi

# ── 3. 备份数据库 ────────────────────────────────────────
echo "  → 备份数据库..."
if [ -f scripts/backup.sh ]; then
    bash scripts/backup.sh 2>/dev/null || echo "  ⚠ 备份失败，继续部署"
fi

# ── 4. 重新部署 ──────────────────────────────────────────
echo "  → 重新构建并启动容器..."
sudo docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d $REBUILD_BACKEND $REBUILD_FRONTEND 2>&1

# ── 5. 运行数据库迁移 ────────────────────────────────────
echo "  → 执行数据库迁移..."
sleep 10  # 等待后端启动
sudo docker exec adcraft_backend alembic upgrade head 2>&1 || echo "  ⚠ 迁移可能已是最新"

# ── 6. 重启 nginx（刷新 DNS 缓存） ───────────────────────
echo "  → 重启 nginx..."
sudo docker restart adcraft_nginx 2>&1

# ── 7. 验证 ──────────────────────────────────────────────
echo ""
echo "============================================"
echo " 部署完成！"
echo ""
echo " 访问: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '192.168.0.51')"
echo " 账号: admin / admin123"
echo ""
echo " 容器状态:"
sudo docker ps --format "  {{.Names}}: {{.Status}}"
echo "============================================"
