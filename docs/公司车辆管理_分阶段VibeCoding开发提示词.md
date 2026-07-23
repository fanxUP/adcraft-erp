# 公司车辆管理模块｜分阶段 Vibe Coding 开发提示词

> 适用场景：广告公司 ERP 系统  
> 模块定位：公司普通车辆管理、司机管理、用车申请、派车、出车/收车、油费维修保险年检、车辆费用统计、安装/送货/外勤关联、微信/飞书 Agent 辅助识别。  
> 说明：本文件用于复制给 Codex / Cursor / Claude Code / Trae / Windsurf 等 AI 编程工具，按阶段开发落地。  
> 注意：**高空作业车台账建议作为独立模块开发**，本文件主要面向普通公司车辆，例如面包车、货车、皮卡、轿车、电动车、三轮车、外租车辆等。

---

## 0. 项目总原则

公司车辆管理模块不是单纯登记车辆信息，而是为了让广告公司日常安装、送货、采购、外勤、售后用车形成完整闭环。

核心目标：

```text
车辆有档案
司机有记录
用车有申请
派车有安排
出车有台账
收车有回执
费用有归集
订单有关联
成本可统计
异常可追溯
到期有提醒
Agent 可辅助
```

开发顺序必须遵守：

```text
先档案
后流程
先只读
后写入
先内部
后客户
先手动
后 Agent
先审计
后自动化
```

---

## 1. 模块边界

### 1.1 本模块包含

```text
1. 车辆档案
2. 司机档案
3. 用车申请
4. 用车审批
5. 派车管理
6. 安装任务关联车辆
7. 出车记录
8. 收车记录
9. 油费记录
10. 维修保养记录
11. 保险/年检/证件管理
12. 违章/事故记录
13. 车辆费用统计
14. 订单运输成本分摊
15. 到期提醒
16. 微信/飞书 Agent 识别用车消息并生成草稿
17. 操作日志和权限控制
```

### 1.2 本模块不包含

```text
1. 高空作业车每日经营台账
2. 高空车单趟收入利润核算
3. GPS 实时定位
4. 复杂车队调度算法
5. 油卡自动对接
6. OBD 车辆数据采集
7. 自动识别违章
8. 自动结算司机工资
9. 自动确认财务报销
```

高空作业车请使用独立模块：

```text
高空作业车台账 / 高空车经营台账 / 高空车每日出车结算
```

普通车辆模块和高空车模块可以共享：

```text
员工表
司机表
车辆基础档案
附件表
操作日志
费用类型字典
权限系统
Agent 消息识别中台
```

但高空车的每日经营收入、单趟利润、司机工资、垫付报销建议独立建表。

---

## 2. 总体功能结构

建议菜单：

```text
车辆管理
├── 车辆看板
├── 车辆档案
├── 司机档案
├── 用车申请
├── 派车管理
├── 出车/收车台账
├── 油费记录
├── 维修保养
├── 保险年检
├── 违章事故
├── 车辆费用
├── 成本分摊
├── 到期提醒
├── 车辆报表
└── 车辆设置
```

---

## 3. 推荐开发阶段

```text
P0：项目结构识别与实施计划
P1：数据库模型与迁移脚本
P2：车辆档案管理
P3：司机档案管理
P4：用车申请与审批
P5：派车管理与安装任务关联
P6：出车/收车台账
P7：车辆费用管理
P8：保险年检与到期提醒
P9：违章事故与异常记录
P10：车辆成本统计与订单分摊
P11：权限控制与审计日志
P12：微信/飞书 Agent 识别草稿
P13：报表看板与老板日报
P14：测试、上线、备份、回滚
```

---

# P0｜项目结构识别与实施计划

## 阶段目标

让 AI 先读项目，不要直接写代码。  
确认现有 ERP 技术栈、目录结构、数据库、权限系统、员工表、订单表、安装任务表、财务费用表、文件上传能力。

---

## 给 AI 的提示词

```text
你现在是我的高级产品经理、系统架构师和全栈工程师，负责为本地部署的广告公司 ERP 系统增加“公司车辆管理”模块。

项目背景：
- 我们是一家广告制作安装公司
- ERP 已经包含客户、订单、报价、生产、安装、财务等模块
- 公司有普通车辆，例如面包车、货车、皮卡、轿车、电动车、三轮车、外租车辆
- 车辆主要用于安装、送货、采购、客户测量、售后、外勤
- 后续还会有单独的“高空作业车台账”模块，本次只开发普通公司车辆管理模块
- 车辆管理需要和员工、订单、安装任务、财务费用、微信/飞书 Agent 打通
- 第一阶段以 ERP 内部使用为主
- 所有关键操作必须记录审计日志
- 财务费用、报销审核、删除记录等高风险动作必须人工确认

本次任务：
请先阅读现有项目结构，不要直接修改代码。

请完成以下分析：
1. 项目使用的技术栈
2. 后端目录结构
3. 前端目录结构
4. 数据库迁移方式
5. 权限系统位置
6. 员工/用户表位置
7. 客户表位置
8. 订单表位置
9. 安装任务表位置
10. 财务费用表位置
11. 文件上传/附件模块位置
12. 审计日志或操作日志模块位置
13. 适合新增车辆管理模块的目录位置
14. 需要新增的后端文件
15. 需要新增的前端页面
16. 需要新增的数据库迁移脚本
17. 可能影响现有业务的风险点
18. 分阶段开发计划
19. 本阶段不做哪些事情

输出格式：
- 项目结构分析
- 现有可复用模块
- 新增模块设计建议
- 数据库迁移方案
- API 设计草案
- 前端页面草案
- 权限接入方案
- 测试方案
- 风险与回滚方案

要求：
1. 不要直接写代码
2. 不要破坏现有功能
3. 不要删除现有文件
4. 不要重构大范围代码
5. 先给我实施计划，等我确认后再进入 P1
```

---

## 验收标准

```text
1. AI 已识别项目结构
2. AI 已说明车辆管理模块放在哪里
3. AI 已列出复用的现有表和模块
4. AI 已给出数据库迁移方案
5. AI 已给出 API 和页面草案
6. AI 没有直接修改代码
```

---

# P1｜数据库模型与迁移脚本

## 阶段目标

新增普通车辆管理所需数据表。  
优先复用现有员工、订单、安装任务、财务模块。

---

## 推荐数据表

