import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  AiMessage,
  AiPageContext,
  AiPendingAction,
  AiSession,
  AiToolCallResult,
  AiWorkflowGuidance,
} from '@/types/aiAssistant'
import * as aiApi from '@/api/aiAssistant'
import {
  extractWorkflowGuidance,
  parseWorkflowGuidance,
} from '@/utils/workflowGuidance'

export const useAiAssistantStore = defineStore('aiAssistant', () => {
  // UI state
  const visible = ref(false)
  const loading = ref(false)
  const error = ref('')
  const lastActionTimestamp = ref(0)  // Incremented after confirmed actions, pages watch this to refresh data

  // Session state
  const sessions = ref<AiSession[]>([])
  const currentSessionId = ref<string | null>(null)
  const messages = ref<AiMessage[]>([])
  const pageContext = ref<AiPageContext>({})

  // Tool call state
  const toolResults = ref<AiToolCallResult[]>([])
  const pendingAction = ref<AiPendingAction | null>(null)
  const activeGuidance = ref<AiWorkflowGuidance | null>(null)
  const guidanceLoading = ref(false)
  const guidanceError = ref('')

  // Input state
  const inputText = ref('')

  // Computed
  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value) || null
  )
  const hasMessages = computed(() => messages.value.length > 0)
  const isProcessing = computed(() => loading.value)
  const canGuideCurrentPage = computed(() => {
    const supported = [
      'quote',
      'order',
      'design_task',
      'production_task',
      'installation_task',
      'acceptance',
    ]
    return Boolean(
      pageContext.value.business_id
      && supported.includes(pageContext.value.business_type || ''),
    )
  })

  // Toggle drawer
  function toggleDrawer() {
    visible.value = !visible.value
    if (visible.value && !currentSessionId.value) {
      loadSessions()
    }
  }

  function openDrawer() { visible.value = true; loadSessions() }
  function closeDrawer() { visible.value = false }

  // Page context
  function setPageContext(ctx: AiPageContext) {
    pageContext.value = { ...pageContext.value, ...ctx }
  }

  /** Full replacement — used on route change to avoid stale context leaking */
  function resetPageContext(ctx: AiPageContext) {
    pageContext.value = { ...ctx }
  }

  // Sessions
  async function loadSessions() {
    try {
      sessions.value = await aiApi.getSessions()
    } catch { /* empty */ }
  }

  async function switchSession(sessionId: string) {
    currentSessionId.value = sessionId
    toolResults.value = []
    pendingAction.value = null
    activeGuidance.value = null
    try {
      messages.value = await aiApi.getSessionMessages(sessionId)
    } catch {
      messages.value = []
    }
  }

  async function createNewSession() {
    currentSessionId.value = null
    messages.value = []
    toolResults.value = []
    pendingAction.value = null
    activeGuidance.value = null
    inputText.value = ''
  }

  // ── Non-streaming send (fallback) ──

  async function sendMessage(text: string) {
    if (!text.trim() || loading.value) return
    loading.value = true
    error.value = ''
    inputText.value = ''

    const userMsg: AiMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId.value || '',
      role: 'user',
      content: text,
    }
    messages.value.push(userMsg)

    try {
      const response = await aiApi.sendChatMessage({
        session_id: currentSessionId.value,
        message: text,
        context: Object.keys(pageContext.value).length > 0
          ? pageContext.value as Record<string, unknown>
          : undefined,
      })

      if (!currentSessionId.value) {
        currentSessionId.value = response.session_id
        userMsg.session_id = response.session_id
        await loadSessions()
      }

      messages.value.push({
        id: response.message_id,
        session_id: response.session_id,
        role: 'assistant',
        content: response.reply,
      })

      toolResults.value = response.tool_calls || []
      adoptWorkflowGuidance(toolResults.value)

      if (response.pending_action) {
        pendingAction.value = response.pending_action
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '请求失败，请重试'
      messages.value.push({
        id: `err-${Date.now()}`,
        session_id: currentSessionId.value || '',
        role: 'system',
        content: '抱歉，我遇到了问题：' + error.value,
      })
    } finally {
      loading.value = false
    }
  }

  // ── SSE streaming send ──

  async function sendMessageStream(text: string) {
    if (!text.trim() || loading.value) return
    loading.value = true
    error.value = ''
    inputText.value = ''

    // Add user message locally
    const userMsgId = `temp-user-${Date.now()}`
    const userMsg: AiMessage = {
      id: userMsgId,
      session_id: currentSessionId.value || '',
      role: 'user',
      content: text,
    }
    messages.value.push(userMsg)

    // Add placeholder assistant message for streaming
    const assistantMsgId = `temp-ai-${Date.now()}`
    const assistantMsg: AiMessage = {
      id: assistantMsgId,
      session_id: currentSessionId.value || '',
      role: 'assistant',
      content: '',
    }
    messages.value.push(assistantMsg)
    toolResults.value = []

    try {
      const response = await aiApi.sendChatMessageStream({
        session_id: currentSessionId.value,
        message: text,
        context: Object.keys(pageContext.value).length > 0
          ? pageContext.value as Record<string, unknown>
          : undefined,
      })

      if (!response.ok) {
        throw new Error(`SSE request failed: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body not readable')
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let streamMessageId = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))

            switch (event.type) {
              case 'session':
                /* streamSessionId unused */
                if (!currentSessionId.value) {
                  currentSessionId.value = event.session_id
                  userMsg.session_id = event.session_id
                  assistantMsg.session_id = event.session_id
                  loadSessions()
                }
                break

              case 'token':
                assistantMsg.content += event.text
                // Force reactivity by replacing the array item
                messages.value = [...messages.value]
                break

              case 'tool_calls':
                toolResults.value = event.tool_calls || []
                adoptWorkflowGuidance(toolResults.value)
                break

              case 'pending_action':
                pendingAction.value = event.pending_action || null
                break

              case 'done':
                streamMessageId = event.message_id
                assistantMsg.id = event.message_id
                messages.value = [...messages.value]
                break

              case 'error':
                throw new Error(event.message)
            }
          } catch {
            // Ignore parse errors for incomplete chunks
          }
        }
      }

      // Finalize: update assistant message id if we got it from done event
      if (streamMessageId) {
        assistantMsg.id = streamMessageId
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '请求失败，请重试'
      // Replace placeholder with error if no content was streamed
      if (!assistantMsg.content) {
        const idx = messages.value.findIndex(m => m.id === assistantMsgId)
        if (idx !== -1) {
          messages.value[idx] = {
            id: `err-${Date.now()}`,
            session_id: currentSessionId.value || '',
            role: 'system',
            content: '抱歉，我遇到了问题：' + error.value,
          }
        }
      }
    } finally {
      loading.value = false
    }
  }

  function adoptWorkflowGuidance(results: AiToolCallResult[]) {
    const guidance = extractWorkflowGuidance(results)
    if (guidance) activeGuidance.value = guidance
  }

  async function requestWorkflowGuidance(
    businessType: string | undefined,
    businessId: string | undefined,
  ) {
    if (!businessType || !businessId || guidanceLoading.value) return null

    guidanceLoading.value = true
    guidanceError.value = ''
    try {
      const response = await aiApi.getWorkflowGuidance({
        business_type: businessType,
        business_id: businessId,
      })
      const guidance = parseWorkflowGuidance(response)
      if (!guidance) throw new Error('流程导航数据格式不正确')
      activeGuidance.value = guidance
      return guidance
    } catch (e: unknown) {
      guidanceError.value = e instanceof Error ? e.message : '流程核验失败'
      return null
    } finally {
      guidanceLoading.value = false
    }
  }

  function startWorkflowGuidance() {
    return requestWorkflowGuidance(
      pageContext.value.business_type,
      pageContext.value.business_id,
    )
  }

  function refreshWorkflowGuidance() {
    return requestWorkflowGuidance(
      activeGuidance.value?.business_type,
      activeGuidance.value?.business_id,
    )
  }

  function clearWorkflowGuidance() {
    activeGuidance.value = null
    guidanceError.value = ''
  }

  // Confirm/cancel actions
  async function confirmPendingAction(actionId: string) {
    try {
      const result = (await aiApi.confirmAction(actionId)) as Record<string, unknown> | null
      pendingAction.value = null
      lastActionTimestamp.value = Date.now()
      await loadSessions()
      // If backend returned a follow-up AI reply, show it in the chat
      if (result && result.reply) {
        messages.value.push({
          id: (result.followup_message_id as string) || `confirm-${Date.now()}`,
          session_id: currentSessionId.value || '',
          role: 'assistant',
          content: result.reply as string,
        })
        // Force reactivity
        messages.value = [...messages.value]
      }
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '确认失败'
      return null
    }
  }

  async function cancelPendingAction(actionId: string) {
    try {
      await aiApi.cancelAction(actionId)
      pendingAction.value = null
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '取消失败'
    }
  }

  return {
    visible, loading, error,
    sessions, currentSessionId, messages, pageContext,
    toolResults, pendingAction, activeGuidance, guidanceLoading, guidanceError, inputText,
    currentSession, hasMessages, isProcessing, canGuideCurrentPage,
    toggleDrawer, openDrawer, closeDrawer, lastActionTimestamp,
    setPageContext, resetPageContext,
    loadSessions, switchSession, createNewSession,
    sendMessage, sendMessageStream,
    startWorkflowGuidance, refreshWorkflowGuidance, clearWorkflowGuidance,
    confirmPendingAction, cancelPendingAction,
  }
})
