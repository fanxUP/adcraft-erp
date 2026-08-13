export interface QuoteOrderItem {
  group_name?: string | null
}

export function isDuplicateQuoteGroupName<T extends QuoteOrderItem>(
  items: T[],
  currentName: string,
  candidateName: string,
): boolean {
  return currentName !== candidateName && items.some(item => item.group_name === candidateName)
}

export type QuoteDisplayRow<T extends QuoteOrderItem> =
  | { type: 'group-header'; groupName: string; gi: number; key: string }
  | { type: 'item'; item: T; groupName: string; gi: number; key: string }
  | { type: 'group-total'; groupName: string; total: number; gi: number; key: string }

export function buildQuoteDisplayRows<T extends QuoteOrderItem>(
  items: T[],
  keyFor: (item: T) => string,
  subtotalFor: (item: T) => number,
): QuoteDisplayRow<T>[] {
  const grouped = new Map<string, T[]>()

  for (const item of items) {
    if (item.group_name) {
      if (!grouped.has(item.group_name)) grouped.set(item.group_name, [])
      grouped.get(item.group_name)!.push(item)
    }
  }

  const rows: QuoteDisplayRow<T>[] = []
  const emittedGroups = new Set<string>()
  let groupIndex = 0
  for (const item of items) {
    const groupName = item.group_name
    if (!groupName) {
      rows.push({ type: 'item', item, groupName: '', gi: -1, key: keyFor(item) })
      continue
    }
    if (emittedGroups.has(groupName)) continue

    const groupItems = grouped.get(groupName)!
    emittedGroups.add(groupName)
    // 分项至少有一个占位明细，用首条明细的稳定 key 标识表头/合计，避免排序后 DOM key 串组。
    const groupKey = keyFor(groupItems[0])
    rows.push({ type: 'group-header', groupName, gi: groupIndex, key: `gh-${groupKey}` })
    for (const item of groupItems) {
      rows.push({ type: 'item', item, groupName, gi: groupIndex, key: keyFor(item) })
    }
    rows.push({
      type: 'group-total',
      groupName,
      total: groupItems.reduce((sum, item) => sum + subtotalFor(item), 0),
      gi: groupIndex,
      key: `gt-${groupKey}`,
    })
    groupIndex++
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
    && row.groupName === header.groupName
  ))
  return rows.slice(headerIndex, end >= 0 ? end + 1 : rows.length)
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

/**
 * 根据拖拽行和它落位后的下一行重新排列展示行。
 * 分项表头代表整个分项；落入其他分项内部时吸附到该分项之后，避免拆散任一分项。
 */
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

/** 将展示顺序写回明细，分项表头/合计只作为边界，不进入保存数据。 */
export function applyQuoteDisplayOrder<T extends QuoteOrderItem>(rows: QuoteDisplayRow<T>[]): T[] {
  const items: T[] = []
  let currentGroup: string | undefined
  for (const row of rows) {
    if (row.type === 'group-header') currentGroup = row.groupName
    else if (row.type === 'group-total') currentGroup = undefined
    else {
      row.item.group_name = currentGroup
      items.push(row.item)
    }
  }
  return items
}
