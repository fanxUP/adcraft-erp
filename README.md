# AdCraft ERP - 广告制作安装工程管理系统

局域网部署的广告行业业务管理系统，覆盖客户管理、直接创建订单、设计、制作、安装、外协、收支、人事和经营报表。旧报价链接仅保留到订单的兼容跳转。

## 技术栈

- 前端：Vue 3 + Vite + TypeScript + Element Plus
- 后端：FastAPI + Python + SQLAlchemy + PostgreSQL
- 部署：systemd + Nginx（现有服务器），或 Docker Compose + Nginx（新装）

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

后续发布只需执行（脚本会自动识别原生服务或 Docker Compose）：

```bash
cd /opt/adcraft
sudo ./deploy.sh
```

部署脚本只从 `https://github.com/fanxUP/adcraft-erp.git` 拉取代码。已有 `adcraft-backend` 原生服务时，脚本复用 systemd/Nginx 并按变更需要构建前端；全新 Ubuntu 安装 Docker 后，脚本使用 Docker Compose 构建、启动和健康检查。它不会自动备份、同步、恢复或删除数据库、Docker 数据卷、上传文件和备份文件。历史数据请在系统内使用备份管理导入；生产 `.env` 也会保留，不会被更新代码覆盖。

## 前端开发

```bash
cd frontend && npm install && npm run dev
```

## 后端开发

```bash
cd backend
python -m pip install --require-hashes -r requirements-bootstrap.txt
python -m pip install --require-hashes -r requirements-dev.txt
python -m pip install --no-deps -e .
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/api/docs

## 附件及恢复

上传文件由后端按所属业务授权读取，禁止在 Nginx 中直接公开 `uploads` 目录。原生发布会通过 `scripts/private_uploads_nginx.py` 替换现有上传别名，配置备份存放在 `/var/backups/adcraft-nginx/`；配置校验失败会恢复原文。历史文件不能确认归属时由系统管理员核对，不依据聊天中粘贴的 URL 授权。

`scripts/backup.sh` 生成独立数据库归档、附件归档及校验文件。数据库沿用 `scripts/restore.sh` 的受控恢复；附件使用 `python3 scripts/uploads_backup.py verify <附件归档>` 校验，使用 `restore <附件归档> --destination <空的隔离目录>` 演练恢复，不覆盖现用目录。备份文件包含业务资料，应限制访问。

配置 `RCLONE_REMOTE` 并安装配置 rclone 后，备份作业会复制并校验异地副本，不镜像删除远端历史；未配置时会明确提示跳过。异地保留期由远端生命周期管理。当前服务器定时器在 UTC 03:07（北京时间 11:07）运行；Docker 定时任务按容器时区 02:00 运行。

Python 运行和开发依赖分别锁在 `backend/requirements.txt`、`backend/requirements-dev.txt`（含哈希），安装工具锁在 `backend/requirements-bootstrap.txt`。依赖变更的原生发布需使用 `INSTALL_DEPENDENCIES=1`，先在副本升级验证并保存原环境，认证继续使用 HS256，既有 token 兼容。独立 Windows 启动入口必须显式提供数据库配置。

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