```text
1. vehicles                      # 车辆档案
2. vehicle_drivers               # 司机档案
3. vehicle_use_requests          # 用车申请
4. vehicle_dispatches            # 派车单
5. vehicle_trip_records          # 出车/收车台账
6. vehicle_fuel_records          # 油费记录
7. vehicle_maintenance_records   # 维修保养
8. vehicle_certificates          # 保险/年检/证件
9. vehicle_incidents             # 违章/事故/异常
10. vehicle_cost_records         # 车辆费用统一表，可选
11. vehicle_cost_allocations     # 费用分摊
12. vehicle_operation_logs       # 车辆操作日志
13. vehicle_attachments          # 车辆附件，可选，若已有附件表则复用
```

---

## 车辆状态字典

```text
available      可用
assigned       已派车
in_use         出车中
maintenance    维修中
disabled       停用
scrapped       报废
rented         外租
```

---

## 用车申请状态

```text
draft          草稿
pending        待审批
approved       已审批
rejected       已驳回
dispatched     已派车
cancelled      已取消
completed      已完成
```

---

## 派车状态

```text
assigned       已派车
started        已出车
arrived        已到达
completed      已完成
returned       已收车
cancelled      已取消
abnormal       异常
```

---

## 费用审核状态

```text
pending_review 待审核
approved       已审核
rejected       已驳回
reimbursed     已报销
paid           已付款
```

---

## 给 AI 的提示词

```text
你现在负责为广告公司 ERP 新增“公司车辆管理”模块的数据库模型和迁移脚本。

背景：
- 车辆管理模块用于普通公司车辆，不包含高空作业车每日经营台账
- 车辆主要用于安装、送货、采购、售后、外勤
- 需要关联现有客户、订单、安装任务、员工、财务费用
- 优先复用现有 users/employees、customers、orders、installation_tasks 等表
- 如果项目已有附件表、审计日志表，请优先复用
- 不允许破坏现有表结构
- 不允许删除现有字段
- 新增字段必须有默认值或允许为空，避免迁移失败

本次任务：
新增车辆管理数据库迁移脚本。

需要新增表：
1. vehicles
2. vehicle_drivers
3. vehicle_use_requests
4. vehicle_dispatches
5. vehicle_trip_records
6. vehicle_fuel_records
7. vehicle_maintenance_records
8. vehicle_certificates
9. vehicle_incidents
10. vehicle_cost_allocations
11. vehicle_operation_logs

字段要求：

vehicles：
- id
- vehicle_code
- plate_number
- vehicle_name
- vehicle_type
- brand_model
- color
- purchase_date
- status
- department_id
- default_driver_id
- load_capacity
- seats
- vehicle_photo_url
- license_photo_url
- remark
- created_at
- updated_at

vehicle_drivers：
- id
- employee_id
- driver_name
- phone
- license_no
- license_type
- license_expire_date
- is_external
- status
- remark
- created_at
- updated_at

vehicle_use_requests：
- id
- request_no
- requester_id
- reason
- related_customer_id
- related_order_id
- related_install_task_id
- start_time
- expected_return_time
- destination
- need_driver
- need_cargo
- cargo_description
- estimated_distance_km
- status
- approver_id
- approved_at
- remark
- created_at
- updated_at

vehicle_dispatches：
- id
- dispatch_no
- request_id
- vehicle_id
- driver_id
- related_customer_id
- related_order_id
- related_install_task_id
- start_location
- destination
- planned_start_time
- planned_return_time
- actual_start_time
- actual_return_time
- start_mileage
- end_mileage
- actual_distance_km
- status
- abnormal_flag
- abnormal_description
- remark
- created_by
- created_at
- updated_at

vehicle_trip_records：
- id
- trip_no
- dispatch_id
- vehicle_id
- driver_id
- trip_date
- start_time
- return_time
- start_mileage
- end_mileage
- distance_km
- start_photo_url
- return_photo_url
- start_remark
- return_remark
- abnormal_flag
- abnormal_description
- created_at
- updated_at

vehicle_fuel_records：
- id
- vehicle_id
- driver_id
- dispatch_id
- fuel_time
- amount
- liters
- unit_price
- gas_station
- mileage
- payment_method
- payer_id
- receipt_url
- status
- remark
- created_at
- updated_at

vehicle_maintenance_records：
- id
- vehicle_id
- maintenance_type
- maintenance_date
- maintenance_item
- repair_shop
- amount
- mileage
- next_maintenance_mileage
- next_maintenance_date
- handler_id
- invoice_url
- before_photo_url
- after_photo_url
- status
- remark
- created_at
- updated_at

vehicle_certificates：
- id
- vehicle_id
- certificate_type
- certificate_no
- start_date
- expire_date
- amount
- file_url
- reminder_days
- status
- remark
- created_at
- updated_at

vehicle_incidents：
- id
- vehicle_id
- driver_id
- incident_type
- incident_time
- location
- description
- fine_amount
- points_deducted
- responsible_user_id
- status
- evidence_url
- remark
- created_at
- updated_at

vehicle_cost_allocations：
- id
- source_type
- source_id
- vehicle_id
- dispatch_id
- related_order_id
- related_install_task_id
- cost_type
- amount
- allocation_method
- allocation_date
- remark
- created_at
- updated_at

vehicle_operation_logs：
- id
- operator_id
- action
- target_type
- target_id
- before_json
- after_json
- ip_address
- user_agent
- created_at

索引要求：
1. vehicles.plate_number 唯一索引
2. vehicles.status 普通索引
3. vehicle_dispatches.vehicle_id + planned_start_time + planned_return_time 索引
4. vehicle_dispatches.driver_id 索引
5. vehicle_dispatches.related_order_id 索引
6. vehicle_fuel_records.vehicle_id + fuel_time 索引
7. vehicle_certificates.vehicle_id + expire_date 索引
8. vehicle_operation_logs.target_type + target_id 索引

约束要求：
1. 车牌号不能为空且唯一
2. 金额字段默认 0
3. 状态字段使用字符串枚举
4. 时间字段允许为空，避免草稿阶段无法保存
5. 外键如果现有项目不强制使用，也可以只保留 ID 字段并建立索引

验收标准：
1. 迁移脚本可以正常执行
2. 迁移脚本可以回滚
3. 新表创建成功
4. 车牌号唯一约束生效
5. 索引创建成功
6. 不影响现有表
7. 提供测试 SQL 或测试命令
8. 提供回滚方式

请先生成迁移方案和迁移脚本，执行前说明会影响哪些表。
```

---

# P2｜车辆档案管理

## 阶段目标

实现车辆新增、编辑、查看、停用、列表筛选。

---

## 字段建议

```text
车辆编号
车牌号
车辆名称
车辆类型
品牌型号
颜色
购买日期
车辆状态
所属部门
默认司机
载重信息
座位数
车辆照片
行驶证照片
备注
```

