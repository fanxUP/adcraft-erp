import { get, post, del } from './index'
import { PaginatedData, OrderListResponse, OrderDetailResponse } from '@/types/api'

export function getOrders(params: { page?: number; page_size?: number; status?: string; customer_id?: string }) {
  return get<PaginatedData<OrderListResponse>>('/orders/', { params })
}

export function getOrder(id: string) {
  return get<OrderDetailResponse>(`/orders/${id}`)
}

export function changeOrderStatus(id: string, data: { to_status: string; reason?: string }) {
  return post<OrderDetailResponse>(`/orders/${id}/change-status`, data)
}

export function setOrderCost(id: string, cost_amount: number) {
  return post<OrderDetailResponse>(`/orders/${id}/set-cost`, { cost_amount })
}

export function autoCalculateCost(id: string) {
  return post<OrderDetailResponse>(`/orders/${id}/auto-cost`)
}

export function deleteOrder(id: string) {
  return del(`/orders/${id}`)
}

export function getDeletedOrders(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<OrderListResponse>>('/orders/recycle/list', { params })
}

export function restoreOrder(id: string) {
  return post<OrderDetailResponse>(`/orders/${id}/restore`)
}
