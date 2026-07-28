import { post, get } from './index'
import type { AiChatResponse, AiSession, AiMessage } from '@/types/aiAssistant'

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
