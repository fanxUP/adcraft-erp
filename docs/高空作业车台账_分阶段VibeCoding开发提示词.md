# 高空作业车台账模块：分阶段 Vibe Coding 开发提示词

> 适用项目：本地部署广告公司 ERP 系统  
> 适用方式：复制对应阶段提示词，逐步交给 Codex / Cursor / Claude Code / 其他 Vibe Coding 工具开发  
> 核心原则：先台账、后结算；先草稿、后确认；先内部、后微信；先可追溯、后自动化。

---

## 0. 项目总目标

我们公司是一家广告制作安装公司，已有本地部署 ERP 系统，业务涉及客户、订单、报价、设计、生产、安装、财务、车辆管理、微信/飞书/企业微信 Agent 等。

现在需要新增一个独立模块：

```text
高空作业车台账 / 高空车经营台账 / 高空车每日出车结算
```

这个模块不是普通车辆管理，而是针对公司的一辆高空作业车进行独立经营核算，需要记录：

```text
1. 每天是否出车
2. 出车日期
3. 驾驶员
4. 随车人员
5. 干活地点
6. 客户 / 项目 / 订单
7. 作业内容
8. 作业金额
9. 应收 / 实收 / 未收
10. 驾驶员垫付
11. 驾驶员报销
12. 驾驶员工资
13. 车辆油费、维修、保险、年检、违章、耗材等费用
14. 单趟利润
15. 每日利润
16. 月度利润
17. 待收款
18. 待报销
19. 安全检查
20. 微信/飞书 Agent 识别聊天内容后生成台账草稿
```

---

## 1. 总体开发原则

### 1.1 高空车要按“经营设备”管理

普通车辆主要解决：

```text
谁开了？
去哪了？
花了多少钱？
```

高空作业车要解决：

```text
谁开了？
去哪了？
给谁干活？
收了多少钱？
司机垫了多少？
报销了多少？
工资多少？
车辆费用多少？
这一趟利润多少？
这个月赚了多少？
还有多少钱没收？
```

### 1.2 第一版必须保守

第一版只做：

```text
台账记录
费用记录
工资记录
收款状态
报销状态
利润统计
人工确认
审计日志
微信识别草稿
```

第一版不要做：

```text
GPS 实时轨迹
自动识别发票并入账
自动确认收款
自动报销
自动发工资
复杂折旧模型
复杂税务模型
自动删除台账
```

### 1.3 Agent 只能生成草稿，不能直接入账

Agent 可以做：

```text
识别微信聊天内容
生成台账草稿
生成垫付草稿
生成报销草稿
生成工资核算建议
查询统计报表
提醒待收款
提醒待报销
```

Agent 禁止做：

```text
自动确认收款
自动报销
自动发工资
自动删除台账
自动修改已审核金额
自动作废台账
自动修改财务数据
```

### 1.4 所有关键动作必须留痕

关键动作包括：

```text
新增台账
修改台账金额
确认收款
审核垫付
标记报销
计算工资
发放工资
新增车辆费用
作废台账
审核台账
生成月报
Agent 生成草稿
人工确认草稿
```

每个动作都要记录：

```text
操作人
操作时间
操作来源
操作对象
操作前数据
操作后数据
IP / 设备 / 来源平台
备注
```

---

# 阶段 0：项目现状扫描与安全准备

## 阶段目标

在正式开发前，先让 AI 读取现有 ERP 项目结构，确认技术栈、数据库、权限系统、员工表、客户表、订单表、安装任务表、财务模块、车辆模块、菜单路由、日志系统、部署方式。

不要直接写代码。

## 给 Vibe Coding 的提示词

```text
你现在是我的高级全栈工程师和系统架构师，请先对我当前本地部署的广告公司 ERP 项目进行现状扫描，不要直接修改代码。

项目背景：
- 我是一家广告制作安装公司的负责人
- 当前已经有一个本地部署 ERP 系统
- 未来要新增“高空作业车台账”模块
- 这个模块需要和客户、订单、安装任务、员工、财务、车辆、微信/飞书 Agent 关联
- 开发必须非常稳，不允许破坏现有系统

本次任务：
请只做项目扫描和实施方案，不要直接写代码。

请完成以下检查：
1. 识别项目技术栈
   - 后端语言和框架
   - 前端框架
   - 数据库类型
   - ORM / 数据库迁移工具
   - 权限系统
   - 菜单系统
   - 文件上传系统
   - 日志系统
   - Docker / docker-compose 部署方式

2. 识别已有业务模块
   - 客户管理
   - 订单管理
   - 报价管理
   - 设计任务
   - 生产任务
   - 安装任务
   - 员工管理
   - 财务费用
   - 车辆管理
   - 微信/飞书/Agent 相关模块

3. 识别可复用数据表
   - customers
   - orders
   - install_tasks
   - employees / users
   - departments
   - finance_records
   - vehicles
   - drivers
   - audit_logs
   - attachments / files

4. 输出高空作业车台账模块的集成方案
   - 需要新增哪些表
   - 需要复用哪些表
   - 需要新增哪些 API
   - 需要新增哪些前端页面
   - 需要新增哪些菜单入口
   - 需要新增哪些权限
   - 需要新增哪些审计日志

5. 输出风险点
   - 哪些现有代码不能轻易修改
   - 哪些数据表不能直接改结构
   - 哪些操作需要迁移脚本
   - 哪些操作需要备份

6. 输出分阶段开发计划
   - 每阶段目标
   - 涉及文件
   - 数据库迁移
   - API
   - 页面
   - 测试方式
   - 回滚方式

约束：
- 不要直接修改代码
- 不要直接新增表
- 不要直接改数据库
- 不要删除任何现有文件
- 先输出分析报告和实施计划

验收标准：
1. 能清楚说明当前项目结构
2. 能列出高空作业车模块需要复用的现有模块
3. 能列出新增模块的文件规划
4. 能列出数据库迁移规划
5. 能列出风险和回滚方案
6. 没有修改任何代码
```

## 本阶段验收表

| 验收项 | 是否通过 |
|---|---|
| 已识别项目技术栈 |  |
| 已识别数据库和迁移方式 |  |
| 已识别权限系统 |  |
| 已识别菜单系统 |  |
| 已识别员工、客户、订单、安装任务表 |  |
| 已输出新增模块方案 |  |
| 未修改任何代码 |  |

---

# 阶段 1：数据库模型与迁移脚本

## 阶段目标

新增高空作业车台账相关数据表，但先不做页面。重点是建立稳定、可扩展的数据基础。

## 数据表清单

建议新增：

```text
1. aerial_work_vehicles              高空作业车档案
2. aerial_work_daily_ledgers         每日出车台账
3. aerial_driver_expenses            驾驶员垫付/报销
4. aerial_driver_wages               驾驶员工资
5. aerial_vehicle_costs              高空车车辆费用
6. aerial_safety_checks              安全检查记录
7. aerial_ledger_attachments         台账附件
8. aerial_ledger_audit_logs          台账审计日志
9. aerial_agent_draft_actions        Agent 识别草稿动作
```

