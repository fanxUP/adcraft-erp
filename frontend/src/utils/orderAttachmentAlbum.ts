import { formatDate } from './datetime'

export interface AttachmentWithCreatedAt {
  id: string
  created_at?: string | null
}

export interface AttachmentWithItem extends AttachmentWithCreatedAt {
  order_item_id?: string | null
  order_item_name?: string | null
  order_item_label?: string | null
  order_item_sort_order?: number | null
}

export interface AttachmentAlbumGroup<T extends AttachmentWithCreatedAt> {
  key: string
  label: string
  isUnknown: boolean
  attachments: T[]
}

export interface AttachmentItemAlbumGroup<T extends AttachmentWithItem> {
  key: string
  label: string
  orderItemId: string | null
  sortOrder: number | null
  dates: AttachmentAlbumGroup<T>[]
}

function parseCreatedAt(value?: string | null) {
  if (!value) return null
  const normalized = /(Z|[+-]\d{2}:?\d{2})$/.test(value.trim())
    ? value.trim()
    : `${value.trim()}Z`
  const timestamp = new Date(normalized).getTime()
  return Number.isFinite(timestamp) ? timestamp : null
}

/** Group server-timestamped attachments by the browser's business date. */
export function groupAttachmentsByDate<T extends AttachmentWithCreatedAt>(
  attachments: readonly T[],
): AttachmentAlbumGroup<T>[] {
  const sorted = attachments
    .map((attachment, index) => ({
      attachment,
      index,
      timestamp: parseCreatedAt(attachment.created_at),
    }))
    .sort((left, right) => {
      if (left.timestamp == null && right.timestamp == null) return left.index - right.index
      if (left.timestamp == null) return 1
      if (right.timestamp == null) return -1
      return right.timestamp - left.timestamp || left.index - right.index
    })

  const groups = new Map<string, AttachmentAlbumGroup<T>>()
  for (const { attachment, timestamp } of sorted) {
    const label = timestamp == null ? '时间未知' : formatDate(attachment.created_at)
    const key = timestamp == null ? 'unknown' : label
    const group = groups.get(key)
    if (group) {
      group.attachments.push(attachment)
      continue
    }
    groups.set(key, {
      key,
      label,
      isUnknown: timestamp == null,
      attachments: [attachment],
    })
  }
  return Array.from(groups.values())
}

/**
 * Group order-owned materials by project content and then by upload date.
 * The item id, rather than its display name, is the identity so two rows with
 * the same name never leak materials into one another.
 */
export function groupAttachmentsByItemAndDate<T extends AttachmentWithItem>(
  attachments: readonly T[],
  options?: { itemLabel?: (attachment: T) => string },
): AttachmentItemAlbumGroup<T>[] {
  const groups = new Map<string, {
    firstIndex: number
    label: string
    orderItemId: string | null
    sortOrder: number | null
    attachments: T[]
  }>()

  attachments.forEach((attachment, index) => {
    const orderItemId = attachment.order_item_id || null
    const key = orderItemId || 'unscoped'
    const current = groups.get(key)
    if (current) {
      current.attachments.push(attachment)
      return
    }

    groups.set(key, {
      firstIndex: index,
      label: orderItemId
        ? options?.itemLabel?.(attachment)
          || attachment.order_item_label
          || attachment.order_item_name
          || '未命名项目内容'
        : '未关联项目内容',
      orderItemId,
      sortOrder: attachment.order_item_sort_order ?? null,
      attachments: [attachment],
    })
  })

  return Array.from(groups.values())
    .sort((left, right) => {
      if (left.orderItemId === null && right.orderItemId !== null) return 1
      if (left.orderItemId !== null && right.orderItemId === null) return -1
      const leftSort = left.sortOrder ?? Number.POSITIVE_INFINITY
      const rightSort = right.sortOrder ?? Number.POSITIVE_INFINITY
      return leftSort - rightSort || left.firstIndex - right.firstIndex
    })
    .map(group => ({
      key: group.orderItemId || 'unscoped',
      label: group.label,
      orderItemId: group.orderItemId,
      sortOrder: group.sortOrder,
      dates: groupAttachmentsByDate(group.attachments),
    }))
}
