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
    expect(source).toContain('item.can_select')
    expect(source).toContain('!item.can_select')
    expect(source).toContain('stageTagType')
    expect(source).not.toContain('getOrder(props.orderId)')
  })
})