## 给 Vibe Coding 的提示词

```text
你现在负责为广告公司 ERP 新增“高空作业车台账”模块的数据库模型和迁移脚本。

重要要求：
- 本阶段只做数据库迁移、模型定义、基础枚举，不做页面
- 不要破坏现有表
- 优先复用现有 customers、orders、install_tasks、employees/users、vehicles、audit_logs、attachments 表
- 如果现有表字段名不同，请适配现有项目实际命名
- 所有新增表必须带 created_at、updated_at
- 金额字段必须使用 decimal/numeric，不要使用 float
- 删除业务记录时优先软删除或作废，不要物理删除

模块目标：
公司有一辆高空作业车，需要单独记录每日出车台账，包括客户、地点、作业内容、应收、实收、未收、驾驶员垫付、报销、工资、车辆费用、利润、安全检查、附件和审计日志。

请新增以下数据表：

1. aerial_work_vehicles
字段建议：
- id
- vehicle_id，可关联普通 vehicles 表，允许为空
- plate_number，车牌号
- vehicle_name，车辆名称
- brand_model，品牌型号
- max_working_height，最大作业高度
- platform_capacity，平台承重
- purchase_date，购买日期
- status，车辆状态：available、in_use、maintenance、disabled、scrapped
- default_driver_id，默认驾驶员
- insurance_expire_date，保险到期日
- inspection_expire_date，年检到期日
- maintenance_due_date，下次保养日期
- remark
- created_at
- updated_at

2. aerial_work_daily_ledgers
字段建议：
- id
- ledger_no，唯一台账编号
- work_date，出车日期
- aerial_vehicle_id，高空车 ID
- plate_number，冗余车牌号
- driver_id，驾驶员
- assistant_user_ids，随车人员 JSON
- customer_id
- customer_name
- contact_name
- contact_phone
- related_order_id
- related_install_task_id
- work_location，作业地点
- work_type，作业类型
- work_content，作业内容
- planned_start_time
- planned_end_time
- actual_start_time
- actual_end_time
- billing_method，计费方式：trip、hour、half_day、day、project、free、included_in_order
- unit_price
- quantity
- receivable_amount，应收金额
- discount_amount，优惠金额
- final_amount，最终应收金额
- received_amount，实收金额
- unpaid_amount，未收金额
- settlement_type，结算方式：separate、included_in_order、monthly、free
- payment_status，收款状态：unpaid、partial、paid、credit、free、included_in_order
- payment_method
- payment_time
- invoice_required
- invoice_status
- start_mileage
- end_mileage
- distance_km
- driver_wage_amount
- reimbursement_amount
- vehicle_direct_cost
- gross_profit
- estimated_profit
- safety_check_status
- abnormal_flag
- abnormal_description
- status：draft、assigned、started、working、completed、returned、reviewed、settled、cancelled、abnormal
- audit_status：pending、approved、rejected
- created_by
- reviewed_by
- reviewed_at
- voided_by
- voided_at
- void_reason
- remark
- created_at
- updated_at

3. aerial_driver_expenses
字段建议：
- id
- ledger_id
- expense_date
- driver_id
- expense_type：fuel、toll、parking、meal、temporary_repair、material、other
- amount
- payment_method
- paid_by_driver
- receipt_url
- description
- review_status：pending、approved、rejected
- reviewed_by
- reviewed_at
- reimbursement_status：unpaid、pending_reimbursement、reimbursed
- reimbursed_at
- reimbursed_by
- created_at
- updated_at

4. aerial_driver_wages
字段建议：
- id
- ledger_id，可为空，月度工资汇总时可为空
- wage_month
- driver_id
- wage_type：daily、trip、hourly、commission、base_plus_commission
- base_wage
- trip_wage
- hourly_wage
- commission_amount
- allowance_amount
- deduction_amount
- final_wage_amount
- payment_status：pending、calculated、pending_payment、paid
- paid_at
- paid_by
- remark
- created_at
- updated_at

5. aerial_vehicle_costs
字段建议：
- id
- aerial_vehicle_id
- ledger_id，可为空
- cost_date
- cost_type：fuel、maintenance、insurance、inspection、violation、tire、hydraulic_system、boom_repair、platform_repair、safety_equipment、tool_consumables、parking_lot、loan、depreciation、other
- amount
- handler_id
- payer_id
- payment_method
- is_driver_advance
- need_reimbursement
- receipt_url
- allocation_type：per_trip、daily、monthly、annual、none
- allocation_month
- related_order_id
- review_status：pending、approved、rejected
- reviewed_by
- reviewed_at
- remark
- created_at
- updated_at

6. aerial_safety_checks
字段建议：
- id
- ledger_id
- check_type：before_work、after_work
- checker_id
- vehicle_appearance_ok
- tire_ok
- brake_ok
- light_ok
- hydraulic_system_ok
- outriggers_ok
- platform_ok
- safety_belt_ok
- warning_equipment_ok
- extinguisher_ok
- documents_ok
- weather_ok
- site_risk_ok
- issue_description
- photo_urls，JSON
- check_result：passed、failed、need_attention
- checked_at
- created_at

7. aerial_ledger_attachments
字段建议：
- id
- ledger_id
- attachment_type：site_photo、completion_photo、receipt、invoice、safety_photo、other
- file_url
- file_name
- uploaded_by
- uploaded_at
- remark

8. aerial_ledger_audit_logs
字段建议：
- id
- ledger_id
- operator_id
- action
- source：erp、wechat_agent、feishu_agent、system
- before_json
- after_json
- remark
- created_at

9. aerial_agent_draft_actions
字段建议：
- id
- source_platform：workbuddy_wechat、wechat、wecom、feishu、manual
- source_message_id
- source_sender_id
- source_sender_name
- raw_content
- intent
- confidence
- extracted_json
- suggested_action
- related_ledger_id
- status：draft、pending_confirm、confirmed、rejected、executed、failed
- confirmed_by
- confirmed_at
- executed_at
- created_at
- updated_at

业务计算规则：
1. unpaid_amount = final_amount - received_amount
2. 如果 received_amount < final_amount，则 payment_status = partial 或 unpaid
3. gross_profit = received_amount - driver_wage_amount - reimbursement_amount - vehicle_direct_cost
4. 如果未收款，则 estimated_profit = final_amount - driver_wage_amount - reimbursement_amount - vehicle_direct_cost
5. 金额字段默认 0，不允许出现 null 导致计算报错

请完成：
1. 新增数据库迁移脚本
2. 新增 ORM model/schema/entity
3. 新增必要枚举
4. 新增基础索引
5. 新增唯一约束：ledger_no 唯一
6. 新增车牌号索引、日期索引、驾驶员索引、客户索引、订单索引
7. 提供回滚迁移
8. 提供一组测试数据 seed

验收标准：
1. 迁移可以成功执行
2. 回滚可以成功执行
3. 表结构符合要求
4. 金额字段类型正确
5. ledger_no 唯一
6. 查询日期、驾驶员、客户、收款状态时有索引
7. 不影响现有 ERP 表
8. 可以插入一条完整测试台账
9. 可以插入垫付、工资、车辆费用、安全检查、附件、审计日志测试数据
```

