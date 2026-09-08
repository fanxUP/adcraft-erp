import { describe, expect, it } from 'vitest'
import { buildProjectCostScopeOptions } from './projectCostScope'

describe('buildProjectCostScopeOptions', () => {
  it('只返回当前有效明细，并带出已登记成本和明细描述', () => {
    const options = buildProjectCostScopeOptions(
      [
        {
          id: 'item-active',
          item_name: '台签纸',
          material_process: '铜版纸彩印',
          specification: '210×297mm',
          quantity: 20,
          unit: '张',
          lifecycle_status: 'active',
        },
        {
          id: 'item-default-active',
          item_name: '亚克力字',
          quantity: 1,
          unit: '套',
        },
        {
          id: 'item-history',
          item_name: '已删除明细',
          lifecycle_status: 'voided',
        },
      ],
      [{ order_item_id: 'item-active', total_registered: 180, record_count: 2 }],
    )

    expect(options).toEqual([
      {
        id: 'item-active',
        label: '台签纸',
        detail: '铜版纸彩印 · 210×297mm · 20 张',
        registeredAmount: 180,
        recordCount: 2,
      },
      {
        id: 'item-default-active',
        label: '亚克力字',
        detail: '1 套',
        registeredAmount: 0,
        recordCount: 0,
      },
    ])
  })

  it('忽略只存在于汇总中的历史明细', () => {
    const options = buildProjectCostScopeOptions(
      [{ id: 'item-active', item_name: '当前明细', lifecycle_status: 'active' }],
      [{ order_item_id: 'item-history', total_registered: 90, record_count: 1 }],
    )

    expect(options).toHaveLength(1)
    expect(options[0].registeredAmount).toBe(0)
  })
})
