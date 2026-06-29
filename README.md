# AdCraft ERP - 广告制作安装工程管理系统

局域网部署的广告行业业务管理系统，覆盖客户管理、报价、订单、设计、制作、安装、收款、对账和经营报表。

## 技术栈

- 前端：Vue 3 + Vite + TypeScript + Element Plus
- 后端：FastAPI + Python + SQLAlchemy + PostgreSQL
- 部署：Docker Compose + Nginx

## 快速启动

```bash
cp config/env.example .env
# 编辑 .env，修改 SECRET_KEY 和数据库密码
docker compose up -d
```

访问 http://localhost | 默认管理员：admin / admin123

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
