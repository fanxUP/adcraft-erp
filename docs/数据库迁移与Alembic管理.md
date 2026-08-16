# 数据库迁移与 Alembic 管理

> 适用范围：AdCraft ERP 后端（`backend/alembic`）
> 最后更新：2026-08-16

## 1. 当前状态（健康）

- 迁移脚本目录：`backend/alembic/versions/`
- 数据库：PostgreSQL 16，库名 `adcraft_erp`
- **当前 head：`f1a2b3c4d5e6`（单 head）**
- 数据库 `alembic_version` 已对齐该 head，无分叉、无待应用迁移。

历史上出现过并行开发分支，但均已通过两个 mergepoint 合并回单链：

```
... 车辆/高空分支 ─┐
                   ├→ 83cd02c2a988 (mergepoint: merge_cdr_quote_and_other_heads)
... CDR 报价分支 ───┘
... 外协分支 ───────┐
                   ├→ 8309d8ebb025 (mergepoint: merge heads)
... 项目成本分支 ───┘
```

## 2. 判断是否分叉：必须用官方命令

**不要手写正则去解析 `revision`/`down_revision`**——合并点的
`down_revision` 是元组（多父节点），手写解析会误判出「假 head」。

正确做法（只读，安全）：

```bash
cd /opt/adcraft/backend
source /opt/adcraft/.env
export DATABASE_URL_SYNC="postgresql+psycopg2://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp"

.venv/bin/alembic heads      # 列出所有 head（应为 1 个）
.venv/bin/alembic current    # 当前 DB 所在版本
.venv/bin/alembic history    # 线性化历史（含 branchpoint/mergepoint 标注）
```

程序化判断（脚本内使用）：

```python
from alembic.config import Config
from alembic.script import ScriptDirectory

cfg = Config("alembic.ini")
cfg.set_main_option("script_location", "alembic")
sd = ScriptDirectory.from_config(cfg)
print(sd.get_heads())   # 权威 head 列表
```

## 3. 日常新增迁移规范

1. 基于**当前唯一 head** 派生：`down_revision = "<当前 head>"`。
2. 一条迁移只做一件事（一个建表 / 一次改列 / 一组索引）。
3. `CREATE INDEX` 等 DDL 一律写 **`IF NOT EXISTS`**（幂等），避免"已在线执行过"导致重复执行报错。
4. 提交前本地跑 `alembic heads` 确认没有多出一个 head。

## 4. 多 head 出现时的安全合并预案

> 仅当 `alembic heads` 真的返回多个 head 时才需要。**前提：数据库 schema 已包含所有分支的变更**（本项目常态如此）。

### 第 1 步 — 确认现状（只读）

```bash
cd /opt/adcraft/backend && source /opt/adcraft/.env
export DATABASE_URL_SYNC="postgresql+psycopg2://adcraft:adcraft_prod@127.0.0.1:5432/adcraft_erp"
.venv/bin/alembic heads
.venv/bin/alembic history -r head:current
```

### 第 2 步 — 全量备份（关键，不可跳过）

```bash
sudo -u postgres pg_dump adcraft_erp > /opt/adcraft/backups/pre_merge_$(date +%F_%H%M).sql
```

### 第 3 步 — 生成 merge 迁移（不改任何已有迁移 SQL）

```bash
.venv/bin/alembic merge -m "merge heads <说明>" <head1> <head2> ...
```

`merge` 只新增一个「合并点」迁移文件，`down_revision` 为多个 head 的元组，
**不会重跑、不改动任何历史迁移**。

### 第 4 步 — 关键：用 `stamp`，不要用 `upgrade`

```bash
.venv/bin/alembic stamp <merge_revision>
```

`stamp` 只把 `alembic_version` 标记到合并点，**不执行任何 SQL**，
避免重复建表/改列报错。

### 第 5 步 — 复核

```bash
.venv/bin/alembic heads     # 应只剩 1 个 head
.venv/bin/alembic current   # 应停在 merge 点上
systemctl restart adcraft-backend
curl -s http://127.0.0.1:8000/api/v1/health   # 期望 {"status":"ok","database":"ok"}
```

## 5. 注意事项

- **先备份、先 `stamp`、后复核**，三者缺一不可。
- 若怀疑「某个分支的变更其实没落到数据库 schema」——例如该分支是他人新增、本机从未跑过——则**不要 `stamp`**，应改为在**测试库**上验证 `upgrade` 结果后再决定。
- 后端每次启动（`entrypoint.py`）会自动执行 `alembic upgrade head` 并吞掉异常为非致命告警；因此迁移错误**不会阻止服务启动，但会反复刷告警**，需关注 `journalctl -u adcraft-backend` 中的 `Migration warning`。
