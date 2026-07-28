import { describe, expect, it } from 'vitest'
import { buildActionPreview } from './actionPreview'

describe('buildActionPreview', () => {
  it('formats order status changes for human review', () => {
    const preview = buildActionPreview({
      action_label: '推进订单状态',
      business_no: 'ORD-001',
      project_name: '门店招牌',
      current_status_label: '设计中',
      target_status_label: '生产中',
      reason: '设计已确认',
      effects: ['创建或衔接生产任务'],
      note: '确认后才会执行',
    })

    expect(preview.title).toBe('推进订单状态')
    expect(preview.rows).toContainEqual({
      label: '状态变化',
      value: '设计中 → 生产中',
    })
    expect(preview.effects).toEqual(['创建或衔接生产任务'])
    expect(preview.fallbackJson).toBe('')
  })

  it('keeps a readable fallback for unknown preview shapes', () => {
    const preview = buildActionPreview({ custom_field: 'custom value' })

    expect(preview.rows).toEqual([])
    expect(preview.fallbackJson).toContain('custom_field')
  })
})