## 本阶段验收表

| 验收项 | 是否通过 |
|---|---|
| 新增迁移脚本 |  |
| 新增 ORM 模型 |  |
| 回滚脚本可用 |  |
| 金额字段为 decimal/numeric |  |
| ledger_no 唯一 |  |
| 可插入测试台账 |  |
| 不影响现有系统 |  |

---

# 阶段 2：后端基础 API

## 阶段目标

建立高空作业车台账模块的基础后端接口，先实现 CRUD、列表筛选、详情查询、基础计算，不做复杂审批。

## API 清单

```text
GET    /api/aerial/vehicles
POST   /api/aerial/vehicles
GET    /api/aerial/vehicles/{id}
PATCH  /api/aerial/vehicles/{id}

GET    /api/aerial/ledgers
POST   /api/aerial/ledgers
GET    /api/aerial/ledgers/{id}
PATCH  /api/aerial/ledgers/{id}
POST   /api/aerial/ledgers/{id}/void

GET    /api/aerial/driver-expenses
POST   /api/aerial/driver-expenses
GET    /api/aerial/vehicle-costs
POST   /api/aerial/vehicle-costs
GET    /api/aerial/driver-wages
POST   /api/aerial/driver-wages
```

## 给 Vibe Coding 的提示词

```text
你现在负责为广告公司 ERP 的“高空作业车台账”模块开发后端基础 API。

前提：
- 阶段 1 已经新增数据库表和模型
- 本阶段只做后端基础 API
- 不做复杂前端页面
- 不做微信 Agent
- 不做自动收款、自动报销、自动发工资

请实现以下 API：

一、高空车档案 API
1. GET /api/aerial/vehicles
   - 支持按状态、车牌号搜索
   - 返回车辆列表

2. POST /api/aerial/vehicles
   - 新增高空车档案
   - 车牌号不能为空
   - 车牌号不能重复

3. GET /api/aerial/vehicles/{id}
   - 返回车辆详情
   - 包含保险到期、年检到期、保养提醒信息

4. PATCH /api/aerial/vehicles/{id}
   - 修改车辆信息
   - 修改状态要记录审计日志

二、每日出车台账 API
1. GET /api/aerial/ledgers
   - 支持筛选：日期范围、驾驶员、客户、作业地点、收款状态、审核状态、台账状态
   - 支持分页
   - 返回核心字段：日期、驾驶员、客户、地点、作业内容、应收、实收、未收、垫付、工资、车辆费用、利润、状态

2. POST /api/aerial/ledgers
   - 新增台账
   - 自动生成 ledger_no
   - work_date、aerial_vehicle_id、driver_id、work_location 必填
   - 自动计算 final_amount、unpaid_amount、gross_profit、estimated_profit
   - 写入审计日志

3. GET /api/aerial/ledgers/{id}
   - 返回台账详情
   - 包含基础信息、客户订单、金额收款、驾驶员垫付、工资、车辆费用、安全检查、附件、审计日志

4. PATCH /api/aerial/ledgers/{id}
   - 修改台账
   - 金额相关字段变化时重新计算未收金额和利润
   - 已审核台账修改金额必须有管理员权限
   - 写入审计日志

5. POST /api/aerial/ledgers/{id}/void
   - 作废台账
   - 不允许物理删除
   - 必须填写作废原因
   - 写入审计日志

三、驾驶员垫付 API
1. GET /api/aerial/driver-expenses
   - 支持筛选：日期、驾驶员、审核状态、报销状态、费用类型

2. POST /api/aerial/driver-expenses
   - 新增驾驶员垫付记录
   - 必须关联 ledger_id
   - amount 必须大于 0
   - 新增后更新台账 reimbursement_amount 或待审核垫付汇总字段
   - 写入审计日志

四、车辆费用 API
1. GET /api/aerial/vehicle-costs
   - 支持筛选：日期、费用类型、审核状态、车辆、是否关联台账

2. POST /api/aerial/vehicle-costs
   - 新增车辆费用
   - amount 必须大于 0
   - 如果关联 ledger_id，则更新台账 vehicle_direct_cost
   - 写入审计日志

五、驾驶员工资 API
1. GET /api/aerial/driver-wages
   - 支持筛选：月份、驾驶员、支付状态

2. POST /api/aerial/driver-wages
   - 新增工资记录
   - 可以关联单条台账，也可以作为月度工资记录
   - 写入审计日志

业务计算要求：
1. final_amount = receivable_amount - discount_amount，除非前端直接传 final_amount
2. unpaid_amount = final_amount - received_amount
3. gross_profit = received_amount - driver_wage_amount - reimbursement_amount - vehicle_direct_cost
4. estimated_profit = final_amount - driver_wage_amount - reimbursement_amount - vehicle_direct_cost
5. 金额不能为负数，优惠金额不能大于应收金额
6. 未收金额不能小于 0，如超收要单独处理或提示

权限要求：
1. 老板/管理员可以查看全部
2. 财务可以查看金额、收款、报销、工资
3. 普通员工不能查看利润和工资
4. 驾驶员只能查看自己的出车和垫付
5. 业务员只能查看自己关联订单/客户的台账
6. 没有权限时返回友好提示

审计要求：
所有新增、修改、作废、金额变更都写入 aerial_ledger_audit_logs 或复用系统 audit_logs。

验收标准：
1. 可以新增高空车档案
2. 车牌号不能重复
3. 可以新增每日出车台账
4. 自动生成台账编号
5. 自动计算应收、实收、未收、利润
6. 可以查询台账列表
7. 可以查看台账详情
8. 可以修改台账并记录日志
9. 可以作废台账但不物理删除
10. 可以新增驾驶员垫付
11. 可以新增车辆费用
12. 可以新增工资记录
13. 无权限用户看不到利润和工资
14. 所有关键操作都有审计日志
15. 提供 API 测试用例
```

---

# 阶段 3：前端菜单、首页和台账列表页

## 阶段目标

新增前端菜单入口，建立高空作业车台账首页和每日台账列表页，让老板/管理员能直观看到出车、金额、利润、待收款、待报销。

## 页面结构

```text
车辆管理
└── 高空作业车台账
    ├── 台账首页
    ├── 每日出车台账
    ├── 驾驶员垫付/报销
    ├── 驾驶员工资
    ├── 车辆费用
    ├── 安全检查
    └── 统计报表
```

## 给 Vibe Coding 的提示词

