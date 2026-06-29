import apiClient from './index'

export function getOrders(params: { page?: number; page_size?: number; status?: string; customer_id?: string }) {
  return apiClient.get('/orders/', { params })
}

export function getOrder(id: string) {
  return apiClient.get(`/orders/${id}`)
}

export function changeOrderStatus(id: string, data: { to_status: string; reason?: string }) {
  return apiClient.post(`/orders/${id}/change-status`, data)
}

export function setOrderCost(id: string, cost_amount: number) {
  return apiClient.post(`/orders/${id}/set-cost`, { cost_amount })
}

export function autoCalculateCost(id: string) {
  return apiClient.post(`/orders/${id}/auto-cost`)
}
