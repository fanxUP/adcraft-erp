export interface UploadRecord {
  id: string
  filename: string
  order_item_id?: string | null
  stage?: string | null
  created_at?: string | null
}
export interface UploadHistory {
  count: number
  latestId: string | null
  records: UploadRecord[]
}

function timestamp(value?: string | null) {
  if (!value) return null
  const normalized = /(Z|[+-]\d{2}:?\d{2})$/.test(value.trim()) ? value.trim() : `${value.trim()}Z`
  const result = Date.parse(normalized)
  return Number.isFinite(result) ? result : null
}

/** Exact filenames are upload history only, never an approved or effective-version relation. */
export function attachmentUploadHistory(attachments: readonly UploadRecord[]): Map<string, UploadHistory> {
  const groups = new Map<string, UploadRecord[]>()
  for (const attachment of attachments) {
    // Unscoped legacy files do not establish identity across uploaders/tasks.
    const key = attachment.order_item_id
      ? JSON.stringify([attachment.stage, attachment.order_item_id, attachment.filename])
      : attachment.id
    const group = groups.get(key) || []
    group.push(attachment)
    groups.set(key, group)
  }
  const result = new Map<string, UploadHistory>()
  for (const records of groups.values()) {
    const sorted = [...records].sort((left, right) => (timestamp(right.created_at) ?? -Infinity) - (timestamp(left.created_at) ?? -Infinity))
    const latest = timestamp(sorted[0]?.created_at)
    const unambiguous = latest !== null && sorted.every(record => timestamp(record.created_at) !== null)
      && (sorted.length === 1 || timestamp(sorted[1]?.created_at) !== latest)
    const history = { count: sorted.length, latestId: unambiguous ? sorted[0]!.id : null, records: sorted }
    for (const record of records) result.set(record.id, history)
  }
  return result
}
