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
})
