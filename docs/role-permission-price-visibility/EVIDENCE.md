# 角色权限与价格可见性验证证据

验证日期：2026-09-10（Asia/Shanghai）

## 已实现的安全边界

- 新增并统一使用 `order:view_price`、`order_item:view_price`、`catalog:view_price`、`finance:view_cost`、`report:view_financial` 五类敏感权限。
- 权限字典由基线 115 个扩展为 120 个；预置角色仍为 `admin`、`sales`、`finance`、`designer`、`production`、`installer` 六类。
- 设计、制作、安装内置角色默认不拥有上述敏感权限；角色服务和角色管理页面均禁止继续授予执行角色敏感权限。
- 用户角色组合校验阻止普通账号同时拥有执行角色和带价格/财务权限的角色，管理员例外。
- 订单、订单明细、任务、任务队列、工作台、产品目录、聊天、外协、合同/框架合同和报表的响应按当前用户权限裁剪价格字段；缺少权限时字段直接省略。
- 前端从 `/auth/me` 读取服务端权限码，任务列表、任务卡片、看板、工作台、目录和导航按权限渲染，不以隐藏字段或 `0` 作为替代。
- 初始化脚本只同步内置角色，保留自定义角色权限；新增权限采用幂等 seed，不修改订单业务数据。

## 执行过的验证命令

| 验证项 | 命令 | 结果 |
|---|---|---|
| 后端全量回归 | `backend/.venv/bin/pytest backend/tests -q` | `1055 passed, 2 warnings` |
| 前端权限/导航回归 | `npm test -- --run src/config/access.test.ts src/config/navigation.test.ts` | 2 个文件、12 项通过 |
| 前端完整质量检查 | `npm run lint` | 通过 |
| 前端类型检查 | `npm run typecheck` | 通过 |
| 前端生产构建 | `npm run build` | 通过；首屏 `152.22 KiB gzip / 200 KiB` |
| 后端语法检查 | `backend/.venv/bin/python -m py_compile ...` | 通过 |
| 补丁空白检查 | `git diff --check` | 通过 |
| 密码字面量扫描 | 针对用户提供的登录密码做字面量扫描 | 未发现密码字面量 |
| 变更 diff 敏感信息扫描 | 针对密码和服务器地址做变更 diff 扫描 | 未发现新增敏感信息 |
| 迁移/部署文件扫描 | `git diff --name-only \| rg 'migrations\|schema\|docker-compose\|deploy.sh'` | 未发现变更 |

## 线上发布证据

- 发布提交：`37838cd7b863cd7e68d55a23397484e505ae23ac`；发布前线上提交：`edb9e2aabe952ae87fa1385ac9957823d184eae0`。
- 数据库版本：Alembic `u4v5w6x7y8z9 (head)`，发布后与迁移头一致。
- 数据库备份：`backup_20260910_135519.tar.gz`，发布脚本报告数据库 dump 约 3.3 MB，备份文件约 462 KB，并通过备份校验工具。
- 线上服务：后端和 Nginx 均为 active；直连和代理健康接口均返回 `status=ok`、`database=ok`。
- 访问控制：未登录访问订单接口返回 HTTP 401；数据库权限核对中，设计/制作/安装角色匹配五类敏感权限的行数为 0。
- 发布后资源：部署标记与提交一致，前端根路径 HTTP 200，发布后 10 分钟后端错误日志行数为 0。
- 临时文件：上传到服务器的 Git bundle 和 dist 包已清理；数据库备份保留在服务器备份目录。

## 未执行项

- 未使用业务测试账号执行设计、制作、安装、销售、财务、管理员六类登录态逐角色线上接口烟囱；本项需要可用的隔离账号，不能用匿名请求替代。
- 范围控制引擎因文件不存在无法运行；已按当前 `.vibe/SCOPE_LOCK.yaml` 和变更统计人工核对范围。

## 发布后跟进

补充六类隔离账号的登录态验证：设计/制作/安装账号响应不得出现订单或明细价格字段；销售/财务/管理员按显式权限验证应有字段。完成后再将 A08 的账号验收项标记为完成。