---

## 车辆类型

```text
面包车
货车
皮卡
轿车
电动车
三轮车
外租车辆
其他
```

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“车辆档案管理”功能。

背景：
- 数据库迁移已完成
- 本阶段只开发 vehicles 车辆档案 CRUD
- 不涉及派车、费用、维修等复杂流程
- 车辆档案是后续用车申请、派车、费用统计的基础
- 车牌号必须唯一
- 删除车辆默认不物理删除，应该改为停用或报废状态

本次目标：
实现车辆档案管理。

后端 API：
1. GET /api/vehicles
   - 支持分页
   - 支持按车牌号、车辆名称、车辆类型、状态、默认司机筛选

2. POST /api/vehicles
   - 新增车辆
   - 校验车牌号唯一
   - 默认状态 available

3. GET /api/vehicles/{id}
   - 查看车辆详情

4. PATCH /api/vehicles/{id}
   - 编辑车辆信息
   - 修改车牌号时校验唯一

5. POST /api/vehicles/{id}/disable
   - 停用车辆

6. POST /api/vehicles/{id}/enable
   - 启用车辆

7. POST /api/vehicles/{id}/scrap
   - 标记报废

前端页面：
1. 车辆列表页
2. 新增车辆弹窗或页面
3. 编辑车辆页面
4. 车辆详情页基础信息 Tab

车辆列表字段：
- 车牌号
- 车辆名称
- 车辆类型
- 品牌型号
- 状态
- 默认司机
- 保险到期
- 年检到期
- 本月费用
- 操作

页面筛选：
- 车牌号
- 车辆类型
- 状态
- 默认司机

权限：
1. 老板和管理员可以新增/编辑/停用车辆
2. 安装主管可以查看车辆
3. 普通员工只能查看可用车辆基础信息
4. 财务可以查看车辆费用相关信息，但本阶段可先不实现费用

审计日志：
以下操作必须写日志：
1. 新增车辆
2. 编辑车辆
3. 停用车辆
4. 启用车辆
5. 报废车辆

验收标准：
1. 可以新增车辆
2. 车牌号重复时提示错误
3. 可以编辑车辆
4. 可以按状态筛选车辆
5. 可以停用车辆
6. 停用车辆不在可派车车辆中出现
7. 报废车辆不能再次派车
8. 所有关键操作写入日志
9. 不影响现有 ERP 功能
```

---

# P3｜司机档案管理

## 阶段目标

实现司机档案，司机可以绑定员工，也可以是外协人员。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“司机档案管理”功能。

背景：
- 车辆档案管理已完成
- 司机可以是公司员工，也可以是外协司机
- 如果是公司员工，需要绑定现有员工表
- 如果是外协司机，可以不绑定员工，只记录姓名和电话
- 驾驶证到期需要后续提醒

本次目标：
实现 vehicle_drivers 司机档案管理。

后端 API：
1. GET /api/vehicle-drivers
2. POST /api/vehicle-drivers
3. GET /api/vehicle-drivers/{id}
4. PATCH /api/vehicle-drivers/{id}
5. POST /api/vehicle-drivers/{id}/disable
6. POST /api/vehicle-drivers/{id}/enable

司机字段：
- 司机姓名
- 绑定员工
- 手机号
- 驾驶证号
- 驾驶证类型
- 驾驶证到期日
- 是否外协人员
- 状态
- 备注

前端页面：
1. 司机列表
2. 新增司机
3. 编辑司机
4. 司机详情

司机列表字段：
- 司机姓名
- 是否员工
- 手机号
- 驾驶证类型
- 驾驶证到期日
- 状态
- 操作

权限：
1. 老板和管理员可以管理司机
2. 安装主管可以查看司机
3. 司机本人只能查看自己的基础信息

审计日志：
1. 新增司机
2. 编辑司机
3. 停用司机
4. 启用司机

验收标准：
1. 可以新增公司员工司机
2. 可以新增外协司机
3. 可以编辑司机信息
4. 可以停用司机
5. 停用司机不能被派车
6. 驾驶证到期日可以保存
7. 所有关键操作写入日志
```

---

# P4｜用车申请与审批

## 阶段目标

业务员、安装主管、生产主管等可以提交用车申请。  
管理员或安装主管审批。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“用车申请与审批”功能。

背景：
- 车辆档案和司机档案已完成
- 公司用车场景包括安装、送货、采购、售后、外勤、客户测量
- 用车申请可以关联客户、订单、安装任务
- 本阶段只做申请和审批，不做正式派车
- 审批通过后进入待派车状态

本次目标：
实现 vehicle_use_requests 用车申请流程。

后端 API：
1. GET /api/vehicle-use-requests
2. POST /api/vehicle-use-requests
3. GET /api/vehicle-use-requests/{id}
4. PATCH /api/vehicle-use-requests/{id}
5. POST /api/vehicle-use-requests/{id}/submit
6. POST /api/vehicle-use-requests/{id}/approve
7. POST /api/vehicle-use-requests/{id}/reject
8. POST /api/vehicle-use-requests/{id}/cancel

用车申请字段：
- 申请人
- 用车原因
- 关联客户
- 关联订单
- 关联安装任务
- 出发时间
- 预计返回时间
- 目的地
- 是否需要司机
- 是否需要装货
- 货物说明
- 预计里程
- 备注

申请状态：
- draft
- pending
- approved
- rejected
- dispatched
- cancelled
- completed

前端页面：
1. 用车申请列表
2. 新增用车申请
3. 用车申请详情
4. 审批操作区

列表筛选：
- 日期
- 申请人
- 状态
- 用车原因
- 关联订单
- 目的地

权限：
1. 员工可以提交自己的用车申请
2. 业务员可以关联自己的订单
3. 安装主管可以审批安装相关用车
4. 管理员可以审批所有用车
5. 普通员工不能审批
6. 已审批的申请不能随意修改核心字段，需要撤回或重新提交

审计日志：
1. 创建申请
2. 提交申请
3. 审批通过
4. 审批驳回
5. 取消申请

