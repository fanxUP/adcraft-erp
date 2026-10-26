import type { OrderItemResponse } from '@/types/api'
import type { OrderEditorEmptyGroup } from './orderEditorDraft'
import type { QuoteDisplayRow } from './quoteItemOrdering'
import { calcQuoteLineArea, calcQuoteLineSubtotal } from './quoteLineCalculation'

export type OrderPricingMode = 'quantity' | 'dimensions' | 'area'
export interface OrderItemSection {
  groupId: string
  groupName: string
  items: OrderItemResponse[]
  total: number
}

function legacyGroupId(name: string): string {
  // A compact, deterministic key also fits the API's 100-character limit.
  let first = 0x811c9dc5
  let second = 0x9e3779b9
  for (const char of name) {
    first = Math.imul(first ^ char.codePointAt(0)!, 0x01000193)
    second = Math.imul(second ^ char.codePointAt(0)!, 0x85ebca6b)
  }
  return `legacy-${(first >>> 0).toString(16)}-${(second >>> 0).toString(16)}`
}

/** Recover old name-only groups without combining distinct groups that have IDs. */
export function normalizeOrderItemGroups(items: OrderItemResponse[], groups: OrderEditorEmptyGroup[] = []): OrderItemResponse[] {
  return items.map(item => {
    if (item.group_id || !item.group_name) return item
    const matches = groups.filter(group => group.groupName === item.group_name)
    return { ...item, group_id: matches.length === 1 ? matches[0]!.groupId : legacyGroupId(item.group_name) }
  })
}

export function buildOrderItemSections(items: OrderItemResponse[], groups: OrderEditorEmptyGroup[] = []): OrderItemSection[] {
  const sections = new Map<string, OrderItemSection>()
  for (const group of groups) {
    if (group.groupId && !sections.has(group.groupId)) {
      sections.set(group.groupId, { groupId: group.groupId, groupName: group.groupName || '未命名分项', items: [], total: 0 })
    }
  }
  const ungrouped: OrderItemResponse[] = []
  const sortedItems = [...items].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
  for (const item of normalizeOrderItemGroups(sortedItems, groups)) {
    if (!item.group_id) { ungrouped.push(item); continue }
    if (!sections.has(item.group_id)) {
      sections.set(item.group_id, { groupId: item.group_id, groupName: item.group_name || '未命名分项', items: [], total: 0 })
    }
    sections.get(item.group_id)!.items.push(item)
  }
  const result = [...sections.values()]
  if (ungrouped.length) result.push({ groupId: '', groupName: '未分项明细', items: ungrouped, total: 0 })
  for (const section of result) {
    section.total = Math.round(section.items.reduce((sum, item) => sum + Number(item.subtotal_amount || 0), 0) * 100) / 100
  }
  return result
}

export function buildOrderDisplayRows(
  items: OrderItemResponse[], groups: OrderEditorEmptyGroup[], keyFor: (item: OrderItemResponse) => string,
  subtotalFor: (item: OrderItemResponse) => number, colorFor: (groupId: string) => number,
): QuoteDisplayRow<OrderItemResponse>[] {
  const rows: QuoteDisplayRow<OrderItemResponse>[] = []
  buildOrderItemSections(items, groups).forEach((section, gi) => {
    const { groupId } = section
    const groupName = groups.find(group => group.groupId === groupId)?.groupName ?? section.groupName
    const colorIndex = groupId ? colorFor(groupId) : 0
    if (groupId) rows.push({ type: 'group-header', groupId, groupName, gi, colorIndex, key: `gh-${groupId}` })
    for (const item of section.items) rows.push({ type: 'item', item, groupId, groupName, gi: groupId ? gi : -1, colorIndex, key: keyFor(item) })
    if (groupId) rows.push({ type: 'group-total', groupId, groupName, gi, colorIndex, total: section.items.reduce((sum, item) => sum + subtotalFor(item), 0), key: `gt-${groupId}` })
  })
  return rows
}

export function getOrderPricingMode(item: OrderItemResponse): OrderPricingMode {
  return item.use_area ? 'dimensions' : item.quantity_mode === 'area' ? 'area' : 'quantity'
}

export function withOrderPricingMode(item: OrderItemResponse, mode: OrderPricingMode, saved?: { quantity: number; unit: string }): OrderItemResponse {
  const next = { ...item, use_area: mode === 'dimensions', quantity_mode: mode === 'quantity' ? 'piece' as const : 'area' as const }
  if (mode === 'dimensions') {
    next.quantity = Math.max(0.01, calcQuoteLineArea(next))
    next.unit = '㎡'
  } else {
    next.quantity = saved?.quantity ?? item.quantity
    next.unit = mode === 'area' ? '㎡' : saved?.unit ?? (item.unit === '㎡' ? '' : item.unit)
  }
  return next
}

export function formatOrderItemSpec(item: OrderItemResponse): string {
  // API responses may already have a formatted legacy specification.
  if (item.length == null && item.width == null && item.height == null) return item.specification || '未设置尺寸'
  const legacy = item.length != null
  const width = legacy ? item.length : item.width
  const height = legacy ? item.width : item.height
  const widthUnit = legacy ? item.length_unit : item.width_unit
  const heightUnit = legacy ? item.width_unit : item.height_unit
  if (width == null && height == null) return '未设置尺寸'
  return `${width ?? '-'}${widthUnit || 'm'} × ${height ?? '-'}${heightUnit || 'm'}${item.pieces && item.pieces !== 1 ? ` × ${item.pieces}件` : ''}`
}

export function orderItemFormula(item: OrderItemResponse): string {
  const base = item.use_area ? calcQuoteLineArea(item) : Number(item.quantity || 0)
  return `${base}${item.use_area || item.quantity_mode === 'area' ? '㎡' : item.unit || ''} × ¥${Number(item.unit_price || 0).toFixed(2)} + 其他费 ¥${Number(item.other_fee || 0).toFixed(2)} = ¥${calcQuoteLineSubtotal(item).toFixed(2)}`
}
