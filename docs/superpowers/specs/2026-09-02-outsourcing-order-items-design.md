# 外协任务按订单明细关联设计

**日期：** 2026-09-02

**状态：** 已确认设计，待生成实施计划

**适用项目：** 广告 ERP

## 1. 目标与范围

让外协任务能够明确归属到订单中的某一条订单明细，并让这个归属在创建、编辑、查询、订单详情展示和订单成本统计中保持一致。

本期目标包括：

- 一个外协任务可以关联一个订单明细；
- 未关联明细的旧任务和整单外协继续可用；
- 创建和编辑外协任务时校验订单与订单明细的归属关系；
- 订单详情可以按订单明细查看外协任务、外协金额和状态；
- 已完成或已结算的有效外协任务继续进入订单成本；
- 外协任务的生命周期变化可以刷新订单成本；
- 订单销售金额变化不会覆盖外协任务自身的成本金额。

本期不改变订单主状态、订单明细销售金额、订单明细数量和内部设计/制作/安装任务状态机。

## 2. 当前实现依据

当前代码已经为 `outsource_tasks` 保留了可空字段 `order_item_id`，但这个字段尚未接入业务链路：

- `backend/app/models/outsource.py` 中存在 `order_item_id`，当前没有外键和关系定义；
- `backend/app/models/business_document.py` 中，`BusinessDocumentItem` 以 `document_id` 归属订单或报价单；
- `backend/app/schemas/outsource.py` 的创建、编辑和响应模型没有暴露 `order_item_id`；
- `backend/app/repositories/outsource_repo.py` 没有按订单明细过滤；
- `backend/app/services/outsource_service.py` 没有校验订单明细是否属于指定订单；
- `backend/app/api/outsource.py` 没有订单明细下拉接口；
- `frontend/src/views/outsource/OutsourceTaskList.vue` 和 `frontend/src/components/outsource/OutsourceTaskCard.vue` 没有明细选择控件；
- `frontend/src/views/orders/OrderDetail.vue` 目前展示订单明细和内部任务，但没有外协任务 Tab；
- `backend/app/services/order_cost_service.py` 按订单汇总已完成/已结算外协任务，但当前查询没有排除软删除任务。

线上数据检查结果显示：当前有 4 条外协任务，`order_item_id` 非空数量为 0，没有历史明细关联需要回填。因此可以采用增量迁移，不需要构造历史任务与明细的映射。

## 3. 已确认的业务决策

### 3.1 关联基数

一期采用“一条外协任务关联一条订单明细”的模型：

```text
OutsourceTask.order_item_id -> BusinessDocumentItem.id
```

一条外协任务如果覆盖多个订单明细，需要拆成多个外协任务。暂不新增多对多关联表，也不做外协金额在多个明细之间的自动分摊。

### 3.2 订单级外协兼容

`order_item_id = NULL` 表示整单外协。以下任务继续允许为空：

- 既有历史任务；
- 整单运输或整单服务；
- 暂时无法确认明细的任务；
- 从内部任务发起但用户没有选择明细的任务。

前端统一将这类任务显示为“整单外协”。

### 3.3 报价单限制

订单明细关联只适用于订单：

- `related_doc_type = order` 时可以传 `order_item_id`；
- `related_doc_type = quote` 时必须将 `order_item_id` 置为空；
- `order_item_id` 不为空时，`related_doc_id` 必须是有效且未删除的订单。

### 3.4 明细替换策略

订单编辑当前会删除旧的 `BusinessDocumentItem` 并生成新的明细 ID。外键采用 `ON DELETE SET NULL`：

- 不阻塞订单编辑；
- 不级联删除外协任务；
- 保留外协金额、付款记录、状态和操作历史；
- 旧明细被删除后，外协任务转为整单外协；
- 不根据名称、排序或金额自动绑定新明细。

### 3.5 成本口径

外协任务的 `total_amount` 是供应商成本，不是订单销售金额。订单明细关联只提供成本归属维度，不会自动修改订单明细的销售单价、数量、小计或订单销售总额。

订单成本只汇总满足以下条件的外协任务：

```text
related_doc_id = 当前订单
deleted_at IS NULL
status IN ('completed', 'settled')
```

### 3.6 状态边界

本期不根据外协任务状态自动修改订单主状态或订单明细状态。原因是当前系统没有明确的订单明细级生产、安装和交付状态机；先建立可靠的明细关联和成本维度，再单独设计明细状态流转。

## 4. 数据库设计

### 4.1 模型变化

在 `OutsourceTask` 中保留现有字段并增加关系：

```python
order_item_id: Mapped[UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("business_document_items.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
order_item: Mapped["BusinessDocumentItem | None"] = relationship(
    foreign_keys=[order_item_id],
    lazy="selectin",
)
```