验收标准：
1. 可以创建用车申请草稿
2. 可以提交审批
3. 管理员可以审批
4. 非授权人员不能审批
5. 驳回时需要填写原因
6. 审批通过后状态为 approved
7. 取消后不能派车
8. 所有关键操作写入日志
```

---

# P5｜派车管理与安装任务关联

## 阶段目标

审批通过后安排车辆和司机。  
检查车辆时间冲突，维修/停用/报废车辆不能派车。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“派车管理”功能。

背景：
- 用车申请与审批已完成
- 已审批的用车申请可以生成派车单
- 派车必须选择车辆和司机
- 派车可以关联客户、订单、安装任务
- 同一车辆在同一时间段不能重复派车
- 维修中、停用、报废车辆不能派车
- 停用司机不能派车

本次目标：
实现 vehicle_dispatches 派车管理。

后端 API：
1. GET /api/vehicle-dispatches
2. POST /api/vehicle-dispatches
3. GET /api/vehicle-dispatches/{id}
4. PATCH /api/vehicle-dispatches/{id}
5. POST /api/vehicle-dispatches/{id}/cancel
6. GET /api/vehicles/available
7. GET /api/vehicle-drivers/available

派车字段：
- 派车单号
- 用车申请
- 车辆
- 司机
- 随车人员
- 关联客户
- 关联订单
- 关联安装任务
- 出发地点
- 目的地
- 计划出发时间
- 计划返回时间
- 装载物料
- 备注

业务规则：
1. 只有 approved 申请可以派车
2. 派车后申请状态改为 dispatched
3. 车辆状态改为 assigned
4. 已派车但未出车时可以取消
5. 取消派车后车辆恢复 available
6. 车辆时间段冲突时禁止派车
7. 车辆状态不是 available 时禁止派车
8. 司机状态不是 active 时禁止派车
9. 安装任务关联车辆后，可在安装任务详情看到派车信息

前端页面：
1. 派车管理列表
2. 待派车申请列表
3. 新增派车单
4. 派车单详情
5. 可用车辆选择器
6. 可用司机选择器

权限：
1. 管理员可以派车
2. 安装主管可以派安装相关车辆
3. 业务员只能查看自己订单相关派车
4. 司机只能查看自己的派车任务

审计日志：
1. 生成派车单
2. 修改派车单
3. 取消派车
4. 车辆状态变更

验收标准：
1. 已审批申请可以生成派车单
2. 未审批申请不能派车
3. 维修中车辆不能派车
4. 停用车辆不能派车
5. 报废车辆不能派车
6. 同一时间段车辆不能重复派车
7. 派车后车辆状态变为 assigned
8. 取消派车后车辆恢复 available
9. 安装任务详情能看到派车信息
10. 所有关键操作写入日志
```

---

# P6｜出车/收车台账

## 阶段目标

司机出车时记录出车时间和里程，收车时记录收车时间和里程，自动计算实际公里数。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“出车/收车台账”功能。

背景：
- 派车管理已完成
- 派车单生成后，司机需要出车打卡和收车回执
- 出车时记录出车时间、出车里程、出车照片
- 收车时记录收车时间、收车里程、收车照片、车辆异常
- 系统自动计算实际行驶里程
- 出车/收车记录用于车辆费用和订单运输成本统计

本次目标：
实现 vehicle_trip_records 出车/收车台账。

后端 API：
1. POST /api/vehicle-dispatches/{id}/start
2. POST /api/vehicle-dispatches/{id}/arrive
3. POST /api/vehicle-dispatches/{id}/finish
4. POST /api/vehicle-dispatches/{id}/return
5. GET /api/vehicle-trip-records
6. GET /api/vehicle-trip-records/{id}

出车字段：
- 派车单
- 车辆
- 司机
- 出车时间
- 出车里程
- 出车照片
- 出车备注

到达字段：
- 到达时间
- 到达备注
- 可选现场照片

收车字段：
- 收车时间
- 收车里程
- 实际公里数
- 收车照片
- 车辆是否异常
- 异常说明
- 司机备注

业务规则：
1. 只有 assigned 状态的派车单可以出车
2. 出车后派车状态改为 started
3. 车辆状态改为 in_use
4. 收车里程必须大于等于出车里程
5. 收车后自动计算公里数
6. 收车后派车状态改为 returned
7. 收车后车辆状态恢复 available，除非有异常
8. 如果车辆异常，车辆状态改为 maintenance 或 abnormal
9. 司机只能操作自己的派车单
10. 管理员可以代操作，但必须写日志

前端页面：
1. 我的派车任务
2. 出车确认页
3. 到达现场页
4. 收车回执页
5. 出车/收车台账列表

权限：
1. 司机只能查看和操作自己的派车任务
2. 管理员可以查看全部
3. 安装主管可以查看安装相关
4. 普通员工不能查看全部车辆位置和任务

审计日志：
1. 出车
2. 到达
3. 完工
4. 收车
5. 异常上报
6. 车辆状态变更

验收标准：
1. 司机可以出车
2. 出车后车辆状态变为 in_use
3. 司机可以收车
4. 收车里程小于出车里程时提示错误
5. 收车后自动计算公里数
6. 正常收车后车辆恢复 available
7. 异常收车后车辆进入异常或维修状态
8. 非司机本人不能随意操作派车单
9. 所有关键操作写入日志
```

---

# P7｜车辆费用管理

## 阶段目标

记录油费、维修、保养、保险、年检、违章、停车费、过路费、外租车辆费等。

---

## 费用类型

```text
油费
过路费
停车费
维修费
保养费
保险费
年检费
违章罚款
事故维修
轮胎
电瓶
洗车费
外租车辆费
司机补贴
其他
```

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“车辆费用管理”功能。

背景：
- 车辆档案、派车、出车/收车台账已完成
- 车辆费用需要关联车辆、司机、派车单、订单、安装任务
- 司机可能垫付油费、停车费、过路费
- 财务需要审核费用
- 普通员工不能查看全部车辆费用
- 本阶段只做普通车辆费用，不做高空车经营收入台账

本次目标：
实现车辆费用管理，包括油费、维修保养、保险年检、违章事故等费用记录。

后端 API：
1. GET /api/vehicle-fuel-records
2. POST /api/vehicle-fuel-records
3. PATCH /api/vehicle-fuel-records/{id}
4. POST /api/vehicle-fuel-records/{id}/review

5. GET /api/vehicle-maintenance-records
6. POST /api/vehicle-maintenance-records
7. PATCH /api/vehicle-maintenance-records/{id}
8. POST /api/vehicle-maintenance-records/{id}/review

9. GET /api/vehicle-cost-records
10. POST /api/vehicle-cost-records
11. POST /api/vehicle-cost-records/{id}/review

油费字段：
- 车辆
- 司机
- 派车单
- 加油时间
- 金额
- 升数
- 单价
- 加油站
- 当前里程
- 支付方式
- 付款人
- 是否司机垫付
- 票据照片
- 审核状态
- 备注

维修保养字段：
- 车辆
- 维修类型
- 维修日期
- 维修项目
- 维修厂
- 金额
- 当前里程
- 下次保养里程
- 下次保养日期
- 经办人
- 发票照片
- 维修前照片
- 维修后照片
- 审核状态
- 备注

通用费用字段：
- 费用日期
- 车辆
- 司机
- 派车单
- 费用类型
- 金额
- 支付方式
- 付款人
- 是否司机垫付
- 是否需要报销
- 票据照片
- 关联订单
- 关联安装任务
- 审核状态
- 备注

业务规则：
1. 费用可以关联派车单
2. 费用可以关联订单或安装任务
3. 司机提交的费用默认 pending_review
4. 财务审核通过后才能计入正式成本
5. 被驳回的费用不计入成本
6. 费用审核必须写日志
7. 司机垫付费用不能自动报销，只能进入待报销状态
8. 财务确认后才可标记已报销
9. 普通员工不能查看全部车辆费用
10. 成本和报销不能混为一项，需要区分费用审核状态和报销状态

前端页面：
1. 车辆费用列表
2. 新增费用
3. 油费记录
4. 维修保养记录
5. 待审核费用
6. 费用详情

权限：
1. 司机可以提交自己的费用
2. 财务可以审核费用
3. 老板可以查看全部费用
4. 管理员可以管理费用
5. 普通员工不能查看全部费用
6. 业务员只能查看自己订单相关车辆费用摘要

审计日志：
1. 新增费用
2. 编辑费用
3. 审核通过
4. 审核驳回
5. 标记报销
6. 删除/作废费用

验收标准：
1. 可以新增油费
2. 可以上传票据
3. 可以关联派车单
4. 可以关联订单
5. 财务可以审核费用
6. 审核通过后计入车辆成本
7. 驳回后不计入车辆成本
8. 普通员工不能查看全部费用
9. 所有关键操作写入日志
```

