import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string) {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

describe('任务详情页界面收敛', () => {
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
    expect(source).toContain('item.capabilities?.select?.allowed')
    expect(source).toContain('function canSelect')
    expect(source).toContain('function disabledReason')
    expect(source).toContain('<StatusTag')
    expect(source).toContain('item.outsource_blocked')
    expect(source).toContain('item.outsource_status_label')
    expect(source).toContain('外协完成后才能推进该明细到下一阶段')
    expect(source).toContain('刷新状态')
    expect(source).not.toContain('getOrder(props.orderId)')
  })

  it('工作台项目看板与独立项目看板复用任务进度', () => {
    const source = readSource('views/home/DashboardView.vue')

    expect(source).toContain('getTaskQueue')
    expect(source).toContain('TaskQueueItem')
    expect(source).toContain('taskProgress')
    expect(source).toContain('isTaskVisible')
    expect(source).toContain('任务进度')
    expect(source).toContain('<ProgressBar')
    expect(source).toContain(':percentage="taskProgress(task)"')
    expect(source).not.toContain('design_progress_pct')
    expect(source).not.toContain('production_progress_pct')
    expect(source).not.toContain('installation_progress_pct')

    const projectBoardSource = readSource('views/tasks/ProductionTaskBoard.vue')
    expect(projectBoardSource).toContain("from '@/utils/task-board'")
    expect(projectBoardSource).toContain('taskProgress')
    expect(projectBoardSource).toContain('isTaskVisible')
  })
})
