# AdCraft ERP - 广告制作安装工程管理系统

局域网部署的广告行业业务管理系统，覆盖客户管理、报价、订单、设计、制作、安装、收款、对账和经营报表。

## 技术栈

- 前端：Vue 3 + Vite + TypeScript + Element Plus
- 后端：FastAPI + Python + SQLAlchemy + PostgreSQL
- 部署：Docker Compose + Nginx

## 快速启动

```bash
cp config/env.example .env
# 编辑 .env，设置 SECRET_KEY、ADMIN_INIT_PASSWORD、数据库密码和 MinIO 密码
docker compose up -d
```

访问 http://localhost。首次启动是否创建管理员由 `.env` 中显式设置的 `ADMIN_INIT_PASSWORD` 决定，项目不提供默认管理员密码。

## Ubuntu 一键部署

全新 Ubuntu 服务器建议直接使用仓库根目录的安装脚本。它会安装 Docker/Compose、从固定 GitHub 仓库拉取代码、生成必要的本机密钥并启动系统：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
curl --fail --silent --show-error --location \
  https://raw.githubusercontent.com/fanxUP/adcraft-erp/master/install-ubuntu.sh \
  --output /tmp/adcraft-install-ubuntu.sh
sudo bash /tmp/adcraft-install-ubuntu.sh
```

也可以先克隆代码，再执行：

```bash
git clone https://github.com/fanxUP/adcraft-erp.git /opt/adcraft
cd /opt/adcraft
sudo ./install-ubuntu.sh
```

后续发布只需执行：

```bash
cd /opt/adcraft
sudo ./deploy.sh
```

部署脚本只从 `https://github.com/fanxUP/adcraft-erp.git` 拉取代码，然后执行 Docker Compose 构建、启动和健康检查。它不会自动备份、同步、恢复或删除数据库、Docker 数据卷、上传文件和备份文件。历史数据请在系统内使用备份管理导入；生产 `.env` 也会保留，不会被更新代码覆盖。

## 前端开发

```bash
cd frontend && npm install && npm run dev
```

## 后端开发

```bash
cd backend && pip install -e ".[dev]" && alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

## 项目结构

```
├── backend/app/{models,schemas,routers,services,repositories,utils}
├── frontend/src/{api,views,components,stores,router,layouts}
├── docs/          # 产品文档
├── schema/        # SQL Schema
├── nginx/         # Nginx 配置
└── docker-compose.yml
```

完整规划文档见 docs/ 目录。
