import { get, post, put, del } from './index'
import type {
  Conversation,
  ConversationDetail,
  ConversationCreate,
  ConversationUpdate,
  Message,
  MessageListResponse,
  MessageCreate,
  UserPresence,
} from '@/types/chat'

// ============ 会话管理 ============

/** 创建会话 */
export function createConversation(data: ConversationCreate) {
  return post<Conversation>('/conversations', data)
}

/** 获取会话列表 */
export function getConversations(params?: { page?: number; page_size?: number }) {
  return get<Conversation[]>('/conversations', { params })
}

/** 获取会话详情 */
export function getConversationDetail(conversationId: string) {
  return get<ConversationDetail>(`/conversations/${conversationId}`)
}

/** 更新群信息 */
export function updateConversation(conversationId: string, data: ConversationUpdate) {
  return put<Conversation>(`/conversations/${conversationId}`, data)
}

/** 删除会话/退出群 */
export function deleteConversation(conversationId: string) {
  return del(`/conversations/${conversationId}`)
}

// ============ 成员管理 ============

/** 添加成员 */
export function addMembers(conversationId: string, userIds: string[]) {
  return post(`/conversations/${conversationId}/members`, { user_ids: userIds })
}

/** 移除成员 */
export function removeMember(conversationId: string, userId: string) {
  return del(`/conversations/${conversationId}/members/${userId}`)
}

/** 更新成员角色 */
export function updateMemberRole(conversationId: string, userId: string, role: string) {
  return put(`/conversations/${conversationId}/members/${userId}`, { role })
}

/** 转让群主 */
export function transferOwner(conversationId: string, newOwnerId: string) {
  return post(`/conversations/${conversationId}/transfer`, null, {
    params: { new_owner_id: newOwnerId },
  })
}

// ============ 消息管理 ============

/** 获取消息列表 */
export function getMessages(
  conversationId: string,
  params?: { before_id?: string; limit?: number }
) {
  return get<MessageListResponse>(`/conversations/${conversationId}/messages`, { params })
}

/** 发送消息 */
export function sendMessage(conversationId: string, data: MessageCreate) {
  return post<Message>(`/conversations/${conversationId}/messages`, data)
}

/** 删除消息 */
export function deleteMessage(messageId: string) {
  return del(`/conversations/messages/${messageId}`)
}

/** 撤回消息 */
export function recallMessage(messageId: string) {
  return post(`/conversations/messages/${messageId}/recall`)
}

/** 搜索消息 */
export function searchMessages(params: {
  keyword: string
  conversation_id?: string
  page?: number
  page_size?: number
}) {
  return get<MessageListResponse>('/conversations/messages/search', { params })
}

// ============ 已读回执 ============

/** 标记消息已读 */
export function markMessageRead(conversationId: string, messageId: string) {
  return post(`/conversations/${conversationId}/messages/${messageId}/read`)
}

/** 标记会话所有消息已读 */
export function markConversationRead(conversationId: string) {
  return post(`/conversations/${conversationId}/read-all`)
}

// ============ 在线状态 ============

/** 获取用户在线状态 */
export function getUserPresence(userId: string) {
  return get<UserPresence>(`/conversations/presence/${userId}`)
}

/** 更新我的在线状态 */
export function updateMyPresence(status: 'online' | 'away' | 'busy') {
  return put<UserPresence>('/conversations/presence', { status })
}

/** 批量获取在线状态 */
export function getBatchPresence(userIds: string[]) {
  return post<UserPresence[]>('/conversations/presence/batch', { user_ids: userIds })
}

// ============ 文件上传 ============

/** 上传聊天文件 */
export async function uploadChatFile(conversationId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const data = await post<{
    url: string
    name: string
    size: number
    type: string
    content_type: string
  }>('/conversations/upload', formData, {
    params: { conversation_id: conversationId },
    headers: { 'Content-Type': 'multipart/form-data' },
  })

  return data
}

// ============ 业务卡片分享 ============

/** 分享业务卡片 */
export function shareBusinessCard(
  conversationId: string,
  cardType: 'order' | 'quote' | 'task' | 'customer',
  cardId: string
) {
  return post<Message>('/conversations/share-card', null, {
    params: {
      conversation_id: conversationId,
      card_type: cardType,
      card_id: cardId,
    },
  })
}

/** 批量分享业务卡片 */
export function batchShareCards(
  conversationId: string,
  items: Array<{ card_type: string; card_id: string }>
) {
  return post<Message>(`/conversations/${conversationId}/messages/batch-share`, { items })
}

/** 获取聊天上下文智能推荐 */
export function getRecommendations(
  conversationId: string,
  limit: number = 10
) {
  return get<Array<{id: string, type: string, title: string, subtitle: string, status: string | null, amount?: number}>>(
    `/conversations/${conversationId}/recommendations`,
    { params: { limit } }
  )
}

/** 搜索业务对象（用于名片分享） */
export function searchBusinessObjects(
  type: 'order' | 'quote' | 'task' | 'customer',
  keyword: string
) {
  return get<Array<{id: string, title: string, subtitle: string, status: string | null}>>(
    '/conversations/search-objects',
    { params: { type, keyword } }
  )
}

/** 获取最近分享的业务卡片 */
export function getRecentSharedCards(
  type?: 'order' | 'quote' | 'task' | 'customer',
  limit: number = 10
) {
  return get<Array<{id: string, card_type: string, title: string, subtitle: string, status: string | null, amount: number | null, shared_at: string | null}>>(
    '/conversations/recent-shared',
    { params: { type, limit } }
  )
}

/** 获取用户最近创建/关联的业务对象 */
export function getMyRecentObjects(
  type: 'order' | 'quote' | 'task' | 'customer',
  limit: number = 10
) {
  return get<Array<{id: string, title: string, subtitle: string, status: string | null}>>(
    '/conversations/my-recent-objects',
    { params: { type, limit } }
  )
}

// ============ 用户列表 ============

/** 获取所有活跃用户（会话列表用） */
export function getAllUsers() {
  return get<Array<{id: string, username: string, real_name: string, avatar: string, role: string}>>('/users/all')
}

/** 获取或创建私聊会话（懒加载） */
export function getOrCreatePrivateConversation(userId: string) {
  return get<Conversation>(`/conversations/private/${userId}`)
}
