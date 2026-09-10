import type { ActionCapability, TaskOrderItemOption } from '@/types/api'

export type ProductionSelectionStage = 'pending' | 'in_progress'

type ProductionSelectionItem = Pick<
  TaskOrderItemOption,
  'id' | 'stage' | 'can_select' | 'capabilities' | 'is_linked' | 'task_status'
>

export interface StageSelectionState {
  checked: boolean
  indeterminate: boolean
  selectedCount: number
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
 * Resolve the quick-selection bucket for a production-task item.
 *
 * Linked items use their status inside the current task. An eligible item not
 * linked yet will be created by the backend as pending, so it belongs to the
 * pending bucket. Other states intentionally remain outside the two shortcuts.
 */
export function getProductionSelectionBucket(
  item: ProductionSelectionItem,
): ProductionSelectionStage | null {
  if (!isTaskOrderItemSelectable(item)) return null

  if (item.is_linked) {
    return item.task_status === 'pending' || item.task_status === 'in_progress'
      ? item.task_status
      : null
  }

  return item.stage === 'in_production' ? 'pending' : null
}

export function getProductionSelectionItemIds(
  items: readonly ProductionSelectionItem[],
  stage: ProductionSelectionStage,
) {
  return items
    .filter(item => getProductionSelectionBucket(item) === stage)
    .map(item => item.id)
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
