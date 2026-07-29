import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  AiMessage,
  AiPageActionGuide,
  AiPageGuideState,
  AiPageContext,
  AiPendingAction,
  AiSession,
  AiToolCallResult,
  AiWorkflowAction,
  AiWorkflowGuidance,
} from '@/types/aiAssistant'
import * as aiApi from '@/api/aiAssistant'
import {
  extractWorkflowGuidance,
  getGuidanceContextKey,
  matchesGuidanceContext,
  parseWorkflowGuidance,
} from '@/utils/workflowGuidance'
import {
  getPageGuideContinuation,
  hasPageActionCompleted,
} from '@/utils/pageActionGuide'
import {
  clearPersistedPageGuide,
  loadPersistedPageGuide,
  persistPageGuide,
} from '@/utils/pageGuidePersistence'

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
  const actionSubmitting = ref(false)
  const activeGuidance = ref<AiWorkflowGuidance | null>(null)
  const guidanceLoading = ref(false)
  const guidanceError = ref('')
  const guidanceRequestKey = ref<string | null>(null)
  const dismissedGuidanceKey = ref<string | null>(null)
  const activePageGuide = ref<AiPageActionGuide | null>(null)
  const pageGuideState = ref<AiPageGuideState>('idle')
  const pageGuideContinuation = ref<AiWorkflowAction | null>(null)
  let pageGuideOwnerId: string | null = null
  let pageGuideStorage: Storage | null = null
  let guidanceRequestSequence = 0

  // Input state
  const inputText = ref('')

  // Computed
  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value) || null
  )
  const hasMessages = computed(() => messages.value.length > 0)
  const isProcessing = computed(() => loading.value)
  const canGuideCurrentPage = computed(() =>
    Boolean(getGuidanceContextKey(pageContext.value)),
  )

  // Toggle drawer
  function toggleDrawer() {
    visible.value = !visible.value
    if (visible.value) {
      dismissedGuidanceKey.value = null
      if (!currentSessionId.value) loadSessions()
      void maybeStartWorkflowGuidance()
    }
  }

  function openDrawer() {
    visible.value = true
    dismissedGuidanceKey.value = null
    loadSessions()
    void maybeStartWorkflowGuidance()
  }
  function closeDrawer() { visible.value = false }

  // Page context
  function setPageContext(ctx: AiPageContext) {
    const previousKey = getGuidanceContextKey(pageContext.value)
    pageContext.value = { ...pageContext.value, ...ctx }
    handleGuidanceContextChange(previousKey)
  }

  /** Full replacement — used on route change to avoid stale context leaking */
  function resetPageContext(ctx: AiPageContext) {
    const previousKey = getGuidanceContextKey(pageContext.value)
    pageContext.value = { ...ctx }
    handleGuidanceContextChange(previousKey)
  }

  function handleGuidanceContextChange(previousKey: string | null) {
    const currentKey = getGuidanceContextKey(pageContext.value)
    if (previousKey !== currentKey) {
      dismissedGuidanceKey.value = null
      guidanceError.value = ''
    }
    if (
      activeGuidance.value
      && !matchesGuidanceContext(activeGuidance.value, pageContext.value)
    ) {
      activeGuidance.value = null
    }
    void maybeStartWorkflowGuidance()
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
    const currentKey = getGuidanceContextKey(pageContext.value)
    if (
      guidance
      && (!currentKey || matchesGuidanceContext(guidance, pageContext.value))
    ) {
      activeGuidance.value = guidance
    }
  }

  async function requestWorkflowGuidance(
    businessType: string | undefined,
    businessId: string | undefined,
    force = false,
  ) {
    if (!businessType || !businessId) return null
    const requestKey = getGuidanceContextKey({
      business_type: businessType,
      business_id: businessId,
    })
    if (!requestKey) return null
    if (
      !force
      && activeGuidance.value
      && matchesGuidanceContext(activeGuidance.value, {
        business_type: businessType,
        business_id: businessId,
      })
    ) {
      return activeGuidance.value
    }
    if (guidanceLoading.value && guidanceRequestKey.value === requestKey) return null

    const requestSequence = ++guidanceRequestSequence
    guidanceLoading.value = true
    guidanceRequestKey.value = requestKey
    guidanceError.value = ''
    try {
      const response = await aiApi.getWorkflowGuidance({
        business_type: businessType,
        business_id: businessId,
      })
      const guidance = parseWorkflowGuidance(response)
      if (!guidance) throw new Error('流程导航数据格式不正确')
      const isCurrentBusiness = (
        requestKey === getGuidanceContextKey(pageContext.value)
      )
      if (isCurrentBusiness) {
        activeGuidance.value = guidance
        dismissedGuidanceKey.value = null
      }
      const canVerifyDetachedGuide = Boolean(
        activePageGuide.value
        && activePageGuide.value.target_path.includes(businessId),
      )
      if (
        activePageGuide.value
        && (isCurrentBusiness || canVerifyDetachedGuide)
        && hasPageActionCompleted(activePageGuide.value, guidance)
      ) {
        pageGuideContinuation.value = getPageGuideContinuation(
          activePageGuide.value,
          guidance,
        )
        pageGuideState.value = 'completed'
        syncPersistedPageGuide()
      }
      return guidance
    } catch (e: unknown) {
      if (
        requestSequence === guidanceRequestSequence
        && requestKey === getGuidanceContextKey(pageContext.value)
      ) {
        guidanceError.value = e instanceof Error ? e.message : '流程核验失败'
      }
      return null
    } finally {
      if (requestSequence === guidanceRequestSequence) {
        guidanceLoading.value = false
        guidanceRequestKey.value = null
      }
    }
  }

  function maybeStartWorkflowGuidance() {
    const currentKey = getGuidanceContextKey(pageContext.value)
    if (
      !visible.value
      || !currentKey
      || dismissedGuidanceKey.value === currentKey
      || matchesGuidanceContext(activeGuidance.value, pageContext.value)
    ) {
      return Promise.resolve(null)
    }
    return requestWorkflowGuidance(
      pageContext.value.business_type,
      pageContext.value.business_id,
    )
  }

  function startWorkflowGuidance() {
    dismissedGuidanceKey.value = null
    return requestWorkflowGuidance(
      pageContext.value.business_type,
      pageContext.value.business_id,
      true,
    )
  }

  function refreshWorkflowGuidance() {
    return requestWorkflowGuidance(
      pageContext.value.business_type,
      pageContext.value.business_id,
      true,
    )
  }

  function clearWorkflowGuidance() {
    dismissedGuidanceKey.value = getGuidanceContextKey(pageContext.value)
    activeGuidance.value = null
    guidanceError.value = ''
  }

  function startPageActionGuide(action: AiWorkflowAction) {
    if (!action?.target_key) return false
    pageGuideContinuation.value = null
    activePageGuide.value = {
      label: action.label,
      target_path: action.target_path,
      target_key: action.target_key,
      ...(action.target_status ? { target_status: action.target_status } : {}),
      ...(action.draft ? { draft: action.draft } : {}),
    }
    pageGuideState.value = 'locating'
    syncPersistedPageGuide()
    closeDrawer()
    return true
  }

  function setPageGuideState(state: AiPageGuideState) {
    if (activePageGuide.value) pageGuideState.value = state
  }

  function clearPageActionGuide() {
    activePageGuide.value = null
    pageGuideState.value = 'idle'
    pageGuideContinuation.value = null
    syncPersistedPageGuide()
  }

  function takePageGuideContinuation() {
    const continuation = pageGuideContinuation.value
    pageGuideContinuation.value = null
    return continuation
  }

  function getBrowserStorage(): Storage | null {
    try {
      return typeof window === 'undefined' ? null : window.localStorage
    } catch {
      return null
    }
  }

  function continuationToPageGuide(action: AiWorkflowAction): AiPageActionGuide | null {
    if (!action.target_key) return null
    return {
      label: action.label,
      target_path: action.target_path,
      target_key: action.target_key,
      ...(action.target_status ? { target_status: action.target_status } : {}),
      ...(action.draft ? { draft: action.draft } : {}),
    }
  }

  function syncPersistedPageGuide() {
    if (!pageGuideOwnerId || !pageGuideStorage) return
    const continuationGuide = pageGuideContinuation.value
      ? continuationToPageGuide(pageGuideContinuation.value)
      : null
    const guide = continuationGuide
      || (pageGuideState.value === 'completed' ? null : activePageGuide.value)
    if (guide) {
      persistPageGuide(pageGuideStorage, pageGuideOwnerId, guide)
    } else {
      clearPersistedPageGuide(pageGuideStorage, pageGuideOwnerId)
    }
  }

  function restorePageActionGuide(ownerId: string, storage = getBrowserStorage()) {
    const ownerChanged = Boolean(pageGuideOwnerId && pageGuideOwnerId !== ownerId)
    if (ownerChanged) {
      activePageGuide.value = null
      pageGuideContinuation.value = null
      pageGuideState.value = 'idle'
    }
    pageGuideOwnerId = ownerId
    pageGuideStorage = storage
    if (!storage) return false
    const guide = loadPersistedPageGuide(storage, ownerId)
    if (!guide) return false
    activePageGuide.value = guide
    pageGuideContinuation.value = null
    pageGuideState.value = 'restored'
    return true
  }

  function resumePageActionGuide() {
    if (!activePageGuide.value || pageGuideState.value !== 'restored') return null
    pageGuideState.value = 'locating'
    syncPersistedPageGuide()
    return activePageGuide.value.target_path
  }

  async function notifyBusinessMutation() {
    if (!getGuidanceContextKey(pageContext.value)) return null
    return refreshWorkflowGuidance()
  }

  // Confirm/cancel actions
  async function confirmPendingAction(actionId: string) {
    if (actionSubmitting.value) return null
    actionSubmitting.value = true
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
      if (getGuidanceContextKey(pageContext.value)) {
        dismissedGuidanceKey.value = null
        await requestWorkflowGuidance(
          pageContext.value.business_type,
          pageContext.value.business_id,
          true,
        )
      }
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '确认失败'
      return null
    } finally {
      actionSubmitting.value = false
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
    toolResults, pendingAction, actionSubmitting,
    activeGuidance, guidanceLoading, guidanceError, inputText,
    activePageGuide, pageGuideState, pageGuideContinuation,
    currentSession, hasMessages, isProcessing, canGuideCurrentPage,
    toggleDrawer, openDrawer, closeDrawer, lastActionTimestamp,
    setPageContext, resetPageContext,
    loadSessions, switchSession, createNewSession,
    sendMessage, sendMessageStream,
    startWorkflowGuidance, refreshWorkflowGuidance, clearWorkflowGuidance,
    requestWorkflowGuidance,
    startPageActionGuide, setPageGuideState, clearPageActionGuide,
    takePageGuideContinuation, restorePageActionGuide, resumePageActionGuide,
    notifyBusinessMutation,
    confirmPendingAction, cancelPendingAction,
  }
})
