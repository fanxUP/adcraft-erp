import { describe, expect, it } from 'vitest'
import type { OrderItemResponse } from '@/types/api'
import { buildOrderDisplayRows, buildOrderItemSections, formatOrderItemSpec, getOrderPricingMode, normalizeOrderItemGroups, orderItemFormula, withOrderPricingMode } from './orderItemPresentation'
import { applyQuoteDisplayOrder, reorderQuoteDisplayRows } from './quoteItemOrdering'
import { calcQuoteLineSubtotal } from './quoteLineCalculation'

function item(id: string, fields: Partial<OrderItemResponse> = {}): OrderItemResponse {
  return { id, item_name: id, quantity: 5, unit: '块', unit_price: 100, use_area: false, quantity_mode: 'piece', process_fee: 0, installation_fee: 0, design_fee: 0, transport_fee: 0, other_fee: 10, subtotal_amount: 510, sort_order: 0, ...fields }
}

describe('order grouping and pricing', () => {
  const groups = [{ groupId: 'b', groupName: '同名分项' }, { groupId: 'empty', groupName: '' }, { groupId: 'a', groupName: '同名分项' }]
  const lines = [item('a1', { group_id: 'a', group_name: '同名分项' }), item('b1', { group_id: 'b', group_name: '同名分项', sort_order: 1 }), item('none', { sort_order: 2 })]

  it('keeps same-named IDs distinct, keeps empty groups and accounts for every line once', () => {
    const sections = buildOrderItemSections(lines, groups)
    expect(sections.map(section => section.groupId)).toEqual(['b', 'empty', 'a', ''])
    expect(sections.map(section => section.items.map(item => item.id))).toEqual([['b1'], [], ['a1'], ['none']])
    expect(sections.reduce((sum, section) => sum + section.total, 0)).toBe(1530)
    expect(lines.map(item => item.id)).toEqual(['a1', 'b1', 'none'])
  })

  it('does not merge ambiguous legacy name-only lines into an existing ID', () => {
    const normalized = normalizeOrderItemGroups([item('legacy', { group_name: '同名分项' })], groups)
    expect(normalized[0]!.group_id).not.toBe('a')
    expect(normalized[0]!.group_id).not.toBe('b')
    const unique = normalizeOrderItemGroups([item('old', { group_name: '门头' })], [{ groupId: 'known', groupName: '门头' }])
    expect(unique[0]!.group_id).toBe('known')
    expect(normalizeOrderItemGroups([item('long', { group_name: '很长的历史分项名称'.repeat(20) })])[0]!.group_id!.length).toBeLessThanOrEqual(100)
  })

  it('moves an entire collapsed group using complete rows and preserves every ID and subtotal', () => {
    const rows = buildOrderDisplayRows(lines, groups, item => item.id, calcQuoteLineSubtotal, () => 1)
    // Screen can hide the children; reordering must use this complete model.
    const reordered = reorderQuoteDisplayRows(rows, 'gh-a', 'gh-b')
    expect(reordered.filter(row => row.type === 'group-header').map(row => row.groupId)).toEqual(['a', 'b', 'empty'])
    const result = applyQuoteDisplayOrder(reordered)
    expect(result.map(item => item.id)).toEqual(['a1', 'b1', 'none'])
    expect(result.map(item => item.group_id)).toEqual(['a', 'b', undefined])
    expect(result.reduce((sum, item) => sum + calcQuoteLineSubtotal(item), 0)).toBe(1530)
  })

  it('reorders empty groups independently from populated groups', () => {
    const rows = buildOrderDisplayRows(lines, groups, item => item.id, calcQuoteLineSubtotal, () => 1)
    const reordered = reorderQuoteDisplayRows(rows, 'gh-empty', 'gh-b')
    expect(reordered.filter(row => row.type === 'group-header').map(row => row.groupId)).toEqual(['empty', 'b', 'a'])
    expect(applyQuoteDisplayOrder(reordered)).toHaveLength(3)
  })

  it('switches geometry, manual area and quantity while restoring the original quantity and unit', () => {
    const source = item('x', { width: 2, width_unit: 'm', height: 50, height_unit: 'cm', pieces: 3 })
    const geometry = withOrderPricingMode(source, 'dimensions')
    expect(geometry.quantity).toBe(3)
    expect(geometry.unit).toBe('㎡')
    expect(getOrderPricingMode(geometry)).toBe('dimensions')
    expect(calcQuoteLineSubtotal(geometry)).toBe(310)
    const restored = withOrderPricingMode(geometry, 'quantity', { quantity: source.quantity, unit: source.unit! })
    expect(restored.quantity).toBe(5)
    expect(restored.unit).toBe('块')
    expect(restored.quantity_mode).toBe('piece')
    expect(restored.width).toBe(2)
    expect(calcQuoteLineSubtotal(restored)).toBe(510)
    const manual = withOrderPricingMode(geometry, 'area', { quantity: 8, unit: '㎡' })
    expect(manual.use_area).toBe(false)
    expect(getOrderPricingMode(manual)).toBe('area')
    expect(calcQuoteLineSubtotal(manual)).toBe(810)
    expect(source.quantity).toBe(5)
  })

  it('explains other fees and formats legacy dimensions with their original units', () => {
    expect(orderItemFormula(item('x'))).toContain('5块 × ¥100.00 + 其他费 ¥10.00 = ¥510.00')
    expect(formatOrderItemSpec(item('x', { length: 3, length_unit: 'm', width: 120, width_unit: 'cm', height: 9, height_unit: 'mm' }))).toBe('3m × 120cm')
    expect(formatOrderItemSpec(item('x', { width: 2, height: 1, pieces: 3 }))).toBe('2m × 1m × 3件')
  })
})