```text
你现在负责为广告公司 ERP 新增“高空作业车台账”模块的前端菜单、首页和每日出车台账列表页。

前提：
- 后端基础 API 已完成
- 本阶段只做前端展示和基础列表
- 不做复杂图表
- 不做微信 Agent

请实现：

一、菜单入口
在系统菜单中新增：
车辆管理 / 高空作业车台账
子菜单包括：
1. 台账首页
2. 每日出车台账
3. 驾驶员垫付/报销
4. 驾驶员工资
5. 车辆费用
6. 安全检查
7. 统计报表

二、台账首页
首页需要显示 KPI 卡片：
1. 今日出车次数
2. 今日应收金额
3. 今日实收金额
4. 今日待收金额
5. 今日驾驶员垫付
6. 今日已审核报销
7. 今日驾驶员工资
8. 今日车辆费用
9. 今日毛利润
10. 本月应收金额
11. 本月实收金额
12. 本月待收金额
13. 本月车辆费用
14. 本月毛利润

首页还需要显示：
1. 今日出车台账列表
2. 待收款台账
3. 待报销费用
4. 待审核台账
5. 保险/年检/保养提醒

三、每日出车台账列表页
列表筛选条件：
1. 日期范围
2. 驾驶员
3. 客户名称
4. 作业地点
5. 收款状态
6. 审核状态
7. 台账状态
8. 是否关联订单

列表字段：
- 出车日期
- 台账编号
- 驾驶员
- 客户名称
- 作业地点
- 作业内容
- 应收金额
- 实收金额
- 未收金额
- 驾驶员垫付
- 驾驶员工资
- 车辆费用
- 毛利润
- 收款状态
- 审核状态
- 台账状态
- 操作

操作按钮：
1. 查看详情
2. 编辑
3. 记录收款
4. 添加垫付
5. 添加车辆费用
6. 审核
7. 作废

权限显示要求：
1. 没有财务权限的用户不显示利润
2. 普通员工不显示驾驶员工资
3. 驾驶员只能看到自己的台账
4. 老板/管理员可以看全部

交互要求：
1. 金额字段右对齐
2. 未收金额大于 0 时突出显示
3. 待报销状态要有明显标识
4. 作废台账置灰显示
5. 列表支持分页
6. 筛选条件支持重置
7. 页面加载失败要有友好提示
8. 空数据时显示引导创建台账

验收标准：
1. 菜单入口正常显示
2. 可以进入台账首页
3. 首页 KPI 正常显示
4. 可以进入每日出车台账列表
5. 筛选功能可用
6. 分页功能可用
7. 权限控制生效
8. 普通员工看不到利润和工资
9. 作废台账置灰
10. 页面刷新不报错
```

---

# 阶段 4：新增/编辑/详情台账页面

## 阶段目标

做完整的每日出车台账录入、编辑、详情页面，这是整个模块的核心。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车每日出车台账”的新增、编辑、详情页面。

页面目标：
每次高空车出车，都能录入一条完整台账，记录驾驶员、客户、地点、作业内容、金额、收款、工资、垫付、车辆费用、安全检查、附件和备注。

请实现以下页面：

一、新增台账页
字段分组如下：

1. 基础信息
- 出车日期，必填
- 高空车，必填
- 车牌号，自动带出
- 驾驶员，必填
- 随车人员
- 台账状态
- 备注

2. 客户与项目
- 客户名称，可选择已有客户，也可临时填写
- 联系人
- 联系电话
- 关联订单，可选
- 关联安装任务，可选

3. 作业信息
- 作业地点，必填
- 作业类型
- 作业内容
- 计划开始时间
- 计划结束时间
- 实际开始时间
- 实际结束时间

4. 计费与收款
- 计费方式
- 单价
- 数量
- 应收金额
- 优惠金额
- 最终金额
- 实收金额
- 未收金额，自动计算
- 收款状态，自动判断，也允许有权限用户调整
- 收款方式
- 收款时间
- 是否开票
- 发票状态
- 结算方式：单独收款、并入订单、月结、免费

5. 里程信息
- 出车里程
- 收车里程
- 实际公里数，自动计算

6. 成本与利润
- 驾驶员工资
- 驾驶员垫付金额
- 已审核报销金额
- 车辆直接费用
- 本趟毛利润，自动计算
- 预计毛利润，自动计算

7. 异常信息
- 是否异常
- 异常说明

二、编辑台账页
要求：
1. 已审核台账修改金额需要管理员权限
2. 修改金额后自动重新计算未收金额和利润
3. 修改关键字段需要写审计日志
4. 作废台账不能编辑，除非管理员恢复

三、台账详情页
详情页分 Tab：
1. 基础信息
2. 客户与项目
3. 作业与地点
4. 金额与收款
5. 驾驶员垫付/报销
6. 驾驶员工资
7. 车辆费用
8. 安全检查
9. 图片附件
10. 审计日志

四、自动计算规则
1. final_amount = receivable_amount - discount_amount
2. unpaid_amount = final_amount - received_amount
3. gross_profit = received_amount - driver_wage_amount - reimbursement_amount - vehicle_direct_cost
4. estimated_profit = final_amount - driver_wage_amount - reimbursement_amount - vehicle_direct_cost
5. distance_km = end_mileage - start_mileage

五、校验规则
1. 出车日期必填
2. 高空车必填
3. 驾驶员必填
4. 作业地点必填
5. 金额不能小于 0
6. 优惠金额不能大于应收金额
7. 收车里程不能小于出车里程
8. 实收金额不能小于 0
9. 如果实收金额大于最终金额，需要提示是否存在超收
10. 作废台账不允许普通用户编辑

验收标准：
1. 可以新增完整台账
2. 必填项为空时有提示
3. 金额自动计算正确
4. 未收金额自动计算正确
5. 毛利润自动计算正确
6. 里程自动计算正确
7. 可以编辑台账
8. 修改金额后重新计算
9. 已审核台账普通用户不能改金额
10. 详情页 Tab 正常显示
11. 审计日志可以显示
12. 页面不影响现有模块
```

---

# 阶段 5：驾驶员垫付与报销

## 阶段目标

实现司机垫付、财务审核、报销状态跟踪。工资和报销必须分开，不能混在一起。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车驾驶员垫付/报销”功能。

业务背景：
高空作业车司机每天可能垫付油费、过路费、停车费、餐费、临时维修、小材料等费用。这些费用需要先记录，再由财务审核，审核通过后再报销。

重要原则：
- 垫付不是工资
- 报销不是工资
- 司机说“我垫了钱”不能直接报销
- 必须财务审核后才能标记报销
- 微信 Agent 只能生成垫付草稿，不能自动报销

请实现：

一、垫付/报销列表页
筛选条件：
1. 日期范围
2. 驾驶员
3. 费用类型
4. 审核状态
5. 报销状态
6. 关联台账

列表字段：
- 日期
- 驾驶员
- 费用类型
- 金额
- 关联台账
- 作业地点
- 票据
- 审核状态
- 报销状态
- 操作

二、新增垫付记录
字段：
- 关联台账，必填
- 驾驶员，自动带出，也可选择
- 费用日期
- 费用类型
- 金额
- 支付方式
- 是否司机垫付
- 票据照片
- 费用说明

三、审核流程
1. 待审核
2. 财务/管理员审核通过
3. 审核驳回
4. 审核通过后进入待报销
5. 财务打款后标记已报销

四、操作按钮
1. 查看
2. 审核通过
3. 审核驳回
4. 标记已报销
5. 编辑
6. 作废

五、权限规则
1. 驾驶员可以提交自己的垫付
2. 驾驶员可以查看自己的垫付和报销状态
3. 财务可以审核和标记报销
4. 老板/管理员可以查看全部
5. 普通员工不能查看别人报销

六、联动规则
1. 新增垫付后，台账显示待审核垫付金额
2. 审核通过后，计入台账 reimbursement_amount
3. 报销后，显示已报销金额
4. 驳回后，不计入台账成本
5. 修改金额后重新计算台账利润

验收标准：
1. 可以新增垫付记录
2. 可以上传票据
3. 可以审核通过
4. 可以审核驳回
5. 可以标记已报销
6. 审核通过后台账成本增加
7. 驳回后不计入台账成本
8. 台账利润自动重新计算
9. 驾驶员只能看自己的报销
10. 财务可以查看全部待报销
11. 所有操作有审计日志
```

