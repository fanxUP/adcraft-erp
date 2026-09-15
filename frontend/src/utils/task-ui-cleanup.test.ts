import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { getTaskItemActions } from './taskItemActions'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string) {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

describe('任务详情页界面收敛', () => {
  it('任务概览卡统一展示客户联系信息且不重复显示订单明细', () => {
    const overviewSource = readSource('components/ui/TaskOverviewCard.vue')

    expect(overviewSource).toContain('任务概览')
    expect(overviewSource).toContain('客户名称')
    expect(overviewSource).toContain('部门/科室')
    expect(overviewSource).toContain('联系人')
    expect(overviewSource).toContain('联系电话')
    expect(overviewSource).not.toContain('订单明细')

    for (const relativePath of [
      'views/tasks/DesignTaskDetail.vue',
      'views/tasks/ProductionTaskDetail.vue',
      'views/tasks/InstallationTaskDetail.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).toContain('TaskOverviewCard')
      expect(source).not.toContain('<el-descriptions-item label="订单明细">')
    }
  })

  it('不再渲染变更历史模块或历史审核状态文案', () => {
    expect(existsSync(resolve(srcRoot, 'components/tasks/TaskHistoryTimeline.vue'))).toBe(false)

    for (const relativePath of [
      'views/tasks/DesignTaskDetail.vue',
      'views/tasks/ProductionTaskDetail.vue',
      'views/tasks/InstallationTaskDetail.vue',
      'views/orders/OrderDetail.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).not.toContain('TaskHistoryTimeline')
      expect(source).not.toContain('历史待确认')
      expect(source).not.toContain('历史需修改')
    }
  })

  it('前端不再保留只服务于已下线时间线的历史接口类型', () => {
    expect(readSource('api/tasks.ts')).not.toContain('getTaskHistory')
    expect(readSource('types/api.ts')).not.toContain('interface TaskHistoryItem')
  })

  it('任务处理明细按后端阶段展示标签并禁用不可关联明细', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).toContain('getTaskOrderItemOptions')
    expect(source).toContain('item.stage_label')
    expect(source).toContain('getTaskItemActions')
    expect(source).toContain('handleItemAction')
    expect(source).toContain('item-table-actions')
    expect(source).toContain('function disabledReason')
    expect(source).toContain('<StatusTag')
    expect(source).toContain('item.outsource_blocked')
    expect(source).toContain('item.outsource_status_label')
    expect(source).toContain('action.disabled_reason')
    expect(source).toContain('刷新状态')
    expect(source).not.toContain('勾选要推进的明细')
    expect(source).not.toContain('stageSelectionGroups')
    expect(source).not.toContain('TaskWorkflow')
    expect(source).not.toContain('getOrder(props.orderId)')
  })

  it('任务处理明细按数量、金额、小计、任务进度顺序展示金额信息', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')
    const quantityHeader = source.indexOf('>数量</span>')
    const amountHeader = source.indexOf('>金额</span>')
    const subtotalHeader = source.indexOf('>小计</span>')
    const progressHeader = source.indexOf('>本任务进度</span>')

    expect(quantityHeader).toBeGreaterThanOrEqual(0)
    expect(amountHeader).toBeGreaterThan(quantityHeader)
    expect(subtotalHeader).toBeGreaterThan(amountHeader)
    expect(progressHeader).toBeGreaterThan(subtotalHeader)
    expect(source).toContain('{{ item.quantity }}')
    expect(source).toContain('{{ formatMoney(item.unit_price) }}')
    expect(source).toContain('{{ formatMoney(item.subtotal_amount) }}')
    expect(source).toContain('{{ item.task_progress_pct }}%')
  })

  it('任务处理明细使用列式列表，全部展示且不建立独立滚动区域', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).toContain('class="item-table"')
    expect(source).toContain('class="item-table-header"')
    expect(source).toContain('item-table-product')
    expect(source).toContain('class="item-assignee-name"')
    expect(source).toContain('has-price-columns')
    expect(source).toContain('has-outsource-column')
    expect(source).not.toContain('class="item-list"')
    expect(source).not.toContain('max-height: 360px')
    expect(source).not.toContain('overflow-y: auto')
  })

  it('任务明细各列在行内上下居中，长文本继续自动换行', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).toContain('.item-table-row > .item-table-cell { align-items: center; }')
    expect(source).toContain('.item-table-name, .item-table-product, .item-table-spec { white-space: normal; word-break: break-word; }')
    expect(source).not.toContain('.item-table-name, .item-table-product, .item-table-spec { align-items: flex-start;')
    expect(source).not.toContain('.item-table-assignee, .item-table-outsourcing { align-items: flex-start; }')
    expect(source).not.toContain('.item-table-actions { align-items: flex-start;')
  })

  it('普通任务不显示独立关联保存按钮，历史任务保留补录入口', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).not.toContain('保存关联 ${selectedItemIds.length}')
    expect(source).not.toContain(": '保存关联'")
    expect(source).not.toContain('无需单独保存关联')
    expect(source).toContain('v-if="isHistoricalReadOnly"')
    expect(source).toContain('添加到本任务')
    expect(source).toContain('handleAddHistoricalItems')
  })

  it('任务处理不重复显示已关联明细汇总框', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).not.toContain('class="linked-item-summary"')
    expect(source).not.toContain('linkedItemNames')
    expect(source).toContain('已关联 {{ linkedItemIds.length }} 条明细')
  })

  it('任务处理不显示重复的状态说明提示，但保留状态操作禁用逻辑', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).not.toContain(':title="isHistoricalReadOnly')
    expect(source).not.toContain('v-if="!canChangeTaskStatus && !isHistoricalReadOnly"')
    expect(source).toContain('action.disabled_reason')
    expect(source).toContain('!action.allowed')
    expect(source).toContain("action.operation === 'rollback'")
    expect(source).not.toContain('取消明细任务')
  })

  it('任务处理按明细显示执行人，不再使用整张任务负责人', () => {
    const cardSource = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(cardSource).toContain('item.assignee_name')
    expect(cardSource).toContain('itemAssigneeLabel(item)')
    expect(cardSource).toContain('item-assignee-name')
    expect(cardSource).not.toContain('assignmentTarget')
    expect(cardSource).not.toContain('请先选择分配人，再变更任务状态')

    for (const relativePath of [
      'views/tasks/DesignTaskDetail.vue',
      'views/tasks/ProductionTaskDetail.vue',
      'views/tasks/InstallationTaskDetail.vue',
    ]) {
      expect(readSource(relativePath)).not.toContain('<template #header><span>任务分配</span></template>')
    }

    expect(readSource('components/ui/TaskBoardCard.vue')).not.toContain('负责人：')
    for (const relativePath of [
      'views/tasks/DesignTaskList.vue',
      'views/tasks/ProductionTaskList.vue',
      'views/tasks/InstallationTaskList.vue',
    ]) {
      expect(readSource(relativePath)).not.toContain('label="派发"')
    }
  })

  it('设计、制作、安装任务不再使用批量状态全选', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(source).not.toContain('stageSelectionGroups')
    expect(source).not.toContain('getTaskStageSelectionGroups')
    expect(source).not.toContain('toggleStageSelection')
    expect(source).not.toContain('按状态选择订单明细')
    expect(source).toContain('仅用于批量改派')
  })

  it('移动端状态变更只提交当前点击的订单明细', () => {
    const source = readSource('views/tasks/MobileInstallation.vue')

    expect(source).toContain('getTaskOrderItemOptions')
    expect(source).toContain('handleItemAction')
    expect(source).toContain('order_item_ids: [item.id]')
    expect(source).not.toContain('const orderItemIds = currentTask.value.order_item_ids')
    expect(source).not.toContain('order_item_ids: orderItemIds')
  })

  it('工作台项目看板与独立项目看板复用任务进度', () => {
    const source = readSource('views/home/DashboardView.vue')
    const cardSource = readSource('components/ui/TaskBoardCard.vue')

    expect(source).toContain('getTaskQueue')
    expect(source).toContain('TaskQueueItem')
    expect(source).toContain('isTaskVisible')
    expect(source).not.toContain('design_progress_pct')
    expect(source).not.toContain('production_progress_pct')
    expect(source).not.toContain('installation_progress_pct')
    expect(cardSource).toContain('taskProgress')
    expect(cardSource).toContain('任务进度')
    expect(cardSource).toContain('<ProgressBar')
    expect(cardSource).toContain(':percentage="taskProgress(task)"')

    const projectBoardSource = readSource('views/tasks/ProductionTaskBoard.vue')
    expect(projectBoardSource).toContain("from '@/utils/task-board'")
    expect(projectBoardSource).toContain('taskProgress')
    expect(projectBoardSource).toContain('isTaskVisible')
  })

  it('两处项目看板复用统一任务卡片并显示订单归属信息', () => {
    const cardSource = readSource('components/ui/TaskBoardCard.vue')

    expect(cardSource).toContain('客户名称')
    expect(cardSource).toContain('部门/科室')
    expect(cardSource).toContain('订单金额')
    expect(cardSource).toContain('formatMoney(task.total_amount)')
    expect(cardSource).toContain('task.department || \'-\'')

    for (const relativePath of ['views/home/DashboardView.vue', 'views/tasks/ProductionTaskBoard.vue']) {
      const source = readSource(relativePath)
      expect(source).toContain("import TaskBoardCard from '@/components/ui/TaskBoardCard.vue'")
      expect(source).toContain('<TaskBoardCard')
    }
  })

  it('项目看板任务卡片不显示订单明细摘要', () => {
    const cardSource = readSource('components/ui/TaskBoardCard.vue')

    expect(cardSource).not.toContain('明细：')
    expect(cardSource).not.toContain('class="card-item"')
    expect(cardSource).not.toContain('itemSummary')
  })

  it('任务人员没有外协查看权限时不加载外协卡片或外协筛选', () => {
    const cardSource = readSource('components/outsource/OutsourceTaskCard.vue')
    expect(cardSource).toContain('v-if="canViewOutsourceTask"')
    expect(cardSource).toContain("authStore.hasPermission('outsource_task:read')")
    expect(cardSource).toContain("authStore.hasPermission('outsource_task:create')")

    for (const relativePath of [
      'views/tasks/DesignTaskDetail.vue',
      'views/tasks/ProductionTaskDetail.vue',
      'views/tasks/InstallationTaskDetail.vue',
    ]) {
      expect(readSource(relativePath)).toContain("v-if=\"authStore.hasPermission('outsource_task:read')\"")
    }

    for (const relativePath of [
      'views/tasks/DesignTaskList.vue',
      'views/tasks/ProductionTaskList.vue',
      'views/tasks/InstallationTaskList.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).toContain('v-if="canViewOutsourceTask"')
      expect(source).toContain("authStore.hasPermission('outsource_task:read')")
    }
  })

  it('外协成本字段只在拥有成本权限时渲染，避免缺失字段显示为零', () => {
    const cardSource = readSource('components/outsource/OutsourceTaskCard.vue')
    const taskListSource = readSource('views/outsource/OutsourceTaskList.vue')
    const recycleSource = readSource('views/outsource/OutsourceTaskRecycle.vue')
    const paymentSource = readSource('views/outsource/OutsourcePaymentList.vue')

    for (const source of [cardSource, taskListSource, recycleSource, paymentSource]) {
      expect(source).toContain("authStore.hasPermission('finance:view_cost')")
    }
    expect(cardSource).toContain('v-if="canViewOutsourceCost"')
    expect(taskListSource).toContain('delete (payload as { unit_price?: number }).unit_price')
    expect(taskListSource).toContain('v-if="canViewOutsourceCost"')
    expect(recycleSource).toContain('v-if="canViewOutsourceCost"')
    expect(paymentSource).toContain('v-if="canViewOutsourceCost"')
  })
})

