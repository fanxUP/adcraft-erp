export type ProjectCostPageRow =
  | { id: string; _type: 'order' }
  | { id: string; _type: 'quote'; cost_amount?: number | null }

export type OrderProjectCostMap = Readonly<Record<string, number | null | undefined>>

function toCents(value: number | null | undefined): number {
  const amount = Number(value ?? 0)
  return Number.isFinite(amount) ? Math.round(amount * 100) : 0
}

export function getProjectCostPageRowAmount(
  row: ProjectCostPageRow,
  orderCostMap: OrderProjectCostMap,
): number {
  const amount = row._type === 'order' ? orderCostMap[row.id] : row.cost_amount
  return toCents(amount) / 100
}

export function sumCurrentPageProjectCosts(
  rows: readonly ProjectCostPageRow[],
  orderCostMap: OrderProjectCostMap,
): number {
  const totalCents = rows.reduce(
    (total, row) => total + toCents(getProjectCostPageRowAmount(row, orderCostMap)),
    0,
  )
  return totalCents / 100
}
