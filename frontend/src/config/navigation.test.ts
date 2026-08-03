import { describe, expect, it } from 'vitest'
import { filterNavigation, navigationItems } from './navigation'

describe('filterNavigation', () => {
  it('shows sales workflow without admin sections', () => {
    const labels = filterNavigation(navigationItems, ['sales']).map(item => item.label)

    expect(labels).toContain('客户与销售')
    expect(labels).toContain('项目交付')
    expect(labels).not.toContain('系统管理')
  })

  it('keeps only permitted delivery entries for installers', () => {
    const delivery = filterNavigation(navigationItems, ['installer'])
      .find(item => item.label === '项目交付')

    expect(delivery?.children?.map(item => item.label)).toEqual(['安装任务'])
  })

  it('gives administrators access to AI business knowledge health', () => {
    const system = filterNavigation(navigationItems, ['admin'])
      .find(item => item.label === '系统管理')

    expect(system?.children).toContainEqual({
      label: 'AI 业务知识健康',
      path: '/admin/ai/knowledge-health',
    })
  })

  it('places 项目看板 as a top-level item right below 工作台 for production roles', () => {
    const items = filterNavigation(navigationItems, ['production'])
    const index = items.findIndex(item => item.label === '项目看板')

    expect(index).toBeGreaterThanOrEqual(0)
    expect(items[index - 1]?.label).toBe('工作台')
    expect(items[index]).toMatchObject({
      label: '项目看板',
      path: '/production-tasks/board',
      icon: 'Grid',
    })
  })

  it('hides 项目看板 from sales roles', () => {
    const labels = filterNavigation(navigationItems, ['sales']).map(item => item.label)

    expect(labels).not.toContain('项目看板')
  })
})