---

# P8｜保险年检与到期提醒

## 阶段目标

管理保险、年检、行驶证、驾驶证、保养到期提醒。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“车辆保险年检与到期提醒”功能。

背景：
- 车辆和司机档案已完成
- 车辆需要记录交强险、商业险、年检、行驶证等到期时间
- 司机需要记录驾驶证到期时间
- 系统需要在车辆首页、ERP 首页、老板日报、飞书/微信通知中提醒
- 第一版先做 ERP 首页提醒和车辆管理首页提醒

本次目标：
实现 vehicle_certificates 和 vehicle_reminders 到期提醒。

后端 API：
1. GET /api/vehicle-certificates
2. POST /api/vehicle-certificates
3. PATCH /api/vehicle-certificates/{id}
4. DELETE /api/vehicle-certificates/{id}
5. GET /api/vehicle-reminders
6. GET /api/vehicle-reminders/expiring

证件类型：
- compulsory_insurance 交强险
- commercial_insurance 商业险
- annual_inspection 年检
- driving_license 行驶证
- transport_license 道路运输证
- driver_license 驾驶证
- maintenance 保养提醒
- other 其他

字段：
- 车辆
- 司机，可选
- 证件类型
- 证件编号
- 开始日期
- 到期日期
- 金额
- 附件
- 提前提醒天数
- 状态
- 备注

提醒规则：
1. 默认提前 30 天提醒
2. 到期 30 天内为 warning
3. 到期 7 天内为 urgent
4. 已过期为 expired
5. 已处理后不再提醒
6. 停用/报废车辆可以不提醒，除非管理员选择继续提醒

前端页面：
1. 保险年检列表
2. 新增证件
3. 到期提醒看板
4. 车辆详情页证件 Tab
5. ERP 首页待办提醒

权限：
1. 管理员可以维护证件
2. 老板可以查看全部提醒
3. 财务可以查看保险费用
4. 普通员工不能编辑

验收标准：
1. 可以新增保险记录
2. 可以新增年检记录
3. 可以新增驾驶证到期记录
4. 30 天内到期可以提醒
5. 7 天内到期显示紧急
6. 已过期显示过期
7. 已处理后不再提醒
8. 车辆详情页能看到证件记录
9. 车辆首页能看到到期提醒
```

---

# P9｜违章事故与异常记录

## 阶段目标

记录违章、事故、剐蹭、车辆损坏、客户投诉、现场异常。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“车辆违章事故与异常记录”功能。

背景：
- 公司车辆可能发生违章、事故、剐蹭、车辆损坏、客户投诉等情况
- 异常可以由司机、安装主管、管理员录入
- 异常可能关联派车单、订单、安装任务
- 异常需要处理状态和责任人
- 罚款和维修金额可以进入车辆费用

本次目标：
实现 vehicle_incidents 异常记录。

后端 API：
1. GET /api/vehicle-incidents
2. POST /api/vehicle-incidents
3. GET /api/vehicle-incidents/{id}
4. PATCH /api/vehicle-incidents/{id}
5. POST /api/vehicle-incidents/{id}/resolve
6. POST /api/vehicle-incidents/{id}/close

事件类型：
- traffic_violation 违章
- accident 事故
- scratch 剐蹭
- vehicle_damage 车辆损坏
- customer_complaint 客户投诉
- traffic_penalty 交通处罚
- site_issue 现场异常
- other 其他

字段：
- 车辆
- 司机
- 派车单
- 关联订单
- 关联安装任务
- 发生时间
- 发生地点
- 事件类型
- 事件描述
- 罚款金额
- 扣分
- 维修金额
- 责任人
- 处理状态
- 证据照片
- 备注

处理状态：
- pending 待处理
- processing 处理中
- resolved 已处理
- closed 已关闭
- disputed 有争议

业务规则：
1. 司机可以提交异常
2. 管理员可以处理异常
3. 财务可以录入罚款/维修金额
4. 异常费用可以关联车辆费用
5. 涉及责任人扣款只生成记录，不自动扣工资
6. 异常关闭必须写处理结果
7. 严重事故应自动把车辆状态改为 maintenance 或 disabled

前端页面：
1. 异常记录列表
2. 新增异常
3. 异常详情
4. 处理异常
5. 车辆详情页异常 Tab

权限：
1. 司机可以提交自己的异常
2. 管理员可以处理异常
3. 老板可以查看全部
4. 普通员工不能查看全部事故和罚款

验收标准：
1. 可以新增违章记录
2. 可以新增事故记录
3. 可以上传证据照片
4. 可以关联派车单
5. 可以设置责任人
6. 可以录入罚款金额
7. 可以处理并关闭异常
8. 严重异常可以改变车辆状态
9. 所有关键操作写入日志
```

