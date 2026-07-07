# AGENTS.md — AdCraft ERP 开发指南

## 本地开发环境启动

项目支持两种运行方式：本地开发（热重载）和 Docker 部署。开发阶段用本地方式，完成后部署到 Docker Desktop。

### 前置条件

| 依赖 | 版本 | 安装方式 |
|---|---|---|
| Python | >= 3.12 | `brew install python@3.12` |
| Node.js | >= 20 | `brew install node` |
| PostgreSQL | 16 | `brew install postgresql@16 && brew services start postgresql@16` |
| Redis | 7 | `brew install redis && brew services start redis` |
| psql | - | 随 PostgreSQL 安装 |

### 一键启动（首次）

```bash
# 1. 启动基础设施
brew services start postgresql@16
brew services start redis

# 2. 创建数据库（仅首次）
psql -U postgres -c "CREATE USER adcraft WITH PASSWORD 'adcraft_dev_password';"
psql -U postgres -c "CREATE DATABASE adcraft_erp OWNER adcraft;"

# 3. 后端
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --only-binary :all: -e ".[dev]"
# 如果 cryptography 安装失败，先单独装：pip install --only-binary :all: cryptography
alembic upgrade head
python scripts/init_app.py

# 4. 前端（新终端）
cd frontend
npm install
```

### 日常启动

```bash
# 终端 1 — 后端
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — 前端
cd frontend && node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5173
```

> **注意：** 使用 `node node_modules/vite/bin/vite.js` 而非 `npm run dev`，后者在含中文/空格的 iCloud 路径下可能无法正常启动。

### 访问地址

| 服务 | 地址 |
|---|---|
| 前端页面 | http://localhost:5173 |
| 后端 API | http://localhost:8000/api/v1 |
| API 文档 | http://localhost:8000/api/docs |
| 管理员登录 | admin / admin123 |

### pip 安装问题处理

如果 `pip install` 遇到 SSL 错误或 maturin/Rust 编译错误：

```bash
# 使用阿里云镜像 + 仅安装预编译 wheel
pip install -i https://mirrors.aliyun.com/pypi/simple/ \
  --trusted-host mirrors.aliyun.com \
  --only-binary :all: \
  -e ".[dev]"

# 如果 cryptography 仍然失败，先单独安装
pip install -i https://mirrors.aliyun.com/pypi/simple/ \
  --trusted-host mirrors.aliyun.com \
  --only-binary :all: cryptography

# 如果 bcrypt 需要 Rust 编译，固定到 4.0.1
pip install bcrypt==4.0.1
```

---

## Docker 部署（项目完成后）

```bash
# 停止本地服务后
docker compose -p adcraft up -d
# 访问 http://localhost
```

数据卷通过 `docker-compose.override.yml` 映射到 `~/.adcraft-data/`，避免 iCloud 文件损坏。

---

## 架构概览

```
backend/app/
├── api/          # 14 个路由模块，挂载在 /api/v1
├── services/     # 17 个业务服务
├── repositories/ # 13 个数据仓库（Repository Pattern）
├── models/       # 14 个 SQLAlchemy ORM 模型（UUID 主键）
├── schemas/      # 16 个 Pydantic 请求/响应模型
├── core/         # config / database / permissions / deps
└── ai/           # 可选 AI 模块（规则引擎兜底，默认关闭）

frontend/src/
├── views/        # 18 个业务视图
├── api/          # Axios 封装 + JWT 拦截器
├── stores/       # Pinia（auth + app 主题）
├── router/       # 路由守卫 + 角色权限
├── layouts/      # 3 种布局（Default / Blank / Mobile）
└── styles/       # 9 套主题（5 暗色 + 4 亮色）
```

### 权限系统

- 6 个预置角色：admin / sales / designer / production / installer / finance
- 72 个权限码，格式 `resource:action`（如 `customer:read`, `order:delete`）
- RBAC 依赖：`require_role("admin")` / `require_permission("customer:read")`

### 数据库

- PostgreSQL 16，UUID 主键，`TimestampMixin` + `SoftDeleteMixin`
- 迁移：`alembic upgrade head`
- 种子：`python scripts/init_app.py`（幂等，可重复运行）

---

## ⚠️ 部署 & 迁移安全须知

> **禁止直接运行** `docker compose run --rm backend <命令>`
>
> 这会触发 `depends_on` 链，**自动重建所有依赖容器（包括 PostgreSQL）**，
> 如果数据卷配置不当会导致**数据全部丢失**。

**安全做法：**

```bash
# ✅ 应用数据库迁移（在已有容器内安全执行）
docker compose exec -T backend sh -c 'cd /app && alembic upgrade head'

# ✅ 构建镜像（不触动数据库）
docker compose build backend

# ✅ 重启服务
docker compose up -d
```

### 持久卷配置（跨平台）

`docker-compose.override.yml` 中的 volumes **禁止使用硬编码绝对路径**
（如 `/Users/xxx/.adcraft-data/`），应使用 **Docker 命名卷**：

```yaml
services:
  postgres:
    volumes:
      - adcraft_data_postgres:/var/lib/postgresql/data

volumes:
  adcraft_data_postgres:
```

命名卷由 Docker 统一管理存储位置，跨 macOS / Linux / Windows 兼容。

### 数据备份

系统每日凌晨 02:00 自动备份到 `backups/` 目录。手动恢复方式：

```bash
docker exec -i adcraft_postgres psql -U adcraft -d adcraft_erp < backups/backup_xxx.sql
```
