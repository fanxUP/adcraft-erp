import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'
import type {
  Conversation,
  ConversationDetail,
  Message,
  UserPresence,
  WsChatMessage,
} from '@/types/chat'
import * as chatApi from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<ConversationDetail | null>(null)
  const messages = ref<Map<string, Message[]>>(new Map())
  const userPresences = ref<Map<string, UserPresence>>(new Map())
  const typingUsers = ref<Map<string, { userId: string; userName: string }[]>>(new Map())
  const loading = ref(false)
  const wsConnected = ref(false)
  const allUsers = ref<Array<{id: string, username: string, real_name: string, avatar: string, role: string}>>([])

  // WebSocket
  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 10
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 计算属性
  const totalUnreadCount = computed(() => {
    return conversations.value.reduce((sum, conv) => sum + conv.unread_count, 0)
  })

  // ============ WebSocket 管理 ============

  function connectWebSocket(token: string) {
    if (ws?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/chat?token=${token}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      console.log('[Chat WS] Connected')
      wsConnected.value = true
      reconnectAttempts = 0
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsChatMessage
        handleWsMessage(data)
      } catch (e) {
        console.error('[Chat WS] Parse error:', e)
      }
    }

    ws.onclose = () => {
      console.log('[Chat WS] Disconnected')
      wsConnected.value = false
      attemptReconnect(token)
    }

    ws.onerror = (error) => {
      console.error('[Chat WS] Error:', error)
    }
  }

  function disconnectWebSocket() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    wsConnected.value = false
    reconnectAttempts = 0
  }

  function attemptReconnect(token: string) {
    if (reconnectAttempts >= maxReconnectAttempts) {
      console.log('[Chat WS] Max reconnect attempts reached')
      return
    }

    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
    reconnectAttempts++

    console.log(`[Chat WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)
    reconnectTimer = setTimeout(() => {
      connectWebSocket(token)
    }, delay)
  }

  function handleWsMessage(data: WsChatMessage) {
    switch (data.type) {
      case 'new_message':
        handleNewMessage(data.data.message, data.data.conversation_id)
        break
      case 'user_typing':
        handleUserTyping(data.data.conversation_id, data.data.user_id, data.data.user_name)
        break
      case 'presence_update':
        handlePresenceUpdate(data.data.user_id, data.data.status)
        break
      case 'message_read':
        handleMessageRead(data.data.conversation_id, data.data.message_id, data.data.user_id)
        break
    }
  }

  function handleNewMessage(message: Message, conversationId: string) {
    // 添加到消息列表
    const convMessages = messages.value.get(conversationId) || []
    convMessages.push(message)
    messages.value.set(conversationId, convMessages)

    // 更新会话列表
    const convIndex = conversations.value.findIndex(c => c.id === conversationId)
    if (convIndex !== -1) {
      const conv = conversations.value[convIndex]
      conv.last_message_at = message.created_at
      conv.last_message_content = message.content
      conv.last_message_sender_id = message.sender_id
      conv.last_message_sender_name = message.sender_name

      // 如果不是当前会话，增加未读数
      if (currentConversation.value?.id !== conversationId) {
        conv.unread_count++
      }

      // 移到顶部
      conversations.value.splice(convIndex, 1)
      conversations.value.unshift(conv)
    }

    // 触发桌面通知
    const authStore = useAuthStore()
    if (message.sender_id !== authStore.user?.id) {
      showDesktopNotification(message)
    }
  }

  function handleUserTyping(conversationId: string, userId: string, userName: string) {
    const typing = typingUsers.value.get(conversationId) || []
    const existing = typing.findIndex(t => t.userId === userId)
    if (existing === -1) {
      typing.push({ userId, userName })
      typingUsers.value.set(conversationId, typing)

      // 3秒后自动移除
      setTimeout(() => {
        const current = typingUsers.value.get(conversationId) || []
        const index = current.findIndex(t => t.userId === userId)
        if (index !== -1) {
          current.splice(index, 1)
          typingUsers.value.set(conversationId, current)
        }
      }, 3000)
    }
  }

  function handlePresenceUpdate(userId: string, status: string) {
    userPresences.value.set(userId, {
      user_id: userId,
      status: status as any,
    })
  }

  function handleMessageRead(conversationId: string, messageId: string, _userId: string) {
    const convMessages = messages.value.get(conversationId) || []
    const message = convMessages.find(m => m.id === messageId)
    if (message) {
      message.read_by_count++
    }
  }

  function showDesktopNotification(message: Message) {
    if (Notification.permission === 'granted') {
      new Notification(message.sender_name || '新消息', {
        body: message.content,
        icon: '/favicon.ico',
      })
    }
  }

  // ============ 会话管理 ============

  async function fetchConversations() {
    loading.value = true
    try {
      const data = await chatApi.getConversations()
      conversations.value = data
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchConversationDetail(conversationId: string) {
    try {
      const data = await chatApi.getConversationDetail(conversationId)
      currentConversation.value = data
      return data
    } catch (error) {
      console.error('Failed to fetch conversation detail:', error)
      return null
    }
  }

  async function createConversation(type: 'private' | 'group', memberIds: string[], name?: string) {
    try {
      const data = await chatApi.createConversation({ type, member_ids: memberIds, name })
      await fetchConversations()
      return data
    } catch (error) {
      console.error('Failed to create conversation:', error)
      throw error
    }
  }

  async function fetchAllUsers() {
    try {
      const data = await chatApi.getAllUsers()
      allUsers.value = data
      return data
    } catch (error) {
      console.error('Failed to fetch all users:', error)
      return []
    }
  }

  async function startPrivateChat(userId: string) {
    try {
      const conversation = await chatApi.getOrCreatePrivateConversation(userId)
      // 刷新会话列表
      await fetchConversations()
      // 设置为当前会话
      await fetchConversationDetail(conversation.id)
      await fetchMessages(conversation.id)
      return conversation
    } catch (error) {
      console.error('Failed to start private chat:', error)
      throw error
    }
  }

  async function deleteConversation(conversationId: string) {
    try {
      await chatApi.deleteConversation(conversationId)
      conversations.value = conversations.value.filter(c => c.id !== conversationId)
      if (currentConversation.value?.id === conversationId) {
        currentConversation.value = null
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      throw error
    }
  }

  // ============ 消息管理 ============

  async function fetchMessages(conversationId: string, beforeId?: string) {
    try {
      const data = await chatApi.getMessages(conversationId, { before_id: beforeId, limit: 50 })
      const existing = messages.value.get(conversationId) || []

      if (beforeId) {
        // 加载更多历史消息
        messages.value.set(conversationId, [...data.items, ...existing])
      } else {
        messages.value.set(conversationId, data.items)
      }

      return data
    } catch (error) {
      console.error('Failed to fetch messages:', error)
      return null
    }
  }

  async function sendMessage(conversationId: string, content: string, type: string = 'text', replyToId?: string, mentions?: string[]) {
    try {
      const message = await chatApi.sendMessage(conversationId, {
        content,
        type: type as any,
        reply_to_id: replyToId,
        mentions,
      })

      // 添加到本地消息列表
      const convMessages = messages.value.get(conversationId) || []
      convMessages.push(message)
      messages.value.set(conversationId, convMessages)

      // 更新会话列表
      const convIndex = conversations.value.findIndex(c => c.id === conversationId)
      if (convIndex !== -1) {
        const conv = conversations.value[convIndex]
        conv.last_message_at = message.created_at
        conv.last_message_content = message.content
        conv.last_message_sender_id = message.sender_id
        conv.last_message_sender_name = message.sender_name

        // 移到顶部
        conversations.value.splice(convIndex, 1)
        conversations.value.unshift(conv)
      }

      return message
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  }

  async function deleteMessage(messageId: string, conversationId: string) {
    try {
      await chatApi.deleteMessage(messageId)
      const convMessages = messages.value.get(conversationId) || []
      messages.value.set(conversationId, convMessages.filter(m => m.id !== messageId))
    } catch (error) {
      console.error('Failed to delete message:', error)
      throw error
    }
  }

  async function recallMessage(messageId: string, conversationId: string) {
    try {
      await chatApi.recallMessage(messageId)
      const convMessages = messages.value.get(conversationId) || []
      const message = convMessages.find(m => m.id === messageId)
      if (message) {
        message.type = 'recalled'
        message.content = '消息已撤回'
      }
    } catch (error) {
      console.error('Failed to recall message:', error)
      throw error
    }
  }

  // ============ 已读回执 ============

  async function markMessageRead(conversationId: string, messageId: string) {
    try {
      await chatApi.markMessageRead(conversationId, messageId)
      const convMessages = messages.value.get(conversationId) || []
      const message = convMessages.find(m => m.id === messageId)
      if (message) {
        message.is_read = true
      }
    } catch (error) {
      console.error('Failed to mark message read:', error)
    }
  }

  async function markConversationRead(conversationId: string) {
    try {
      await chatApi.markConversationRead(conversationId)

      // 更新会话未读数
      const conv = conversations.value.find(c => c.id === conversationId)
      if (conv) {
        conv.unread_count = 0
      }

      // 更新消息已读状态
      const convMessages = messages.value.get(conversationId) || []
      convMessages.forEach(msg => {
        msg.is_read = true
      })
    } catch (error) {
      console.error('Failed to mark conversation read:', error)
    }
  }

  // ============ 在线状态 ============

  async function fetchUserPresence(userId: string) {
    try {
      const data = await chatApi.getUserPresence(userId)
      userPresences.value.set(userId, data)
      return data
    } catch (error) {
      console.error('Failed to fetch user presence:', error)
      return null
    }
  }

  async function fetchBatchPresence(userIds: string[]) {
    try {
      const data = await chatApi.getBatchPresence(userIds)
      data.forEach(presence => {
        userPresences.value.set(presence.user_id, presence)
      })
      return data
    } catch (error) {
      console.error('Failed to fetch batch presence:', error)
      return []
    }
  }

  async function updateMyPresence(status: 'online' | 'away' | 'busy') {
    try {
      const data = await chatApi.updateMyPresence(status)
      return data
    } catch (error) {
      console.error('Failed to update presence:', error)
      throw error
    }
  }

  // ============ 搜索 ============

  async function searchMessages(keyword: string, conversationId?: string) {
    try {
      const data = await chatApi.searchMessages({
        keyword,
        conversation_id: conversationId,
      })
      return data
    } catch (error) {
      console.error('Failed to search messages:', error)
      return { items: [], total: 0, has_more: false }
    }
  }

  // ============ 工具方法 ============

  function getUserPresence(userId: string): UserPresence {
    return userPresences.value.get(userId) || { user_id: userId, status: 'offline' }
  }

  function getTypingUsers(conversationId: string) {
    return typingUsers.value.get(conversationId) || []
  }

  function getMessages(conversationId: string): Message[] {
    return messages.value.get(conversationId) || []
  }

  function clearCurrentConversation() {
    currentConversation.value = null
  }

  return {
    // 状态
    conversations,
    currentConversation,
    messages,
    userPresences,
    typingUsers,
    loading,
    wsConnected,
    allUsers,

    // 计算属性
    totalUnreadCount,

    // WebSocket
    connectWebSocket,
    disconnectWebSocket,

    // 会话管理
    fetchConversations,
    fetchConversationDetail,
    createConversation,
    deleteConversation,

    // 用户列表
    fetchAllUsers,
    startPrivateChat,

    // 消息管理
    fetchMessages,
    sendMessage,
    deleteMessage,
    recallMessage,

    // 已读回执
    markMessageRead,
    markConversationRead,

    // 在线状态
    fetchUserPresence,
    fetchBatchPresence,
    updateMyPresence,

    // 搜索
    searchMessages,

    // 工具方法
    getUserPresence,
    getTypingUsers,
    getMessages,
    clearCurrentConversation,
    handleNewMessage,
  }
})
