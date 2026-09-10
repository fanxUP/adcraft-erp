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

## 未执行项

- 未连接生产数据库，未执行迁移、权限 seed、业务数据修复或批量更新。
- 未部署到线上环境，未重启线上服务，未执行线上角色账号烟囱。
- 范围控制引擎因文件不存在无法运行；已按当前 `.vibe/SCOPE_LOCK.yaml` 和变更统计人工核对范围。

## 发布前检查

发布前仍需在用户明确授权后执行：记录当前提交和服务状态、备份数据库及权限关联数据、在隔离账号上验证六类角色、检查健康接口和静态资源，并保留可回滚版本。此次本地验证不等同于线上发布验收。
