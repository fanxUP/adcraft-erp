import type { StatusView, TaskQueueItem } from '@/types/api'

export const TASK_BOARD_COLUMNS = [
  { key: 'design', label: '设计' },
  { key: 'production', label: '制作' },
  { key: 'installation', label: '安装' },
] as const

export function taskProgress(task: Pick<TaskQueueItem, 'progress_pct'>) {
  return Math.min(100, Math.max(0, Number(task.progress_pct ?? 0)))
}

export function isTaskVisible(task: Pick<TaskQueueItem, 'status' | 'progress_pct'> & { status_view?: StatusView | null }) {
  const terminal = task.status_view?.terminal
    ?? ['completed', 'confirmed', 'cancelled', 'rolled_back'].includes(task.status)
  return !terminal
    && taskProgress(task) < 100
}

export function taskProgressColor(stage: TaskQueueItem['stage']) {
  const colors: Record<TaskQueueItem['stage'], string> = {
    design: '#409eff',
    production: '#e6a23c',
    installation: '#67c23a',
  }
  return colors[stage]
}
