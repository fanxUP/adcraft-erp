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

export function expenditureLastPaymentDateLabel(value?: string | null, paidAmount?: number | null): string {
  if (value) return value.slice(0, 10)
  return Number(paidAmount || 0) > 0 ? '日期待核实' : '未付款'
}

export function expenditureCategoryLabel(source: string, category?: string | null): string {
  if (!category) return '—'
  if (source !== 'outsource') return category
  return ({ production: '制作', installation: '安装', design: '设计', transport: '运输' } as Record<string, string>)[category] || category
}

export function expenditureDimensionCategoryLabel(source: string, category?: string | null): string {
  const sourceLabel = ({ expense: '经营支出', project_cost: '项目实际费用', outsource: '外协' } as Record<string, string>)[source] || '其他来源'
  const categoryLabel = category ? expenditureCategoryLabel(source, category) : '未分类'
  return `${categoryLabel}（${sourceLabel}）`
}

export function expenditureDimensionShare(amount: number, total: number): number {
  if (!Number.isFinite(amount) || !Number.isFinite(total) || amount <= 0 || total <= 0) return 0
  return Math.min(100, Math.round((amount / total) * 1000) / 10)
}

export function expenditureDefaultDateRange(now = new Date()): string[] {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now)
  const part = (type: string) => parts.find(item => item.type === type)?.value || ''
  const year = part('year')
  const month = part('month')
  return [`${year}-${month}-01`, `${year}-${month}-${part('day')}`]
}

export function latestRequest() {
  let current = 0
  return { begin: () => ++current, isCurrent: (id: number) => id === current }
}
