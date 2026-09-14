import type {
  ActionCapability,
  OrderItemStage,
  TaskItemAction,
  TaskType,
} from '@/types/api'

export interface TaskItemActionSource {
  is_linked: boolean
  stage: OrderItemStage
  task_status?: string | null
  can_select: boolean
  disabled_reason?: string | null
  capabilities?: Record<string, ActionCapability>
  actions?: TaskItemAction[]
  outsource_blocked?: boolean
}

/** Whether the current account may operate on this item for management actions. */
export function isTaskOrderItemSelectable(
  item: Pick<TaskItemActionSource, 'can_select' | 'capabilities'>,
) {
  const selectCapability = item.capabilities?.select as ActionCapability | undefined
  return selectCapability?.allowed ?? item.can_select
}

const EXPECTED_ORDER_STAGE: Record<TaskType, OrderItemStage> = {
  design: 'designing',
  production: 'in_production',
  installation: 'in_installation',
}

const START_STATUS: Record<TaskType, string> = {
  design: 'designing',
  production: 'in_progress',
  installation: 'in_progress',
}

const STAGE_LABEL: Record<TaskType, string> = {
  design: '设计',
  production: '制作',
  installation: '安装',
}

function selectCapability(item: TaskItemActionSource) {
  return item.capabilities?.select as ActionCapability | undefined
}

function isAllowed(item: TaskItemActionSource) {
  return isTaskOrderItemSelectable(item)
}

function baseDisabledReason(item: TaskItemActionSource) {
  return selectCapability(item)?.disabled_reason
    || item.disabled_reason
    || '当前账号不能操作该明细'
}

function actionKey(toStatus: string, currentStatus: string) {
  if (toStatus === 'completed' || toStatus === 'confirmed') return 'complete'
  if (toStatus === 'cancelled') return 'cancel'
  if (toStatus === 'rolled_back') return 'rollback_stage'
  if (toStatus === 'pending') return 'rollback'
  if (toStatus === currentStatus) return 'continue'
  if (toStatus === 'rework' || toStatus === 'revision') return 'rework'
  if (toStatus === 'pending_review' || toStatus === 'pending_acceptance') return 'submit'
  if (toStatus === 'assigned') return 'assign'
  return 'start'
}

function actionLabel(taskType: TaskType, toStatus: string, currentStatus: string) {
  if (toStatus === 'confirmed' || toStatus === 'completed') return `完成${STAGE_LABEL[taskType]}`
  if (toStatus === 'cancelled') return `取消${STAGE_LABEL[taskType]}`
  if (toStatus === 'rolled_back') return `退回${taskType === 'production' ? '设计' : '制作'}`
  if (toStatus === 'pending') return `退回${taskType === 'production' ? '待制作' : '待分配'}`
  if (taskType === 'design' && toStatus === 'designing') return '开始设计'
  if (taskType === 'production' && toStatus === 'in_progress') {
    return currentStatus === 'rework' ? '继续制作' : '开始制作'
  }
  if (taskType === 'installation' && toStatus === 'in_progress') return '开始安装'
  if (toStatus === 'assigned') return '确认分配'
  if (toStatus === 'rework') return '提交返工'
  if (toStatus === 'revision') return '退回修改'
  if (toStatus === 'pending_review' || toStatus === 'pending_acceptance') return '提交待处理'
  return `变更为${toStatus}`
}

function actionKind(taskType: TaskType, toStatus: string) {
  if (toStatus === 'confirmed' || toStatus === 'completed') return 'primary' as const
  if (taskType === 'design' && toStatus === 'designing') return 'primary' as const
  if (taskType === 'production' && toStatus === 'in_progress') return 'primary' as const
  if (taskType === 'installation' && toStatus === 'in_progress') return 'primary' as const
  return 'secondary' as const
}

/**
 * Resolve the actions for exactly one order item.
 *
 * The server-provided action list is authoritative. The workflow fallback is
 * kept for old responses and local callers so a partially upgraded server does
 * not make the detail page lose its action column.
 */
export function getTaskItemActions(
  taskType: TaskType,
  item: TaskItemActionSource,
  workflow: Record<string, string[]>,
): TaskItemAction[] {
  // Presence of the field is meaningful: an empty server list means that the
  // item has no legal action (for example, a terminal or out-of-scope item).
  // Do not reconstruct a fallback action in that case.
  if (item.actions !== undefined) return item.actions

  const allowed = isAllowed(item)
  const disabledReason = baseDisabledReason(item)

  if (!item.is_linked) {
    if (item.stage !== EXPECTED_ORDER_STAGE[taskType]) return []
    const toStatus = START_STATUS[taskType]
    return [{
      key: 'link_start',
      to_status: toStatus,
      label: `加入并开始${STAGE_LABEL[taskType]}`,
      allowed,
      disabled_reason: allowed ? null : disabledReason,
      kind: 'primary',
      requires_confirmation: true,
      operation: 'status_change',
      target_stage: null,
    }]
  }

  const currentStatus = item.task_status || 'pending'
  const actions: TaskItemAction[] = (workflow[currentStatus] || [])
    .filter(toStatus => toStatus !== 'cancelled')
    .map(toStatus => {
    const isCompletion = toStatus === 'completed' || toStatus === 'confirmed'
    const blockedByOutsource = isCompletion && Boolean(item.outsource_blocked)
    const actionAllowed = allowed && !blockedByOutsource
    return {
      key: actionKey(toStatus, currentStatus),
      to_status: toStatus,
      label: actionLabel(taskType, toStatus, currentStatus),
      allowed: actionAllowed,
      disabled_reason: actionAllowed
        ? null
        : blockedByOutsource
          ? '外协任务进行中，完成后才能继续'
          : disabledReason,
      kind: actionKind(taskType, toStatus),
      requires_confirmation: true,
      operation: 'status_change' as const,
    }
  })
  const rollbackTarget = taskType === 'production'
    ? 'design'
    : taskType === 'installation'
      ? 'production'
      : null
  if (
    rollbackTarget
    && !['completed', 'confirmed', 'cancelled', 'rolled_back'].includes(currentStatus)
  ) {
    const rollbackAllowed = allowed && !item.outsource_blocked
    actions.push({
      key: 'rollback_stage',
      to_status: 'rolled_back',
      label: `退回${rollbackTarget === 'design' ? '设计' : '制作'}`,
      allowed: rollbackAllowed,
      disabled_reason: rollbackAllowed
        ? null
        : item.outsource_blocked
          ? '外协任务进行中，完成外协后才能退回上一阶段'
          : disabledReason,
      kind: 'secondary',
      requires_confirmation: true,
      operation: 'rollback' as const,
      target_stage: rollbackTarget,
    })
  }
  return actions
}
