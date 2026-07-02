<template>
  <div class="chat-layout">
    <!-- 左侧会话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <h3>消息</h3>
        <el-button :icon="Plus" circle size="small" @click="showCreateGroup = true" title="创建群聊" />
      </div>

      <div class="sidebar-search">
        <el-input
          v-model="searchQuery"
          placeholder="搜索"
          :prefix-icon="Search"
          clearable
        />
      </div>

      <!-- 标签页切换 -->
      <el-tabs v-model="activeTab" class="sidebar-tabs">
        <el-tab-pane label="全部用户" name="users">
          <div class="user-list">
            <div
              v-for="user in filteredUsers"
              :key="user.id"
              class="user-item"
              @click="handleStartChat(user)"
            >
              <div class="user-avatar">
                <el-avatar :size="40">
                  {{ (user.real_name || user.username).charAt(0) }}
                </el-avatar>
                <span class="online-status" :class="getUserOnlineStatus(user.id)" />
              </div>
              <div class="user-info">
                <div class="user-name">{{ user.real_name || user.username }}</div>
                <div class="user-role">{{ roleLabels[user.role] || user.role }}</div>
              </div>
            </div>
            <el-empty v-if="filteredUsers.length === 0" description="暂无用户" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的会话" name="conversations">
          <div class="conversation-list">
            <div
              v-for="conv in filteredConversations"
              :key="conv.id"
              class="conversation-item"
              :class="{ active: currentConversation?.id === conv.id }"
              @click="selectConversation(conv)"
            >
              <div class="conv-avatar">
                <el-avatar :size="40" :src="conv.avatar">
                  {{ getConvName(conv).charAt(0) }}
                </el-avatar>
                <span
                  v-if="conv.type === 'private'"
                  class="online-status"
                  :class="getOnlineStatus(conv)"
                />
              </div>

              <div class="conv-info">
                <div class="conv-name">{{ getConvName(conv) }}</div>
                <div class="conv-last-message">
                  <span v-if="conv.last_message_sender_name" class="sender">
                    {{ conv.last_message_sender_name }}:
                  </span>
                  {{ conv.last_message_content || '暂无消息' }}
                </div>
              </div>

              <div class="conv-meta">
                <div class="conv-time">{{ formatTime(conv.last_message_at) }}</div>
                <el-badge
                  v-if="conv.unread_count > 0"
                  :value="conv.unread_count"
                  :max="99"
                  class="unread-badge"
                />
              </div>
            </div>

            <el-empty v-if="filteredConversations.length === 0" description="暂无会话" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 右侧聊天窗口 -->
    <div class="chat-main">
      <ChatWindow
        v-if="currentConversation"
        :conversation="currentConversation"
        @send-message="handleSendMessage"
        @load-more="handleLoadMore"
        @delete-message="handleDeleteMessage"
        @recall-message="handleRecallMessage"
        @mark-read="handleMarkRead"
      />

      <div v-else class="chat-placeholder">
        <el-icon :size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>选择一个会话开始聊天</p>
      </div>
    </div>

    <!-- 创建群聊对话框 -->
    <el-dialog
      v-model="showCreateGroup"
      title="创建群聊"
      width="500px"
    >
      <el-form label-width="80px">
        <el-form-item label="群名称">
          <el-input v-model="groupName" placeholder="请输入群名称" />
        </el-form-item>

        <el-form-item label="选择成员">
          <el-select
            v-model="selectedMemberIds"
            multiple
            filterable
            placeholder="搜索用户"
          >
            <el-option
              v-for="user in chatStore.allUsers"
              :key="user.id"
              :label="user.real_name || user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateGroup = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Plus, Search, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import ChatWindow from './ChatWindow.vue'
import type { Conversation } from '@/types/chat'

const chatStore = useChatStore()
const authStore = useAuthStore()

const searchQuery = ref('')
const activeTab = ref('conversations')
const showCreateGroup = ref(false)
const creating = ref(false)
const groupName = ref('')
const selectedMemberIds = ref<string[]>([])

// 角色标签
const roleLabels: Record<string, string> = {
  admin: '管理员',
  sales: '销售',
  designer: '设计师',
  production: '制作',
  installer: '安装',
  finance: '财务',
}

const currentConversation = computed(() => chatStore.currentConversation)

// 过滤用户列表
const filteredUsers = computed(() => {
  if (!searchQuery.value) return chatStore.allUsers

  const query = searchQuery.value.toLowerCase()
  return chatStore.allUsers.filter(user => {
    const name = (user.real_name || user.username).toLowerCase()
    return name.includes(query) || user.username.toLowerCase().includes(query)
  })
})

// 过滤会话列表
const filteredConversations = computed(() => {
  if (!searchQuery.value) return chatStore.conversations

  const query = searchQuery.value.toLowerCase()
  return chatStore.conversations.filter(conv => {
    const name = getConvName(conv).toLowerCase()
    return name.includes(query)
  })
})

