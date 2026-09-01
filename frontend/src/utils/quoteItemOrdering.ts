export interface QuoteOrderItem {
  group_id?: string | null
  group_name?: string | null
}

export interface QuoteEmptyGroup {
  groupId: string
  groupName?: string | null
}

export function isDuplicateQuoteGroupName<T extends QuoteOrderItem>(
  items: T[],
  currentGroupId: string,
  candidateName: string,
): boolean {
  if (!candidateName) return false
  return currentGroupId
    ? items.some(item => item.group_name === candidateName && item.group_id !== currentGroupId)
    : items.some(item => item.group_name === candidateName)
}

export type QuoteDisplayRow<T extends QuoteOrderItem> =
  | { type: 'group-header'; groupId: string; groupName: string; gi: number; colorIndex: number; key: string }
  | { type: 'item'; item: T; groupId: string; groupName: string; gi: number; colorIndex: number; key: string }
  | { type: 'group-total'; groupId: string; groupName: string; total: number; gi: number; colorIndex: number; key: string }

export function buildQuoteDisplayRows<T extends QuoteOrderItem>(
  items: T[],
  keyFor: (item: T) => string,
  subtotalFor: (item: T) => number,
  groupColorFor?: (groupId: string) => number,
  emptyGroups: QuoteEmptyGroup[] = [],
): QuoteDisplayRow<T>[] {
  const grouped = new Map<string, T[]>()
  const groupNames = new Map<string, string>()

  for (const item of items) {
    const gid = item.group_id
    if (gid) {
      if (!grouped.has(gid)) {
        grouped.set(gid, [])
        groupNames.set(gid, item.group_name || '')
      }
      grouped.get(gid)!.push(item)
    }
  }

  // A group can temporarily remain after its last detail is deleted. Keep it
  // in the display model without manufacturing an empty detail row.
  for (const group of emptyGroups) {
    if (!group.groupId || grouped.has(group.groupId)) continue
    grouped.set(group.groupId, [])
    groupNames.set(group.groupId, group.groupName || '')
  }

  const rows: QuoteDisplayRow<T>[] = []
  const emittedGroups = new Set<string>()
  let groupIndex = 0
  const appendGroup = (groupId: string, groupItems: T[], groupName: string, groupKey: string) => {
    if (emittedGroups.has(groupId)) return
    emittedGroups.add(groupId)
    const colorIndex = groupColorFor?.(groupId) ?? ((groupIndex % 5) + 1)
    rows.push({ type: 'group-header', groupId, groupName, gi: groupIndex, colorIndex, key: `gh-${groupKey}` })
    for (const item of groupItems) {
      rows.push({ type: 'item', item, groupId, groupName, gi: groupIndex, colorIndex, key: keyFor(item) })
    }
    rows.push({
      type: 'group-total',
      groupId,
      groupName,
      total: groupItems.reduce((sum, item) => sum + subtotalFor(item), 0),
      gi: groupIndex,
      colorIndex,
      key: `gt-${groupKey}`,
    })
    groupIndex++
  }

  for (const item of items) {
    const gid = item.group_id
    if (!gid) {
      rows.push({ type: 'item', item, groupId: '', groupName: '', gi: -1, colorIndex: 0, key: keyFor(item) })
      continue
    }
    if (emittedGroups.has(gid)) continue

    const groupItems = grouped.get(gid)!
    const groupName = groupNames.get(gid) || ''
    appendGroup(gid, groupItems, groupName, keyFor(groupItems[0]))
  }

  for (const group of emptyGroups) {
    if (!group.groupId || emittedGroups.has(group.groupId)) continue
    appendGroup(group.groupId, [], group.groupName || '', `empty-${group.groupId}`)
  }
  return rows
}

export function getQuoteGroupBlock<T extends QuoteOrderItem>(
  rows: QuoteDisplayRow<T>[],
  headerIndex: number,
): QuoteDisplayRow<T>[] {
  const header = rows[headerIndex]
  if (!header || header.type !== 'group-header') return []
  const end = rows.findIndex((row, index) => (
    index > headerIndex
    && row.type === 'group-total'
    && row.groupId === header.groupId
  ))
  return rows.slice(headerIndex, end >= 0 ? end + 1 : rows.length)
}

