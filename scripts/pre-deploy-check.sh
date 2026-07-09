#!/bin/bash
# =============================================================================
# 部署前检查脚本 — 在推送/构建前运行，确保不会在服务器上踩坑
# 用法: ./scripts/pre-deploy-check.sh
# =============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $desc"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗${NC} $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "============================================"
echo " AdCraft ERP — 部署前检查"
echo "============================================"
echo ""

# ── 1. 迁移检查 ──────────────────────────────────────────
echo -e "${YELLOW}[1/4] 数据库迁移检查${NC}"

cd "$(dirname "$0")/../backend"

# 检查是否有未提交的模型变更（通过比较模型和最新迁移）
if [ -f "alembic.ini" ]; then
    if source .venv/bin/activate 2>/dev/null; then
        check "alembic 可以运行" alembic current 2>&1
        # 检查是否有未迁移的变更
        MIGRATION_CHECK=$(alembic check 2>&1 || true)
        if echo "$MIGRATION_CHECK" | grep -q "No new upgrade operations detected"; then
            echo -e "  ${GREEN}✓${NC} 数据库模型与迁移一致"
            PASS=$((PASS + 1))
        elif echo "$MIGRATION_CHECK" | grep -q "New upgrade operations detected"; then
            echo -e "  ${RED}✗${NC} 存在未迁移的模型变更！请运行: alembic revision --autogenerate"
            FAIL=$((FAIL + 1))
        else
            echo -e "  ${YELLOW}⚠${NC} 无法检查迁移（可能数据库未连接），请确保已提交所有迁移文件"
        fi
        deactivate 2>/dev/null || true
    else
        echo -e "  ${YELLOW}⚠${NC} 虚拟环境未激活，跳过迁移检查"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} 未找到 alembic.ini，跳过"
fi

# ── 2. 前端类型检查 ──────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/4] 前端构建检查${NC}"

cd "$(dirname "$0")/../frontend"
check "npm 依赖已安装" test -d node_modules
if [ -d node_modules ]; then
    check "Vite 可以构建" npx vite build
fi

# ── 3. Git 状态检查 ──────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/4] Git 状态检查${NC}"

cd "$(dirname "$0")/.."
check "工作区干净（无未提交的改动）" git diff --quiet
check "暂存区干净" git diff --cached --quiet

# ── 4. 关键文件检查 ──────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/4] 关键文件完整性${NC}"

check "docker-compose.yml 存在" test -f docker-compose.yml
check ".env.example 存在" test -f .env.example
check "nginx/default.conf 存在" test -f nginx/default.conf
check "backend/Dockerfile 存在" test -f backend/Dockerfile
check "frontend/Dockerfile 存在" test -f frontend/Dockerfile

# ── 结果 ──────────────────────────────────────────────────
echo ""
echo "============================================"
if [ $FAIL -eq 0 ]; then
    echo -e " ${GREEN}全部通过！${NC} 可以安全部署 ($PASS 项检查)"
else
    echo -e " ${RED}$FAIL 项失败${NC} / ${GREEN}$PASS 项通过${NC}"
    echo ""
    echo "修复步骤:"
    echo "  1. 模型有变更? → backend/ 下运行: alembic revision --autogenerate -m '描述'"
    echo "  2. 前端有改动? → frontend/ 下运行: npm run build 确认能通过"
    echo "  3. 提交所有改动: git add . && git commit"
fi
echo "============================================"

exit $FAIL
