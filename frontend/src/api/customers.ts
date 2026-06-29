import apiClient from './index'

export function getCustomers(params: { page?: number; page_size?: number; keyword?: string; customer_type?: string }) {
  return apiClient.get('/customers/', { params })
}

export function getCustomer(id: string) {
  return apiClient.get(`/customers/${id}`)
}

export function createCustomer(data: any) {
  return apiClient.post('/customers/', data)
}

export function updateCustomer(id: string, data: any) {
  return apiClient.put(`/customers/${id}`, data)
}

export function deleteCustomer(id: string) {
  return apiClient.delete(`/customers/${id}`)
}
