import type { OrderEditGroup, OrderEditItem, OrderItemResponse } from '@/types/api'

export interface OrderEditorEmptyGroup {
  groupId: string
  groupName?: string | null
}

export interface OrderBatchItemUpdate {
  id: string
  item: OrderEditItem
  changedFields: string[]
}

export interface OrderBatchItemDiff {
  added: Array<{ item: OrderEditItem }>
  updated: OrderBatchItemUpdate[]
  deleted: Array<{ id: string; itemName: string }>
}

const ORDER_EDIT_ITEM_FIELDS = [
  'item_name',
  'product_id',
  'material_id',
  'process_id',
  'length',
  'length_unit',
  'width',
  'width_unit',
  'height',
  'height_unit',
  'quantity',
  'unit',
  'use_area',
  'quantity_mode',
  'pieces',
  'unit_price',
  'process_fee',
  'installation_fee',
  'design_fee',
  'transport_fee',
  'other_fee',
  'remark',
  'image_url',
  'sort_order',
  'group_name',
  'group_id',
  'material_process',
] as const

function canonicalValue(value: unknown): unknown {
  if (value === undefined || value === '') return null
  if (typeof value === 'number' && Number.isNaN(value)) return null
  return value
}

export function serializeOrderItemDraft(item: OrderItemResponse, sortOrder = item.sort_order ?? 0): OrderEditItem {
  const payload: OrderEditItem = {}
  for (const field of ORDER_EDIT_ITEM_FIELDS) {
    const value = field === 'sort_order' ? sortOrder : item[field]
    ;(payload as Record<string, unknown>)[field] = canonicalValue(value)
  }
  if (item.id) payload.id = item.id
  return payload
}

export function buildOrderBatchItemDiff(
  originalItems: OrderItemResponse[],
  draftItems: OrderItemResponse[],
): OrderBatchItemDiff {
  const originalById = new Map(originalItems.map(item => [item.id, item]))
  const seen = new Set<string>()
  const added: Array<{ item: OrderEditItem }> = []
  const updated: OrderBatchItemUpdate[] = []

  draftItems.forEach((draftItem, index) => {
    const payload = serializeOrderItemDraft(draftItem, index)
    if (!draftItem.id || !originalById.has(draftItem.id)) {
      delete payload.id
      added.push({ item: payload })
      return
    }

    seen.add(draftItem.id)
    const original = originalById.get(draftItem.id)!
    const changedFields = ORDER_EDIT_ITEM_FIELDS.filter(field => (
      canonicalValue(field === 'sort_order' ? index : draftItem[field])
      !== canonicalValue(original[field])
    ))
    if (changedFields.length) {
      updated.push({ id: draftItem.id, item: payload, changedFields: [...changedFields] })
    }
  })

  const deleted = originalItems
    .filter(item => !seen.has(item.id))
    .map(item => ({ id: item.id, itemName: item.item_name }))

  return { added, updated, deleted }
}

export function buildOrderGroupPayload(
  items: OrderItemResponse[],
  emptyGroups: OrderEditorEmptyGroup[] = [],
): OrderEditGroup[] {
  const groups = new Map<string, { group_name: string | null; firstSort: number }>()
  for (const item of items) {
    if (!item.group_id || groups.has(item.group_id)) continue
    groups.set(item.group_id, {
      group_name: item.group_name || null,
      firstSort: item.sort_order ?? Number.MAX_SAFE_INTEGER,
    })
  }
  const ordered = [...groups.entries()].sort((left, right) => (
    left[1].firstSort - right[1].firstSort || left[0].localeCompare(right[0])
  ))
  const result: OrderEditGroup[] = ordered.map(([groupId, group], sort_order) => ({
    group_id: groupId,
    group_name: group.group_name,
    sort_order,
  }))
  const existing = new Set(result.map(group => group.group_id))
  for (const emptyGroup of emptyGroups) {
    if (!emptyGroup.groupId || existing.has(emptyGroup.groupId)) continue
    result.push({
      group_id: emptyGroup.groupId,
      group_name: emptyGroup.groupName || null,
      sort_order: result.length,
    })
    existing.add(emptyGroup.groupId)
  }
  return result
}
