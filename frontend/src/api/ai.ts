/**
 * AI module API calls — all endpoints return ApiResponse<Data> unwrapped by interceptor.
 */
import { get, post } from './index'
import type {
  AIQuoteAssistResponse,
  AnomalyScanResponse,
  SimilarQuotesResponse,
  BusinessNarrativeResponse,
  SitePhotoAnalyzeResponse,
  OCRRecognizeResponse,
} from '@/types/api'

// ── AI Quote Assistant (Feature 1) ────────────────────────────────────

export function assistQuote(data: { description: string; customer_id?: string }) {
  return post<AIQuoteAssistResponse>('/ai/quotes/assist', data)
}

export function saveAssistedQuote(draftData: Record<string, unknown>) {
  return post<Record<string, unknown>>('/ai/quotes/assist/save', draftData)
}

// ── Site Photo Recognition (Feature 2) ─────────────────────────────────

export function analyzeSitePhoto(file: File, installationTaskId?: string) {
  const formData = new FormData()
  formData.append('file', file)
  const params = new URLSearchParams()
  if (installationTaskId) params.append('installation_task_id', installationTaskId)
  return post<SitePhotoAnalyzeResponse>(`/ai/site-photos/analyze?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── Payment Screenshot OCR (Feature 3) ─────────────────────────────────

export function recognizePaymentScreenshot(file: File, orderId?: string) {
  const formData = new FormData()
  formData.append('file', file)
  const params = new URLSearchParams()
  if (orderId) params.append('order_id', orderId)
  return post<OCRRecognizeResponse>(`/ai/payment-ocr/recognize?${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── Smart Business Reports (Feature 4) ─────────────────────────────────

export function getBusinessNarrative(params: {
  period?: string
  year?: number
  month?: number
  week?: number
}) {
  return get<BusinessNarrativeResponse>('/ai/reports/business-narrative', { params })
}

// ── Smart Anomaly Alerts (Feature 5) ──────────────────────────────────

export function scanAnomalies() {
  return get<AnomalyScanResponse>('/ai/anomalies/scan')
}

// ── Smart Quote Knowledge Base (Feature 6) ─────────────────────────────

export function findSimilarQuotes(params: {
  keyword: string
  min_area?: number
  max_area?: number
  material_ids?: string
  limit?: number
}) {
  return get<SimilarQuotesResponse>('/ai/knowledge/similar-quotes', { params })
}

export function searchByDescription(description: string, limit = 5) {
  return get<SimilarQuotesResponse>('/ai/knowledge/search-by-description', {
    params: { description, limit },
  })
}
