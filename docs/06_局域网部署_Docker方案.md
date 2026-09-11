# 06. 局域网部署与 Docker 方案

## 1. 部署目标

系统部署在公司内部服务器，员工在同一局域网内通过浏览器访问。

访问方式示例：

```text
http://192.168.1.10
http://erp.local
```

## 2. 推荐服务器配置

最低配置：

```text
CPU：4 核
内存：16GB
硬盘：1TB SSD
系统：Ubuntu Server 22.04/24.04 或 Windows + Docker Desktop
```

推荐配置：

```text
CPU：8 核
内存：32GB
硬盘：1TB SSD + 2TB 备份盘
系统：Ubuntu Server
```

## 3. Docker 服务组成

```text
nginx       对外统一入口
frontend    Vue 前端
backend     FastAPI 后端
postgres    PostgreSQL 数据库
redis       缓存和任务队列
minio       文件存储
backup      定时备份服务
```

## 4. 目录结构

```text
adcraft-erp/
  docker-compose.yml
  .env
  frontend/
  backend/
  nginx/
  data/
    postgres/
    redis/
    minio/
  uploads/
  backups/
  logs/
```

## 5. 局域网 IP 固定

建议给服务器设置固定 IP，例如：

```text
192.168.1.10
```

路由器里可以给服务器做 DHCP 地址保留，避免重启后 IP 变化。

## 6. 局域网域名

可选方式：

1. 在每台电脑 hosts 文件中添加：

```text
192.168.1.10 erp.local
```

2. 在路由器/DNS 里配置本地域名。

## 7. Ubuntu 部署

支持 Ubuntu 22.04/24.04 等带 Docker/Compose 的 Ubuntu LTS。全新服务器执行：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
curl --fail --silent --show-error --location \
  https://raw.githubusercontent.com/fanxUP/adcraft-erp/master/install-ubuntu.sh \
  --output /tmp/adcraft-install-ubuntu.sh
sudo bash /tmp/adcraft-install-ubuntu.sh
```

安装脚本会从固定 GitHub 仓库克隆代码，创建 `.env`，安装 Docker/Compose，启动全部容器，并检查 `/health`。以后发布代码执行：

```bash
cd /opt/adcraft
sudo ./deploy.sh
```

部署只处理代码和容器，不自动备份、同步、恢复或删除业务数据。`.env`、数据库卷、`uploads`、`backups` 和 `logs` 会保留；历史数据由系统备份管理导入。

## 8. 数据备份策略

数据由系统内的备份管理功能负责。部署脚本只拉取代码和启动容器，不自动备份、同步、恢复或删除业务数据；数据库、上传文件、MinIO 数据和配置的保留方式以你的备份策略为准。

恢复新服务器时，先按本页完成代码和容器部署，再登录系统，通过备份管理导入历史数据。不要用部署脚本代替备份导入。

### 备份保留

建议：

```text
每日备份保留 14 天
每周备份保留 8 周
每月备份保留 12 个月
```

### 备份位置

- 服务器本地备份盘
- 局域网 NAS
- 外置硬盘，定期人工复制

## 9. 数据安全

- 系统管理员账号必须强密码。
- 财务和删除操作必须记录日志。
- 不建议直接暴露到公网。
- 如果未来需要外网访问，建议使用 VPN，不要直接端口映射。

## 10. 启动命令

开发完成后，在服务器执行：

```bash
docker compose up -d
```

查看服务：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f backend
```

## 11. 恢复策略

恢复通过系统内备份管理完成：

1. 在新 Ubuntu 服务器执行安装脚本并确认 `/health` 正常。
2. 登录系统，打开备份管理，选择需要恢复的备份并按页面提示导入。
3. 导入完成后检查订单、任务、附件和权限数据。

部署脚本不会自动导入备份，也不会执行删除 Docker 数据卷的操作。