关系只在外协任务侧建立，避免为了本期展示引入不必要的反向关系和级联行为。

### 4.2 Alembic 迁移

新增一条从当前 migration head 继承的迁移，完成以下操作：

1. 验证现有非空 `order_item_id` 均能找到对应的 `business_document_items.id`；
2. 创建 `fk_outsource_tasks_order_item_id` 外键；
3. 设置外键删除行为为 `SET NULL`；
4. 创建 `ix_outsource_order_item` 索引；
5. downgrade 时按相反顺序删除索引和外键。

迁移不得把现有字段改为非空，也不得删除已有外协任务。

## 5. 后端接口与服务设计

### 5.1 Schema

`OutsourceTaskCreate` 和 `OutsourceTaskUpdate` 增加：

```python
order_item_id: UUID | None = None
```

`OutsourceTaskResponse` 增加：

```python
order_item_id: UUID | None
order_item_name: str | None
```

订单明细下拉响应包含：

```python
{
    "id": str,
    "label": str,
    "item_name": str,
    "quantity": Decimal,
    "unit": str | None,
    "group_name": str | None,
    "sort_order": int,
}
```

### 5.2 关联校验

在 `OutsourceService` 中集中实现订单明细校验，创建和编辑共用：

```python
async def _validate_order_item_link(
    self,
    related_doc_id: UUID | None,
    related_doc_type: str | None,
    order_item_id: UUID | None,
) -> None:
    ...
```

校验顺序：

1. `order_item_id` 为空时直接返回；
2. 文档类型不是 `order` 时拒绝；
3. 订单不存在或已删除时拒绝；
4. 订单明细不存在时拒绝；
5. 订单明细的 `document_id` 不等于订单 ID 时拒绝。

创建时沿用现有 `order_id -> related_doc_id` 兼容映射，然后执行统一校验。编辑时先计算更新后的文档 ID、文档类型和明细 ID，再执行校验，避免只校验旧值。

### 5.3 显式清除关联

编辑接口需要区分“字段未传”和“字段传 null”：

- API 路由使用 `model_dump(exclude_unset=True)`；
- repository 只更新调用方实际传入的字段，包括显式 `None`；
- service 以旧任务值与请求字段合并，计算新的关联关系。

已产生付款的外协任务不允许修改 `order_item_id`，返回冲突错误并保留原关联；未付款任务可以绑定、修改或清除关联。

### 5.4 列表过滤

以下方法增加 `order_item_id` 可选参数：

- `OutsourceTaskRepository.list_tasks`；
- `OutsourceService.list_tasks`；
- `GET /outsource/tasks`。

列表查询继续固定过滤 `deleted_at IS NULL`。响应序列化从关联的订单明细读取 `order_item_name`，没有关联时返回 `null`。

### 5.5 订单明细下拉接口

增加：

```text
GET /outsource/orders/{order_id}/items-for-dropdown
```

服务层方法：

```python
async def list_order_items_for_dropdown(
    self,
    order_id: UUID,
) -> list[dict]:
    ...
```

接口只返回未删除订单下的明细，按 `sort_order`、`created_at` 排序。订单不是有效订单时返回与当前项目约定一致的 404/业务错误。路由权限沿用 `PERM_OUTSOURCE_READ`。

### 5.6 成本刷新

在外协服务中增加按相关订单刷新的内部方法：

```python
async def _sync_related_order_cost(
    self,
    related_doc_id: UUID | None,
    related_doc_type: str | None,
) -> None:
    ...
```

只有文档类型为订单且订单有效时才调用订单成本服务。以下操作需要刷新受影响的订单：

- 创建任务后；
- 更新任务后；
- 创建付款后；
- 取消任务后；
- 软删除任务后；
- 恢复任务后。

更新任务时保留旧订单 ID 和新订单 ID；如果两者不同，两个订单都刷新。创建、更新、付款和删除均在数据库写入成功后刷新，避免成本统计读到未提交状态。

### 5.7 订单更新与外协成本隔离

`BusinessDocumentService` 保留订单项目名称到外协描述的同步，但删除订单 `total_amount` 到外协任务 `unit_price/total_amount` 的覆盖逻辑。外协成本只能由外协任务的数量、单价、付款和状态操作维护。

## 6. 前端设计

### 6.1 类型和 API

`frontend/src/types/api.ts` 的 `OutsourceTaskResponse` 增加：

```ts
order_item_id: string | null
order_item_name: string | null
```

新增订单明细下拉类型：

```ts
export interface OutsourceOrderItemOption {
  id: string
  label: string
  item_name: string
  quantity: number
  unit: string | null
  group_name: string | null
  sort_order: number
}
```

`frontend/src/api/outsource.ts`：

