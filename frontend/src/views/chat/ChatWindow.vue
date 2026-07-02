<template>
  <div class="chat-window" @drop.prevent="handleDrop" @dragover.prevent>
    <!-- 头部 -->
    <div class="chat-header">
      <div class="header-info">
        <h4>{{ conversation.name }}</h4>
        <span v-if="conversation.type === 'group'" class="member-count">
          {{ conversation.member_count }}人
        </span>
      </div>
      <div class="header-actions">
        <el-button :icon="Search" circle size="small" @click="showSearch = true" />
        <el-button
          v-if="conversation.type === 'group'"
          :icon="Setting"
          circle
          size="small"
          @click="showGroupSetting = true"
        />
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="messageListRef" class="message-list" @scroll="handleScroll">
      <div v-if="chatStore.loading" class="loading-tip">
        <el-icon class="is-loading"><Loading /></el-icon>
        加载中...
      </div>

      <template v-for="(msg, index) in messages" :key="msg.id">
        <!-- 时间分割线 -->
        <div
          v-if="shouldShowTime(msg, messages[index - 1])"
          class="time-divider"
        >
          <span>{{ formatMessageTime(msg.created_at) }}</span>
        </div>

        <!-- 消息气泡 -->
        <div
          class="message-item"
          :class="{
            'is-mine': msg.sender_id === currentUserId,
            'is-recalled': msg.type === 'recalled',
          }"
        >
          <el-avatar :size="36" class="msg-avatar">
            {{ msg.sender_name?.charAt(0) || '用' }}
          </el-avatar>

          <div class="msg-content">
            <div class="msg-sender">{{ msg.sender_name }}</div>

            <!-- 回复引用 -->
            <div v-if="msg.reply_to_content" class="reply-quote" @click="scrollToMessage(msg.reply_to_id)">
              <el-icon><ChatLineSquare /></el-icon>
              <span class="reply-sender">{{ msg.reply_to_sender_name }}</span>
              <span class="reply-text">{{ msg.reply_to_content }}</span>
            </div>

            <!-- 消息体 -->
            <div
              class="msg-bubble"
              @contextmenu.prevent="showContextMenu($event, msg)"
            >
              <!-- 文本消息 -->
              <div v-if="msg.type === 'text'" class="msg-text" v-html="formatTextContent(msg.content)" />

              <!-- 图片消息 -->
              <div v-else-if="msg.type === 'image'" class="msg-image">
                <el-image
                  :src="msg.extra_data?.url || msg.content"
                  :preview-src-list="[msg.extra_data?.url || msg.content]"
                  fit="cover"
                  :max-width="300"
                  :max-height="300"
                />
              </div>

              <!-- 文件消息 -->
              <div v-else-if="msg.type === 'file'" class="msg-file" @click="downloadFile(msg)">
                <el-icon :size="32"><Document /></el-icon>
                <div class="file-info">
                  <div class="file-name">{{ msg.extra_data?.name || '文件' }}</div>
                  <div class="file-size">{{ formatFileSize(msg.extra_data?.size) }}</div>
                </div>
                <el-icon class="download-icon"><Download /></el-icon>
              </div>

              <!-- 业务卡片 -->
              <!-- 单卡片 -->
              <div v-else-if="msg.type === 'card' && msg.extra_data?.card_type !== 'batch'" class="msg-card" @click="navigateToCard(msg.extra_data)">
                <div class="card-icon">
                  <el-icon :size="24">
                    <component :is="getCardIcon(msg.extra_data?.card_type)" />
                  </el-icon>
                </div>
                <div class="card-info">
                  <div class="card-header">
                    <span class="card-title">{{ msg.extra_data?.title || msg.content }}</span>
                    <el-tag
                      v-if="msg.extra_data?.status"
                      :type="getStatusTagType(msg.extra_data.status, msg.extra_data?.card_type)"
                      size="small"
                      class="card-status-tag"
                    >
                      {{ getStatusLabel(msg.extra_data.status, msg.extra_data?.card_type) }}
                    </el-tag>
                  </div>
                  <div class="card-subtitle">{{ msg.extra_data?.subtitle }}</div>
                  <div v-if="msg.extra_data?.amount" class="card-amount">
                    ¥{{ formatAmount(msg.extra_data.amount) }}
                  </div>
                </div>
                <el-icon class="card-arrow"><ArrowRight /></el-icon>
                <!-- 快速操作按钮 -->
                <div class="card-actions" @click.stop>
                  <el-button-group size="small">
                    <el-button @click="navigateToCard(msg.extra_data)">
                      <el-icon><View /></el-icon>
                      <span>查看</span>
                    </el-button>
                    <el-button v-if="msg.extra_data?.card_type === 'order' && msg.extra_data?.customer_id" @click="router.push(`/customers/${msg.extra_data.customer_id}`)">
                      <el-icon><User /></el-icon>
                      <span>客户</span>
                    </el-button>
                    <el-button @click="copyCardLink(msg.extra_data)">
                      <el-icon><Link /></el-icon>
                      <span>复制</span>
                    </el-button>
                  </el-button-group>
                </div>
              </div>

              <!-- 批量卡片 -->
              <div v-else-if="msg.type === 'card' && msg.extra_data?.card_type === 'batch'" class="msg-batch-card">
                <div class="batch-card-header">
                  <el-icon :size="18"><Grid /></el-icon>
                  <span>{{ msg.content }}</span>
                </div>
                <div class="batch-card-list">
                  <div
                    v-for="(card, idx) in msg.extra_data.cards"
                    :key="idx"
                    class="batch-card-item"
                    @click="navigateToCard(card)"
                  >
                    <el-icon :size="16">
                      <component :is="getCardIcon(card.card_type)" />
                    </el-icon>
                    <span class="batch-card-item-title">{{ card.title }}</span>
                    <el-tag v-if="card.status" :type="getStatusTagType(card.status, card.card_type)" size="small">
                      {{ getStatusLabel(card.status, card.card_type) }}
                    </el-tag>
                    <el-icon class="batch-card-item-arrow"><ArrowRight /></el-icon>
                  </div>
                </div>
              </div>

              <!-- 系统消息 -->
              <div v-else-if="msg.type === 'system'" class="msg-system">
                <el-icon><InfoFilled /></el-icon>
                <span>{{ msg.content }}</span>
              </div>

              <!-- 撤回消息 -->
              <div v-else-if="msg.type === 'recalled'" class="msg-recalled">
                <el-icon><Remove /></el-icon>
                <span>{{ msg.sender_id === currentUserId ? '你' : msg.sender_name }}撤回了一条消息</span>
              </div>

              <!-- 默认文本 -->
              <div v-else class="msg-text">{{ msg.content }}</div>
            </div>

            <!-- 消息状态 -->
            <div class="msg-status">
              <span v-if="msg.is_read" class="read-status">已读</span>
              <span v-else-if="msg.sender_id === currentUserId" class="read-status unread">未读</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 输入状态 -->
      <div v-if="typingUsers.length > 0" class="typing-indicator">
        <span class="typing-dot" />
        <span class="typing-dot" />
        <span class="typing-dot" />
        <span class="typing-text">
          {{ typingUsers.map(u => u.userName).join('、') }} 正在输入...
        </span>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 工具栏 -->
      <div class="input-toolbar">
        <el-popover placement="top" :width="340" trigger="click">
          <template #reference>
            <el-button :icon="ChatDotRound" circle size="small" />
          </template>
          <div class="emoji-picker">
            <div v-for="group in emojiGroups" :key="group.name" class="emoji-group">
              <div class="emoji-group-name">{{ group.name }}</div>
              <div class="emoji-list">
                <span
                  v-for="emoji in group.emojis"
                  :key="emoji"
                  class="emoji-item"
                  @click="insertEmoji(emoji)"
                >
                  {{ emoji }}
                </span>
              </div>
            </div>
          </div>
        </el-popover>

        <el-upload
          :show-file-list="false"
          :before-upload="handleBeforeUpload"
          accept="image/*"
        >
          <el-button :icon="Picture" circle size="small" />
        </el-upload>

        <el-upload
          :show-file-list="false"
          :before-upload="handleBeforeFileUpload"
        >
          <el-button :icon="Folder" circle size="small" />
        </el-upload>

        <el-popover placement="top" :width="300" trigger="click">
          <template #reference>
            <el-button circle size="small">@</el-button>
          </template>
          <div class="mention-list">
            <div class="mention-title">@提醒</div>
            <el-scrollbar max-height="200px">
              <div
                v-for="member in conversationMembers"
                :key="member.user_id"
                class="mention-item"
                @click="insertMention(member)"
              >
                <el-avatar :size="24">{{ member.user_name?.charAt(0) || '用' }}</el-avatar>
                <span>{{ member.user_name }}</span>
                <span v-if="member.is_online" class="online-dot" />
              </div>
            </el-scrollbar>
          </div>
        </el-popover>

        <el-popover placement="top" :width="200" trigger="click">
          <template #reference>
            <el-button :icon="Tickets" circle size="small" />
          </template>
          <div class="share-card-menu">
            <div class="share-card-title">分享业务卡片</div>
            <div class="share-card-item" @click="showShareDialog('order')">
              <el-icon><ShoppingCart /></el-icon>
              <span>订单</span>
            </div>
            <div class="share-card-item" @click="showShareDialog('quote')">
              <el-icon><Tickets /></el-icon>
              <span>报价单</span>
            </div>
            <div class="share-card-item" @click="showShareDialog('task')">
              <el-icon><List /></el-icon>
              <span>任务</span>
            </div>
            <div class="share-card-item" @click="showShareDialog('customer')">
              <el-icon><User /></el-icon>
              <span>客户</span>
            </div>
            <div class="share-card-divider" />
            <div class="share-card-item batch-share-item" @click="openBatchShare">
              <el-icon><Grid /></el-icon>
              <span>批量分享</span>
            </div>
          </div>
        </el-popover>
      </div>

      <!-- 输入框 -->
      <div class="input-box">
        <el-input
          ref="inputRef"
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入消息... (Enter发送，Shift+Enter换行)"
          resize="none"
          @keydown="handleKeydown"
        />
        <el-button
          type="primary"
          class="send-btn"
          :disabled="!inputText.trim()"
          @click="sendTextMessage"
        >
          发送
        </el-button>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <div class="menu-item" @click="handleReply">
        <el-icon><ChatLineSquare /></el-icon>
        <span>回复</span>
      </div>
      <div
        v-if="canRecall(contextMenu.message)"
        class="menu-item"
        @click="handleRecall"
      >
        <el-icon><Remove /></el-icon>
        <span>撤回</span>
      </div>
      <div
        v-if="contextMenu.message?.sender_id === currentUserId"
        class="menu-item danger"
        @click="handleDelete"
      >
        <el-icon><Delete /></el-icon>
        <span>删除</span>
      </div>
      <div class="menu-item" @click="handleCopy">
        <el-icon><CopyDocument /></el-icon>
        <span>复制</span>
      </div>
    </div>

    <!-- 搜索对话框 -->
    <el-dialog v-model="showSearch" title="搜索消息" width="500px">
      <el-input
        v-model="searchKeyword"
        placeholder="输入关键词搜索"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
      <div v-if="searchResults.length > 0" class="search-results">
        <div
          v-for="result in searchResults"
          :key="result.id"
          class="search-result-item"
        >
          <div class="result-sender">{{ result.sender_name }}</div>
          <div class="result-content">{{ result.content }}</div>
          <div class="result-time">{{ formatMessageTime(result.created_at) }}</div>
        </div>
      </div>
    </el-dialog>

    <!-- 分享卡片对话框 -->
    <el-dialog v-model="showShareCard" :title="`分享${shareCardTypeLabel}`" width="500px">
      <div class="share-card-dialog">
        <el-input
          v-model="shareCardKeyword"
          :placeholder="`搜索${shareCardTypeLabel}`"
          clearable
          @keyup.enter="searchBusinessObjects"
        >
          <template #append>
            <el-button :icon="Search" @click="searchBusinessObjects" />
          </template>
        </el-input>

        <!-- 搜索结果 -->
        <div v-if="shareCardResults.length > 0" class="share-results">
          <div class="share-section-title">搜索结果</div>
          <el-scrollbar max-height="300px">
            <div
              v-for="item in shareCardResults"
              :key="item.id"
              class="share-result-item"
              @click="handleShareCard(item)"
            >
              <div class="result-header">
                <span class="result-title">{{ item.title }}</span>
                <el-tag
                  v-if="item.status"
                  :type="getStatusTagType(item.status, shareCardType)"
                  size="small"
                >
                  {{ getStatusLabel(item.status, shareCardType) }}
                </el-tag>
              </div>
              <div class="result-subtitle">{{ item.subtitle }}</div>
              <div v-if="item.amount" class="result-amount">¥{{ formatAmount(item.amount) }}</div>
            </div>
          </el-scrollbar>
        </div>
        <el-empty v-else-if="shareCardSearched" description="未找到匹配项" />

        <!-- 智能推荐（搜索前展示） -->
        <div v-if="!shareCardSearched && shareRecommendations.length > 0" class="share-section share-recommendations">
          <div class="share-section-title">
            <el-icon><MagicStick /></el-icon>
            智能推荐
          </div>
          <el-scrollbar max-height="150px">
            <div
              v-for="item in shareRecommendations"
              :key="'rec-' + item.id"
              class="share-result-item"
              @click="handleShareCard(item)"
            >
              <div class="result-header">
                <span class="result-title">{{ item.title }}</span>
                <el-tag
                  v-if="item.status"
                  :type="getStatusTagType(item.status, item.type)"
                  size="small"
                >
                  {{ getStatusLabel(item.status, item.type) }}
                </el-tag>
              </div>
              <div class="result-subtitle">{{ item.subtitle }}</div>
              <div v-if="item.amount" class="result-amount">¥{{ formatAmount(item.amount) }}</div>
            </div>
          </el-scrollbar>
        </div>

        <!-- 最近分享 & 我的最近（搜索前展示） -->
        <div v-if="!shareCardSearched && !isLoadingRecent" class="share-recent-sections">
          <!-- 最近分享 -->
          <div v-if="recentSharedCards.length > 0" class="share-section">
            <div class="share-section-title">最近分享</div>
            <div
              v-for="item in recentSharedCards"
              :key="'shared-' + item.id"
              class="share-result-item"
              @click="handleShareCard(item)"
            >
              <div class="result-header">
                <span class="result-title">{{ item.title }}</span>
                <el-tag
                  v-if="item.status"
                  :type="getStatusTagType(item.status, item.card_type)"
                  size="small"
                >
                  {{ getStatusLabel(item.status, item.card_type) }}
                </el-tag>
              </div>
              <div class="result-subtitle">{{ item.subtitle }}</div>
              <div v-if="item.amount" class="result-amount">¥{{ formatAmount(item.amount) }}</div>
            </div>
          </div>

          <!-- 我的最近 -->
          <div v-if="myRecentObjects.length > 0" class="share-section">
            <div class="share-section-title">我的最近</div>
            <div
              v-for="item in myRecentObjects"
              :key="'recent-' + item.id"
              class="share-result-item"
              @click="handleShareCard(item)"
            >
              <div class="result-header">
                <span class="result-title">{{ item.title }}</span>
                <el-tag
                  v-if="item.status"
                  :type="getStatusTagType(item.status, shareCardType)"
                  size="small"
                >
                  {{ getStatusLabel(item.status, shareCardType) }}
                </el-tag>
              </div>
              <div class="result-subtitle">{{ item.subtitle }}</div>
              <div v-if="item.amount" class="result-amount">¥{{ formatAmount(item.amount) }}</div>
            </div>
          </div>

          <!-- 无数据提示 -->
          <el-empty
            v-if="recentSharedCards.length === 0 && myRecentObjects.length === 0 && shareRecommendations.length === 0"
            description="暂无数据，请搜索"
            :image-size="80"
          />
        </div>

        <!-- 加载中 -->
        <div v-else class="share-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
      </div>
    </el-dialog>

    <!-- 批量分享对话框 -->
    <el-dialog v-model="showBatchShare" title="批量分享" width="600px">
      <div class="batch-share-dialog">
        <!-- 类型切换 -->
        <div class="batch-type-tabs">
          <el-radio-group v-model="batchShareType" size="small" @change="loadBatchItems">
            <el-radio-button value="order">订单</el-radio-button>
            <el-radio-button value="quote">报价单</el-radio-button>
            <el-radio-button value="task">任务</el-radio-button>
            <el-radio-button value="customer">客户</el-radio-button>
          </el-radio-group>
        </div>

        <el-input
          v-model="batchShareKeyword"
          placeholder="搜索..."
          clearable
          class="batch-search-input"
          @keyup.enter="searchBatchItems"
        >
          <template #append>
            <el-button :icon="Search" @click="searchBatchItems" />
          </template>
        </el-input>

        <!-- 可选列表 -->
        <el-scrollbar max-height="300px" class="batch-item-list">
          <div
            v-for="item in batchShareItems"
            :key="item.id"
            class="batch-item"
            :class="{ selected: batchSelectedIds.has(item.id) }"
            @click="toggleBatchItem(item)"
          >
            <el-checkbox :model-value="batchSelectedIds.has(item.id)" @click.stop />
            <div class="batch-item-info">
              <div class="batch-item-title">{{ item.title }}</div>
              <div class="batch-item-subtitle">{{ item.subtitle }}</div>
            </div>
            <el-tag v-if="item.status" :type="getStatusTagType(item.status, batchShareType)" size="small">
              {{ getStatusLabel(item.status, batchShareType) }}
            </el-tag>
          </div>
          <el-empty v-if="batchShareItems.length === 0" description="暂无数据" :image-size="60" />
        </el-scrollbar>

        <!-- 已选 -->
        <div v-if="batchSelected.size > 0" class="batch-selected-bar">
          <span>已选 {{ batchSelected.size }} 项</span>
          <el-button text type="primary" size="small" @click="batchSelected.clear(); batchSelectedIds.clear()">清空</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showBatchShare = false">取消</el-button>
        <el-button type="primary" :disabled="batchSelected.size === 0" :loading="batchShareLoading" @click="submitBatchShare">
          分享 ({{ batchSelected.size }})
        </el-button>
      </template>
    </el-dialog>

    <!-- 群设置对话框 -->
    <el-dialog v-model="showGroupSetting" title="群设置" width="500px">
      <div class="group-setting">
        <el-form label-width="80px">
          <el-form-item label="群名称">
            <el-input v-model="groupName" />
          </el-form-item>
        </el-form>

        <div class="member-list-title">群成员 ({{ conversationMembers.length }})</div>
        <el-scrollbar max-height="300px">
          <div
            v-for="member in conversationMembers"
            :key="member.user_id"
            class="member-item"
          >
            <el-avatar :size="32">{{ member.user_name?.charAt(0) || '用' }}</el-avatar>
            <div class="member-info">
              <span class="member-name">{{ member.user_name }}</span>
              <el-tag v-if="member.role === 'owner'" size="small" type="danger">群主</el-tag>
              <el-tag v-else-if="member.role === 'admin'" size="small">管理员</el-tag>
            </div>
            <span v-if="member.is_online" class="online-status online">在线</span>
          </div>
        </el-scrollbar>
      </div>
    </el-dialog>

    <!-- 回复引用提示 -->
    <div v-if="replyTo" class="reply-preview">
      <div class="reply-info">
        <el-icon><ChatLineSquare /></el-icon>
        <span>回复 {{ replyTo.sender_name }}: {{ replyTo.content?.substring(0, 50) }}</span>
      </div>
      <el-button :icon="Close" circle size="small" @click="cancelReply" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search,
  Setting,
  Loading,
  ChatLineSquare,
  Picture,
  Folder,
  Delete,
  CopyDocument,
  Close,
  Document,
  Download,
  InfoFilled,
  Remove,
  ArrowRight,
  ShoppingCart,
  Tickets,
  List,
  User,
  ChatDotRound,
  View,
  Link,
  Grid,
  MagicStick,
} from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { searchMessages, uploadChatFile } from '@/api/chat'
import type { Message, Conversation, ConversationMember } from '@/types/chat'

