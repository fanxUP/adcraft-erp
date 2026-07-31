import { get, post, put, del } from './index'
import type { PaginatedData, CustomerResponse, SuccessResponse, ImportResponse } from '@/types/api'

export interface ContactInput {
  name: string
  phone?: string | null
  wechat?: string | null
  position?: string | null
  is_primary?: boolean
  remark?: string | null
}

export type CustomerInput = Partial<Omit<CustomerResponse, 'id' | 'customer_no' | 'created_at' | 'contacts'>> & {
  contacts?: ContactInput[]
}

export function getCustomers(params: { page?: number; page_size?: number; keyword?: string; customer_type?: string }) {
  return get<PaginatedData<CustomerResponse>>('/customers/', { params })
}

export function getCustomer(id: string) {
  return get<CustomerResponse>(`/customers/${id}`)
}

export function createCustomer(data: CustomerInput) {
  return post<CustomerResponse>('/customers/', data)
}

export function updateCustomer(id: string, data: CustomerInput) {
  return put<CustomerResponse>(`/customers/${id}`, data)
}

export function deleteCustomer(id: string) {
  return del<SuccessResponse>(`/customers/${id}`)
}


export function getCustomerTree() {
  return get<import('@/types/api').CustomerTreeNode[]>('/customers/tree')
}

export function importCustomers(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<ImportResponse>('/customers/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
