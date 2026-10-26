# 执行证据与复跑方式

对应 [REPORT.md](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/REPORT.md)。检查基准为 `bd54aededd626b28db76222ffa7a31109fb79e89`，修复后的代码是本地工作区版本；本次没有生成发布提交。

## 自动化检查

| 执行内容 | 证据 | 结果 |
|---|---|---|
| 后端全量，含显式启用的 PostgreSQL 测试 | [JUnit](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/backend-final.xml)、[输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/backend-final.txt) | 以最终 XML 的 tests/failures/errors/skipped 为准，全部通过 |
| 前端全量 | [JUnit](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/frontend-final.xml) | 222 通过 |
| 类型及生产构建 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/frontend-final-build.txt) | 通过，首屏 159.38 KiB gzip |
| 前端 Lint | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/frontend-final-lint.txt) | 通过 |
| AI 页面契约 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/frontend-final-contract.txt) | 通过；实际 DOM 可达性仍有 R13 待办 |
| 部署脚本回归 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/deploy-script-tests.txt) | 通过 |
| Compose 解析 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/compose-config.txt) | 临时项目目录、示例配置和源目录链接；通过，无容器操作 |
| 全新库迁移 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/migration-fresh.txt) | 失败，`employees` 缺失；证据保留，不标为通过 |
| npm 官方安全审计 | [JSON](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/frontend-dependencies-official.json) | 0 已知漏洞；默认镜像不支持审计接口，已使用官方 registry |
| 服务器 Python 安装清单审计 | [JSON](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/production-dependencies.json) | 6 包、8 个不同公告 ID；安装清单为只读采集 |

首轮后端测试的唯一失败来自备份测试受 `DATABASE_URL_SYNC` 污染。修复后使用相同隔离库环境变量执行完整回归。聊天、通知、报价分组和旧字段问题均先有失败复现，再有通过结果。

## 引用、接口与业务复现

| 内容 | 证据 |
|---|---|
| 前端引用及无入口候选 | [frontend-references.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/frontend-references.json) |
| 后端入口引用与重复定义 | [backend-references.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/backend-references.json) |
| 618 路由、认证依赖、遮挡检查 | [routes.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/routes.json)；修复前另有 `routes-before.json` |
| 519 处可解析的 API 调用 | [api-contracts.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/api-contracts.json) |
| 无效 ORM 模型字段访问 | [修复前](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/model-contracts-before.json)、[修复后](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/model-contracts.json) |
| 报表日期、月界、优惠转单与并发编号 | [isolated-reproductions.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/isolated-reproductions.json) |
| 附件公开读取、聊天成员检查边界 | [security-reproductions.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/security-reproductions.json)；仅本地无害文件和 Mock 仓库 |
| 后端静态提示完整清单 | [backend-static-final.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/backend-static-final.json) |
| CDR 默认地址与服务器入口 | [cdr-endpoint.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/cdr-endpoint.json) |
| 密码策略与 bcrypt 字节边界 | [password-policy.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/password-policy.json)；仅使用合成输入 |

## 生产只读证据

| 内容 | 证据与限制 |
|---|---|
| 业务读取 | [116 个请求](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/production-read-smoke.json)；独立 ASGI 进程，DB `default_transaction_read_only=on`，复用服务器依赖；3 个指定占位 ID 的路径验证空结果/参数契约 |
| 关系及金额一致性 | [检查 SQL 与汇总](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/production-integrity.json)；每项 SQL 在只读事务执行并回滚 |
| 成本归属、订单成本和利润 | [汇总](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/production-cost-audit.json)；使用项目既有 `ProjectCostAuditService` |
| 模型表/字段存在性 | [schema-audit.json](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/schema-audit.json)；无缺表缺字段，未断言约束/类型完全一致 |
| 实际 HTTP 与附件 Nginx 配置 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/production-http-security.txt) |
| 备份归档格式 | [输出](/Users/estefan-macworkstation/Downloads/ERP/docs/project-audit-2026-10-26/evidence/production-backup-validation.txt)；没有执行恢复 |
| 付款日期差异及历史重复关联 | `production-date-basis.txt`、`task-link-review.txt` 的汇总；详细记录存于下述本地日志目录 |

详细生产财务行保存在 [本地证据目录](/Users/estefan-macworkstation/Downloads/ERP/logs/project-audit-2026-10-26)，目录权限 0700、文件 0600，受现有 Git 忽略规则保护。报告目录使用汇总结果，未保存用户密码、JWT、数据库连接口令或客户身份字段。

## 本地复跑

以下命令仅面向本机专用测试数据库。执行者应先确认数据库名与本机连接，不能替换成生产库。审计结束后，本次创建的两个专用数据库已清理；复跑需要重新创建。

```bash
cd /Users/estefan-macworkstation/Downloads/ERP
createdb adcraft_audit_20261026
createdb adcraft_audit_migrations_20261026

cd backend
DATABASE_URL=postgresql+asyncpg:///adcraft_audit_20261026 \
DATABASE_URL_SYNC=postgresql+psycopg2:///adcraft_audit_20261026 \
EXPENDITURE_TEST_URL=postgresql+asyncpg:///adcraft_audit_20261026 \
SUPPLIER_MIGRATION_TEST_URL=postgresql+psycopg2:///adcraft_audit_20261026 \
FINANCE_RECON_MIGRATION_TEST_URL=postgresql+psycopg2:///adcraft_audit_20261026 \
../.venv/bin/python -m pytest -q

DATABASE_URL_SYNC=postgresql+psycopg2:///adcraft_audit_migrations_20261026 \
../.venv/bin/alembic upgrade head
```

第二条升级命令目前预期失败，作为 R03 的独立复现。不得据此对现有业务库执行重建、补表或版本标记。

```bash
cd /Users/estefan-macworkstation/Downloads/ERP/frontend
npm test
npm run lint
npm run build
npm run check:ai-contract
npm audit --registry=https://registry.npmjs.org --json

cd /Users/estefan-macworkstation/Downloads/ERP
bash scripts/tests/test_deploy.sh
PYTHONPATH=backend .venv/bin/python docs/project-audit-2026-10-26/tools/backend_references.py
node docs/project-audit-2026-10-26/tools/frontend_references.mjs
PYTHONPATH=backend .venv/bin/python docs/project-audit-2026-10-26/tools/route_audit.py
node docs/project-audit-2026-10-26/tools/api_contract_audit.mjs
PYTHONPATH=backend .venv/bin/python docs/project-audit-2026-10-26/tools/model_contract_audit.py
PYTHONPATH=backend .venv/bin/python docs/project-audit-2026-10-26/tools/isolated_reproductions.py
PYTHONPATH=backend .venv/bin/python docs/project-audit-2026-10-26/tools/security_reproductions.py
```

引用和模型脚本为审计辅助工具：静态扫描结果需要人工复核，不能单独作为删除模块或授权正确的证明。运行复现脚本会重新生成相应证据文件。
