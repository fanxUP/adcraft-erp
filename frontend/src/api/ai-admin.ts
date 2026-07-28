import { get, post, patch, del } from './index'
import type { SuccessResponse, PaginatedData } from '@/types/api'

// ── Types ──

export interface AIProviderItem {
  id: string
  provider_code: string
  provider_name: string
  provider_type: string
  protocol: string
  base_url: string | null
  full_url_mode: boolean
  endpoint_url: string | null
  api_key_display: string | null
  has_api_key: boolean
  auth_header: string
  auth_prefix: string | null
  custom_headers_json: Record<string, string>
  timeout_seconds: number
  retry_count: number
  tls_verify: boolean
  enabled: boolean
  priority: number
  health_status: string
  health_score: number | null
  last_health_check_at: string | null
  model_count: number
  created_at: string
  updated_at: string
}

export interface AIModelItem {
  id: string
  provider_id: string
  provider_name: string | null
  upstream_model_code: string
  display_name: string
  model_role: string | null
  model_type: string
  context_window: number | null
  max_output_tokens: number | null
  supports_streaming: boolean
  supports_tools: boolean
  supports_json_schema: boolean
  supports_vision: boolean
  supports_embedding: boolean
  pricing_json: Record<string, unknown>
  enabled: boolean
  priority: number
  health_status: string
  health_score: number | null
  last_verified_at: string | null
  created_at: string
  updated_at: string
}

export interface ProviderCreateData {
  provider_code: string
  provider_name: string
  provider_type?: string
  protocol?: string
  base_url?: string | null
  full_url_mode?: boolean
  endpoint_url?: string | null
  api_key?: string | null
  auth_header?: string
  auth_prefix?: string | null
  custom_headers?: Record<string, string>
  timeout_seconds?: number
  retry_count?: number
  tls_verify?: boolean
  enabled?: boolean
  priority?: number
}

export interface ProviderUpdateData {
  provider_name?: string
  base_url?: string | null
  api_key?: string | null
  enabled?: boolean
  priority?: number
  timeout_seconds?: number
  [key: string]: unknown
}

export interface ModelCreateData {
  provider_id: string
  upstream_model_code: string
  display_name: string
  model_role?: string
  model_type?: string
  context_window?: number | null
  max_output_tokens?: number | null
  supports_streaming?: boolean
  supports_tools?: boolean
  supports_json_schema?: boolean
  supports_vision?: boolean
  pricing?: Record<string, unknown>
}

export interface ModelUpdateData {
  display_name?: string
  model_role?: string
  enabled?: boolean
  priority?: number
  [key: string]: unknown
}

export interface TestResult {
  success: boolean
  status_code: number | null
  latency_ms: number | null
  first_token_latency_ms: number | null
  input_tokens: number | null
  output_tokens: number | null
  output_text: string | null
  error_code: string | null
  error_message: string | null
}

// ── Provider APIs ──

export function getProviders(params?: { page?: number; page_size?: number; enabled_only?: boolean }) {
  return get<PaginatedData<AIProviderItem>>('/ai/providers/', { params })
}

export function getProvider(id: string) {
  return get<AIProviderItem>(`/ai/providers/${id}`)
}

export function createProvider(data: ProviderCreateData) {
  return post<AIProviderItem>('/ai/providers/', data)
}

export function updateProvider(id: string, data: ProviderUpdateData) {
  return patch<AIProviderItem>(`/ai/providers/${id}`, data)
}

export function deleteProvider(id: string) {
  return del<SuccessResponse>(`/ai/providers/${id}`)
}

export function enableProvider(id: string) {
  return post<AIProviderItem>(`/ai/providers/${id}/enable`)
}

export function disableProvider(id: string) {
  return post<AIProviderItem>(`/ai/providers/${id}/disable`)
}

export function duplicateProvider(id: string, newCode: string, newName: string) {
  return post<AIProviderItem>(`/ai/providers/${id}/duplicate`, {}, {
    params: { new_code: newCode, new_name: newName },
  })
}

export function testProvider(id: string, params?: { test_type?: string; model_code?: string }) {
  return post<TestResult>(`/ai/providers/${id}/test`, {}, { params })
}

// ── Model APIs ──

export function getModels(params?: {
  page?: number
  page_size?: number
  provider_id?: string
  enabled_only?: boolean
}) {
  return get<PaginatedData<AIModelItem>>('/ai/models/', { params })
}

export function getModel(id: string) {
  return get<AIModelItem>(`/ai/models/${id}`)
}

export function createModel(data: ModelCreateData) {
  return post<AIModelItem>('/ai/models/', data)
}

export function updateModel(id: string, data: ModelUpdateData) {
  return patch<AIModelItem>(`/ai/models/${id}`, data)
}

export function deleteModel(id: string) {
  return del<SuccessResponse>(`/ai/models/${id}`)
}
