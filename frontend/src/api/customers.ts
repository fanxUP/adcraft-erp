import { get, post, put, del } from './index'
import { PaginatedData, CustomerResponse, SuccessResponse, ImportResponse } from '@/types/api'

export function getCustomers(params: { page?: number; page_size?: number; keyword?: string; customer_type?: string }) {
  return get<PaginatedData<CustomerResponse>>('/customers/', { params })
}

export function getCustomer(id: string) {
  return get<CustomerResponse>(`/customers/${id}`)
}

export function createCustomer(data: Omit<Partial<CustomerResponse>, 'id' | 'created_at'>) {
  return post<CustomerResponse>('/customers/', data)
}

export function updateCustomer(id: string, data: Partial<Omit<CustomerResponse, 'id' | 'created_at'>>) {
  return put<CustomerResponse>(`/customers/${id}`, data)
}

export function deleteCustomer(id: string) {
  return del<SuccessResponse>(`/customers/${id}`)
}

export function importCustomers(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<ImportResponse>('/customers/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