---

# P10｜车辆成本统计与订单分摊

## 阶段目标

把车辆费用分摊到订单、安装任务、部门、月份。  
让广告公司知道运输/安装车辆成本。

---

## 给 AI 的提示词

```text
你现在负责开发广告公司 ERP 的“车辆成本统计与订单分摊”功能。

背景：
- 车辆费用、派车、出车/收车台账已完成
- 公司需要知道每辆车每月花了多少钱
- 需要知道每个订单关联了多少车辆运输成本
- 车辆成本可以来自油费、过路费、停车费、维修费、保险年检分摊、外租车辆费等
- 第一版不做复杂折旧模型，只做直接费用和简单月度统计

本次目标：
实现车辆成本统计和订单分摊。

后端 API：
1. GET /api/vehicle-reports/overview
2. GET /api/vehicle-reports/costs
3. GET /api/vehicle-reports/mileage
4. GET /api/vehicle-reports/dispatches
5. GET /api/vehicle-reports/order-costs
6. POST /api/vehicle-cost-allocations
7. GET /api/vehicle-cost-allocations

统计维度：
- 按车辆
- 按司机
- 按月份
- 按费用类型
- 按订单
- 按安装任务
- 按部门

费用口径：
1. 已审核费用才计入正式成本
2. 待审核费用只计入预计成本
3. 驳回费用不计入成本
4. 派车单关联订单时，费用可以归集到订单
5. 没有关联订单的费用归为车辆公共费用
6. 保险、年检等年度费用第一版可以按实际发生月统计
7. 后续可扩展按月分摊

报表指标：
- 车辆总数
- 本月出车次数
- 本月行驶公里
- 本月油费
- 本月维修费
- 本月保险年检费
- 本月车辆总费用
- 单车费用排名
- 司机出车次数
- 订单车辆成本
- 平均每公里成本
- 平均每次出车成本

前端页面：
1. 车辆报表首页
2. 车辆费用统计
3. 里程统计
4. 派车统计
5. 订单运输成本统计
6. 费用类型分析

权限：
1. 老板可以看全部成本
2. 财务可以看全部费用
3. 管理员可以看车辆运营数据
4. 业务员只能看自己订单相关运输成本摘要
5. 普通员工不能看利润和全部费用

验收标准：
1. 可以按车辆统计本月费用
2. 可以按费用类型统计
3. 可以按司机统计出车次数
4. 可以按订单查看车辆成本
5. 待审核费用不计入正式成本
6. 驳回费用不计入成本
7. 可以导出或复制报表数据
8. 权限控制生效
```

---

# P11｜权限控制与审计日志

## 阶段目标

统一车辆管理权限，所有关键操作留痕。

---

## 角色权限建议

```text
老板：
查看全部车辆、费用、报表、异常、成本

管理员：
管理车辆、司机、派车、维修、保险、异常

安装主管：
审批安装用车、派车、查看安装相关车辆

业务员：
申请用车、查看自己订单相关派车

司机：
查看自己的派车任务、提交出车/收车/油费/异常

财务：
审核车辆费用、查看车辆费用统计、处理报销

普通员工：
只能申请用车或查看授权信息
```

---

## 给 AI 的提示词

```text
你现在负责为广告公司 ERP 的“公司车辆管理”模块增加权限控制和审计日志。

背景：
- 车辆管理基础功能已完成
- 需要控制不同角色能查看和操作的数据
- 所有关键动作必须有审计记录
- 如果现有 ERP 已有权限系统，请复用
- 如果现有 ERP 已有审计日志表，请复用
- 不要重复造一套冲突的权限系统

本次目标：
完善车辆管理权限和审计日志。

角色权限：
1. 老板
   - 查看全部车辆
   - 查看全部费用
   - 查看全部报表
   - 查看异常事故
   - 查看订单运输成本

2. 管理员
   - 管理车辆档案
   - 管理司机档案
   - 审批用车
   - 派车
   - 维护保险年检
   - 处理异常

3. 安装主管
   - 查看安装相关车辆
   - 审批安装用车
   - 派车安装任务
   - 查看司机任务

4. 业务员
   - 提交用车申请
   - 查看自己订单相关派车
   - 查看自己订单相关车辆成本摘要
   - 不能查看全部车辆费用

5. 司机
   - 查看自己的派车任务
   - 出车
   - 到达
   - 收车
   - 提交油费
   - 提交异常
   - 不能查看全部费用

6. 财务
   - 查看车辆费用
   - 审核费用
   - 处理报销状态
   - 查看费用报表
   - 不能随意派车，除非另有权限

7. 普通员工
   - 只能提交用车申请
   - 查看自己的申请

必须记录审计日志的动作：
1. 新增车辆
2. 编辑车辆
3. 停用车辆
4. 报废车辆
5. 新增司机
6. 编辑司机
7. 提交用车申请
8. 审批用车
9. 驳回用车
10. 生成派车单
11. 取消派车
12. 出车
13. 收车
14. 上报异常
15. 新增费用
16. 审核费用
17. 驳回费用
18. 标记报销
19. 新增保险年检
20. 处理到期提醒
21. 作废记录

审计日志字段：
- 操作人
- 操作动作
- 目标类型
- 目标 ID
- 操作前数据
- 操作后数据
- IP
- User-Agent
- 操作时间

验收标准：
1. 不同角色看到不同菜单和按钮
2. 未授权 API 调用会被拒绝
3. 普通员工不能查看全部车辆费用
4. 司机只能操作自己的派车单
5. 财务可以审核费用
6. 业务员只能看自己订单相关派车
7. 所有关键操作都有日志
8. 日志可在详情页查看
```

---

# P12｜微信/飞书 Agent 识别草稿

## 阶段目标

让微信/飞书消息可以识别用车需求、油费、车辆异常、收车回执，并生成草稿。  
Agent 不直接执行高风险操作。

---

## 可识别消息示例

```text
明天王师傅开辽A12345去装XX餐饮门头，早上8点出发。
今天加油280，票据发你了。
车右后轮没气了，今天得换胎。
我已经到现场了。
我已经收车，里程表 35680。
明天安装需要一辆车，去万达广场。
```

---

## 给 AI 的提示词

