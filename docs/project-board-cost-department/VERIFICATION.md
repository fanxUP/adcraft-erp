# 项目看板与项目成本部门/科室展示验证记录

## 验证范围

- 项目看板增加项目队列，并与工作台共用队列加载方法和卡片组件。
- 项目队列卡片显示客户名称、部门/科室；金额仍受现有价格能力控制。
- 项目成本列表增加部门/科室列，覆盖订单和报价两种来源。
- 项目成本详情增加部门/科室信息，覆盖订单和报价详情。
- 未修改数据库、后端权限、任务状态机、成本计算和依赖清单。

## 执行环境

- 仓库：`/private/tmp/adcraft-push.mo3jjV`
- 分支：`fix/completed-resource-rows`
- 执行时间：2026-09-12 02:14（Asia/Shanghai）
- 执行前基线提交：`9c5634e6cf2416ab7de595f134b8685f7d7dc464`
- 状态：实现代码未提交，未部署服务器。

## 自动化证据

| 命令 | 结果 | 摘要 |
|---|---|---|
| `npm test -- --run src/utils/project-board-cost-department.test.ts` | 通过，退出码 0 | 1 个测试文件，5 个测试通过 |
| `npm run typecheck` | 通过，退出码 0 | `vue-tsc --noEmit` 无类型错误 |
| `npm test` | 通过，退出码 0 | 27 个测试文件，178 个测试通过 |
| `npm run lint` | 通过，退出码 0 | ESLint 无错误 |
| `npm run build` | 通过，退出码 0 | Vite 构建完成，bundle-size 检查通过 |
| `.venv/bin/pytest -q tests/test_business_document_price_visibility.py tests/test_project_cost_service.py tests/test_modular_permissions.py` | 通过，退出码 0 | 37 个后端测试通过 |
| `git diff --check` | 通过，退出码 0 | 已跟踪变更无空白错误 |

## 尚未执行

- 使用线上管理员、财务、设计、制作、安装账号进行页面验收。
- 提交 Git、推送远端和部署服务器。
- 线上接口响应与真实部门/科室数据的浏览器验证。

这些事项不能用本地构建结果替代，提交部署前应继续执行。
