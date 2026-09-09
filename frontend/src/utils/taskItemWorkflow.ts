export interface TaskItemWorkflowState {
  id: string
  is_linked?: boolean
  task_status?: string | null
}

export interface TaskWorkflowControl {
  currentStatus: string
  workflow: Record<string, string[]>
  selectedStatuses: string[]
  hasSelection: boolean
  hasMixedStatuses: boolean
}

const MIXED_SELECTION_STATUS = '__selected_mixed__'

function effectiveStatus(item: TaskItemWorkflowState, aggregateStatus: string) {
  // Newly selected rows are materialized as `pending` by the backend when the
  // status request arrives. Keep the UI on that same initial state before the
  // link has been persisted.
  return item.task_status || (item.is_linked ? aggregateStatus : 'pending')
}

/**
 * Build the status control for the currently checked order items.
 *
 * A task may contain several order items at different stages, so its
 * aggregate status cannot decide which action is valid for the checked rows.
 * For mixed selections, only transitions valid for every selected row remain.
 */
export function getTaskWorkflowControl(
  items: TaskItemWorkflowState[],
  selectedIds: string[],
  aggregateStatus: string,
  workflow: Record<string, string[]>,
): TaskWorkflowControl {
  const selected = items.filter(item => selectedIds.includes(item.id))
  if (!selected.length) {
    return {
      currentStatus: aggregateStatus,
      workflow,
      selectedStatuses: [],
      hasSelection: false,
      hasMixedStatuses: false,
    }
  }

  const selectedStatuses = Array.from(new Set(
    selected.map(item => effectiveStatus(item, aggregateStatus)),
  ))
  if (selectedStatuses.length === 1) {
    return {
      currentStatus: selectedStatuses[0],
      workflow,
      selectedStatuses,
      hasSelection: true,
      hasMixedStatuses: false,
    }
  }

  const commonTargets = selectedStatuses.slice(1).reduce((targets, status) => {
    const allowed = new Set(workflow[status] || [])
    return new Set([...targets].filter(target => allowed.has(target)))
  }, new Set(workflow[selectedStatuses[0]] || []))

  return {
    currentStatus: MIXED_SELECTION_STATUS,
    workflow: {
      ...workflow,
      [MIXED_SELECTION_STATUS]: [...commonTargets],
    },
    selectedStatuses,
    hasSelection: true,
    hasMixedStatuses: true,
  }
}
