import type { TaskOrderItemOption, TaskOrderItemState } from '@/types/api'
import { normalizeOrderItemGroups } from './orderItemPresentation'
import { isTaskOrderItemSelectable } from './taskItemActions'

export type TaskItemFilter = 'all' | 'pending' | 'in_progress' | 'completed' | 'mine'
export type TaskItemScope = 'all' | 'linked'

export function isCompletedTaskItem(status?: string | null) {
  return status === 'confirmed' || status === 'completed'
}

export function isActiveTaskItem(status?: string | null) {
  return !['cancelled', 'rolled_back'].includes(status || '')
}

export function filterTaskItems<T extends TaskOrderItemOption>(
  items: T[], scope: TaskItemScope, filter: TaskItemFilter, keyword: string, userId?: string,
): T[] {
  const query = keyword.trim().toLocaleLowerCase()
  return items.filter(item => {
    if (scope === 'linked' && !item.is_linked) return false
    if (query && ![item.item_name, item.group_name, item.material_process, item.specification, item.assignee_name]
      .some(value => value?.toLocaleLowerCase().includes(query))) return false
    if (filter === 'mine') return Boolean(userId) && item.is_linked && item.assignee_user_id === userId
    if (filter === 'completed') return item.is_linked && isCompletedTaskItem(item.task_status)
    if (filter === 'pending') return item.is_linked
      ? !item.task_status || ['pending', 'assigned'].includes(item.task_status)
      : isTaskOrderItemSelectable(item)
    if (filter === 'in_progress') return item.is_linked && Boolean(item.task_status)
      && isActiveTaskItem(item.task_status) && !isCompletedTaskItem(item.task_status) && !['pending', 'assigned'].includes(item.task_status || '')
    return true
  })
}

export function buildTaskItemSections<T extends TaskOrderItemOption>(items: T[]) {
  // Reuse the order's group normalization, including legacy name-only groups.
  const normalized = normalizeOrderItemGroups(items as unknown as Parameters<typeof normalizeOrderItemGroups>[0])
  const sections = new Map<string, { key: string; name: string; items: T[]; completed: number }>()
  const sorted = items.map((item, index) => ({ item, groupId: normalized[index]!.group_id }))
    .sort((a, b) => (a.item.sort_order ?? 0) - (b.item.sort_order ?? 0))
  for (const { item, groupId } of sorted) {
    const key = groupId ? `group:${groupId}` : 'ungrouped'
    if (!sections.has(key)) sections.set(key, { key, name: item.group_name || (groupId ? '未命名分项' : '未分项明细'), items: [], completed: 0 })
    const section = sections.get(key)!
    section.items.push(item)
    if (item.is_linked && isCompletedTaskItem(item.task_status)) section.completed++
  }
  return [...sections.values()]
}

export function taskCompletionSummary(states?: Record<string, TaskOrderItemState>) {
  const active = Object.values(states || {}).filter(state => isActiveTaskItem(state.status))
  return { total: active.length, completed: active.filter(state => isCompletedTaskItem(state.status)).length }
}
