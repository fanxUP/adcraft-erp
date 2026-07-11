import { get, post, put, del } from './index'
import { PaginatedData, SupplierResponse, SuccessResponse } from '@/types/api'

export function getSuppliers(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<SupplierResponse>>('/suppliers/', { params })
}

export function getSupplier(id: string) {
  return get<SupplierResponse>(`/suppliers/${id}`)
}

export function createSupplier(data: Omit<Partial<SupplierResponse>, 'id' | 'supplier_no' | 'created_at'>) {
  return post<SupplierResponse>('/suppliers/', data)
}

export function updateSupplier(id: string, data: Partial<Omit<SupplierResponse, 'id' | 'supplier_no' | 'created_at'>>) {
  return put<SupplierResponse>(`/suppliers/${id}`, data)
}

export function deleteSupplier(id: string) {
  return del<SuccessResponse>(`/suppliers/${id}`)
}
