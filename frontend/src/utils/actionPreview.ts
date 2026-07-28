export interface ActionPreviewRow {
  label: string
  value: string
}

export interface ActionPreviewPresentation {
  title: string
  rows: ActionPreviewRow[]
  effects: string[]
  note: string
  fallbackJson: string
}

function text(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number'
    ? String(value)
    : ''
}

export function buildActionPreview(
  data: Record<string, unknown> | null | undefined,
): ActionPreviewPresentation {
  if (!data) {
    return {
      title: '',
      rows: [],
      effects: [],
      note: '',
      fallbackJson: '无数据',
    }
  }

  const rows: ActionPreviewRow[] = []
  const append = (label: string, value: unknown) => {
    const normalized = text(value)
    if (normalized) rows.push({ label, value: normalized })
  }

  append('业务单号', data.business_no)
  append('项目名称', data.project_name)

  const currentStatus = text(data.current_status_label)
  const targetStatus = text(data.target_status_label)
  if (currentStatus && targetStatus) {
    rows.push({ label: '状态变化', value: `${currentStatus} → ${targetStatus}` })
  }

  append('变更原因', data.reason)
  append('明细数量', data.items_count)
  append('预计金额', data.total_amount)

  const effects = Array.isArray(data.effects)
    ? data.effects.filter((item): item is string => typeof item === 'string')
    : []
  const hasStructuredContent = rows.length > 0 || effects.length > 0

  return {
    title: text(data.action_label),
    rows,
    effects,
    note: text(data.note) || text(data._note),
    fallbackJson: hasStructuredContent ? '' : JSON.stringify(data, null, 2),
  }
}