const props = defineProps<{
  conversation: Conversation
}>()

const emit = defineEmits<{
  sendMessage: [content: string, type: string, replyToId?: string, mentions?: string[]]
  loadMore: []
  deleteMessage: [messageId: string]
  recallMessage: [messageId: string]
  markRead: [messageId: string]
}>()

const router = useRouter()
const chatStore = useChatStore()
const authStore = useAuthStore()

const messageListRef = ref<HTMLElement>()
const inputRef = ref()
const inputText = ref('')
const showSearch = ref(false)
const showGroupSetting = ref(false)
const searchKeyword = ref('')
const searchResults = ref<any[]>([])
const groupName = ref('')
const replyTo = ref<Message | null>(null)
const showShareCard = ref(false)
const shareCardType = ref<string>('')
const shareCardKeyword = ref('')
const shareCardResults = ref<any[]>([])
const shareCardSearched = ref(false)
const recentSharedCards = ref<any[]>([])
const myRecentObjects = ref<any[]>([])
const shareRecommendations = ref<any[]>([])
const isLoadingRecommendations = ref(false)
const isLoadingRecent = ref(false)

// 批量分享
const showBatchShare = ref(false)
const batchShareType = ref<string>('order')
const batchShareKeyword = ref('')
const batchShareItems = ref<any[]>([])
const batchSelected = ref<Map<string, any>>(new Map())
const batchSelectedIds = ref<Set<string>>(new Set())
const batchShareLoading = ref(false)

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  message: null as Message | null,
})