describe('单条订单明细动作', () => {
  const designWorkflow = {
    pending: ['designing'],
    designing: ['confirmed', 'pending'],
    confirmed: [],
  }

  it('待分配明细只显示开始设计，且只包含一个目标状态', () => {
    const actions = getTaskItemActions('design', {
      is_linked: true,
      stage: 'designing',
      task_status: 'pending',
      can_select: true,
    }, designWorkflow)

    expect(actions[0]).toMatchObject({
      key: 'start',
      to_status: 'designing',
      label: '开始设计',
      allowed: true,
    })
  })

  it('设计中明细提供完成设计和退回待分配两个独立动作且不能取消', () => {
    const actions = getTaskItemActions('design', {
      is_linked: true,
      stage: 'designing',
      task_status: 'designing',
      can_select: true,
    }, designWorkflow)

    expect(actions.map(action => action.to_status)).toEqual([
      'confirmed',
      'pending',
    ])
    expect(actions.find(action => action.to_status === 'confirmed')?.label).toBe('完成设计')
    expect(actions.find(action => action.to_status === 'pending')?.label).toBe('退回待分配')
    expect(actions.some(action => action.to_status === 'cancelled')).toBe(false)
  })

  it('未关联明细使用加入并开始动作，不会暗示已经关联', () => {
    const actions = getTaskItemActions('design', {
      is_linked: false,
      stage: 'designing',
      task_status: null,
      can_select: true,
    }, designWorkflow)

    expect(actions).toHaveLength(1)
    expect(actions[0]).toMatchObject({
      key: 'link_start',
      to_status: 'designing',
      label: '加入并开始设计',
    })
  })

  it('动作由服务端提供时优先使用服务端语义', () => {
    const serverActions = [{
      key: 'complete',
      to_status: 'completed',
      label: '完成制作',
      allowed: false,
      disabled_reason: '外协任务进行中',
      kind: 'primary' as const,
    }]
    const actions = getTaskItemActions('production', {
      is_linked: true,
      stage: 'in_production',
      task_status: 'in_progress',
      can_select: false,
      actions: serverActions,
    }, {
      pending: ['in_progress'],
      in_progress: ['completed', 'pending'],
    })

    expect(actions).toEqual(serverActions)
  })

  it('服务端返回空动作时保持只读，不回退生成旧流程按钮', () => {
    const actions = getTaskItemActions('design', {
      is_linked: true,
      stage: 'completed',
      task_status: 'confirmed',
      can_select: true,
      actions: [],
    }, {
      confirmed: ['cancelled'],
    })

    expect(actions).toEqual([])
  })

  it('制作中明细支持退回设计和回退到待制作，同时保留完成入口', () => {
    const productionWorkflow = {
      pending: ['in_progress'],
      in_progress: ['completed', 'rework', 'pending'],
      rework: ['in_progress'],
      completed: [],
    }
    const actions = getTaskItemActions('production', {
      is_linked: true,
      stage: 'in_production',
      task_status: 'in_progress',
      can_select: true,
    }, productionWorkflow)

    expect(actions.map(action => action.to_status)).toEqual([
      'completed',
      'rework',
      'pending',
      'rolled_back',
    ])
    expect(actions.find(action => action.to_status === 'pending')?.label).toBe('退回待制作')
    expect(actions.find(action => action.to_status === 'completed')?.label).toBe('完成制作')
    expect(actions.find(action => action.to_status === 'rolled_back')).toMatchObject({
      operation: 'rollback',
      target_stage: 'design',
      label: '退回设计',
    })
  })

  it('历史取消的制作或安装明细提供明确的恢复入口', () => {
    const productionActions = getTaskItemActions('production', {
      is_linked: true,
      stage: 'in_production',
      task_status: 'cancelled',
      can_select: false,
    }, {
      cancelled: [],
    })
    const installationActions = getTaskItemActions('installation', {
      is_linked: true,
      stage: 'in_installation',
      task_status: 'cancelled',
      can_select: false,
    }, {
      cancelled: [],
    })

    expect(productionActions.find(action => action.key === 'rollback_stage')).toMatchObject({
      label: '恢复到设计',
      operation: 'rollback',
      target_stage: 'design',
      allowed: false,
    })
    expect(installationActions.find(action => action.key === 'rollback_stage')).toMatchObject({
      label: '恢复到制作',
      operation: 'rollback',
      target_stage: 'production',
      allowed: false,
    })
  })

  it('没有操作权限时仍返回禁用动作和可读原因', () => {
    const actions = getTaskItemActions('design', {
      is_linked: true,
      stage: 'designing',
      task_status: 'designing',
      can_select: false,
      disabled_reason: '该明细由李四负责',
    }, designWorkflow)

    expect(actions.every(action => action.allowed === false)).toBe(true)
    expect(actions[0].disabled_reason).toBe('该明细由李四负责')
  })
})
