import { get, post, put, del } from './index'
import type { PaginatedData, AcceptanceListResponse, AcceptanceDetailResponse } from '@/types/api'

export interface AvailableItem {
  id: string
  order_no?: string
  quote_no?: string
  customer_name?: string
  project_name: string
  total_amount: number
  status: string
  department?: string
  created_at: string
}

export function getAvailableOrders() {
  return get<AvailableItem[]>('/acceptances/available-orders')
}

export function getAvailableQuotes() {
  return get<AvailableItem[]>('/acceptances/available-quotes')
}

export function getAcceptances(params: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  order_id?: string
}) {
  return get<PaginatedData<AcceptanceListResponse>>('/acceptances/', { params })
}

export function getAcceptance(id: string) {
  return get<AcceptanceDetailResponse>(`/acceptances/${id}`)
}

export function createAcceptance(data: {
  document_id?: string
  order_id?: string   // backward compat
  quote_id?: string   // backward compat
  accepted_by?: string
  our_acceptor_id?: string
  remark?: string
  items?: Array<{
    item_name: string
    specification?: string
    quantity?: number
    unit?: string
    order_item_id?: string
  }>
}) {
  return post<AcceptanceDetailResponse>('/acceptances/', data)
}

export function updateAcceptance(id: string, data: {
  accepted_by?: string
  our_acceptor_id?: string
  remark?: string
  items?: Array<{
    item_name: string
    specification?: string
    quantity?: number
    unit?: string
    order_item_id?: string
  }>
}) {
  return put<AcceptanceDetailResponse>(`/acceptances/${id}`, data)
}

export function deleteAcceptance(id: string) {
  return del(`/acceptances/${id}`)
}

export function changeAcceptanceStatus(id: string, data: {
  to_status: string
  reason?: string
  accepted_by?: string
}) {
  return post<AcceptanceDetailResponse>(`/acceptances/${id}/change-status`, data)
}

export function uploadAcceptanceAttachment(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<{ id: string; filename: string; filepath: string; filesize: number }>(
    `/acceptances/${id}/attachments`,
    formData
  )
}

export function deleteAcceptanceAttachment(acceptanceId: string, attId: string) {
  return del(`/acceptances/${acceptanceId}/attachments/${attId}`)
}
