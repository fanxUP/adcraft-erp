import { get, post, put } from './index'
import { PaginatedData, InventoryItemResponse, StockRecordResponse } from '@/types/api'

export function getInventoryItems(params: { page?: number; page_size?: number; keyword?: string; category?: string }) {
  return get<PaginatedData<InventoryItemResponse>>('/inventory/items', { params })
}

export function getInventoryItem(id: string) {
  return get<InventoryItemResponse>(`/inventory/items/${id}`)
}

export function createInventoryItem(data: Omit<Partial<InventoryItemResponse>, 'id' | 'created_at'>) {
  return post<InventoryItemResponse>('/inventory/items', data)
}

export function updateInventoryItem(id: string, data: Partial<Omit<InventoryItemResponse, 'id' | 'created_at'>>) {
  return put<InventoryItemResponse>(`/inventory/items/${id}`, data)
}

export function getStockRecords(params: { page?: number; page_size?: number; item_id?: string; record_type?: string }) {
  return get<PaginatedData<StockRecordResponse>>('/inventory/records', { params })
}

export function stockIn(data: { item_id: string; quantity: number; unit_cost?: number; remark?: string }) {
  return post<InventoryItemResponse>('/inventory/stock-in', data)
}

export function stockOut(data: { item_id: string; quantity: number; remark?: string }) {
  return post<InventoryItemResponse>('/inventory/stock-out', data)
}
