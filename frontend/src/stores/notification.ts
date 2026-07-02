import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElNotification } from 'element-plus'
import {
  getNotifications,
  getRecentNotifications,
  getUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
} from '@/api/notifications'
import type { NotificationResponse, PaginatedData } from '@/types/api'
import router from '@/router'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<NotificationResponse[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const ws: { value: WebSocket | null } = ref(null)
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const MAX_RECONNECT_ATTEMPTS = 10

  // Connect to WebSocket for real-time notifications
  function connectWebSocket(token: string) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return

    // Clean up existing connection
    disconnectWebSocket()

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/notifications?token=${token}`

    try {
      const socket = new WebSocket(url)
      ws.value = socket

      socket.onopen = () => {
        reconnectAttempts = 0
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleWsMessage(data)
        } catch {
          // Ignore non-JSON messages (e.g., "pong")
        }
      }

      socket.onclose = () => {
        ws.value = null
        // Auto-reconnect with backoff
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000)
          reconnectTimer = setTimeout(() => {
            reconnectAttempts++
            connectWebSocket(token)
          }, delay)
        }
      }

      socket.onerror = () => {
        // Will trigger onclose
      }
    } catch {
      // WebSocket not supported or URL error
    }
  }

  function disconnectWebSocket() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    reconnectAttempts = 0
  }

  function handleWsMessage(data: { type: string; data: unknown }) {
    switch (data.type) {
      case 'new_notification': {
        const notification = data.data as NotificationResponse
        // Add to list
        notifications.value.unshift(notification)
        // Update unread count
        unreadCount.value++
        // Show desktop notification
        showDesktopNotification(notification)
        break
      }
      case 'unread_count': {
        const payload = data.data as { count: number }
        unreadCount.value = payload.count
        break
      }
    }
  }

  function showDesktopNotification(notification: NotificationResponse) {
    ElNotification({
      title: notification.title,
      message: notification.content.slice(0, 100),
      type: notification.type.includes('alert') ? 'warning' : 'info',
      duration: 5000,
      onClick: () => {
        if (notification.link) {
          router.push(notification.link)
        }
      },
    })
  }

  // Fetch notifications list
  async function fetchNotifications(params: {
    type?: string
    is_read?: boolean
    page?: number
    page_size?: number
  } = {}): Promise<PaginatedData<NotificationResponse>> {
    loading.value = true
    try {
      const data = await getNotifications(params)
      notifications.value = data.items
      return data
    } finally {
      loading.value = false
    }
  }

  // Fetch recent notifications (for dropdown)
  async function fetchRecent(limit = 10) {
    try {
      notifications.value = await getRecentNotifications(limit)
    } catch {
      // Silently fail
    }
  }

  // Fetch unread count
  async function fetchUnreadCount() {
    try {
      const data = await getUnreadCount()
      unreadCount.value = data.count
    } catch {
      // Silently fail
    }
  }

  // Mark single notification as read
  async function markRead(id: string) {
    try {
      await markNotificationRead(id)
      const notification = notifications.value.find(n => n.id === id)
      if (notification && !notification.is_read) {
        notification.is_read = true
        notification.read_at = new Date().toISOString()
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
    } catch {
      // Silently fail
    }
  }

  // Mark all as read
  async function markAllRead() {
    try {
      await markAllNotificationsRead()
      notifications.value.forEach(n => {
        if (!n.is_read) {
          n.is_read = true
          n.read_at = new Date().toISOString()
        }
      })
      unreadCount.value = 0
    } catch {
      // Silently fail
    }
  }

  // Delete a notification
  async function remove(id: string) {
    try {
      await deleteNotification(id)
      const notification = notifications.value.find(n => n.id === id)
      if (notification && !notification.is_read) {
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
      notifications.value = notifications.value.filter(n => n.id !== id)
    } catch {
      // Silently fail
    }
  }

  return {
    notifications,
    unreadCount,
    loading,
    connectWebSocket,
    disconnectWebSocket,
    fetchNotifications,
    fetchRecent,
    fetchUnreadCount,
    markRead,
    markAllRead,
    remove,
  }
})
