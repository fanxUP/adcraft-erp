import { describe, expect, it } from 'vitest'
import { buildProjectCostScopeOptions, getProjectCostScopeIds } from './projectCostScope'

describe('buildProjectCostScopeOptions', () => {
  it('只返回当前有效明细，并带出已登记成本和明细描述', () => {
    const options = buildProjectCostScopeOptions(
      [
        {
          id: 'item-active',
          item_name: '台签纸',
          material_process: '铜版纸彩印',
          specification: '210×297mm',
          use_area: true,
          area: 1.25,
          quantity: 20,
          unit: '张',
          unit_price: 12.5,
          subtotal_amount: 250,
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
        materialProcess: '铜版纸彩印',
        specification: '210×297mm',
        area: 1.25,
        useArea: true,
        quantity: 20,
        unit: '张',
        unitPrice: 12.5,
        subtotalAmount: 250,
        registeredAmount: 180,
        recordCount: 2,
      },
      {
        id: 'item-default-active',
        label: '亚克力字',
        detail: '1 套',
        materialProcess: '',
        specification: '',
        area: null,
        useArea: false,
        quantity: 1,
        unit: '套',
        unitPrice: null,
        subtotalAmount: null,
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

  it('保留面积开关、尺寸回退和零值金额，供明细表逐列展示', () => {
    const [option] = buildProjectCostScopeOptions(
      [{
        id: 'item-area',
        item_name: '户外展板',
        length: 1.2,
        length_unit: 'm',
        width: 0.8,
        width_unit: 'm',
        use_area: false,
        area: 0.96,
        quantity: 0,
        unit_price: 0,
        subtotal_amount: 0,
      }],
      [],
    )

    expect(option).toMatchObject({
      materialProcess: '',
      specification: '1.20m × 0.80m',
      area: 0.96,
      useArea: false,
      quantity: 0,
      unit: '',
      unitPrice: 0,
      subtotalAmount: 0,
    })
  })
})

describe('getProjectCostScopeIds', () => {
  it('优先返回多明细归属，并去除重复ID', () => {
    expect(getProjectCostScopeIds({
      order_item_id: 'legacy-item',
      order_item_ids: ['item-a', 'item-b', 'item-a'],
    })).toEqual(['item-a', 'item-b'])
  })

  it('兼容历史单明细响应', () => {
    expect(getProjectCostScopeIds({ order_item_id: 'legacy-item' })).toEqual(['legacy-item'])
    expect(getProjectCostScopeIds({})).toEqual([])
  })
})
