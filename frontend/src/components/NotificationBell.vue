<template>
  <el-popover
    placement="bottom-end"
    :width="360"
    trigger="click"
    @show="handleShow"
  >
    <template #reference>
      <el-badge :value="notificationStore.unreadCount" :hidden="notificationStore.unreadCount === 0" :max="99">
        <el-button text class="bell-btn">
          <el-icon :size="20"><Bell /></el-icon>
        </el-button>
      </el-badge>
    </template>

    <div class="notification-dropdown">
      <div class="dropdown-header">
        <span class="dropdown-title">消息通知</span>
        <el-button text size="small" @click="handleMarkAllRead" :disabled="notificationStore.unreadCount === 0">
          全部已读
        </el-button>
      </div>

      <div class="notification-list" v-loading="loading">
        <div v-if="notificationStore.notifications.length === 0" class="empty-hint">
          暂无通知
        </div>
        <div
          v-for="item in notificationStore.notifications"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.is_read }"
          @click="handleClick(item)"
        >
          <div class="item-icon">
            <el-icon :size="18" :color="getIconColor(item.type)">
              <component :is="getIcon(item.type)" />
            </el-icon>
          </div>
          <div class="item-content">
            <div class="item-title">{{ item.title }}</div>
            <div class="item-text">{{ item.content.slice(0, 60) }}{{ item.content.length > 60 ? '...' : '' }}</div>
            <div class="item-time">{{ formatTime(item.created_at) }}</div>
          </div>
          <div v-if="!item.is_read" class="unread-dot"></div>
        </div>
      </div>

      <div class="dropdown-footer">
        <el-button text size="small" @click="goToNotifications">查看全部</el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import type { NotificationResponse } from '@/types/api'
import {
  Bell,
  Document,
  List,
  Money,
  Warning,
  ChatDotRound,
  Setting,
} from '@element-plus/icons-vue'

const router = useRouter()
const notificationStore = useNotificationStore()
const loading = ref(false)

const iconMap: Record<string, ReturnType<typeof markRaw>> = {
  order_status: markRaw(Document),
  task_assigned: markRaw(List),
  quote_status: markRaw(Document),
  payment_received: markRaw(Money),
  inventory_alert: markRaw(Warning),
  user_message: markRaw(ChatDotRound),
  system_message: markRaw(Setting),
}

const colorMap: Record<string, string> = {
  order_status: '#409eff',
  task_assigned: '#67c23a',
  quote_status: '#e6a23c',
  payment_received: '#f56c6c',
  inventory_alert: '#f56c6c',
  user_message: '#409eff',
  system_message: '#909399',
}

function getIcon(type: string) {
  return iconMap[type] || markRaw(Setting)
}

function getIconColor(type: string) {
  return colorMap[type] || '#909399'
}

function formatTime(ts: string): string {
  const date = new Date(ts)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return ts.replace('T', ' ').slice(0, 16)
}

async function handleShow() {
  loading.value = true
  await notificationStore.fetchRecent(10)
  loading.value = false
}

async function handleClick(item: NotificationResponse) {
  if (!item.is_read) {
    await notificationStore.markRead(item.id)
  }
  if (item.link) {
    router.push(item.link)
  }
}

async function handleMarkAllRead() {
  await notificationStore.markAllRead()
}

function goToNotifications() {
  router.push('/notifications')
}
</script>

<style scoped>
.bell-btn {
  padding: 4px;
  color: var(--ad-text-secondary);
}

.bell-btn:hover {
  color: var(--ad-text);
}

.notification-dropdown {
  margin: -12px;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ad-border);
}

.dropdown-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ad-text);
}

.notification-list {
  max-height: 400px;
  overflow-y: auto;
}

.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: var(--ad-text-secondary);
  font-size: 13px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}

.notification-item:hover {
  background: var(--ad-card);
}

.notification-item.unread {
  background: rgba(64, 158, 255, 0.05);
}

.item-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--ad-darker);
  display: flex;
  align-items: center;
  justify-content: center;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-text {
  font-size: 12px;
  color: var(--ad-text-secondary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-time {
  font-size: 11px;
  color: var(--ad-text-secondary);
  opacity: 0.7;
}

.unread-dot {
  position: absolute;
  right: 16px;
  top: 18px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
}

.dropdown-footer {
  text-align: center;
  padding: 8px 16px;
  border-top: 1px solid var(--ad-border);
}
</style>
