import { describe, expect, it } from 'vitest'
import type { OrderItemResponse } from '@/types/api'
import {
  buildOrderBatchItemDiff,
  buildOrderGroupPayload,
  serializeOrderItemDraft,
} from './orderEditorDraft'

function item(overrides: Partial<OrderItemResponse> = {}): OrderItemResponse {
  return {
    id: 'item-1',
    item_name: '灯箱字',
    quantity: 2,
    unit: '个',
    use_area: false,
    quantity_mode: 'piece',
    pieces: 1,
    unit_price: 100,
    process_fee: 0,
    installation_fee: 0,
    design_fee: 0,
    transport_fee: 0,
    other_fee: 10,
    subtotal_amount: 210,
    sort_order: 0,
    group_id: 'group-a',
    group_name: '门头',
    material_process: '亚克力',
    ...overrides,
  }
}

describe('order editor draft helpers', () => {
  it('separates added, updated and deleted items while preserving stable ids', () => {
    const diff = buildOrderBatchItemDiff(
      [item(), item({ id: 'item-2', item_name: '安装', sort_order: 1 })],
      [
        item({ quantity: 3 }),
        item({ id: '', item_name: '运输', sort_order: 1 }),
      ],
    )

    expect(diff.updated).toHaveLength(1)
    expect(diff.updated[0].id).toBe('item-1')
    expect(diff.updated[0].changedFields).toContain('quantity')
    expect(diff.added).toHaveLength(1)
    expect(diff.added[0].item.item_name).toBe('运输')
    expect(diff.deleted).toEqual([{ id: 'item-2', itemName: '安装' }])
  })

  it('serializes the quote-compatible item fields without trusting client totals', () => {
    const payload = serializeOrderItemDraft(item({ id: '', subtotal_amount: 999 }))

    expect(payload).toMatchObject({
      item_name: '灯箱字',
      quantity: 2,
      unit_price: 100,
      other_fee: 10,
      group_id: 'group-a',
      group_name: '门头',
    })
    expect(payload).not.toHaveProperty('subtotal_amount')
    expect(payload).not.toHaveProperty('lifecycle_status')
  })

  it('builds deterministic group order and retains empty groups', () => {
    const groups = buildOrderGroupPayload(
      [
        item({ group_id: 'group-b', group_name: '灯箱', sort_order: 2 }),
        item({ id: 'item-2', group_id: 'group-a', group_name: '门头', sort_order: 1 }),
      ],
      [{ groupId: 'group-empty', groupName: '待制作' }],
    )

    expect(groups).toEqual([
      { group_id: 'group-a', group_name: '门头', sort_order: 0 },
      { group_id: 'group-b', group_name: '灯箱', sort_order: 1 },
      { group_id: 'group-empty', group_name: '待制作', sort_order: 2 },
    ])
  })
})
