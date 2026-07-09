import { get, post, put, del } from './index'
import { PaginatedData, VendorResponse, OutsourceTaskResponse, OutsourcePaymentResponse, SuccessResponse } from '@/types/api'

export function getOutsourceVendors(params: { page?: number; page_size?: number; keyword?: string; service_type?: string }) {
  return get<PaginatedData<VendorResponse>>('/outsource/vendors', { params })
}

export function getOutsourceVendor(id: string) {
  return get<VendorResponse>(`/outsource/vendors/${id}`)
}

export function createOutsourceVendor(data: Omit<Partial<VendorResponse>, 'id' | 'created_at'>) {
  return post<VendorResponse>('/outsource/vendors', data)
}

export function updateOutsourceVendor(id: string, data: Partial<Omit<VendorResponse, 'id' | 'created_at'>>) {
  return put<VendorResponse>(`/outsource/vendors/${id}`, data)
}

export function deleteOutsourceVendor(id: string) {
  return del<SuccessResponse>(`/outsource/vendors/${id}`)
}

export function getOutsourceTasks(params: { page?: number; page_size?: number; status?: string; vendor_id?: string; order_id?: string }) {
  return get<PaginatedData<OutsourceTaskResponse>>('/outsource/tasks', { params })
}

export function getOutsourceTask(id: string) {
  return get<OutsourceTaskResponse>(`/outsource/tasks/${id}`)
}

export function createOutsourceTask(data: Omit<Partial<OutsourceTaskResponse>, 'id' | 'task_no' | 'created_at' | 'vendor_name'>) {
  return post<OutsourceTaskResponse>('/outsource/tasks', data)
}

export function updateOutsourceTask(id: string, data: Partial<Omit<OutsourceTaskResponse, 'id' | 'task_no' | 'created_at' | 'vendor_name'>>) {
  return put<OutsourceTaskResponse>(`/outsource/tasks/${id}`, data)
}

export function getOutsourcePayments(params: { page?: number; page_size?: number; vendor_id?: string; task_id?: string }) {
  return get<PaginatedData<OutsourcePaymentResponse>>('/outsource/payments', { params })
}

export function createOutsourcePayment(data: Omit<Partial<OutsourcePaymentResponse>, 'id' | 'payment_no' | 'vendor_name' | 'created_at' | 'created_by'>) {
  return post<OutsourcePaymentResponse>('/outsource/payments', data)
}

export function cancelOutsourceTask(id: string) {
  return post<OutsourceTaskResponse>(`/outsource/tasks/${id}/cancel`)
}

export function revertOutsourceTask(id: string) {
  return post<OutsourceTaskResponse>(`/outsource/tasks/${id}/revert`)
}

export function deleteOutsourceTask(id: string) {
  return del<SuccessResponse>(`/outsource/tasks/${id}`)
}

export function getQuotesForDropdown() {
  return get<{id: string; label: string; quote_no: string; project_name: string; customer_name: string | null}[]>('/outsource/quotes-for-dropdown')
}

export function getOrdersForDropdown() {
  return get<{id: string; label: string; order_no: string; project_name: string}[]>('/outsource/orders-for-dropdown')
}

export function getDocumentsForDropdown() {
  return get<{id: string; doc_no: string; project_name: string; doc_type: string; label: string}[]>('/outsource/documents-for-dropdown')
}
