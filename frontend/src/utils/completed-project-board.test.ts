import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string) {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

describe('完成项目看板', () => {
  it('独立项目看板增加完成列并使用完成项目接口', () => {
    const source = readSource('views/tasks/ProductionTaskBoard.vue')

    expect(source).toContain('getCompletedProjects')
    expect(source).toContain('CompletedProjectCard')
    expect(source).toContain('completedProjects')
    expect(source).toContain("label: '完成'")
    expect(source).toContain('getCompletedProject')
    expect(source).toContain('CompletedProjectDetailDrawer')
  })

  it('工作台使用同一完成项目接口而不是复制完成筛选逻辑', () => {
    const source = readSource('views/home/DashboardView.vue')

    expect(source).toContain('getCompletedProjects')
    expect(source).toContain('CompletedProjectCard')
    expect(source).toContain("label: '完成'")
    expect(source).toContain('getCompletedProject')
    expect(source).toContain('CompletedProjectDetailDrawer')
  })

  it('完成卡片和详情抽屉是只读展示，不提供状态或恢复操作', () => {
    const cardPath = resolve(srcRoot, 'components/ui/CompletedProjectCard.vue')
    const drawerPath = resolve(srcRoot, 'components/ui/CompletedProjectDetailDrawer.vue')

    expect(existsSync(cardPath)).toBe(true)
    expect(existsSync(drawerPath)).toBe(true)
    const source = readFileSync(cardPath, 'utf8') + readFileSync(drawerPath, 'utf8')

    expect(source).toContain('完成明细')
    expect(source).toContain('完成时间')
    expect(source).not.toContain('变更状态')
    expect(source).not.toContain('恢复项目')
    expect(source).not.toContain('删除项目')
  })

  it('前端 API 和类型包含完成项目列表与只读详情契约', () => {
    const apiSource = readSource('api/tasks.ts')
    const typeSource = readSource('types/api.ts')

    expect(apiSource).toContain('getCompletedProjects')
    expect(apiSource).toContain('getCompletedProject')
    expect(apiSource).toContain('/task-queue/completed-projects')
    expect(typeSource).toContain('interface CompletedProjectCard')
    expect(typeSource).toContain('interface CompletedProjectDetail')
  })
})
