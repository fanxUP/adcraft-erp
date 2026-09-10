import type {
  ActionCapability,
  OrderItemStage,
  TaskOrderItemOption,
  TaskType,
} from '@/types/api'

export type TaskStageSelectionKey = 'pending' | 'designing' | 'assigned' | 'in_progress'
export type ProductionSelectionStage = Extract<TaskStageSelectionKey, 'pending' | 'in_progress'>

type TaskStageSelectionItem = Pick<
  TaskOrderItemOption,
  'id' | 'stage' | 'can_select' | 'capabilities' | 'is_linked' | 'task_status'
>

export interface TaskStageSelectionGroup {
  key: TaskStageSelectionKey
  label: string
  taskStatuses: readonly string[]
  orderItemStage: OrderItemStage
}

export interface StageSelectionState {
  checked: boolean
  indeterminate: boolean
  selectedCount: number
}

const TASK_STAGE_SELECTION_GROUPS: Record<TaskType, readonly TaskStageSelectionGroup[]> = {
  design: [
    {
      key: 'pending',
      label: '待分配',
      taskStatuses: ['pending'],
      orderItemStage: 'designing',
    },
    {
      key: 'designing',
      label: '设计中',
      taskStatuses: ['designing'],
      orderItemStage: 'designing',
    },
  ],
  production: [
    {
      key: 'pending',
      label: '待制作',
      taskStatuses: ['pending'],
      orderItemStage: 'in_production',
    },
    {
      key: 'in_progress',
      label: '制作中',
      taskStatuses: ['in_progress'],
      orderItemStage: 'in_production',
    },
  ],
  installation: [
    {
      key: 'pending',
      label: '待分配',
      taskStatuses: ['pending'],
      orderItemStage: 'in_installation',
    },
    {
      key: 'assigned',
      label: '已分配',
      taskStatuses: ['assigned'],
      orderItemStage: 'in_installation',
    },
    {
      key: 'in_progress',
      label: '安装中',
      taskStatuses: ['in_progress'],
      orderItemStage: 'in_installation',
    },
  ],
}

export function getTaskStageSelectionGroups(taskType: TaskType) {
  return TASK_STAGE_SELECTION_GROUPS[taskType]
}

/**
 * The server capability overrides the legacy boolean when both are present.
 * Keeping this rule in one place prevents bulk selection from bypassing row
 * level selection restrictions.
 */
export function isTaskOrderItemSelectable(
  item: Pick<TaskOrderItemOption, 'can_select' | 'capabilities'>,
) {
  const selectCapability = item.capabilities?.select as ActionCapability | undefined
  return selectCapability?.allowed ?? item.can_select
}

/**
 * Resolve the quick-selection bucket for one task item.
 *
 * A newly selected item is materialized by the backend as pending, so an
 * eligible unlinked item in the task's order stage belongs to that task's
 * pending bucket. Linked items use their status inside the current task.
 */
export function getTaskStageSelectionBucket(
  item: TaskStageSelectionItem,
  taskType: TaskType,
): TaskStageSelectionKey | null {
  if (!isTaskOrderItemSelectable(item)) return null

  const groups = getTaskStageSelectionGroups(taskType)
  if (item.is_linked) {
    return groups.find(group => group.taskStatuses.includes(item.task_status || ''))?.key || null
  }

  const pendingGroup = groups.find(group => group.key === 'pending')
  return pendingGroup && item.stage === pendingGroup.orderItemStage
    ? pendingGroup.key
    : null
}

export function getTaskStageSelectionItemIds(
  items: readonly TaskStageSelectionItem[],
  taskType: TaskType,
  stage: TaskStageSelectionKey,
) {
  return items
    .filter(item => getTaskStageSelectionBucket(item, taskType) === stage)
    .map(item => item.id)
}

/**
 * Resolve the quick-selection bucket for a production-task item.
 *
 * Linked items use their status inside the current task. An eligible item not
 * linked yet will be created by the backend as pending, so it belongs to the
 * pending bucket. Other states intentionally remain outside the two shortcuts.
 */
export function getProductionSelectionBucket(
  item: TaskStageSelectionItem,
): ProductionSelectionStage | null {
  return getTaskStageSelectionBucket(item, 'production') as ProductionSelectionStage | null
}

export function getProductionSelectionItemIds(
  items: readonly TaskStageSelectionItem[],
  stage: ProductionSelectionStage,
) {
  return getTaskStageSelectionItemIds(items, 'production', stage)
}

export function toggleStageSelection(
  selectedIds: readonly string[],
  stageItemIds: readonly string[],
  checked: boolean,
) {
  const stageIds = Array.from(new Set(stageItemIds))
  if (checked) return Array.from(new Set([...selectedIds, ...stageIds]))

  const stageIdSet = new Set(stageIds)
  return selectedIds.filter(id => !stageIdSet.has(id))
}

export function getStageSelectionState(
  selectedIds: readonly string[],
  stageItemIds: readonly string[],
): StageSelectionState {
  const selectedIdSet = new Set(selectedIds)
  const selectedCount = stageItemIds.filter(id => selectedIdSet.has(id)).length
  const hasItems = stageItemIds.length > 0

  return {
    checked: hasItems && selectedCount === stageItemIds.length,
    indeterminate: selectedCount > 0 && selectedCount < stageItemIds.length,
    selectedCount,
  }
}
