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
