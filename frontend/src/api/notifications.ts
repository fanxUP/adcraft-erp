import { get, post, put, del } from './index'
import type { NotificationResponse, PaginatedData, UnreadCountResponse } from '@/types/api'

export function getNotifications(params: {
  type?: string
  is_read?: boolean
  page?: number
  page_size?: number
} = {}): Promise<PaginatedData<NotificationResponse>> {
  return get('/notifications', params)
}

export function getRecentNotifications(limit = 10): Promise<NotificationResponse[]> {
  return get('/notifications/recent', { limit })
}

export function getUnreadCount(): Promise<UnreadCountResponse> {
  return get('/notifications/unread-count')
}

export function markNotificationRead(id: string): Promise<void> {
  return put(`/notifications/${id}/read`)
}

export function markAllNotificationsRead(): Promise<void> {
  return put('/notifications/read-all')
}

export function deleteNotification(id: string): Promise<void> {
  return del(`/notifications/${id}`)
}

export function sendNotificationMessage(data: {
  user_id: string
  title: string
  content: string
  link?: string
}): Promise<{ id: string }> {
  return post('/notifications/send', data)
}