const currentUserId = computed(() => authStore.user?.id)
const messages = computed(() => chatStore.getMessages(props.conversation.id))
const conversationMembers = computed(() => {
  const detail = chatStore.conversations.find(c => c.id === props.conversation.id)
  return (detail as any)?.members || []
})

const typingUsers = computed(() => {
  return chatStore.getTypingUsers(props.conversation.id)
})

const shareCardTypeLabel = computed(() => {
  const labels: Record<string, string> = {
    order: '订单',
    quote: '报价单',
    task: '任务',
    customer: '客户',
  }
  return labels[shareCardType.value] || '业务对象'
})

// 表情分组
const emojiGroups = [
  {
    name: '常用',
    emojis: ['😊', '😂', '🤣', '❤️', '👍', '🎉', '🔥', '✨', '😍', '🤔', '😅', '😢', '😡', '🙏', '💪', '👏'],
  },
  {
    name: '表情',
    emojis: ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🫡', '🤐', '🤨', '😐', '😑', '😶', '🫥', '😏', '😒', '🙄', '😬', '🤥', '🫨', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '🥸', '😎', '🤓', '🧐'],
  },
  {
    name: '手势',
    emojis: ['👋', '🤚', '🖐️', '✋', '🖖', '🫱', '🫲', '🫳', '🫴', '👌', '🤌', '🤏', '✌️', '🤞', '🫰', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '🫵', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '🫶', '👐', '🤲', '🤝', '🙏'],
  },
  {
    name: '物品',
    emojis: ['💼', '📁', '📂', '📊', '📈', '📉', '📋', '📌', '📎', '🔒', '🔓', '🔑', '🔨', '🔧', '🔩', '💡', '📱', '💻', '🖥️', '🖨️', '📷', '📸', '📹', '🎬', '📺', '📻', '🎵', '🎶', '🔔', '📢'],
  },
]