function getConvName(conv: Conversation) {
  if (conv.type === 'group') return conv.name || '群聊'
  return conv.name || '私聊'
}

function getOnlineStatus(conv: Conversation) {
  if (conv.type !== 'private') return ''
  const otherUserId = conv.last_message_sender_id
  if (!otherUserId) return ''
  const presence = chatStore.getUserPresence(otherUserId)
  return presence.status
}

function getUserOnlineStatus(userId: string) {
  const presence = chatStore.getUserPresence(userId)
  return presence.status
}

function formatTime(time?: string) {
  if (!time) return ''

  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`

  return `${date.getMonth() + 1}/${date.getDate()}`
}

async function handleStartChat(user: {id: string, real_name: string, username: string}) {
  try {
    await chatStore.startPrivateChat(user.id)
    activeTab.value = 'conversations'
    ElMessage.success(`与 ${user.real_name || user.username} 的会话已创建`)
  } catch (error) {
    ElMessage.error('创建会话失败')
  }
}

async function selectConversation(conv: Conversation) {
  await chatStore.fetchConversationDetail(conv.id)
  await chatStore.fetchMessages(conv.id)
  await chatStore.markConversationRead(conv.id)
}

async function handleCreateGroup() {
  if (!groupName.value) {
    ElMessage.warning('请输入群名称')
    return
  }

  if (selectedMemberIds.value.length === 0) {
    ElMessage.warning('请选择至少一个成员')
    return
  }

  creating.value = true
  try {
    await chatStore.createConversation('group', selectedMemberIds.value, groupName.value)
    showCreateGroup.value = false
    groupName.value = ''
    selectedMemberIds.value = []
    activeTab.value = 'conversations'
    ElMessage.success('群聊创建成功')
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function handleSendMessage(content: string, type: string, replyToId?: string, mentions?: string[]) {
  if (!currentConversation.value) return

  try {
    await chatStore.sendMessage(currentConversation.value.id, content, type, replyToId, mentions)
  } catch (error) {
    ElMessage.error('发送失败')
  }
}

async function handleLoadMore() {
  if (!currentConversation.value) return

  const messages = chatStore.messages.get(currentConversation.value.id) || []
  if (messages.length > 0) {
    await chatStore.fetchMessages(currentConversation.value.id, messages[0].id)
  }
}

async function handleDeleteMessage(messageId: string) {
  if (!currentConversation.value) return

  try {
    await chatStore.deleteMessage(messageId, currentConversation.value.id)
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

async function handleRecallMessage(messageId: string) {
  if (!currentConversation.value) return

  try {
    await chatStore.recallMessage(messageId, currentConversation.value.id)
    ElMessage.success('撤回成功')
  } catch (error) {
    ElMessage.error('撤回失败')
  }
}

async function handleMarkRead(messageId: string) {
  if (!currentConversation.value) return
  await chatStore.markMessageRead(currentConversation.value.id, messageId)
}

onMounted(async () => {
  // 并行加载用户列表和会话列表
  await Promise.all([
    chatStore.fetchAllUsers(),
    chatStore.fetchConversations(),
  ])

  // 连接 WebSocket
  if (authStore.token) {
    chatStore.connectWebSocket(authStore.token)
  }

  // 请求通知权限
  if (Notification.permission === 'default') {
    Notification.requestPermission()
  }
})

onUnmounted(() => {
  chatStore.clearCurrentConversation()
})
</script>

<style scoped lang="scss">
.chat-layout {
  display: flex;
  height: calc(100vh - 60px);
  background: #f5f5f5;
}

.chat-sidebar {
  width: 320px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;

  h3 {
    margin: 0;
    font-size: 16px;
  }
}

.sidebar-search {
  padding: 12px 16px;
}

.sidebar-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 16px;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    overflow: hidden;
  }

  :deep(.el-tab-pane) {
    height: 100%;
    overflow-y: auto;
  }
}

.user-list,
.conversation-list {
  height: 100%;
}

.user-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #f5f7fa;
  }
}

.user-avatar {
  position: relative;
  margin-right: 12px;

  .online-status {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid #fff;
    background: #909399;

    &.online {
      background: #67c23a;
    }

    &.away {
      background: #e6a23c;
    }

    &.busy {
      background: #f56c6c;
    }
  }
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 2px;
}

.user-role {
  font-size: 12px;
  color: #909399;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #f5f7fa;
  }

  &.active {
    background: #ecf5ff;
  }
}

.conv-avatar {
  position: relative;
  margin-right: 12px;

  .online-status {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid #fff;

    &.online {
      background: #67c23a;
    }

    &.away {
      background: #e6a23c;
    }

    &.busy {
      background: #f56c6c;
    }

    &.offline {
      background: #909399;
    }
  }
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-last-message {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  .sender {
    color: #606266;
  }
}

.conv-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-left: 12px;
}

.conv-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.unread-badge {
  :deep(.el-badge__content) {
    font-size: 10px;
  }
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;

  p {
    margin-top: 16px;
    font-size: 14px;
  }
}
</style>
