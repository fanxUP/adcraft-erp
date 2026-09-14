import { formatDate } from './datetime'

export interface AttachmentWithCreatedAt {
  id: string
  created_at?: string | null
}

export interface AttachmentAlbumGroup<T extends AttachmentWithCreatedAt> {
  key: string
  label: string
  isUnknown: boolean
  attachments: T[]
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