// 获取卡片图标
function getCardIcon(cardType?: string) {
  const icons: Record<string, any> = {
    order: ShoppingCart,
    quote: Tickets,
    task: List,
    customer: User,
  }
  return (cardType && icons[cardType]) || Document
}

// 状态标签类型映射（Element Plus tag type）
function getStatusTagType(status: string, cardType?: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  // 订单状态
  if (cardType === 'order') {
    const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
      pending_confirm: 'warning',
      confirmed: '',
      in_production: '',
      production_complete: 'success',
      installing: '',
      completed: 'success',
      cancelled: 'danger',
    }
    return map[status] || 'info'
  }
  // 报价单状态
  if (cardType === 'quote') {
    const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
      draft: 'info',
      submitted: '',
      approved: 'success',
      rejected: 'danger',
      expired: 'info',
    }
    return map[status] || 'info'
  }
  // 任务状态
  if (cardType === 'task') {
    const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
      pending: 'warning',
      in_progress: '',
      completed: 'success',
      failed: 'danger',
      rework: 'warning',
    }
    return map[status] || 'info'
  }
  return 'info'
}

// 状态中文标签
function getStatusLabel(status: string, cardType?: string): string {
  const orderLabels: Record<string, string> = {
    pending_confirm: '待确认',
    confirmed: '已确认',
    in_production: '生产中',
    production_complete: '生产完成',
    installing: '安装中',
    completed: '已完成',
    cancelled: '已取消',
  }
  const quoteLabels: Record<string, string> = {
    draft: '草稿',
    submitted: '已提交',
    approved: '已通过',
    rejected: '已拒绝',
    expired: '已过期',
  }
  const taskLabels: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    failed: '失败',
    rework: '返工',
  }

  if (cardType === 'order') return orderLabels[status] || status
  if (cardType === 'quote') return quoteLabels[status] || status
  if (cardType === 'task') return taskLabels[status] || status
  return status
}