---

# 阶段 6：驾驶员工资核算

## 阶段目标

实现高空车驾驶员工资记录与月度工资汇总。工资和报销分开。工资可以按日、按趟、按小时、按提成或固定工资+提成计算。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车驾驶员工资核算”功能。

业务背景：
高空作业车驾驶员工资需要根据出车记录核算，可能有固定日工资、按趟工资、按小时工资、按金额比例提成、固定工资+提成等规则。工资和垫付报销必须分开。

本阶段目标：
1. 可以为单趟台账记录驾驶员工资
2. 可以按月统计驾驶员工资
3. 可以生成工资汇总
4. 可以标记工资已发放
5. 所有工资发放必须人工确认

请实现：

一、工资规则配置，可先做简单版本
字段：
- 驾驶员
- 工资类型：daily、trip、hourly、commission、base_plus_commission
- 固定日工资
- 单趟工资
- 小时单价
- 提成比例
- 提成基数：应收金额、实收金额、最终金额
- 生效日期
- 失效日期
- 备注

如果当前项目不适合新增工资规则表，第一版可以先在工资核算页面手动输入工资金额，同时预留规则扩展。

二、单趟工资记录
字段：
- 关联台账
- 驾驶员
- 工资类型
- 基础工资
- 趟次工资
- 小时工资
- 提成金额
- 补贴
- 扣款
- 最终工资
- 备注

三、月度工资汇总页
筛选：
- 月份
- 驾驶员
- 支付状态

统计字段：
- 月份
- 驾驶员
- 出车天数
- 出车趟数
- 作业金额
- 实收金额
- 固定工资
- 趟次工资
- 提成工资
- 补贴
- 扣款
- 应发工资
- 垫付报销金额，单独显示，不并入工资
- 已报销金额，单独显示
- 支付状态

四、工资发放流程
1. 生成工资草稿
2. 财务/老板确认
3. 标记待发放
4. 标记已发放
5. 写入审计日志

五、权限规则
1. 老板可以查看全部工资
2. 财务可以核算和发放工资
3. 驾驶员只能查看自己的工资汇总
4. 普通员工不能查看工资
5. Agent 不能自动发工资

六、计算规则
示例：
1. 固定日工资：出车天数 × 日工资
2. 按趟工资：出车趟数 × 单趟工资
3. 按小时工资：作业小时数 × 小时单价
4. 提成工资：提成基数 × 提成比例
5. 最终工资 = 基础工资 + 趟次工资 + 小时工资 + 提成 + 补贴 - 扣款

验收标准：
1. 可以为单趟台账记录工资
2. 台账详情可以看到工资
3. 台账利润扣除工资
4. 可以按月统计驾驶员工资
5. 可以生成工资汇总
6. 可以标记已发放
7. 发放工资需要权限
8. 驾驶员只能看自己的工资
9. 工资和报销分开展示
10. 所有工资操作有审计日志
```

---

# 阶段 7：车辆费用管理

## 阶段目标

实现高空车车辆费用独立记录，包括油费、维修、保险、年检、违章、轮胎、液压系统、升降臂、平台、安全用品、工具耗材等。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车车辆费用管理”功能。

业务背景：
高空作业车除了每天出车收入，还会产生各种费用，包括油费、维修、保养、保险、年检、违章、轮胎、液压系统维修、升降臂维修、平台维修、安全用品、工具耗材、停车场费、折旧等。这些费用需要单独记录，并可以关联到具体台账或按月统计。

请实现：

一、车辆费用列表页
筛选条件：
1. 日期范围
2. 费用类型
3. 车辆
4. 是否关联台账
5. 审核状态
6. 是否司机垫付

列表字段：
- 费用日期
- 费用类型
- 金额
- 经办人
- 付款人
- 是否司机垫付
- 是否需要报销
- 关联台账
- 关联订单
- 票据
- 审核状态
- 操作

二、新增车辆费用
字段：
- 高空车
- 关联台账，可选
- 费用日期
- 费用类型
- 金额
- 经办人
- 付款人
- 支付方式
- 是否司机垫付
- 是否需要报销
- 票据照片
- 分摊方式：per_trip、daily、monthly、annual、none
- 分摊月份
- 关联订单
- 备注

三、费用类型
请支持：
- 油费
- 过路费
- 停车费
- 维修费
- 保养费
- 保险费
- 年检费
- 审车费
- 违章罚款
- 事故维修
- 轮胎
- 电瓶
- 液压系统维修
- 升降臂维修
- 支腿维修
- 平台维修
- 安全带/安全绳
- 工具耗材
- 洗车费
- 停车场费
- 贷款/月供
- 折旧
- 其他费用

四、费用审核
1. 新增费用默认待审核
2. 财务/管理员可以审核通过或驳回
3. 审核通过后计入车辆费用统计
4. 如果费用关联台账，则计入该台账 vehicle_direct_cost
5. 驳回费用不计入成本
6. 修改已审核费用需要管理员权限

五、费用归属
费用需要区分：
1. 本趟作业费用
2. 当日车辆费用
3. 月度固定费用
4. 年度固定费用
5. 不分摊费用

六、权限
1. 老板可以查看全部费用和统计
2. 财务可以审核费用
3. 管理员可以新增和修改费用
4. 驾驶员可以提交自己垫付的费用
5. 普通员工不能查看全部费用统计

验收标准：
1. 可以新增车辆费用
2. 可以上传票据
3. 可以关联台账
4. 关联台账后能影响该台账利润
5. 可以审核通过
6. 可以审核驳回
7. 驳回费用不计入成本
8. 可以按费用类型统计
9. 可以按月份统计
10. 所有费用操作有审计日志
```

---

# 阶段 8：收款结算与待收款管理

