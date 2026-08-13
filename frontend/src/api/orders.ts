import { get, post, put, del } from './index'
import { PaginatedData, OrderListResponse, OrderDetailResponse, QuoteDetailResponse } from '@/types/api'

export function getOrders(params: { page?: number; page_size?: number; status?: string; customer_id?: string; keyword?: string }) {
  return get<PaginatedData<OrderListResponse>>('/orders/', { params })
}

export function getOrder(id: string) {
  return get<OrderDetailResponse>(`/orders/${id}`)
}

export function changeOrderStatus(id: string, data: { to_status: string; reason?: string }) {
  return post<OrderDetailResponse>(`/orders/${id}/change-status`, data)
}

export function reopenCompletedOrder(id: string, reason: string) {
  return post<OrderDetailResponse>(`/orders/${id}/reopen-completed`, { to_status: 'in_installation', reason })
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

export function convertOrderToQuote(id: string) {
  return post<QuoteDetailResponse>(`/orders/${id}/convert-to-quote`)
}

export function updateOrderContact(id: string, data: { contact_person?: string | null; contact_phone?: string | null }) {
  return put<OrderDetailResponse>(`/orders/${id}/contact`, data)
}