// 格式化金额
function formatAmount(amount: number): string {
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 格式化文本内容（支持@高亮和链接）
function formatTextContent(content: string) {
  if (!content) return ''
  // @高亮
  let formatted = content.replace(/@(\S+)/g, '<span class="mention-highlight">@$1</span>')
  // 链接
  formatted = formatted.replace(
    /(https?:\/\/[^\s]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>'
  )
  return formatted
}

// 格式化文件大小
function formatFileSize(size?: number) {
  if (!size) return ''
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

// 判断是否显示时间
function shouldShowTime(current: Message, prev?: Message) {
  if (!prev) return true
  const diff = new Date(current.created_at).getTime() - new Date(prev.created_at).getTime()
  return diff > 5 * 60 * 1000 // 5分钟
}

// 格式化消息时间
function formatMessageTime(time: string) {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')

  if (diff < 86400000 && date.getDate() === now.getDate()) {
    return `${hours}:${minutes}`
  }

  if (diff < 172800000) {
    return `昨天 ${hours}:${minutes}`
  }

  return `${date.getMonth() + 1}/${date.getDate()} ${hours}:${minutes}`
}

// 判断是否可以撤回
function canRecall(message: Message | null) {
  if (!message || message.sender_id !== currentUserId.value) return false
  if (message.type === 'recalled') return false
  const diff = Date.now() - new Date(message.created_at).getTime()
  return diff < 2 * 60 * 1000 // 2分钟
}

// 插入表情
function insertEmoji(emoji: string) {
  inputText.value += emoji
  inputRef.value?.focus()
}

// 插入@提及
function insertMention(member: ConversationMember) {
  inputText.value += `@${member.user_name} `
  inputRef.value?.focus()
}

// 导航到业务卡片
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isValidUUID(id?: string): boolean {
  return !!id && UUID_RE.test(id)
}

function navigateToCard(data?: Record<string, any>) {
  if (!data?.card_type || !data?.card_id) return
  if (!isValidUUID(data.card_id)) {
    ElMessage.warning('卡片ID无效，无法跳转')
    return
  }

  let route = ''

  if (data.card_type === 'order') {
    route = `/orders/${data.card_id}`
  } else if (data.card_type === 'quote') {
    route = `/quotes/${data.card_id}/edit`
  } else if (data.card_type === 'task') {
    // 根据任务类型选择不同路由
    const taskRoutes: Record<string, string> = {
      design: `/design-tasks/${data.card_id}`,
      production: `/production-tasks/${data.card_id}`,
      installation: `/installation-tasks/${data.card_id}`,
    }
    route = taskRoutes[data.task_type] || `/tasks/${data.card_id}`
  } else if (data.card_type === 'customer') {
    route = `/customers/${data.card_id}`
  }

  if (route) {
    router.push(route)
  }
}

// 复制卡片链接
function copyCardLink(data?: Record<string, any>) {
  if (!data?.card_type || !data?.card_id) return
  if (!isValidUUID(data.card_id)) {
    ElMessage.warning('卡片ID无效')
    return
  }

  let route = ''
  if (data.card_type === 'order') {
    route = `/orders/${data.card_id}`
  } else if (data.card_type === 'quote') {
    route = `/quotes/${data.card_id}/edit`
  } else if (data.card_type === 'task') {
    const taskRoutes: Record<string, string> = {
      design: `/design-tasks/${data.card_id}`,
      production: `/production-tasks/${data.card_id}`,
      installation: `/installation-tasks/${data.card_id}`,
    }
    route = taskRoutes[data.task_type] || `/tasks/${data.card_id}`
  } else if (data.card_type === 'customer') {
    route = `/customers/${data.card_id}`
  }

  if (route) {
    const url = `${window.location.origin}${route}`
    navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  }
}

// 下载文件
function downloadFile(msg: Message) {
  const url = msg.extra_data?.url || msg.content
  if (url) {
    window.open(url, '_blank')
  }
}

// 发送文本消息
function sendTextMessage() {
  const content = inputText.value.trim()
  if (!content) return

  const mentions: string[] = []
  const mentionRegex = /@(\S+)/g
  let match
  while ((match = mentionRegex.exec(content)) !== null) {
    mentions.push(match[1])
  }

  emit('sendMessage', content, 'text', replyTo.value?.id, mentions.length > 0 ? mentions : undefined)
  inputText.value = ''
  replyTo.value = null
}

// 处理键盘事件
function handleKeydown(e: Event) {
  const ke = e as KeyboardEvent
  if (ke.key === 'Enter' && !ke.shiftKey) {
    ke.preventDefault()
    sendTextMessage()
  }
}

// 处理图片上传
async function handleBeforeUpload(file: File) {
  if (!props.conversation) return false

  try {
    const result = await uploadChatFile(props.conversation.id, file)
    emit('sendMessage', result.url, 'image')
    ElMessage.success('图片发送成功')
  } catch (error) {
    ElMessage.error('图片上传失败')
  }
  return false
}

// 处理文件上传
async function handleBeforeFileUpload(file: File) {
  if (!props.conversation) return false

  try {
    const result = await uploadChatFile(props.conversation.id, file)
    emit('sendMessage', JSON.stringify({ url: result.url, name: file.name, size: file.size }), 'file')
    ElMessage.success('文件发送成功')
  } catch (error) {
    ElMessage.error('文件上传失败')
  }
  return false
}

// 处理拖拽上传
async function handleDrop(e: DragEvent) {
  const files = e.dataTransfer?.files
  if (!files || files.length === 0 || !props.conversation) return

  for (const file of Array.from(files)) {
    try {
      const result = await uploadChatFile(props.conversation.id, file)
      if (file.type.startsWith('image/')) {
        emit('sendMessage', result.url, 'image')
      } else {
        emit('sendMessage', JSON.stringify({ url: result.url, name: file.name, size: file.size }), 'file')
      }
    } catch (error) {
      ElMessage.error(`${file.name} 上传失败`)
    }
  }
}

// 显示右键菜单
function showContextMenu(e: MouseEvent, message: Message) {
  contextMenu.value = {
    visible: true,
    x: e.clientX,
    y: e.clientY,
    message,
  }

  const closeMenu = () => {
    contextMenu.value.visible = false
    document.removeEventListener('click', closeMenu)
  }
  setTimeout(() => document.addEventListener('click', closeMenu), 0)
}

// 回复消息
function handleReply() {
  if (contextMenu.value.message) {
    replyTo.value = contextMenu.value.message
    inputRef.value?.focus()
  }
  contextMenu.value.visible = false
}

// 取消回复
function cancelReply() {
  replyTo.value = null
}

// 撤回消息
function handleRecall() {
  if (contextMenu.value.message) {
    emit('recallMessage', contextMenu.value.message.id)
  }
  contextMenu.value.visible = false
}

// 删除消息
function handleDelete() {
  if (contextMenu.value.message) {
    emit('deleteMessage', contextMenu.value.message.id)
  }
  contextMenu.value.visible = false
}

// 复制消息
function handleCopy() {
  if (contextMenu.value.message?.content) {
    navigator.clipboard.writeText(contextMenu.value.message.content)
    ElMessage.success('已复制')
  }
  contextMenu.value.visible = false
}

// 滚动到指定消息
function scrollToMessage(messageId?: string) {
  if (!messageId) return
  const el = document.getElementById(`msg-${messageId}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('highlight')
    setTimeout(() => el.classList.remove('highlight'), 2000)
  }
}

// 显示分享卡片对话框
async function showShareDialog(type: string) {
  shareCardType.value = type
  shareCardKeyword.value = ''
  shareCardResults.value = []
  shareCardSearched.value = false
  recentSharedCards.value = []
  myRecentObjects.value = []
  showShareCard.value = true

  // 加载最近数据 + 智能推荐
  isLoadingRecent.value = true
  isLoadingRecommendations.value = true
  const { getRecentSharedCards: getShared, getMyRecentObjects: getMine, getRecommendations: getRecs } = await import('@/api/chat')

  // 并行加载最近数据
  try {
    const [shared, recent] = await Promise.all([
      getShared(type as any, 5).catch(() => []),
      getMine(type as any, 5).catch(() => []),
    ])
    recentSharedCards.value = shared || []
    myRecentObjects.value = recent || []
  } catch {
    // 忽略错误，不影响搜索功能
  } finally {
    isLoadingRecent.value = false
  }

  // 异步加载推荐（不阻塞主对话框）
  if (props.conversation) {
    try {
      const recs = await getRecs(props.conversation.id, 8)
      shareRecommendations.value = (recs || []).filter(r => r.type === type)
    } catch {
      shareRecommendations.value = []
    } finally {
      isLoadingRecommendations.value = false
    }
  } else {
    isLoadingRecommendations.value = false
  }
}

// 搜索业务对象
async function searchBusinessObjects() {
  if (!shareCardKeyword.value.trim()) return

  shareCardSearched.value = false
  try {
    const { searchBusinessObjects: searchApi } = await import('@/api/chat')
    const results = await searchApi(shareCardType.value as any, shareCardKeyword.value)
    shareCardResults.value = results || []
    shareCardSearched.value = true
  } catch (error) {
    ElMessage.error('搜索失败')
  }
}

// 处理分享卡片
async function handleShareCard(item: any) {
  if (!props.conversation) return
  if (!isValidUUID(item.id)) {
    ElMessage.warning('该记录ID无效，无法分享')
    return
  }

  try {
    const { shareBusinessCard } = await import('@/api/chat')
    const msg = await shareBusinessCard(props.conversation.id, shareCardType.value as any, item.id)
    // 广播排除了发送者，手动把消息加入本地列表
    if (msg) {
      chatStore.handleNewMessage(msg, props.conversation.id)
    }
    showShareCard.value = false
    ElMessage.success('分享成功')
  } catch (error) {
    ElMessage.error('分享失败')
  }
}

// 批量分享
async function openBatchShare() {
  showBatchShare.value = true
  batchShareType.value = 'order'
  batchShareKeyword.value = ''
  batchSelected.value.clear()
  batchSelectedIds.value.clear()
  await loadBatchItems()
}

async function loadBatchItems() {
  batchShareItems.value = []
  batchShareKeyword.value = ''
  try {
    const { searchBusinessObjects } = await import('@/api/chat')
    const results = await searchBusinessObjects(batchShareType.value as any, '')
    batchShareItems.value = results || []
  } catch {
    batchShareItems.value = []
  }
}

async function searchBatchItems() {
  if (!batchShareKeyword.value.trim()) {
    await loadBatchItems()
    return
  }
  try {
    const { searchBusinessObjects } = await import('@/api/chat')
    const results = await searchBusinessObjects(batchShareType.value as any, batchShareKeyword.value)
    batchShareItems.value = results || []
  } catch {
    batchShareItems.value = []
  }
}

function toggleBatchItem(item: any) {
  if (batchSelectedIds.value.has(item.id)) {
    batchSelected.value.delete(item.id)
    batchSelectedIds.value.delete(item.id)
  } else {
    batchSelected.value.set(item.id, item)
    batchSelectedIds.value.add(item.id)
  }
}

async function submitBatchShare() {
  if (!props.conversation || batchSelected.value.size === 0) return
  batchShareLoading.value = true
  try {
    const { batchShareCards } = await import('@/api/chat')
    const items = Array.from(batchSelected.value.values()).map(item => ({
      card_type: batchShareType.value,
      card_id: item.id,
    }))
    const msg = await batchShareCards(props.conversation.id, items)
    // 广播排除了发送者，手动把消息加入本地列表
    if (msg) {
      chatStore.handleNewMessage(msg, props.conversation.id)
    }
    showBatchShare.value = false
    ElMessage.success(`已分享 ${items.length} 个项目`)
  } catch {
    ElMessage.error('批量分享失败')
  } finally {
    batchShareLoading.value = false
  }
}

// 搜索消息
async function handleSearch() {
  if (!searchKeyword.value.trim()) return

  try {
    const result = await searchMessages({
      keyword: searchKeyword.value,
      conversation_id: props.conversation.id,
    })
    searchResults.value = result.items || []
  } catch (error) {
    ElMessage.error('搜索失败')
  }
}

// 处理滚动加载
function handleScroll() {
  if (!messageListRef.value) return
  if (messageListRef.value.scrollTop < 50) {
    emit('loadMore')
  }
}

// 滚动到底部
function scrollToBottom(smooth = true) {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTo({
        top: messageListRef.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      })
    }
  })
}

// 监听消息变化，自动滚动
watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
  }
)

// 监听会话变化
watch(
  () => props.conversation.id,
  () => {
    groupName.value = props.conversation.name || ''
    replyTo.value = null
  },
  { immediate: true }
)

onMounted(() => {
  scrollToBottom(false)
})

defineExpose({
  scrollToBottom,
})
</script>

<style scoped lang="scss">
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;

  .header-info {
    display: flex;
    align-items: center;
    gap: 8px;

    h4 {
      margin: 0;
      font-size: 15px;
    }

    .member-count {
      font-size: 12px;
      color: #909399;
    }
  }

  .header-actions {
    display: flex;
    gap: 4px;
  }
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.loading-tip {
  text-align: center;
  padding: 16px;
  color: #909399;
  font-size: 13px;
}

.time-divider {
  text-align: center;
  margin: 16px 0;

  span {
    display: inline-block;
    padding: 4px 12px;
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
    font-size: 12px;
    color: #909399;
  }
}

.message-item {
  display: flex;
  margin-bottom: 16px;

  &.is-mine {
    flex-direction: row-reverse;

    .msg-content {
      align-items: flex-end;
    }

    .msg-sender {
      text-align: right;
    }

    .msg-bubble {
      background: #95ec69;
    }

    .msg-status {
      text-align: right;
    }
  }

  &.is-recalled {
    opacity: 0.6;
  }
}

.msg-avatar {
  flex-shrink: 0;
}

.msg-content {
  display: flex;
  flex-direction: column;
  max-width: 70%;
  margin: 0 8px;
}

.msg-sender {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.reply-quote {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
  cursor: pointer;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  .reply-sender {
    color: #409eff;
    margin-right: 4px;
  }

  .reply-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }
}

.msg-bubble {
  padding: 10px 14px;
  background: #fff;
  border-radius: 8px;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.msg-text {
  font-size: 14px;
  line-height: 1.6;

  :deep(.mention-highlight) {
    color: #409eff;
    font-weight: 500;
  }

  :deep(a) {
    color: #409eff;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}

.msg-image {
  max-width: 300px;
  max-height: 300px;
  overflow: hidden;
  border-radius: 4px;
}

.msg-file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
  min-width: 200px;

  &:hover {
    background: rgba(0, 0, 0, 0.03);
  }

  .file-info {
    flex: 1;

    .file-name {
      font-size: 14px;
      margin-bottom: 2px;
    }

    .file-size {
      font-size: 12px;
      color: #909399;
    }
  }

  .download-icon {
    color: #909399;
  }
}

.msg-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
  min-width: 200px;
  border: 1px solid #e4e7ed;

  &:hover {
    background: #f5f7fa;
  }

  .card-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ecf5ff;
    border-radius: 8px;
    color: #409eff;
  }

  .card-info {
    flex: 1;
    min-width: 0;

    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 2px;

      .card-title {
        font-size: 14px;
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .card-status-tag {
        flex-shrink: 0;
      }
    }

    .card-subtitle {
      font-size: 12px;
      color: #909399;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-amount {
      font-size: 13px;
      color: #e6a23c;
      font-weight: 500;
      margin-top: 2px;
    }
  }

  .card-arrow {
    color: #909399;
  }

  .card-actions {
    position: absolute;
    bottom: -4px;
    right: 8px;
    opacity: 0;
    transform: translateY(4px);
    transition: all 0.2s ease;
    z-index: 10;

    .el-button-group {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      border-radius: 4px;
      overflow: hidden;

      .el-button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 5px 10px;
        font-size: 12px;

        .el-icon {
          font-size: 12px;
        }
      }
    }
  }

  &:hover .card-actions {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-system {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
  background: transparent;
  box-shadow: none;
  padding: 4px 0;
}

.msg-recalled {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
  background: transparent;
  box-shadow: none;
}

.msg-status {
  margin-top: 2px;

  .read-status {
    font-size: 11px;
    color: #67c23a;

    &.unread {
      color: #909399;
    }
  }
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;

  .typing-dot {
    width: 6px;
    height: 6px;
    background: #909399;
    border-radius: 50%;
    animation: typing 1.4s infinite;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }

  .typing-text {
    font-size: 12px;
    color: #909399;
    margin-left: 4px;
  }
}

@keyframes typing {
  0%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

.input-area {
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.input-toolbar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.input-box {
  display: flex;
  align-items: flex-end;
  padding: 8px 12px;
  gap: 8px;

  .el-textarea {
    flex: 1;
  }

  .send-btn {
    height: 36px;
  }
}

.context-menu {
  position: fixed;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 3000;
  overflow: hidden;

  .menu-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    cursor: pointer;
    font-size: 13px;

    &:hover {
      background: #f5f7fa;
    }

    &.danger {
      color: #f56c6c;
    }
  }
}

.emoji-picker {
  max-height: 300px;
  overflow-y: auto;
}

.emoji-group {
  margin-bottom: 12px;

  .emoji-group-name {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
  }

  .emoji-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .emoji-item {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border-radius: 4px;
    font-size: 20px;

    &:hover {
      background: #f5f7fa;
    }
  }
}

.mention-list {
  max-height: 250px;

  .mention-title {
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 8px;
  }

  .mention-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    cursor: pointer;
    border-radius: 4px;

    &:hover {
      background: #f5f7fa;
    }

    .online-dot {
      width: 6px;
      height: 6px;
      background: #67c23a;
      border-radius: 50%;
      margin-left: auto;
    }
  }
}

.search-results {
  margin-top: 16px;

  .search-result-item {
    padding: 12px;
    border-bottom: 1px solid #f0f0f0;

    &:hover {
      background: #f5f7fa;
    }

    .result-sender {
      font-size: 12px;
      color: #909399;
      margin-bottom: 4px;
    }

    .result-content {
      font-size: 14px;
    }

    .result-time {
      font-size: 12px;
      color: #909399;
      margin-top: 4px;
    }
  }
}

.group-setting {
  .member-list-title {
    font-size: 14px;
    font-weight: 500;
    margin: 16px 0 12px;
  }

  .member-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;

    .member-info {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 8px;

      .member-name {
        font-size: 14px;
      }
    }

    .online-status {
      font-size: 12px;

      &.online {
        color: #67c23a;
      }
    }
  }
}

.reply-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;

  .reply-info {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #606266;
  }
}

.highlight {
  animation: highlight-bg 2s ease-out;
}

@keyframes highlight-bg {
  0% {
    background: #fef08a;
  }
  100% {
    background: transparent;
  }
}

.share-card-menu {
  .share-card-title {
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 8px;
    color: #606266;
  }

  .share-card-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    cursor: pointer;
    border-radius: 4px;
    font-size: 13px;

    &:hover {
      background: #f5f7fa;
    }

    .el-icon {
      color: #409eff;
    }
  }
}

.share-card-dialog {
  .share-results {
    margin-top: 16px;
  }

  .share-recent-sections {
    margin-top: 16px;
  }

  .share-section {
    margin-bottom: 16px;
  }

  .share-recommendations {
    background: linear-gradient(135deg, #f0f9ff 0%, #e8f4fd 100%);
    border-radius: 8px;
    padding-bottom: 4px;

    .share-section-title {
      color: #409eff;
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }

  .share-section-title {
    font-size: 12px;
    color: #909399;
    padding: 8px 12px 4px;
    font-weight: 500;
  }

  .share-result-item {
    padding: 12px;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;

    &:hover {
      background: #f5f7fa;
    }

    .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .result-title {
        font-size: 14px;
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .result-subtitle {
      font-size: 12px;
      color: #909399;
    }

    .result-amount {
      font-size: 13px;
      color: #e6a23c;
      font-weight: 500;
      margin-top: 2px;
    }
  }

  .share-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 32px 0;
    color: #909399;
    font-size: 14px;
  }
}

.share-card-divider {
  height: 1px;
  background: #e4e7ed;
  margin: 8px 0;
}

.batch-share-item {
  color: #409eff;
  font-weight: 500;
}

.batch-share-dialog {
  .batch-type-tabs {
    margin-bottom: 12px;
  }

  .batch-search-input {
    margin-bottom: 12px;
  }

  .batch-item-list {
    border: 1px solid #e4e7ed;
    border-radius: 4px;
  }

  .batch-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
    transition: background 0.2s;

    &:hover {
      background: #f5f7fa;
    }

    &.selected {
      background: #ecf5ff;
    }

    .batch-item-info {
      flex: 1;
      min-width: 0;

      .batch-item-title {
        font-size: 14px;
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .batch-item-subtitle {
        font-size: 12px;
        color: #909399;
        margin-top: 2px;
      }
    }
  }

  .batch-selected-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    margin-top: 8px;
    font-size: 13px;
    color: #606266;
  }
}

.msg-batch-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  max-width: 360px;

  .batch-card-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid #f0f0f0;
  }

  .batch-card-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .batch-card-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #f5f7fa;
    }

    .batch-card-item-title {
      flex: 1;
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .batch-card-item-arrow {
      color: #c0c4cc;
      font-size: 12px;
    }
  }
}
</style>