## 阶段目标

实现高空车作业的应收、实收、未收、挂账、并入订单、免费售后、月结等状态管理。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车收款结算与待收款管理”功能。

业务背景：
高空作业车可能单独对外收费，也可能服务公司内部订单。有些当天收款，有些挂账，有些并入广告订单，有些免费售后。因此必须单独管理应收、实收、未收和收款状态。

重要原则：
- Agent 不能自动确认收款
- 客户微信说“钱转了”只能生成财务核对提醒
- 收款必须由财务或老板确认
- 并入订单的高空车费用不能重复计算收入

请实现：

一、收款状态
支持：
- unpaid，未收款
- partial，部分收款
- paid，已收款
- credit，挂账
- free，免费
- included_in_order，并入订单

二、结算方式
支持：
- separate，单独收款
- included_in_order，并入订单
- monthly，客户月结
- free，免费/售后

三、待收款列表页
筛选：
- 日期范围
- 客户
- 驾驶员
- 收款状态
- 结算方式
- 关联订单

列表字段：
- 出车日期
- 客户
- 作业地点
- 作业内容
- 应收金额
- 实收金额
- 未收金额
- 收款状态
- 结算方式
- 关联订单
- 操作

操作：
1. 记录收款
2. 标记挂账
3. 标记并入订单
4. 标记免费
5. 查看详情

四、记录收款
字段：
- 收款金额
- 收款方式
- 收款时间
- 收款人
- 收款账户
- 备注

规则：
1. 收款金额不能小于 0
2. 如果累计实收 = 最终金额，状态为 paid
3. 如果累计实收 > 0 且小于最终金额，状态为 partial
4. 如果实收为 0，状态为 unpaid 或 credit/free/included_in_order
5. 如果收款金额超过应收金额，需要提示是否超收

五、并入订单
如果高空车收入并入广告订单：
1. 台账 settlement_type = included_in_order
2. payment_status = included_in_order
3. 高空车本身不重复计算收入
4. 可以作为订单成本或订单附加收入，根据现有财务规则处理

六、权限
1. 财务可以记录收款
2. 老板可以记录和调整收款
3. 普通员工不能确认收款
4. Agent 不能确认收款

验收标准：
1. 可以查看待收款列表
2. 可以记录收款
3. 收款后自动更新实收和未收
4. 收款状态自动变化
5. 可以标记挂账
6. 可以标记并入订单
7. 可以标记免费
8. 普通员工不能确认收款
9. Agent 无法直接确认收款
10. 所有收款变更有审计日志
```

---

# 阶段 9：安全检查与附件管理

## 阶段目标

高空作业车存在安全风险，每次出车前后应保留简单检查记录、现场照片、完成照片、票据、异常记录。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车安全检查与附件管理”功能。

业务背景：
高空作业车不同于普通车辆，涉及高空施工、液压系统、支腿、作业平台、安全带、安全绳、现场天气和障碍物风险。系统需要保留出车前和收车后的安全检查记录，并支持上传现场照片、完成照片、票据和异常照片。

请实现：

一、安全检查类型
1. 出车前检查 before_work
2. 收车后检查 after_work

二、出车前检查项
- 车辆外观是否正常
- 轮胎是否正常
- 刹车是否正常
- 灯光是否正常
- 液压系统是否正常
- 支腿是否正常
- 作业平台是否正常
- 安全带/安全绳是否齐全
- 警示锥/警示牌是否齐全
- 灭火器是否正常
- 行驶证/保险是否有效
- 驾驶员证件是否有效
- 天气是否适合作业
- 现场是否存在高压线/障碍物风险

三、收车后检查项
- 车辆是否损坏
- 平台是否异常
- 液压是否漏油
- 工具是否齐全
- 是否发生事故
- 是否有客户投诉
- 是否需要维修
- 是否需要保养

四、附件类型
- site_photo，现场照片
- completion_photo，完工照片
- receipt，费用票据
- invoice，发票
- safety_photo，安全检查照片
- issue_photo，异常照片
- other，其他

五、页面要求
在台账详情页新增两个 Tab：
1. 安全检查
2. 图片附件

安全检查 Tab：
- 可以新增出车前检查
- 可以新增收车后检查
- 可以查看检查结果
- 如果有异常，要显示异常说明

附件 Tab：
- 可以上传多个文件
- 支持图片预览
- 可以按附件类型筛选
- 显示上传人和上传时间

六、规则
1. 如果安全检查失败，台账应显示异常提醒
2. 如果有异常说明，必须允许创建车辆费用或维修草稿
3. 作业完成照片可以作为台账完成凭证
4. 票据照片可以关联垫付或车辆费用

验收标准：
1. 可以新增出车前检查
2. 可以新增收车后检查
3. 可以记录异常说明
4. 可以上传现场照片
5. 可以上传完工照片
6. 可以上传票据
7. 附件能在台账详情页查看
8. 安全检查失败时台账显示异常
9. 所有上传记录有上传人和时间
10. 不影响现有文件上传系统
```

---

# 阶段 10：统计报表

## 阶段目标

实现老板最关心的经营统计：这辆高空车今天干了几趟、本月收了多少钱、还有多少钱没收、司机工资多少、费用多少、利润多少。

## 给 Vibe Coding 的提示词

```text
你现在负责开发“高空作业车经营统计报表”功能。

业务目标：
老板需要清楚看到高空作业车的经营情况，包括每天、每月、每趟的收入、成本、利润、待收款、待报销、司机工资、车辆费用分类。

请实现以下报表 API 和页面：

一、报表 API
1. GET /api/aerial/reports/daily
   参数：date
   返回：当天出车次数、应收、实收、待收、司机工资、司机垫付、已审核报销、车辆费用、毛利润、台账列表

2. GET /api/aerial/reports/monthly
   参数：month
   返回：本月出车天数、出车趟数、应收、实收、待收、司机工资、报销金额、车辆费用、毛利润、预计利润

3. GET /api/aerial/reports/profit
   参数：date_range、driver_id、customer_id
   返回：按台账、日期、驾驶员、客户统计利润

4. GET /api/aerial/reports/receivables
   返回：待收款列表和汇总

5. GET /api/aerial/reports/reimbursements
   返回：待审核、待报销、已报销列表和汇总

6. GET /api/aerial/reports/costs
   返回：按费用类型、月份、车辆、台账统计车辆费用

二、统计页面
新增“高空车统计报表”页面，包含：
1. 今日统计
2. 本月统计
3. 待收款
4. 待报销
5. 费用分类
6. 驾驶员工资汇总
7. 单趟利润列表

三、核心指标
今日指标：
- 今日出车次数
- 今日应收金额
- 今日实收金额
- 今日待收金额
- 今日司机工资
- 今日垫付金额
- 今日已审核报销
- 今日车辆费用
- 今日毛利润

本月指标：
- 本月出车天数
- 本月出车趟数
- 本月应收金额
- 本月实收金额
- 本月待收金额
- 本月司机工资
- 本月报销金额
- 本月油费
- 本月维修费
- 本月保险/年检分摊
- 本月车辆总成本
- 本月毛利润
- 平均单趟收入
- 平均单趟成本
- 平均单趟利润

四、计算规则
1. 台账数量按未作废台账统计
2. 作废台账不计入收入和利润
3. 待审核费用不计入正式成本，但可以显示为待确认成本
4. 已审核费用计入成本
5. 未收款台账显示预计利润
6. 已收款台账显示实际毛利润

五、权限
1. 老板可以看全部统计
2. 财务可以看金额、成本、利润
3. 驾驶员只能看自己的出车次数和工资，不看利润
4. 普通员工不能看利润报表

验收标准：
1. 可以查看今日统计
2. 可以查看本月统计
3. 可以查看待收款列表
4. 可以查看待报销列表
5. 可以查看费用分类统计
6. 可以查看驾驶员工资汇总
7. 可以查看单趟利润
8. 作废台账不计入统计
9. 待审核费用不计入正式成本
10. 权限控制正确
```

