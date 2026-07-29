import { post, get } from './index'
import type {
  AiChatResponse,
  AiMessage,
  AiSession,
  AiWorkflowGuidance,
} from '@/types/aiAssistant'

export interface AiBusinessRuleSyncLog {
  status: string
  catalog_digest: string
  added_count: number
  updated_count: number
  retired_count: number
  unchanged_count: number
  created_at: string | null
}

export interface AiPageContractHealth {
  version: number
  source_version: number
  active_rule_version: number | null
  database_contract_version: number | null
  page_count: number
  capability_count: number
  semantic_complete_count: number
  write_capability_count: number
  all_write_actions_require_confirmation: boolean
  unknown_permissions: string[]
  in_sync: boolean
  added_targets: string[]
  retired_targets: string[]
}

export interface AiBusinessRuleStatus {
  catalog_digest: string
  in_sync: boolean
  active_count: number
  pending: {
    added_count: number
    updated_count: number
    retired_count: number
    unchanged_count: number
  }
  contract: AiPageContractHealth
  last_sync: AiBusinessRuleSyncLog | null
  recent_syncs: AiBusinessRuleSyncLog[]
}

export interface AiBusinessRuleSyncResult {
  catalog_digest: string
  in_sync: boolean
  added_count: number
  updated_count: number
  retired_count: number
  unchanged_count: number
  details: {
    added: string[]
    updated: string[]
    retired: string[]
  }
}

export function sendChatMessage(data: {
  session_id?: string | null
  message: string
  context?: Record<string, unknown>
}) {
  return post<AiChatResponse>('/ai-assistant/chat', data)
}

export function sendChatMessageStream(data: {
  session_id?: string | null
  message: string
  context?: Record<string, unknown>
}): Promise<Response> {
  // Use fetch directly for SSE streaming
  const token = localStorage.getItem('token') || ''
  return fetch('/api/v1/ai-assistant/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
}

export function getSessions() {
  return get<AiSession[]>('/ai-assistant/sessions')
}

export function getWorkflowGuidance(data: {
  business_type: string
  business_id: string
}) {
  return post<AiWorkflowGuidance>('/ai-assistant/workflow-guidance', data)
}

export function getBusinessRuleStatus() {
  return get<AiBusinessRuleStatus>('/ai-assistant/business-rules/status')
}

export function syncBusinessRules() {
  return post<AiBusinessRuleSyncResult>('/ai-assistant/business-rules/sync')
}

export function getSessionMessages(sessionId: string) {
  return get<AiMessage[]>(`/ai-assistant/sessions/${sessionId}/messages`)
}

export function confirmAction(actionId: string) {
  return post<Record<string, unknown>>(`/ai-assistant/actions/${actionId}/confirm`, {})
}

export function cancelAction(actionId: string) {
  return post<Record<string, unknown>>(`/ai-assistant/actions/${actionId}/cancel`, {})
}

export function getToolCallLogs(page = 1, pageSize = 20) {
  return get<{ items: unknown[]; total: number }>('/ai-assistant/tool-call-logs', { params: { page, page_size: pageSize } })
}

export function getAuditLogs(page = 1, pageSize = 20) {
  return get<{ items: unknown[]; total: number }>('/ai-assistant/audit-logs', { params: { page, page_size: pageSize } })
}
