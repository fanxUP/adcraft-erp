# TAV-P01 本地验证证据

验证环境：`/tmp/adcraft-current`，分支 `master`，2026-09-11（Asia/Shanghai）。本轮未执行服务器 SSH、Git 推送、数据库升级或服务重启。

## 自动化结果

| 检查项 | 命令 | 结果 |
| --- | --- | --- |
| 后端全量回归 | `backend/.venv/bin/python -m pytest -q` | 1079 passed，2 条依赖弃用警告 |
| TAV 专项与路由权限 | `backend/.venv/bin/python -m pytest -q tests/test_task_assignment_visibility.py` | 7 passed |
| 前端全量测试 | `frontend/npm test -- --run` | 25 个测试文件、160 passed |
| 前端类型检查 | `frontend/npm run typecheck` | 通过 |
| 前端 Lint | `frontend/npm run lint` | 通过 |
| 前端生产构建 | `frontend/npm run build` | 通过，首屏 gzip 152.44 KiB，低于 200 KiB 门槛 |
| AI 页面契约 | `frontend/npm run check:ai-contract` | 通过，7 个页面、30 个语义控件、93 个命名路由 |
| Python 编译检查 | `backend/.venv/bin/python -m compileall -q app alembic scripts` | 通过 |
| 差异空白检查 | `git diff --check` | 通过 |

## 迁移状态

- Alembic 代码头：`tavp01_order_task_assignees`。
- 当前连接数据库版本：`d9e0f1a2b3c4`。
- `alembic check` 返回“Target database is not up to date”，原因是数据库尚未沿用当前代码头升级；这是发布前待执行的迁移步骤，不在本轮自动执行。

## 已验证的关键行为

- 三类任务列表与详情使用独立权限；任务负责人维护使用独立 `*:assign` 接口。
- 订单任务可见范围以员工 ID 多选保存；空集合恢复全员可见。
- 普通员工不能在状态请求中伪造其他负责人；后端强制解析当前登录绑定的在职员工。
- 订单可见性条件同时覆盖任务仓储、工作台、任务明细选项和任务附件上传/删除检查。
- 没有外协读取权限时，前端不渲染外协卡片，后端也不返回外协状态字段。

## 待发布前动作

1. 备份数据库并确认 `d9e0f1a2b3c4 -> tavp01_order_task_assignees` 的升级窗口。
2. 在隔离环境先执行迁移 upgrade/downgrade 演练，再对生产数据库执行 upgrade。
3. 发布前端和后端后，用管理员/销售、设计、制作、安装及未绑定员工账号做真实浏览器回归。