---

# 阶段 11：微信 / WorkBuddy / 飞书 Agent 识别草稿

## 阶段目标

让微信或 WorkBuddy 里的聊天内容可以被 Agent 识别为高空车台账草稿、垫付草稿、报销确认草稿、查询请求。

## 关键原则

```text
Agent 只生成草稿，不自动入账。
Agent 不能自动确认收款。
Agent 不能自动报销。
Agent 不能自动发工资。
Agent 不能删除台账。
```

## 给 Vibe Coding 的提示词

```text
你现在负责为广告公司 ERP 的“高空作业车台账”模块新增微信/WorkBuddy/飞书 Agent 识别草稿功能。

背景：
公司大量业务在微信里沟通。高空作业车驾驶员、老板、业务员可能通过微信发送：
- 今天去了哪里干活
- 收了多少钱
- 客户有没有付款
- 司机垫付了多少油费、停车费、过路费
- 车辆出了什么问题
- 老板查询本月高空车收入和利润

本阶段目标：
实现统一消息接入接口，将微信/WorkBuddy/飞书消息识别为高空车相关业务草稿。

重要限制：
1. Agent 只能生成草稿
2. Agent 不能自动确认收款
3. Agent 不能自动报销
4. Agent 不能自动发工资
5. Agent 不能删除台账
6. 所有草稿必须人工确认后才能写入正式台账

请实现：

一、统一消息输入 API
POST /api/aerial/agent/messages/ingest

输入格式：
{
  "platform": "workbuddy_wechat",
  "conversation_id": "xxx",
  "message_id": "xxx",
  "sender_id": "xxx",
  "sender_name": "王师傅",
  "message_type": "text",
  "content": "今天去万达广场装门头，高空车收800，油费我垫了120，停车20。",
  "attachments": [],
  "sent_at": "2026-07-23T10:00:00+08:00"
}

二、需要识别的意图
1. aerial_work_ledger
   高空车出车台账

2. aerial_driver_expense
   驾驶员垫付费用

3. aerial_payment_claim
   客户声称已付款 / 司机说客户已付

4. aerial_vehicle_issue
   车辆异常 / 维修问题

5. aerial_query_report
   查询高空车统计

6. aerial_reimbursement_claim
   报销确认类消息

7. normal_chat
   普通消息

三、识别输出格式
{
  "intent": "aerial_work_ledger",
  "confidence": 0.88,
  "risk_level": "medium",
  "extracted": {
    "work_date": "2026-07-23",
    "driver_name": "王师傅",
    "work_location": "万达广场",
    "work_content": "装门头",
    "receivable_amount": 800,
    "received_amount": null,
    "payment_status": "unknown",
    "driver_expenses": [
      {"expense_type": "油费", "amount": 120},
      {"expense_type": "停车费", "amount": 20}
    ]
  },
  "suggested_action": "create_aerial_ledger_draft",
  "requires_confirmation": true
}

四、示例识别
示例 1：
输入：今天去万达装门头，高空车收800，油费我垫了120
输出：
- intent = aerial_work_ledger
- 地点 = 万达
- 作业内容 = 装门头
- 应收金额 = 800
- 垫付费用 = 油费 120
- suggested_action = create_aerial_ledger_draft
- requires_confirmation = true

示例 2：
输入：今天停车费20，过路费35，我垫的
输出：
- intent = aerial_driver_expense
- 垫付费用 = 停车费20，过路费35
- 需要匹配当天该司机台账
- 匹配不准时生成待选择草稿

示例 3：
输入：客户说钱已经转了
输出：
- intent = aerial_payment_claim
- 只能生成财务核对提醒
- 不能自动确认收款

示例 4：
输入：高空车右后轮没气了
输出：
- intent = aerial_vehicle_issue
- 生成车辆维修/异常草稿

示例 5：
输入：这个月高空车赚了多少钱
输出：
- intent = aerial_query_report
- 调用统计 API 返回摘要

五、草稿中心
新增或复用 aerial_agent_draft_actions，用于保存：
- 原始消息
- 识别结果
- 提取字段
- 建议动作
- 草稿状态
- 人工确认状态

六、人工确认流程
1. Agent 接收消息
2. 识别意图和字段
3. 生成草稿
4. 推送到 ERP 草稿中心，后续可推送飞书/微信
5. 人工确认
6. 系统再次校验权限
7. 写入正式台账/费用/提醒
8. 写入审计日志

七、查询类消息
对于“这个月高空车赚了多少钱”这类查询：
1. 需要校验发送人权限
2. 老板/财务可以看利润
3. 驾驶员只能看自己的出车和工资
4. 普通员工不能看利润

验收标准：
1. 可以接收 WorkBuddy 微信消息
2. 可以保存原始消息
3. 可以识别高空车出车台账
4. 可以识别司机垫付
5. 可以识别付款声称但不自动确认收款
6. 可以识别车辆异常
7. 可以生成草稿
8. 草稿需要人工确认
9. 人工确认后才能写入正式台账
10. Agent 不能自动报销
11. Agent 不能自动发工资
12. 查询报表时权限控制正确
13. 所有消息和草稿有审计记录
```

---

# 阶段 12：权限、审计、测试与回滚

## 阶段目标

这是上线前的收口阶段，重点做权限安全、审计日志、测试用例、数据备份和回滚方案。

## 给 Vibe Coding 的提示词

