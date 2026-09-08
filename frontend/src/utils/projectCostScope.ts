export interface ProjectCostScopeItemLike {
  id: string
  item_name: string
  material_process?: string
  specification?: string
  length?: number
  length_unit?: string
  width?: number
  width_unit?: string
  height?: number
  height_unit?: string
  quantity?: number
  unit?: string
  lifecycle_status?: string
}

export interface ProjectCostScopeSummaryLike {
  order_item_id: string
  total_registered: number
  record_count: number
}

export interface ProjectCostScopeOption {
  id: string
  label: string
  detail: string
  registeredAmount: number
  recordCount: number
}

function formatNumber(value: number | undefined) {
  if (value == null) return ''
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function formatSpecification(item: ProjectCostScopeItemLike) {
  if (item.specification) return item.specification
  const dimensions = [
    item.length != null ? `${formatNumber(item.length)}${item.length_unit || 'm'}` : '',
    item.width != null ? `${formatNumber(item.width)}${item.width_unit || 'm'}` : '',
    item.height != null ? `${formatNumber(item.height)}${item.height_unit || 'm'}` : '',
  ].filter(Boolean)
  return dimensions.join(' × ')
}

function formatItemDetail(item: ProjectCostScopeItemLike) {
  return [
    item.material_process,
    formatSpecification(item),
    item.quantity != null ? `${formatNumber(item.quantity)} ${item.unit || ''}`.trim() : '',
  ].filter(Boolean).join(' · ')
}

export function buildProjectCostScopeOptions(
  items: ProjectCostScopeItemLike[],
  summaries: ProjectCostScopeSummaryLike[],
): ProjectCostScopeOption[] {
  const summaryMap = new Map(summaries.map(item => [item.order_item_id, item]))
  return items
    .filter(item => item.lifecycle_status == null || item.lifecycle_status === 'active')
    .map(item => {
      const summary = summaryMap.get(item.id)
      return {
        id: item.id,
        label: item.item_name,
        detail: formatItemDetail(item),
        registeredAmount: summary?.total_registered || 0,
        recordCount: summary?.record_count || 0,
      }
    })
}
