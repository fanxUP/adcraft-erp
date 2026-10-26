import { describe, expect, it } from 'vitest'
import type { OrderItemResponse } from '@/types/api'
import {
  buildOrderBatchItemDiff,
  buildOrderGroupPayload,
  cloneOrderItemDraft,
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

  it('copies only editable fields and submits the copy as a new, unlinked item', () => {
    const source = { ...item(), lifecycle_status: 'active', order_item_ids: ['task-linked-item'], paid_amount: 500, task_id: 'task-1' }
    const copy = cloneOrderItemDraft(source)
    const diff = buildOrderBatchItemDiff([source], [source, copy])
    expect(copy.id).toBe('')
    expect(copy.other_fee).toBe(10)
    expect(copy).not.toHaveProperty('task_id')
    expect(copy).not.toHaveProperty('order_item_ids')
    expect(copy).not.toHaveProperty('paid_amount')
    expect(copy).not.toHaveProperty('lifecycle_status')
    expect(diff.added).toHaveLength(1)
    expect(diff.deleted).toEqual([])
    expect(diff.updated).toEqual([])
  })

  it('treats moving and ungrouping as updates, preserving the linked item identity', () => {
    const source = item()
    const moved = { ...source, group_id: 'group-b', group_name: '室内' }
    const diff = buildOrderBatchItemDiff([source], [moved])
    expect(diff.added).toEqual([])
    expect(diff.deleted).toEqual([])
    expect(diff.updated[0]).toMatchObject({ id: source.id, changedFields: ['group_name', 'group_id'] })
    const ungrouped = buildOrderBatchItemDiff([source], [{ ...source, group_id: undefined, group_name: undefined }])
    expect(ungrouped.updated[0].item.group_id).toBeNull()
    expect(ungrouped.updated[0].item.group_name).toBeNull()
    expect(ungrouped.deleted).toEqual([])
  })

  it('retains explicit group order including an empty group between populated groups', () => {
    const groups = buildOrderGroupPayload([item(), item({ id: 'item-2', group_id: 'group-b', sort_order: 1 })], [], [
      { groupId: 'group-b', groupName: '室内' },
      { groupId: 'empty', groupName: '待定' },
      { groupId: 'group-a', groupName: '门头' },
    ])
    expect(groups.map(group => group.group_id)).toEqual(['group-b', 'empty', 'group-a'])
    expect(groups.map(group => group.sort_order)).toEqual([0, 1, 2])
  })
})
