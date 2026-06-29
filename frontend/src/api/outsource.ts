import apiClient from './index'

export function getOutsourceVendors(params: { page?: number; page_size?: number; keyword?: string; service_type?: string }) {
  return apiClient.get('/outsource/vendors', { params })
}

export function getOutsourceVendor(id: string) {
  return apiClient.get(`/outsource/vendors/${id}`)
}

export function createOutsourceVendor(data: any) {
  return apiClient.post('/outsource/vendors', data)
}

export function updateOutsourceVendor(id: string, data: any) {
  return apiClient.put(`/outsource/vendors/${id}`, data)
}

export function deleteOutsourceVendor(id: string) {
  return apiClient.delete(`/outsource/vendors/${id}`)
}

export function getOutsourceTasks(params: { page?: number; page_size?: number; status?: string; vendor_id?: string; order_id?: string }) {
  return apiClient.get('/outsource/tasks', { params })
}

export function getOutsourceTask(id: string) {
  return apiClient.get(`/outsource/tasks/${id}`)
}

export function createOutsourceTask(data: any) {
  return apiClient.post('/outsource/tasks', data)
}

export function updateOutsourceTask(id: string, data: any) {
  return apiClient.put(`/outsource/tasks/${id}`, data)
}

export function getOutsourcePayments(params: { page?: number; page_size?: number; vendor_id?: string; task_id?: string }) {
  return apiClient.get('/outsource/payments', { params })
}

export function createOutsourcePayment(data: any) {
  return apiClient.post('/outsource/payments', data)
}
