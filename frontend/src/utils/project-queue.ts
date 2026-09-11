import type { OrderListResponse } from '@/types/api'

export const PROJECT_QUEUE_STATUSES = ['pending_confirm', 'confirmed'] as const

export type ProjectQueueStatus = typeof PROJECT_QUEUE_STATUSES[number]

export function isProjectQueueStatus(status: string | null | undefined): status is ProjectQueueStatus {
  return status != null && PROJECT_QUEUE_STATUSES.includes(status as ProjectQueueStatus)
}

/**
 * Keep one order card per project and prefer the latest row when two status
 * queries overlap during a concurrent refresh.
 */
export function dedupeProjectQueueOrders(orders: OrderListResponse[]): OrderListResponse[] {
  const byId = new Map<string, OrderListResponse>()

  for (const order of orders) {
    if (isProjectQueueStatus(order.status)) byId.set(order.id, order)
  }

  return [...byId.values()].sort((a, b) => {
    const createdAtDiff = (b.created_at || '').localeCompare(a.created_at || '')
    if (createdAtDiff !== 0) return createdAtDiff
    return b.order_no.localeCompare(a.order_no)
  })
}