```text
你现在负责为广告公司 ERP 的“公司车辆管理”模块增加微信/飞书 Agent 消息识别草稿功能。

背景：
- 公司很多业务通过微信沟通
- 车辆用车、派车、油费、异常、收车等信息也会出现在微信/飞书聊天中
- Agent 只负责识别消息并生成草稿
- Agent 不允许直接执行高风险写操作
- 所有写入必须人工确认
- 如果已有统一 Agent Gateway，请复用
- 如果已有微信消息识别中台，请接入该中台

本次目标：
支持识别车辆管理相关消息，生成待确认草稿。

需要识别的 intent：
1. vehicle_use_request
   - 用车申请
   - 示例：明天安装需要一辆车，去万达广场

2. vehicle_dispatch
   - 派车安排
   - 示例：明天王师傅开辽A12345去装XX餐饮门头，早上8点出发

3. vehicle_start
   - 出车
   - 示例：我出车了，里程表 35200

4. vehicle_arrival
   - 到达现场
   - 示例：我已经到现场了

5. vehicle_return
   - 收车
   - 示例：我已经收车，里程表 35680

6. fuel_expense
   - 油费
   - 示例：今天加油280，票据发你了

7. vehicle_issue
   - 车辆异常
   - 示例：车右后轮没气了，今天得换胎

8. maintenance_request
   - 维修保养
   - 示例：这辆车该保养了

9. vehicle_query
   - 车辆查询
   - 示例：今天哪些车出去了

统一输入格式：
{
  "platform": "workbuddy_wechat",
  "conversation_id": "xxx",
  "message_id": "xxx",
  "sender_id": "xxx",
  "sender_name": "王师傅",
  "message_type": "text",
  "content": "今天加油280，票据发你了",
  "attachments": [],
  "sent_at": "2026-07-23T10:00:00+08:00"
}

识别输出格式：
{
  "intent": "fuel_expense",
  "confidence": 0.88,
  "risk_level": "medium",
  "extracted": {
    "amount": 280,
    "expense_type": "油费",
    "driver_name": "王师傅",
    "vehicle_plate": null,
    "related_dispatch_id": null
  },
  "suggested_action": "create_vehicle_expense_draft",
  "requires_confirmation": true,
  "requires_finance_review": true
}

业务规则：
1. 查询类可以直接返回查询结果
2. 草稿类必须人工确认后写入
3. 派车必须人工确认
4. 出车/收车如果司机身份明确，可以进入待确认或根据权限自动更新，但第一版建议仍需确认
5. 油费必须财务审核后计入成本
6. 车辆异常必须生成异常草稿
7. Agent 不能删除车辆记录
8. Agent 不能自动报销
9. Agent 不能自动修改车辆核心档案
10. Agent 不能自动确认财务付款

需要新增：
1. vehicle_agent_drafts 表，或复用 erp_draft_actions
2. Agent 识别服务
3. 草稿列表页面
4. 草稿确认/驳回接口
5. 消息来源追溯

API：
1. POST /api/vehicle-agent/messages/analyze
2. GET /api/vehicle-agent/drafts
3. POST /api/vehicle-agent/drafts/{id}/confirm
4. POST /api/vehicle-agent/drafts/{id}/reject
5. GET /api/vehicle-agent/drafts/{id}

验收标准：
1. “明天安装需要一辆车”可以识别为用车申请草稿
2. “王师傅开辽A12345去装门头”可以识别为派车草稿
3. “今天加油280”可以识别为油费草稿
4. “车右后轮没气了”可以识别为车辆异常草稿
5. Agent 不会直接写正式费用
6. Agent 不会直接派车
7. 草稿确认后才进入正式数据
8. 草稿驳回后不会写入
9. 所有草稿保留原始消息来源
```

---

# P13｜报表看板与老板日报

## 阶段目标

车辆管理首页、老板日报、月度费用报表。

---

## 给 AI 的提示词

```text
你现在负责为广告公司 ERP 的“公司车辆管理”模块增加报表看板和老板日报内容。

背景：
- 车辆档案、派车、出车/收车、费用、提醒已完成
- 老板需要看到车辆整体运营情况
- 安装主管需要看到今日派车和待收车
- 财务需要看到车辆费用和待审核费用
- 司机需要看到自己的任务

本次目标：
开发车辆管理看板和日报统计。

车辆管理首页指标：
1. 车辆总数
2. 可用车辆
3. 使用中车辆
4. 维修中车辆
5. 停用车辆
6. 今日出车次数
7. 今日待收车
8. 今日异常
9. 本月油费
10. 本月维修费
11. 本月车辆总费用
12. 即将保险到期
13. 即将年检到期
14. 驾驶证即将到期

老板日报增加内容：
【车辆与安装运输】
- 今日出车：X 次
- 今日安装关联派车：X 次
- 今日未收车：X 辆
- 今日车辆异常：X 条
- 今日油费：X 元
- 今日其他车辆费用：X 元
- 明日预计用车：X 次
- 即将到期提醒：X 条

报表页面：
1. 车辆费用趋势
2. 单车费用排行
3. 司机出车排行
4. 订单车辆成本排行
5. 油费统计
6. 维修费用统计
7. 到期提醒列表
8. 异常事故统计

API：
1. GET /api/vehicle-dashboard/overview
2. GET /api/vehicle-dashboard/today
3. GET /api/vehicle-dashboard/monthly
4. GET /api/vehicle-dashboard/reminders
5. GET /api/vehicle-dashboard/daily-report
6. GET /api/vehicle-dashboard/expense-ranking
7. GET /api/vehicle-dashboard/driver-ranking

权限：
1. 老板看全部
2. 财务看费用
3. 安装主管看派车和待收车
4. 司机看自己的任务
5. 普通员工只看自己的申请

验收标准：
1. 车辆首页显示核心指标
2. 今日出车统计准确
3. 待收车数量准确
4. 本月费用统计准确
5. 到期提醒准确
6. 老板日报包含车辆内容
7. 权限控制生效
```

---

# P14｜测试、上线、备份、回滚

## 阶段目标

确保模块可用、不会破坏现有 ERP，可备份、可回滚。

---

## 给 AI 的提示词

