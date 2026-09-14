# 实施计划：单项状态操作与附件日期相册

## 1. 实施模式与边界

- 模式：STRICT；原因是同时涉及任务状态写入、执行人领取、权限边界和附件访问。
- 目标：三类任务详情从批量勾选推进改为逐条明确操作；订单源附件按服务端上传日期分组为相册/时间轴；不破坏现有工作流、权限和订单级附件接口。
- 本轮状态：已完成本地实现与验证；未执行服务器部署，等待用户明确要求发布。
- 不新增数据库迁移，不新增依赖，不改变 API 的既有批量字段兼容性。

## 2. 计划项

### TASK-SINGLE-ALBUM-P01：确定单项操作与相册交互契约

**范围**

- 固化三类任务每条明细的主动作、回退动作、未关联动作、禁用原因和确认文案。
- 固化订单附件的日期分组、排序、媒体/普通文件展示、上传失败和空日期处理。
- 明确桌面端、移动安装端、订单详情和完成项目详情的共享边界。

**产出**

- 以本设计文档为实现依据。
- 明确不再使用批量勾选推进，但保留后端批量接口兼容。

**依赖**

- 无。

**对应验收**

- A01：单项状态交互契约。

### TASK-SINGLE-ALBUM-P02：补齐服务端单项动作与安全校验契约

**范围**

- 在现有明细选项响应中增加轻量 `actions` 描述，或提供等价的服务端动作能力结构。
- 保持现有三类 `change-status` 接口，确认前端始终传单个明细 ID。
- 复核并补强服务端的单项状态、权限、领取、外协阻断、完成时间、状态日志和任务聚合校验。
- 将内部状态错误转换为用户能理解的错误语义；不得因为请求只带一个 ID 而放宽校验。

**不包含**

- 不新增任务或附件数据表。
- 不删除批量字段或破坏历史调用。

**依赖**

- P01。

**对应验收**

- A02：服务端单项安全和兼容。

### TASK-SINGLE-ALBUM-P03：改造桌面端三类任务明细操作

**范围**

- 改造 `TaskOrderItemLinkCard`：去掉状态推进复选框、阶段全选和底部批量工作流，增加逐行操作列。
- 增加逐行确认、单行 loading、防重复点击、成功刷新和大白话错误提示。
- 处理未关联明细的“加入并开始/添加到本任务”动作。
- 继续显示各流程状态、执行人、进度、外协阻断和权限禁用原因。
- 清理因批量 UI 移除而失效的 import、computed、handler 和死样式；保留确实还被其他兼容路径使用的工具。

**涉及文件方向**

- `frontend/src/components/tasks/TaskOrderItemLinkCard.vue`
- `frontend/src/components/tasks/TaskItemActionList.vue`（如抽取共享动作组件）
- `frontend/src/views/tasks/DesignTaskDetail.vue`
- `frontend/src/views/tasks/ProductionTaskDetail.vue`
- `frontend/src/views/tasks/InstallationTaskDetail.vue`
- `frontend/src/api/tasks.ts`
- `frontend/src/types/api.ts`

**依赖**

- P01、P02。

**对应验收**

- A03：桌面端逐条操作。

### TASK-SINGLE-ALBUM-P04：改造移动端安装任务的状态入口

**范围**

- 移除 `MobileInstallation.vue` 中“取整张任务所有明细 ID 并一次提交”的状态变更路径。
- 在移动任务抽屉加载明细动作，复用桌面端单项动作语义；至少做到一条明细一个操作按钮、一次请求只带一个 ID。
- 保持移动端现场照片与视频上传入口和权限规则。
- 验证移动端完成一条明细后其他明细不变，任务聚合进度只按真实状态更新。

**涉及文件方向**

- `frontend/src/views/tasks/MobileInstallation.vue`
- 必要时复用 `frontend/src/components/tasks/TaskItemActionList.vue`

**依赖**

- P01、P02、P03（若共享动作组件已抽取）。

**对应验收**

- A04：移动端逐条操作和聚合进度。

### TASK-SINGLE-ALBUM-P05：将订单附件改为日期相册/时间轴

**范围**

- 改造 `OrderTaskAttachments`，按服务端 `created_at` 以本地日期分组、按新到旧排序。
- 日期组内分别展示媒体网格和普通文件行；图片放大、视频播放、普通文件预览/下载/删除保持现有能力。
- 保留点击/拖拽上传、格式和大小校验、上传队列、失败重试。
- 处理历史 `created_at` 为空、删除后空组、批量上传不同日期和时区边界。
- 确认订单详情、三类任务详情、完成项目详情和移动端的显示一致。

**涉及文件方向**

- `frontend/src/components/orders/OrderTaskAttachments.vue`
- `frontend/src/utils/datetime.ts`（仅在现有公共格式化契约不足时调整）
- `frontend/src/api/orders.ts`（仅在接口类型需要补充时调整）

**依赖**

- P01；服务端现有 `created_at` 接口字段可直接复用。

**对应验收**

- A05：附件服务端时间和相册展示。

### TASK-SINGLE-ALBUM-P06：测试、清理与质量门禁

**范围**

- 后端测试：单项状态、其他明细不变、执行人不串写、外协阻断、权限、回退、日志/完成时间和任务聚合。
- 前端测试：动作映射、单 ID 请求、禁用原因、移动端不整单提交、日期分组/排序/空时间、媒体与普通文件展示。
- 运行类型检查、单元测试、构建、lint/格式检查和 `git diff --check`。
- 检查旧批量 UI 是否还有未使用代码；确认未引入 DB migration、依赖或价格/外协信息泄漏。

**涉及文件方向**

- `backend/tests/test_order_item_task_progress.py`
- `backend/tests/test_task_item_execution_ownership.py`
- `backend/tests/test_design_task_service.py`
- `backend/tests/test_production_task_service.py`
- `backend/tests/test_task_service.py`
- `backend/tests/test_order_task_attachments.py`
- `frontend/src/utils/task-ui-cleanup.test.ts`
- `frontend/src/utils/taskStageSelection.test.ts`
- 新增动作和附件分组测试（按项目现有测试框架落位）

**依赖**

- P02、P03、P04、P05。

**对应验收**

- A06：回归、纯净度和质量门禁。

## 3. 技术实现原则

1. 服务端是状态、权限、外协和时间的最终裁决者；前端动作按钮只是服务端能力的呈现。
2. 每次明细状态请求只传一个 `order_item_id`；不得使用整个任务的 ID 列表兜底。
3. 不用客户端时间写入附件日期，不按原始时间字符串截取日期，不以 optimistic update 掩盖失败。
4. 共享组件优先，避免订单、任务和移动端各自复制一套附件分组逻辑。
5. 任务聚合状态和进度保持现有算法；本次只改变操作粒度和展示方式。
6. 先 RED 测试，再实现 GREEN，再清理 REFACTOR，最后执行完整 VERIFY。

## 4. 实施顺序

```text
P01 需求/交互契约
 ├─> P02 服务端动作与校验
 │    └─> P03 桌面端逐条操作
 │          └─> P04 移动端安装逐条操作
 └─> P05 附件日期相册

P02 + P03 + P04 + P05
 └─> P06 测试与质量门禁
```

## 5. 发布前检查

- 只在用户明确要求开始实施后进入代码修改；实施前更新任务对应的变更预算和作用域锁定。
- 先在本地完成测试和构建，再提交 Git；服务器部署前保存当前版本信息并执行健康检查。
- 发布后重点抽查：一条设计明细完成是否只改变一条；移动安装是否还会整单完成；跨日期附件是否正确归组；无外协权限用户是否仍看不到外协细节。
