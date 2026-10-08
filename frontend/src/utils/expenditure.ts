import type { RouteLocationRaw } from 'vue-router'

export function expenditureSourceTarget(row: { source_kind: string; source_id?: string; document_id?: string | null; document_type?: string | null }): RouteLocationRaw | null {
  if (row.source_kind === 'project_cost' && row.document_id) {
    return row.document_type === 'quote'
      ? { name: 'QuoteCostDetail', params: { quoteId: row.document_id } }
      : { name: 'ProjectCostDetail', params: { orderId: row.document_id } }
  }
  // Existing task-page deep links support order_id, not task_id. Exact
  // source information is already displayed in the read-only drawer.
  if (row.source_kind === 'outsource_task') return row.document_id && row.document_type === 'order'
    ? { name: 'OutsourceTaskList', query: { order_id: row.document_id } }
    : { name: 'OutsourceTaskList' }
  if (row.source_kind === 'outsource_payment') return { name: 'OutsourcePaymentList' }
  return null
}

/** API values are already normalized to Shanghai business time. */
export function expenditureDateLabel(value?: string | null): string {
  return value ? value.slice(0, 10) : '付款日期待核实'
}

export function expenditureCategoryLabel(source: string, category?: string | null): string {
  if (!category) return '—'
  if (source !== 'outsource') return category
  return ({ production: '制作', installation: '安装', design: '设计', transport: '运输' } as Record<string, string>)[category] || category
}

export function latestRequest() {
  let current = 0
  return { begin: () => ++current, isCurrent: (id: number) => id === current }
}