```text
你现在负责对“高空作业车台账”模块做上线前安全检查、权限检查、审计日志检查、测试用例补全和回滚方案。

模块范围：
- 高空车档案
- 每日出车台账
- 驾驶员垫付/报销
- 驾驶员工资
- 车辆费用
- 收款结算
- 安全检查
- 附件上传
- 统计报表
- 微信/WorkBuddy/飞书 Agent 草稿

请完成以下工作：

一、权限检查
角色包括：
1. 老板
2. 管理员
3. 财务
4. 安装主管
5. 业务员
6. 驾驶员
7. 普通员工
8. Agent 系统用户

权限规则：
1. 老板可以查看全部台账、收入、成本、利润、工资、报销
2. 管理员可以管理台账、车辆、费用、安全检查
3. 财务可以确认收款、审核报销、查看工资、查看利润
4. 安装主管可以查看安装相关台账，不能确认收款和发工资
5. 业务员只能查看自己客户/订单相关台账
6. 驾驶员只能查看自己的出车、垫付、报销、工资
7. 普通员工不能查看利润、工资、全部费用
8. Agent 只能生成草稿和查询有权限的数据，不能执行高风险写操作

二、高风险操作检查
以下操作必须有权限和审计：
1. 修改应收金额
2. 修改实收金额
3. 确认收款
4. 审核报销
5. 标记已报销
6. 计算工资
7. 标记工资已发放
8. 作废台账
9. 修改已审核台账
10. 删除/作废费用
11. Agent 草稿确认执行

三、审计日志检查
每条审计日志至少包含：
- 操作人
- 操作时间
- 操作类型
- 操作对象
- 来源：ERP、微信 Agent、飞书 Agent、系统
- 操作前数据
- 操作后数据
- 备注

四、测试用例
请补充自动化测试或接口测试，覆盖：

基础台账：
1. 新增台账成功
2. 缺少必填项失败
3. 金额自动计算正确
4. 未收金额自动计算正确
5. 利润自动计算正确
6. 作废台账不进入统计

垫付报销：
1. 新增垫付成功
2. 审核通过后计入成本
3. 驳回后不计入成本
4. 标记已报销成功
5. 无权限不能审核

工资：
1. 单趟工资记录成功
2. 月度工资汇总正确
3. 驾驶员只能查看自己工资
4. Agent 不能发工资

车辆费用：
1. 新增费用成功
2. 关联台账后影响利润
3. 审核通过后计入成本
4. 驳回后不计入成本

收款：
1. 财务可以确认收款
2. 普通员工不能确认收款
3. Agent 不能确认收款
4. 收款后状态自动更新

Agent：
1. 微信消息能生成台账草稿
2. 付款消息只生成核对提醒
3. 垫付消息生成草稿
4. 草稿未确认不能写正式台账
5. 人工确认后写入正式台账

权限：
1. 老板看全部
2. 财务看金额和成本
3. 驾驶员只能看自己
4. 普通员工不能看利润

五、备份与回滚
请提供：
1. 数据库备份命令
2. 迁移回滚命令
3. 出错时如何禁用高空车模块菜单
4. 如何保留数据但关闭 Agent 入口
5. 如何恢复到上线前状态

六、上线检查清单
输出一份上线前 checklist。

验收标准：
1. 所有关键权限通过测试
2. 所有高风险操作有审计日志
3. 所有核心 API 有测试
4. Agent 不能执行高风险动作
5. 作废台账不计入统计
6. 备份方案可执行
7. 回滚方案可执行
8. 输出上线前 checklist
```

---

# 阶段 13：上线后优化计划

## 阶段目标

第一版上线稳定后，再逐步增强体验和自动化能力。

## 后续可迭代功能

```text
1. 微信图片票据识别
2. 微信语音转文字识别台账
3. 自动生成每日高空车日报
4. 自动生成月度高空车经营报表
5. 高空车费用分摊模型
6. 折旧模型
7. 保险/年检/保养到期提醒
8. 驾驶员绩效统计
9. 客户欠款提醒
10. 高空车对外出租报价规则
11. 关联小程序客户确认
12. 飞书/企业微信审批卡片
13. GPS/轨迹记录
14. 高空作业安全检查标准化表单
15. 现场施工照片自动归档
```

## 给 Vibe Coding 的提示词

```text
你现在负责为“高空作业车台账”模块设计上线后的优化路线，不要直接开发。

请基于当前已上线模块，输出后续三期迭代规划：

第二期：体验优化
- 快速录入台账
- 手机端适配
- 图片上传优化
- 待收款提醒
- 待报销提醒
- 日报推送

第三期：Agent 增强
- 微信语音转文字
- 图片票据识别
- 聊天内容自动生成台账草稿
- 飞书/企业微信审批确认
- 老板微信查询经营报表

第四期：经营分析
- 月度利润分析
- 单趟利润排名
- 客户贡献分析
- 驾驶员绩效
- 车辆费用分摊
- 折旧模型
- 高空车对外出租报价建议

请输出：
1. 每期目标
2. 每期功能清单
3. 每期风险
4. 每期验收标准
5. 每期适合给 Vibe Coding 的开发提示词
```

---

# 通用提示词模板：每次开发前都可以加上

```text
你现在是我的高级全栈工程师，负责开发本地部署的广告公司 ERP 系统。

总原则：
1. 不要破坏现有功能
2. 不要直接修改生产数据
3. 不要删除现有业务数据
4. 不要硬编码密钥
5. 所有密钥放入 .env
6. 所有数据库结构变化必须有迁移脚本和回滚脚本
7. 所有关键操作必须写审计日志
8. 所有金额字段必须使用 decimal/numeric
9. 所有高风险动作必须人工确认
10. Agent 只能生成草稿，不能直接执行财务和结算动作
11. 开发前先阅读项目结构
12. 修改前先输出实施计划、涉及文件、数据库迁移方案、测试方案
13. 等确认后再开始写代码

业务背景：
我们是一家广告制作安装公司，系统需要管理客户、订单、报价、生产、安装、财务、车辆、高空作业车、微信/飞书 Agent 等业务。

本次任务：
【在这里填写本次具体任务】

验收标准：
【在这里填写本次具体验收标准】
```

---

# 最终落地顺序建议

建议按下面顺序开发：

```text
阶段 0：项目现状扫描与安全准备
阶段 1：数据库模型与迁移脚本
阶段 2：后端基础 API
阶段 3：前端菜单、首页和台账列表页
阶段 4：新增/编辑/详情台账页面
阶段 5：驾驶员垫付与报销
阶段 6：驾驶员工资核算
阶段 7：车辆费用管理
阶段 8：收款结算与待收款管理
阶段 9：安全检查与附件管理
阶段 10：统计报表
阶段 11：微信 / WorkBuddy / 飞书 Agent 识别草稿
阶段 12：权限、审计、测试与回滚
阶段 13：上线后优化计划
```

推荐第一轮 MVP 只完成到阶段 10，先不要急着自动化微信 Agent。

最小可上线版本：

```text
1. 高空车档案
2. 每日出车台账
3. 应收/实收/未收
4. 驾驶员垫付
5. 报销审核
6. 驾驶员工资
7. 车辆费用
8. 台账详情
9. 月度统计
10. 权限和审计
```

等 MVP 稳定后，再做：

```text
1. 微信识别台账草稿
2. 飞书/企业微信审批
3. 老板日报
4. 高空车经营分析
5. 更复杂的费用分摊和折旧模型
```
