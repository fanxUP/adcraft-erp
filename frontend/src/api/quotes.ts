import { get, post, put, del } from './index'
import { PaginatedData, QuoteListResponse, QuoteDetailResponse, SuccessResponse, OrderDetailResponse } from '@/types/api'

export function getQuotes(params: { page?: number; page_size?: number; status?: string; customer_id?: string }) {
  return get<PaginatedData<QuoteListResponse>>('/quotes/', { params })
}

export function getQuote(id: string) {
  return get<QuoteDetailResponse>(`/quotes/${id}`)
}

export function createQuote(data: Omit<Partial<QuoteDetailResponse>, 'id' | 'quote_no' | 'created_at' | 'items'>) {
  return post<QuoteDetailResponse>('/quotes/', data)
}

export function updateQuote(id: string, data: Partial<Omit<QuoteDetailResponse, 'id' | 'quote_no' | 'created_at' | 'items'>>) {
  return put<QuoteDetailResponse>(`/quotes/${id}`, data)
}

export function deleteQuote(id: string) {
  return del<SuccessResponse>(`/quotes/${id}`)
}

export function calculateQuote(id: string) {
  return post<QuoteDetailResponse>(`/quotes/${id}/calculate`)
}

export function confirmQuote(id: string) {
  return post<QuoteDetailResponse>(`/quotes/${id}/confirm`)
}

export function convertQuoteToOrder(id: string) {
  return post<OrderDetailResponse>(`/quotes/${id}/convert-to-order`)
}
