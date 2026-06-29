import apiClient from './index'

export function getInventoryItems(params: { page?: number; page_size?: number; keyword?: string; category?: string }) {
  return apiClient.get('/inventory/items', { params })
}

export function getInventoryItem(id: string) {
  return apiClient.get(`/inventory/items/${id}`)
}

export function createInventoryItem(data: any) {
  return apiClient.post('/inventory/items', data)
}

export function updateInventoryItem(id: string, data: any) {
  return apiClient.put(`/inventory/items/${id}`, data)
}

export function getStockRecords(params: { page?: number; page_size?: number; item_id?: string; record_type?: string }) {
  return apiClient.get('/inventory/records', { params })
}

export function stockIn(data: any) {
  return apiClient.post('/inventory/stock-in', data)
}

export function stockOut(data: any) {
  return apiClient.post('/inventory/stock-out', data)
}