export function getQuoteGroupDropSuccessorKey<T extends QuoteOrderItem>(
  rows: QuoteDisplayRow<T>[],
  draggedHeaderKey: string,
  relatedKey: string,
  willInsertAfter = false,
): string | null {
  const draggedIndex = rows.findIndex(row => row.key === draggedHeaderKey)
  const dragged = rows[draggedIndex]
  const relatedIndex = rows.findIndex(row => row.key === relatedKey)
  const related = rows[relatedIndex]
  if (!dragged || dragged.type !== 'group-header' || !related) return relatedKey || null

  const draggedBlock = getQuoteGroupBlock(rows, draggedIndex)
  if (draggedBlock.includes(related)) return related.key

  if (related.type === 'group-header') return related.key
  if (related.gi >= 0) {
    const totalIndex = related.type === 'group-total'
      ? relatedIndex
      : rows.findIndex((row, index) => (
          index > relatedIndex
          && row.type === 'group-total'
          && row.groupId === related.groupId
        ))
    return rows[totalIndex + 1]?.key ?? null
  }

  return willInsertAfter ? (rows[relatedIndex + 1]?.key ?? null) : related.key
}

export function getQuoteDropSuccessorKey<T extends QuoteOrderItem>(
  rows: QuoteDisplayRow<T>[],
  draggedKey: string,
  relatedKey: string,
  willInsertAfter = false,
): string | null {
  const dragged = rows.find(row => row.key === draggedKey)
  if (dragged?.type === 'group-header') {
    return getQuoteGroupDropSuccessorKey(rows, draggedKey, relatedKey, willInsertAfter)
  }

  const relatedIndex = rows.findIndex(row => row.key === relatedKey)
  if (relatedIndex < 0) return relatedKey || null
  return willInsertAfter ? (rows[relatedIndex + 1]?.key ?? null) : relatedKey
}

function groupBoundaryIndex<T extends QuoteOrderItem>(
  rows: QuoteDisplayRow<T>[],
  successorKey: string | null,
): number {
  if (!successorKey) return rows.length
  const successorIndex = rows.findIndex(row => row.key === successorKey)
  if (successorIndex < 0) return rows.length
  const successor = rows[successorIndex]
  if (successor.type === 'group-header' || successor.gi < 0) return successorIndex

  let index = successorIndex
  while (index < rows.length && rows[index].type !== 'group-total') index++
  return index < rows.length ? index + 1 : rows.length
}

export function reorderQuoteDisplayRows<T extends QuoteOrderItem>(
  rows: QuoteDisplayRow<T>[],
  draggedKey: string,
  successorKey: string | null,
): QuoteDisplayRow<T>[] {
  const draggedIndex = rows.findIndex(row => row.key === draggedKey)
  const dragged = rows[draggedIndex]
  if (!dragged || dragged.type === 'group-total') return rows

  const block = dragged.type === 'group-header' ? getQuoteGroupBlock(rows, draggedIndex) : [dragged]
  if (successorKey && block.some(row => row.key === successorKey)) return rows
  const rest = rows.filter(row => !block.includes(row))

  if (dragged.type === 'group-header') {
    const insertAt = groupBoundaryIndex(rest, successorKey)
    return [...rest.slice(0, insertAt), ...block, ...rest.slice(insertAt)]
  }

  if (!successorKey) return [...rest, dragged]
  const successorIndex = rest.findIndex(row => row.key === successorKey)
  if (successorIndex < 0) return [...rest, dragged]
  return [...rest.slice(0, successorIndex), dragged, ...rest.slice(successorIndex)]
}

export function applyQuoteDisplayOrder<T extends QuoteOrderItem>(rows: QuoteDisplayRow<T>[]): T[] {
  const items: T[] = []
  let currentGroupId: string | undefined
  let currentGroupName: string | undefined
  for (const row of rows) {
    if (row.type === 'group-header') {
      currentGroupId = row.groupId
      currentGroupName = row.groupName
    }
    else if (row.type === 'group-total') {
      currentGroupId = undefined
      currentGroupName = undefined
    }
    else {
      row.item.group_id = currentGroupId
      row.item.group_name = currentGroupName
      items.push(row.item)
    }
  }
  return items
}
