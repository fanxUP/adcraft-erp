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
    expect(source).toContain("name: 'CompletedProjectDetail'")
    expect(source).not.toContain('getCompletedProject(')
    expect(source).not.toContain('CompletedProjectDetailDrawer')
  })

  it('工作台使用同一完成项目接口而不是复制完成筛选逻辑', () => {
    const source = readSource('views/home/DashboardView.vue')

    expect(source).toContain('getCompletedProjects')
    expect(source).toContain('CompletedProjectCard')
    expect(source).toContain("label: '完成'")
    expect(source).toContain("name: 'CompletedProjectDetail'")
    expect(source).not.toContain('getCompletedProject(')
    expect(source).not.toContain('CompletedProjectDetailDrawer')
  })

  it('完成卡片和独立详情页是只读展示，不提供状态或恢复操作', () => {
    const cardPath = resolve(srcRoot, 'components/ui/CompletedProjectCard.vue')
    const detailPath = resolve(srcRoot, 'views/tasks/CompletedProjectDetail.vue')
    const drawerPath = resolve(srcRoot, 'components/ui/CompletedProjectDetailDrawer.vue')

    expect(existsSync(cardPath)).toBe(true)
    expect(existsSync(detailPath)).toBe(true)
    expect(existsSync(drawerPath)).toBe(false)
    const source = readFileSync(cardPath, 'utf8') + readFileSync(detailPath, 'utf8')

    expect(source).toContain('完成明细')
    expect(source).toContain('完成时间')
    expect(source).toContain('返回完成看板')
    expect(source).not.toContain('变更状态')
    expect(source).not.toContain('恢复项目')
    expect(source).not.toContain('删除项目')
  })

  it('工作台只保留完成统计摘要，不嵌入完成明细查询和表格', () => {
    const source = readSource('views/home/DashboardView.vue')

    expect(source).not.toContain('getTaskCompletionDetails')
    expect(source).not.toContain('completionProjectRows')
    expect(source).not.toContain('completionDetailRows')
    expect(source).not.toContain('completionDetailsLoading')
    expect(source).not.toContain('CompletedProjectDetailDrawer')
    expect(source).toContain('完成明细已集中到完成看板')
  })

  it('独立完成详情页复用只读详情接口并处理加载、错误和空数据状态', () => {
    const source = readSource('views/tasks/CompletedProjectDetail.vue')

    expect(source).toContain('getCompletedProject')
    expect(source).toContain('v-loading="loading"')
    expect(source).toContain('完成项目详情暂时无法加载，请稍后重试')
    expect(source).toContain('暂无可见的完成明细')
    expect(source).toContain('el-table-column')
    expect(source).toContain('产品/材质/工艺')
    expect(source).toContain('规格')
    expect(source).toContain('数量')
    expect(source).toContain('row.stages.design')
    expect(source).toContain('执行人：')
    expect(source).toContain('完成时间：')
    expect(source).toContain('设计任务：任务附件')
    expect(source).toContain('制作任务：任务附件')
    expect(source).toContain('安装任务：现场照片与视频')
    expect(source).not.toContain('handleDeleteAttachment')
  })

  it('完成详情的三类任务资料按整行排列，并标识多条安装任务的归档范围', () => {
    const source = readSource('views/tasks/CompletedProjectDetail.vue')

    expect(source).toContain('三类资料分行展示，现场资料按安装任务归档')
    expect(source).toContain('.resource-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }')
    expect(source).toContain('resourceFor(stage.key)?.task_count')
    expect(source).toContain('class="resource-task"')
  })

  it('前端 API 和类型包含完成项目列表与只读详情契约', () => {
    const apiSource = readSource('api/tasks.ts')
    const typeSource = readSource('types/api.ts')

    expect(apiSource).toContain('getCompletedProjects')
    expect(apiSource).toContain('getCompletedProject')
    expect(apiSource).toContain('/task-queue/completed-projects')
    expect(typeSource).toContain('interface CompletedProjectCard')
    expect(typeSource).toContain('interface CompletedProjectDetail')
    expect(typeSource).toContain('interface CompletedProjectStage')
    expect(typeSource).toContain('interface CompletedProjectResourceSection')
  })
})
