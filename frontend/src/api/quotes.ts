import { get, post, put, del, apiClient } from './index'
import { PaginatedData, QuoteListResponse, QuoteDetailResponse, SuccessResponse, OrderDetailResponse, ImportResponse } from '@/types/api'

export function getQuotes(params: { page?: number; page_size?: number; status?: string; customer_id?: string }) {
  return get<PaginatedData<QuoteListResponse>>('/quotes/', { params })
}

export function getQuote(id: string) {
  return get<QuoteDetailResponse>(`/quotes/${id}`)
}

export function createQuote(data: Omit<Partial<QuoteDetailResponse>, 'id' | 'quote_no' | 'created_at' | 'items'>) {
  return post<QuoteDetailResponse>('/quotes/', data)
}

export function updateQuote(id: string, data: Partial<Omit<QuoteDetailResponse, 'id' | 'quote_no' | 'created_at'>> & { items?: Partial<QuoteDetailResponse['items'][0]>[] }) {
  return put<QuoteDetailResponse>(`/quotes/${id}`, data)
}

export function deleteQuote(id: string) {
  return del<SuccessResponse>(`/quotes/${id}`)
}

export function confirmQuote(id: string) {
  return post<QuoteDetailResponse>(`/quotes/${id}/confirm`)
}

export function convertQuoteToOrder(id: string) {
  return post<OrderDetailResponse>(`/quotes/${id}/convert-to-order`)
}

export function revertQuoteToDraft(id: string) {
  return post<QuoteDetailResponse>(`/quotes/${id}/revert-to-draft`)
}

export function importQuotes(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<ImportResponse>('/quotes/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function importQuoteItems(quoteId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<QuoteDetailResponse>(`/quotes/${quoteId}/import-items`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function downloadQuoteTemplate() {
  const response = await apiClient.get('/quotes/template', { responseType: 'blob' })
  const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '报价导入模版.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
