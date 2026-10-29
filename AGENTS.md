# AGENTS.md — AdCraft ERP 开发指南

## 本地开发环境启动

项目支持两种运行方式：本地开发（热重载）和 Docker 部署。开发阶段用本地方式，完成后部署到 Docker Desktop。

### 前置条件

| 依赖 | 版本 | 安装方式 |
|---|---|---|
| Python | 3.12.x | `brew install python@3.12` |
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
# 使用本地密码管理器生成并填入唯一密码，不要把密码写入仓库或命令历史。
psql -U postgres -c "CREATE USER adcraft WITH PASSWORD '<set-a-local-password>';"
psql -U postgres -c "CREATE DATABASE adcraft_erp OWNER adcraft;"

# 3. 后端
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements-dev.txt
pip install --no-deps -e .
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
| 管理员登录 | admin / 由 `ADMIN_INIT_PASSWORD` 设置的密码（不会提供默认密码） |

### pip 安装问题处理

优先修复 Python 3.12 环境、证书或可信镜像配置，然后按锁文件重装。不要单独降级认证库，也不要修改哈希来绕过安装失败。可使用 `pip install --require-hashes --only-binary :all: -r requirements-dev.txt` 验证平台 wheel。

---

## Docker 部署（项目完成后）

```bash
# 停止本地服务后
docker compose -p adcraft up -d
# 访问 http://localhost
```

PostgreSQL、Redis 和 MinIO 使用 Docker 命名卷，避免云盘文件损坏。现有 192.168.0.102 服务器使用原生 systemd/Nginx，发布走 `deploy.sh`，不要为了更新应用切换数据库运行方式。

---

## 架构概览

```
backend/app/
├── api/          # 业务路由，挂载在 /api/v1
├── services/     # 业务服务与业务规则
├── repositories/ # 数据仓库（Repository Pattern）
├── models/       # SQLAlchemy ORM 模型（UUID 主键）
├── schemas/      # Pydantic 请求/响应模型
├── core/         # config / database / permissions / deps
└── ai/           # 可选 AI 模块（规则引擎兜底，默认关闭）

frontend/src/
├── views/        # 业务视图
├── api/          # Axios 封装 + JWT 拦截器
├── stores/       # Pinia（auth + app 主题）
├── router/       # 路由守卫 + 角色权限
├── layouts/      # 3 种布局（Default / Blank / Mobile）
└── styles/       # 9 套主题（5 暗色 + 4 亮色）
```

### 权限系统

- 6 个预置角色：admin / sales / designer / production / installer / finance
- 权限目录以 `backend/app/core/permission_catalog.py` 和初始化脚本为准，格式 `resource:action`（如 `customer:read`, `order:delete`）
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
docker compose up -d --no-deps backend frontend nginx
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

现有服务器的 systemd 定时器在 UTC 03:07（北京时间 11:07）备份到 `backups/`；Docker 定时器按容器时区 02:00 运行。数据库和附件各自归档并校验；异地同步须显式配置 `RCLONE_REMOTE` 和 rclone。数据库恢复必须通过带有文件名、路径和归档成员校验的恢复脚本：

```bash
./scripts/restore.sh backup_YYYYMMDD_HHMMSS.tar.gz
```

## ⚠️ 数据安全 — 常见事故与预防

### 事故案例：容器重建导致数据丢失

**根因：** 以下命令会触发 PostgreSQL 容器重建，若 volume 配置不当，数据将永久丢失：

```bash
# ❌ 危险！会重建 postgres 容器，可能导致数据丢失
docker compose -p adcraft run --rm backend <command>
docker compose -p adcraft up -d          # 当容器名冲突时重建
docker compose -p adcraft up -d --force-recreate
```

**预防措施：**

| 措施 | 说明 |
|---|---|
| **使用命名卷** | 禁止 `./data/postgres:/var/lib/postgresql/data` 这种 bind mount，改用 `adcraft_data_postgres:/var/lib/postgresql/data` |
| **单独部署服务** | 更新单服务用 `docker compose build <service> && docker rm -f <container> && docker compose up -d <service>` |
| **先备份再操作** | 任何涉及 postgres 重建的操作前，先 `pg_dump` 备份 |
| **容器名冲突处理** | `docker rm -f <旧容器> && docker compose up -d <服务>`，不要用 `up -d` 全覆盖重建 |
| **区分项目名** | 始终使用相同的 `-p` 参数或默认项目名，避免网络隔离、数据卷孤立 |

### 命名卷 vs 宿主机目录

| 存储方式 | 优缺点 |
|---|---|
| **Docker 命名卷**（推荐） | 由 Docker 管理存储位置，跨平台兼容，容器删除不丢失数据 |
| **宿主机 bind mount**（不推荐） | 路径硬编码不可移植，iCloud 等云盘可能自动清除文件 |

### 日常健康检查

```bash
# 检查数据库是否有数据
docker exec adcraft_postgres psql -U adcraft -d adcraft_erp -c "SELECT count(*) FROM quotes;"

# 查看备份文件
ls -la backups/

# 检查所有容器状态
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### 紧急恢复数据

```bash
# 恢复前先停止后端服务，脚本会校验文件名、路径和压缩包内唯一 SQL 成员
./scripts/restore.sh backup_YYYYMMDD_HHMMSS.tar.gz
```

## 当前依赖、附件及验证约定

Python 使用 3.12.x，先按哈希安装 `backend/requirements-bootstrap.txt` 中的安装工具，再分别安装开发锁 `backend/requirements-dev.txt` 或运行锁 `backend/requirements.txt`，最后 `pip install --no-deps -e backend`。不要临时降级 bcrypt 或绕过锁文件。新密码至少 6 位且不超过 72 个 UTF-8 字节，旧超限密码通过受控重设处理，不静默截断。

附件目录必须通过后端授权读取；Nginx 不得配置公开 alias。附件恢复先执行 `scripts/uploads_backup.py verify`，再恢复到空隔离目录核对，不覆盖现用文件。

数据库 CI 必须设置四个专用测试 URL，使用随机 schema，`CI_REQUIRE_DATABASE_TESTS=1` 禁止静默跳过；空库迁移也必须完成。审计报告和整改记录在 `docs/project-audit-2026-10-29/`。
