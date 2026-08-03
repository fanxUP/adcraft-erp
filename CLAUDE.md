# CLAUDE.md — AdCraft ERP 开发指南

## 项目位置

项目部署在 Proxmox LXC 容器 102 上。

| 项目 | 地址 |
|---|---|
| 前端页面 | http://192.168.0.102/ |
| 后端 API | http://192.168.0.102:8000/api/v1 |
| API 文档 | http://192.168.0.102:8000/api/docs |
| 代码目录 | /opt/adcraft |
| Git 远程 | https://github.com/fanxUP/adcraft-erp.git |

## 登录

- 管理员: admin（密码不写入代码库，见 AGENTS.md / README，首次登录后请立即修改）

## 日常开发

通过容器 SSH 进入:
```
ssh root@192.168.0.102
cd /opt/adcraft
```

### 修改代码后部署
```
cd /opt/adcraft/frontend && npx vite build && chmod -R o+rX dist/
systemctl restart adcraft-backend
```
或一键部署: /opt/adcraft/deploy.sh

### 代码同步
```
git add . && git commit -m "说明" && git push origin master
git pull origin master
```

## 服务管理
- `systemctl restart adcraft-backend` — 重启后端
- `systemctl status adcraft-backend` — 查看状态
- `journalctl -u adcraft-backend -n 30` — 查看日志
- `tail -20 /var/log/nginx/error.log` — 查看 nginx 错误日志

## 数据库
- PostgreSQL 16, 127.0.0.1:5432, 用户 adcraft / 密码见 /opt/adcraft/.env
- 数据库: adcraft_erp
- 迁移: `cd /opt/adcraft/backend && PYTHONPATH=. .venv/bin/alembic upgrade head`

## 架构
```
/opt/adcraft/
├── backend/       FastAPI 后端
│   ├── app/api/   路由模块
│   └── app/services/ 业务服务
├── frontend/      Vue 3 前端
│   ├── src/       源代码
│   └── dist/      构建产物 (nginx 托管)
└── deploy.sh      一键部署脚本
```

## 注意事项
- 前端 build 后必须 `chmod -R o+rX dist/`，否则 nginx 403
- git pull/push 走 HTTPS (Tailscale 拦截 SSH)
- 凭据一律放在 /opt/adcraft/.env（本地、不入库），不得写入任何源码/文档/提交