- `getOutsourceTasks` 增加 `order_item_id` 参数；
- 增加 `getOutsourceOrderItems(orderId)`；
- 创建和编辑请求类型增加可选 `order_item_id`；
- 保持现有订单、报价单和来源内部任务参数兼容。

### 6.2 订单详情外协 Tab

新增 `frontend/src/components/outsource/OrderOutsourcePanel.vue`，由 `OrderDetail.vue` 的“外协任务”Tab 使用。

组件职责：

- 接收当前订单 ID和订单明细列表；
- 调用订单外协任务列表接口；
- 按 `order_item_id` 分组；
- 显示明细名称、任务状态、供应商、数量、金额和付款信息；
- 将 `order_item_id = null` 的任务显示为“整单外协”；
- 每个明细分组提供“发起外协”按钮；
- 点击按钮跳转到现有外协任务管理页面，并带上 `order_id`、`order_item_id` 路由参数。

页面不在 156 条订单明细的每一行内嵌入完整外协任务列表，避免订单详情加载和布局复杂度随明细数量线性膨胀。

### 6.3 外协任务管理页面

修改 `frontend/src/views/outsource/OutsourceTaskList.vue`：

- 创建/编辑表单增加“订单明细”选择器；
- 选择订单后加载该订单明细；
- 选择报价单时清空明细并禁用明细选择器；
- 识别 `order_id`、`order_item_id` 路由参数并预填新建表单；
- 列表增加“订单明细”列；
- 编辑已付款任务时禁用明细归属字段；
- 创建成功或编辑成功后刷新任务列表。

### 6.4 内部任务外协卡片

修改 `frontend/src/components/outsource/OutsourceTaskCard.vue`：

- 根据卡片的订单 ID加载订单明细；
- 增加可选明细选择器；
- 创建请求带上 `order_item_id`；
- 未选择时继续按整单外协创建；
- 保留 `source_task_type/source_task_id`，不改变内部任务的外协标记逻辑。

### 6.5 前端分组纯函数

新增 `frontend/src/utils/outsourceTaskGrouping.ts`，将分组和摘要逻辑从 Vue 组件中抽出。至少提供：

```ts
groupTasksByOrderItem(tasks)
summarizeOutsourceTasks(tasks)
```

分组键使用订单明细 ID，空值使用固定的整单分组键。摘要同时区分任务总金额和已完成/已结算成本金额，避免把待处理任务误显示为已发生成本。

## 7. 错误处理与兼容性

用户传入不存在、已删除或跨订单的明细时，接口返回明确的业务错误，不执行外协任务写入。

已付款任务尝试修改明细归属时返回冲突错误，不改变任务和付款记录。报价单选择明细时返回参数错误，并在前端切换单据时主动清空明细。

旧请求不传 `order_item_id` 时，创建结果与现有整单外协行为一致。旧任务读取时 `order_item_name` 返回 `null`，前端显示“整单外协”。

软删除任务不出现在有效列表，也不再计入订单成本；恢复任务后，如果其状态满足成本条件，则重新进入订单成本。

## 8. 验收标准

### 数据与后端

- 数据库存在订单明细外键和索引，外键删除行为为 `SET NULL`；
- 可以创建绑定当前订单明细的外协任务；
- 不能将其他订单的明细绑定到当前订单；
- 报价单不能绑定订单明细；
- 未付款任务可以绑定、修改和清除明细关联；
- 已付款任务不能修改明细归属；
- 列表可以按订单和订单明细过滤；
- 响应包含明细 ID和明细名称；
- 软删除任务不参与订单成本；
- 完成、结算、取消、删除和恢复后的订单成本正确；
- 订单销售金额变化不改变外协任务成本。

### 前端

- 订单详情存在“外协任务”Tab；
- 外协任务按订单明细分组，整单任务单独显示；
- 从明细分组发起外协时，订单和明细自动预填；
- 外协任务管理页和内部任务外协卡片都可以选择明细；
- 报价单不会保留订单明细选择；
- 类型检查、Lint、单元测试和构建通过。

## 9. 上线与回滚

上线前执行现有 `order_item_id` 数据完整性检查并备份数据库。上线顺序为：

1. 发布包含兼容接口的后端代码；
2. 执行 Alembic migration；
3. 发布前端构建产物；
4. 验证列表、创建、编辑、订单详情和成本刷新链路；
5. 按应用服务发布流程重启后端进程，不重启操作系统。

如果发布验证失败，优先回滚前端和后端代码；数据库迁移本身只增加外键和索引，不删除数据。只有确认应用代码已回退且新外键没有被后续数据依赖时，才执行 migration downgrade。已有订单明细被删除后产生的 `NULL` 关联不会被强行恢复。
