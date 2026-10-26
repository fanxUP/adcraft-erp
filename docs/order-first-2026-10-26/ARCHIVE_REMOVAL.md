# 历史报价档案页面移除

日期：2026-10-26。基于用户确认的方案移除历史报价档案入口和页面，保留历史来源及关联财务数据。本轮完成本地修改，未提交、推送或部署。

## 行为

- 订单管理不再展示“历史报价档案”按钮，删除 `OrderHistory.vue`。
- `/quotes`、`/cdr/quotes` 返回订单管理；原新建地址进入新建订单。
- 原普通报价和 CDR 报价详情、编辑地址，仅查询 `source_quote_id` 对应的已有、未删除订单，有对应订单时打开订单详情，否则返回订单管理并提示报价功能已停用。历史来源存在多份有效订单时按创建时间、ID 稳定选择首份。
- 新增只读 `GET /api/v1/orders/from-history/{quote_id}`，仅返回订单 ID 或 null，要求 `order:read`，不返回报价及财务内容。跳转不会调用原创建订单的 POST 接口。
- 移除旧页面权限映射、页面上下文及 AI 页面能力描述。历史消息的报价业务指引改为打开对应订单，保留旧链接兼容。
- 保留历史报价底层数据、现有内部读取能力、来源关联及历史业务、财务记录，无数据库迁移。

## 验证

| 检查 | 结果 |
| --- | --- |
| 后端订单集成、业务指引、AI 页面契约 | 63 passed |
| 前端旧链接真实内存路由、权限、页面上下文、导航 | 42 passed |
| 前端 ESLint | 通过 |
| 类型检查与生产构建 | 通过，首屏 159.02 KiB gzip / 200 KiB |
| AI 页面能力契约 | 通过，8 个页面、27 个语义控件 |
| 构建产物 | 无 `OrderHistory-*` 资源 |
| diff 空白错误 | 无 |

后端在本地独立测试库 `adcraft_archive_test_20261026` 的随机 schema 内验证普通/CDR 来源、有效/回收站/无对应订单、无效 UUID、401/403，以及查询前后单据数量和状态不变。测试库在完成后删除，未连接生产数据库。

首轮检查发现新测试数据缺少必填订单日期、兼容路由缺少 TypeScript 组件声明；已修正并重新运行上述全部检查。Vite 现有 `__dirname` 前瞻性配置提示不影响构建。

实际命令：

```bash
# backend，使用本地隔离数据库环境变量
../.venv/bin/python -m pytest -q --tb=short tests/test_order_first_integration.py tests/test_workflow_guidance.py tests/test_ai_page_contract.py

# frontend
npm run test -- src/router/legacyQuotes.test.ts src/config/access.test.ts src/config/pageContext.test.ts src/config/navigation.test.ts
npm run lint
npm run check:ai-contract
npm run build
```
