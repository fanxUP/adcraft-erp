import apiClient from './index'

export function getQuotes(params: { page?: number; page_size?: number; status?: string; customer_id?: string }) {
  return apiClient.get('/quotes/', { params })
}

export function getQuote(id: string) {
  return apiClient.get(`/quotes/${id}`)
}

export function createQuote(data: any) {
  return apiClient.post('/quotes/', data)
}

export function updateQuote(id: string, data: any) {
  return apiClient.put(`/quotes/${id}`, data)
}

export function deleteQuote(id: string) {
  return apiClient.delete(`/quotes/${id}`)
}

export function calculateQuote(id: string) {
  return apiClient.post(`/quotes/${id}/calculate`)
}

export function confirmQuote(id: string) {
  return apiClient.post(`/quotes/${id}/confirm`)
}

export function convertQuoteToOrder(id: string) {
  return apiClient.post(`/quotes/${id}/convert-to-order`)
}
