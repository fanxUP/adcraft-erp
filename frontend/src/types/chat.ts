// 聊天系统类型定义

export interface Conversation {
  id: string
  type: 'private' | 'group'
  name?: string
  avatar?: string
  owner_id?: string
  last_message_at?: string
  last_message_content?: string
  last_message_sender_id?: string
  last_message_sender_name?: string
  unread_count: number
  member_count: number
  created_at: string
}

export interface ConversationMember {
  id: string
  user_id: string
  user_name?: string
  user_avatar?: string
  role: 'owner' | 'admin' | 'member'
  nickname?: string
  muted: boolean
  joined_at: string
  last_read_at?: string
  is_online: boolean
}

export interface ConversationDetail extends Conversation {
  members: ConversationMember[]
}

export interface Message {
  id: string
  conversation_id: string
  sender_id: string
  sender_name?: string
  sender_avatar?: string
  type: 'text' | 'image' | 'file' | 'system' | 'reply' | 'recalled' | 'card'
  content: string
  reply_to_id?: string
  reply_to_content?: string
  reply_to_sender_name?: string
  mentions?: string[]
  extra_data?: Record<string, any>
  is_read: boolean
  read_by_count: number
  created_at: string
}

export interface MessageListResponse {
  items: Message[]
  total: number
  has_more: boolean
}

export interface UserPresence {
  user_id: string
  status: 'online' | 'away' | 'busy' | 'offline'
  last_seen_at?: string
}

export interface ConversationCreate {
  type: 'private' | 'group'
  name?: string
  member_ids: string[]
}

export interface ConversationUpdate {
  name?: string
  avatar?: string
}

export interface MessageCreate {
  content: string
  type?: 'text' | 'image' | 'file'
  reply_to_id?: string
  mentions?: string[]
  extra_data?: Record<string, any>
}

// WebSocket 消息类型
export interface WsNewMessage {
  type: 'new_message'
  data: {
    message: Message
    conversation_id: string
  }
}

export interface WsUserTyping {
  type: 'user_typing'
  data: {
    conversation_id: string
    user_id: string
    user_name: string
  }
}

export interface WsPresenceUpdate {
  type: 'presence_update'
  data: {
    user_id: string
    status: 'online' | 'away' | 'busy' | 'offline'
  }
}

export interface WsMessageRead {
  type: 'message_read'
  data: {
    conversation_id: string
    message_id: string
    user_id: string
  }
}

export type WsChatMessage = WsNewMessage | WsUserTyping | WsPresenceUpdate | WsMessageRead
