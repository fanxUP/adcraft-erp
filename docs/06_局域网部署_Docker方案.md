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

## 7. 数据备份策略

### 自动备份

每天凌晨 2 点自动备份：

- PostgreSQL 数据库
- 上传文件目录
- MinIO 数据
- 系统配置

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

## 8. 数据安全

- 系统管理员账号必须强密码。
- 财务和删除操作必须记录日志。
- 不建议直接暴露到公网。
- 如果未来需要外网访问，建议使用 VPN，不要直接端口映射。

## 9. 启动命令

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

## 10. 恢复策略

必须提供恢复脚本：

```bash
./scripts/restore.sh backups/backup_2026_06_29.tar.gz
```

恢复前必须：

- 停止服务。
- 备份当前数据。
- 管理员确认。
- 恢复后执行数据一致性检查。