```text
你现在负责为广告公司 ERP 的“公司车辆管理”模块做完整测试、上线检查、备份和回滚方案。

背景：
- 公司车辆管理模块已完成主要开发
- 需要确保不影响现有客户、订单、安装、财务模块
- 上线前必须进行测试数据验证
- 需要提供回滚方案
- 需要提供操作文档

本次目标：
完成车辆管理模块上线前检查。

请完成以下工作：

1. 数据库检查
- 迁移脚本是否可重复执行
- 回滚脚本是否可用
- 新表是否创建成功
- 索引是否创建成功
- 车牌唯一约束是否生效

2. API 测试
- 车辆 CRUD
- 司机 CRUD
- 用车申请
- 审批
- 派车
- 出车
- 收车
- 油费
- 维修
- 保险年检
- 异常记录
- 费用审核
- 报表统计

3. 权限测试
- 老板
- 管理员
- 安装主管
- 业务员
- 司机
- 财务
- 普通员工

4. 业务流程测试
流程 A：
新增车辆 → 新增司机 → 用车申请 → 审批 → 派车 → 出车 → 收车 → 费用统计

流程 B：
安装任务 → 关联派车 → 出车 → 收车 → 订单车辆成本统计

流程 C：
司机提交油费 → 财务审核 → 计入车辆成本

流程 D：
车辆保险到期 → 提醒 → 处理提醒

流程 E：
车辆异常 → 上报 → 处理 → 关闭

5. Agent 草稿测试
- 用车申请消息
- 派车消息
- 油费消息
- 车辆异常消息
- 收车消息

6. 数据安全
- 普通员工不能查看全部费用
- 司机不能查看他人派车
- 业务员只能看自己订单相关数据
- 财务不能随意派车
- Agent 不能自动执行高风险动作

7. 上线前备份
- 备份数据库
- 备份配置文件
- 备份上传文件
- 记录当前 Git commit

8. 回滚方案
- 回滚代码
- 回滚数据库迁移
- 恢复备份
- 验证旧功能正常

9. 操作文档
- 管理员如何新增车辆
- 如何新增司机
- 如何提交用车申请
- 如何派车
- 司机如何出车/收车
- 财务如何审核费用
- 老板如何查看报表

验收标准：
1. 所有核心流程测试通过
2. 权限测试通过
3. API 测试通过
4. 数据库迁移可回滚
5. 现有 ERP 功能未受影响
6. 提供测试报告
7. 提供上线步骤
8. 提供回滚步骤
9. 提供用户操作文档
```

---

# 附录 A｜公司车辆管理 MVP 最小功能清单

第一版只做这些就够：

```text
1. 车辆档案
2. 司机档案
3. 用车申请
4. 用车审批
5. 派车
6. 出车
7. 收车
8. 油费记录
9. 维修保养
10. 保险年检提醒
11. 车辆异常
12. 费用统计
13. 订单车辆成本
14. 权限控制
15. 操作日志
```

---

# 附录 B｜第一版不要做的功能

```text
1. GPS 实时定位
2. 自动油卡对账
3. OBD 车辆数据采集
4. 自动识别违章
5. 复杂折旧模型
6. 自动结算司机工资
7. 自动报销
8. 客户侧车辆查询
9. 个人微信全自动监听所有消息
10. 无确认直接修改车辆状态
```

---

# 附录 C｜建议验收总表

| 验收项 | 是否通过 |
|---|---|
| 可以新增车辆 |  |
| 车牌号不能重复 |  |
| 可以新增司机 |  |
| 可以提交用车申请 |  |
| 可以审批用车申请 |  |
| 可以生成派车单 |  |
| 维修中车辆不能派车 |  |
| 停用车辆不能派车 |  |
| 同一时间段车辆不能重复派车 |  |
| 司机可以出车 |  |
| 司机可以收车 |  |
| 收车自动计算公里数 |  |
| 可以提交油费 |  |
| 财务可以审核费用 |  |
| 审核通过后计入成本 |  |
| 驳回费用不计入成本 |  |
| 可以记录维修保养 |  |
| 可以记录保险年检 |  |
| 到期提醒正常 |  |
| 可以记录违章事故 |  |
| 可以按车辆统计费用 |  |
| 可以按订单统计车辆成本 |  |
| 普通员工不能查看全部费用 |  |
| 司机只能查看自己的任务 |  |
| 业务员只能看自己订单相关数据 |  |
| 所有关键操作有审计日志 |  |
| Agent 只能生成草稿 |  |
| Agent 不会直接执行高风险动作 |  |
| 现有 ERP 功能未受影响 |  |
| 有数据库备份方案 |  |
| 有回滚方案 |  |

---

# 附录 D｜推荐开发顺序压缩版

如果你想更快落地，可以按这个顺序：

```text
第 1 周：
车辆档案、司机档案

第 2 周：
用车申请、审批、派车

第 3 周：
出车、收车、安装任务关联

第 4 周：
油费、维修、保险年检、到期提醒

第 5 周：
费用统计、订单成本、权限审计

第 6 周：
微信/飞书 Agent 草稿、老板日报、上线测试
```

---

# 附录 E｜最终给 AI 的总控提示词

如果你只想给 AI 一段总提示词，可以复制下面这段：

```text
你现在是我的高级产品经理、系统架构师和全栈工程师，负责为本地部署的广告公司 ERP 增加“公司车辆管理”模块。

项目背景：
- 我们是一家广告制作安装公司
- ERP 已有客户、订单、报价、生产、安装、财务等模块
- 公司车辆用于安装、送货、采购、售后、客户测量、外勤
- 本模块是普通公司车辆管理，不包含高空作业车每日经营台账
- 高空作业车会作为独立模块开发
- 车辆管理需要和订单、安装任务、员工、财务费用、微信/飞书 Agent 打通
- 第一阶段以内部使用为主
- 所有关键操作必须有审计日志
- 财务费用、报销、删除、车辆状态变更等高风险动作必须人工确认
- Agent 只能生成草稿或查询，不允许直接执行高风险动作

核心功能：
1. 车辆档案
2. 司机档案
3. 用车申请
4. 用车审批
5. 派车管理
6. 安装任务关联车辆
7. 出车记录
8. 收车记录
9. 油费记录
10. 维修保养
11. 保险年检
12. 到期提醒
13. 违章事故
14. 车辆费用统计
15. 订单运输成本
16. 权限控制
17. 审计日志
18. 微信/飞书 Agent 识别草稿
19. 老板日报车辆部分

开发要求：
1. 先阅读现有项目结构
2. 优先复用现有用户、员工、客户、订单、安装任务、财务、附件、权限模块
3. 不要破坏现有功能
4. 不要直接大规模重构
5. 按阶段开发
6. 每阶段都有数据库迁移、API、前端、权限、测试、回滚
7. 所有密钥放 .env
8. 所有关键操作写日志
9. 所有高风险写操作人工确认
10. 提供测试数据、测试命令、上线步骤、回滚方案

请先输出项目结构分析和分阶段实施计划，不要直接写代码。等我确认后，从 P1 数据库模型开始开发。
```

---

## 文件结束

建议你将本文件放入项目文档目录：

```text
docs/公司车辆管理_分阶段VibeCoding开发提示词.md
```

然后按阶段复制给 Codex / Cursor / Claude Code 执行。
