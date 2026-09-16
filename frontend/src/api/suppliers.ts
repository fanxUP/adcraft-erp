import { get, post, put } from './index'
import type { PaginatedData, SupplierResponse } from '@/types/api'

export interface SupplierPayload {
  name: string
  short_name?: string | null
  supplier_type?: string
  contact_person?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  tax_id?: string | null
  bank_name?: string | null
  bank_account?: string | null
  tax_rate?: number | null
  settlement_method?: string | null
  settlement_days?: number | null
  service_type?: string | null
  coop_rating?: string | null
  remark?: string | null
  is_active?: boolean
}

export interface SupplierQuery {
  page?: number
  page_size?: number
  keyword?: string
  supplier_type?: string
  is_active?: boolean
}

export function getSuppliers(params?: SupplierQuery) {
  return get<PaginatedData<SupplierResponse>>('/suppliers/', { params })
}

export function getSupplier(id: string) {
  return get<SupplierResponse>(`/suppliers/${id}`)
}

export function createSupplier(data: SupplierPayload) {
  return post<SupplierResponse>('/suppliers/', data)
}

export function updateSupplier(id: string, data: Partial<SupplierPayload>) {
  return put<SupplierResponse>(`/suppliers/${id}`, data)
}

export function deactivateSupplier(id: string) {
  return post<SupplierResponse>(`/suppliers/${id}/deactivate`)
}
