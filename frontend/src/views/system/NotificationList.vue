<template>
  <div class="page">
    <div class="page-header">
      <h2 style="color: var(--ad-text)">消息中心</h2>
      <el-button type="primary" @click="handleMarkAllRead" :disabled="notificationStore.unreadCount === 0">
        全部已读
      </el-button>
    </div>

    <!-- Filters -->
    <div class="filters">
      <el-select v-model="typeFilter" placeholder="通知类型" clearable style="width: 160px" @change="handleFilterChange">
        <el-option label="全部类型" value="" />
        <el-option label="订单状态" value="order_status" />
        <el-option label="任务分配" value="task_assigned" />
        <el-option label="报价状态" value="quote_status" />
        <el-option label="收款通知" value="payment_received" />
        <el-option label="库存预警" value="inventory_alert" />
        <el-option label="用户消息" value="user_message" />
        <el-option label="系统消息" value="system_message" />
      </el-select>
      <el-select v-model="readFilter" placeholder="已读状态" clearable style="width: 140px" @change="handleFilterChange">
        <el-option label="全部" :value="undefined" />
        <el-option label="未读" :value="false" />
        <el-option label="已读" :value="true" />
      </el-select>
    </div>

    <!-- Notification List -->
    <el-card shadow="never" v-loading="notificationStore.loading">
      <div v-if="notificationStore.notifications.length === 0" class="empty-state">
        <el-empty description="暂无通知" />
      </div>
      <div
        v-for="item in notificationStore.notifications"
        :key="item.id"
        class="notification-row"
        :class="{ unread: !item.is_read }"
        @click="handleClick(item)"
      >
        <div class="row-icon">
          <el-icon :size="20" :color="getIconColor(item.type)">
            <component :is="getIcon(item.type)" />
          </el-icon>
        </div>
        <div class="row-content">
          <div class="row-title">{{ item.title }}</div>
          <div class="row-text">{{ item.content }}</div>
          <div class="row-meta">
            <span v-if="item.sender_name" class="sender">{{ item.sender_name }}</span>
            <span class="time">{{ formatTime(item.created_at) }}</span>
          </div>
        </div>
        <div class="row-actions">
          <el-tag v-if="!item.is_read" type="danger" size="small">未读</el-tag>
          <el-button text size="small" @click.stop="handleDelete(item.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Pagination -->
    <div class="pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import type { NotificationResponse } from '@/types/api'
import {
  Document,
  List,
  Money,
  Warning,
  ChatDotRound,
  Setting,
  Delete,
} from '@element-plus/icons-vue'

const router = useRouter()
const notificationStore = useNotificationStore()

const typeFilter = ref('')
const readFilter = ref<boolean | undefined>(undefined)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

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
  return ts.replace('T', ' ').slice(0, 19)
}

async function fetchList() {
  const data = await notificationStore.fetchNotifications({
    type: typeFilter.value || undefined,
    is_read: readFilter.value,
    page: currentPage.value,
    page_size: pageSize.value,
  })
  total.value = data.total
}

function handleFilterChange() {
  currentPage.value = 1
  fetchList()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchList()
}

async function handleClick(item: NotificationResponse) {
  if (!item.is_read) {
    await notificationStore.markRead(item.id)
  }
  if (item.link) {
    router.push(item.link)
  }
}

async function handleDelete(id: string) {
  await notificationStore.remove(id)
  total.value = Math.max(0, total.value - 1)
}

async function handleMarkAllRead() {
  await notificationStore.markAllRead()
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.notification-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px;
  border-bottom: 1px solid var(--ad-border);
  cursor: pointer;
  transition: background 0.2s;
}

.notification-row:last-child {
  border-bottom: none;
}

.notification-row:hover {
  background: var(--ad-card);
}

.notification-row.unread {
  background: rgba(64, 158, 255, 0.04);
}

.row-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--ad-darker);
  display: flex;
  align-items: center;
  justify-content: center;
}

.row-content {
  flex: 1;
  min-width: 0;
}

.row-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  margin-bottom: 4px;
}

.row-text {
  font-size: 13px;
  color: var(--ad-text-secondary);
  margin-bottom: 6px;
  line-height: 1.5;
}

.row-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--ad-text-secondary);
  opacity: 0.7;
}

.sender {
  color: var(--ad-text);
  font-weight: 500;
}

.row-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-state {
  padding: 60px 0;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
