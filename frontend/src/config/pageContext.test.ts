import { describe, expect, it } from 'vitest'
import {
  getPageCapability,
  getPageQuickActions,
  resolvePageContext,
} from './pageContext'

describe('resolvePageContext', () => {
  it('describes the current order page and adds its business id', () => {
    expect(resolvePageContext('OrderDetail', { id: 'order-1' })).toEqual({
      page: 'order_detail',
      page_title: '订单详情',
      page_purpose: '查看订单信息、交付任务、验收与收款进度',
      business_type: 'order',
      business_id: 'order-1',
      workflow_stage: 'order_delivery',
      available_actions: ['查看订单进度', '查看关联任务', '查看收款情况'],
    })
  })

  it('uses one capability as the source for labels and quick actions', () => {
    const capability = getPageCapability('customer_detail')

    expect(capability?.title).toBe('客户详情')
    expect(capability?.quickActions).toContainEqual({
      label: '订单',
      prompt: '这个客户有哪些订单',
    })
  })

  it('describes resource pages outside the core order flow', () => {
    expect(resolvePageContext('VehicleDispatchList', {})).toMatchObject({
      page: 'vehicle_dispatches',
      page_title: '派车管理',
      page_purpose: '安排用车申请的车辆、司机与出车时间',
      business_type: 'vehicle',
      workflow_stage: 'vehicle_dispatch',
    })
  })

  it('turns normal page actions into guidance prompts when no custom prompts exist', () => {
    expect(getPageQuickActions('vehicle_dispatches')).toEqual([
      { label: '查看待派车申请', prompt: '查看待派车申请' },
      { label: '创建派车单', prompt: '创建派车单' },
      { label: '更新派车状态', prompt: '更新派车状态' },
    ])
  })

  it('returns an empty context for unknown routes', () => {
    expect(resolvePageContext('Unknown', {})).toEqual({})
  })
})
