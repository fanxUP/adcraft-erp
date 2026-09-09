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
  use_area?: boolean
  area?: number
  quantity?: number
  unit?: string
  unit_price?: number
  subtotal_amount?: number
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
  materialProcess: string
  specification: string
  area: number | null
  useArea: boolean
  quantity: number | null
  unit: string
  unitPrice: number | null
  subtotalAmount: number | null
  registeredAmount: number
  recordCount: number
}

export function getProjectCostScopeIds(cost: {
  order_item_id?: string | null
  order_item_ids?: string[] | null
}): string[] {
  const ids = cost.order_item_ids?.length
    ? cost.order_item_ids
    : (cost.order_item_id ? [cost.order_item_id] : [])
  return [...new Set(ids)]
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
        materialProcess: item.material_process || '',
        specification: formatSpecification(item),
        area: item.area ?? null,
        useArea: item.use_area === true,
        quantity: item.quantity ?? null,
        unit: item.unit || '',
        unitPrice: item.unit_price ?? null,
        subtotalAmount: item.subtotal_amount ?? null,
        registeredAmount: summary?.total_registered || 0,
        recordCount: summary?.record_count || 0,
      }
    })
}
