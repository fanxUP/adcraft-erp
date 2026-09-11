import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { getTaskWorkflowControl } from './taskItemWorkflow'

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
    const selectionSource = readSource('utils/taskStageSelection.ts')

    expect(source).toContain('getTaskOrderItemOptions')
    expect(source).toContain('item.stage_label')
    expect(source).toContain('isTaskOrderItemSelectable')
    expect(selectionSource).toContain('item.capabilities?.select')
    expect(source).toContain('function canSelect')
    expect(source).toContain('function disabledReason')
    expect(source).toContain('<StatusTag')
    expect(source).toContain('item.outsource_blocked')
    expect(source).toContain('item.outsource_status_label')
    expect(source).toContain('外协完成后才能推进该明细到下一阶段')
    expect(source).toContain('刷新状态')
    expect(source).not.toContain('getOrder(props.orderId)')
  })

  it('任务处理明细按数量、金额、小计、任务进度顺序展示金额信息', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')
    const metaStart = source.indexOf('<span class="item-option-meta">')
    const metaEnd = source.indexOf('\n            </span>', metaStart)
    const metaSource = source.slice(metaStart, metaEnd)

    expect(metaStart).toBeGreaterThanOrEqual(0)
    expect(metaEnd).toBeGreaterThan(metaStart)
    expect(metaSource).toContain('数量 {{ item.quantity }}')
    expect(metaSource).toContain('金额 {{ formatMoney(item.unit_price) }}')
    expect(metaSource).toContain('小计 {{ formatMoney(item.subtotal_amount) }}')
    expect(metaSource).toContain('本任务进度 {{ item.task_progress_pct }}%')
    expect(metaSource.indexOf('数量')).toBeLessThan(metaSource.indexOf('金额'))
    expect(metaSource.indexOf('金额')).toBeLessThan(metaSource.indexOf('小计'))
    expect(metaSource.indexOf('小计')).toBeLessThan(metaSource.indexOf('本任务进度'))
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
    expect(source).toContain('changeStatusDisabledReason.value')
    expect(source).toContain(':changing="changing || isHistoricalReadOnly || !canChangeTaskStatus"')
  })

  it('任务分配与变更状态合并到共享卡片，并要求负责人', () => {
    const cardSource = readSource('components/tasks/TaskOrderItemLinkCard.vue')

    expect(cardSource).toContain('employeeOptions')
    expect(cardSource).toContain('assignedTo')
    expect(cardSource).toContain('请先选择分配人，再变更任务状态')
    expect(cardSource).toContain("emit('assign', assignmentTarget.value || null)")
    expect(cardSource).toContain('assignedToId')
    expect(cardSource).toContain('分配人：')

    for (const relativePath of [
      'views/tasks/DesignTaskDetail.vue',
      'views/tasks/ProductionTaskDetail.vue',
      'views/tasks/InstallationTaskDetail.vue',
    ]) {
      expect(readSource(relativePath)).not.toContain('<template #header><span>任务分配</span></template>')
    }
  })

  it('设计、制作、安装任务提供按状态的三态分类全选', () => {
    const source = readSource('components/tasks/TaskOrderItemLinkCard.vue')
    const selectionSource = readSource('utils/taskStageSelection.ts')

    expect(source).toContain('v-if="stageSelectionGroups.length && !isHistoricalReadOnly"')
    expect(source).toContain('{{ group.label }}（{{ stageSelectionItemIds[group.key].length }} 条可选）')
    expect(source).toContain(':indeterminate="stageSelectionState[group.key].indeterminate"')
    expect(source).toContain('@change="handleStageSelection(group.key, $event)"')
    expect(source).toContain('getTaskStageSelectionGroups')
    expect(source).toContain('getTaskStageSelectionItemIds')
    expect(selectionSource).toContain("design: [")
    expect(selectionSource).toContain("production: [")
    expect(selectionSource).toContain("installation: [")
    expect(selectionSource).toContain("label: '设计中'")
    expect(selectionSource).toContain("label: '制作中'")
    expect(selectionSource).toContain("label: '安装中'")
    expect(source).toContain('toggleStageSelection')
    expect(source).toContain('selectedItemIds.value')
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

describe('按已选订单明细控制任务状态', () => {
  const designWorkflow = {
    pending: ['designing', 'cancelled'],
    designing: ['confirmed', 'pending', 'cancelled'],
    confirmed: [],
  }

  it('任务整体已在设计中时，待分配明细仍可单独推进到设计中', () => {
    const control = getTaskWorkflowControl(
      [{ id: 'sign', is_linked: true, task_status: 'pending' }],
      ['sign'],
      'designing',
      designWorkflow,
    )

    expect(control.currentStatus).toBe('pending')
    expect(control.workflow.pending).toContain('designing')
    expect(control.workflow.pending).not.toContain('confirmed')
  })

  it('新勾选但尚未写入关联表的明细按待分配处理', () => {
    const control = getTaskWorkflowControl(
      [{ id: 'sign', is_linked: false, task_status: null }],
      ['sign'],
      'designing',
      designWorkflow,
    )

    expect(control.currentStatus).toBe('pending')
    expect(control.workflow.pending).toEqual(['designing', 'cancelled'])
  })

  it('混合状态批量选择只保留所有明细都允许的目标状态', () => {
    const control = getTaskWorkflowControl(
      [
        { id: 'pending-item', is_linked: true, task_status: 'pending' },
        { id: 'designing-item', is_linked: true, task_status: 'designing' },
      ],
      ['pending-item', 'designing-item'],
      'designing',
      designWorkflow,
    )

    expect(control.currentStatus).toBe('__selected_mixed__')
    expect(control.workflow.__selected_mixed__).toEqual(['cancelled'])
  })

  it('制作中明细支持回退到待制作，同时保留完成入口', () => {
    const productionWorkflow = {
      pending: ['in_progress', 'cancelled'],
      in_progress: ['completed', 'rework', 'pending', 'cancelled'],
      rework: ['in_progress', 'cancelled'],
      completed: [],
      cancelled: [],
    }
    const control = getTaskWorkflowControl(
      [{ id: 'production-item', is_linked: true, task_status: 'in_progress' }],
      ['production-item'],
      'in_progress',
      productionWorkflow,
    )

    expect(control.workflow.in_progress).toContain('pending')
    expect(control.workflow.in_progress).toContain('completed')
  })

  it('制作任务页面和状态条明确提供回退入口', () => {
    const productionSource = readSource('views/tasks/ProductionTaskDetail.vue')
    const workflowSource = readSource('components/workflow/TaskWorkflow.vue')

    expect(productionSource).toContain("in_progress: ['completed', 'rework', 'pending', 'cancelled']")
    expect(workflowSource).toContain('function isRollback')
    expect(workflowSource).toContain('可回退')
  })
})
