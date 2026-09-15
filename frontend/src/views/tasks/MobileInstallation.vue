<template>
  <div class="mobile-page">
    <!-- Header -->
    <div class="mobile-header">
      <div class="header-top">
        <span class="header-title">安装任务</span>
        <span class="header-user">{{ authStore.user?.real_name || '' }}</span>
      </div>
      <div class="header-subtitle">
        <span>{{ statusCounts.all }} 个任务</span>
        <span v-if="refreshing" class="refresh-hint">刷新中…</span>
      </div>
    </div>

    <!-- Status filter tabs -->
    <div class="status-tabs" ref="tabsRef">
      <div
        v-for="tab in statusTabs"
        :key="tab.value"
        class="status-tab"
        :class="{ active: activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        <span class="tab-label">{{ tab.label }}</span>
        <span class="tab-count" :class="tab.value">{{ statusCounts[tab.value] || 0 }}</span>
      </div>
    </div>

    <!-- Pull-to-refresh indicator -->
    <div v-if="pullDistance > 0" class="pull-indicator" :style="{ opacity: Math.min(pullDistance / 60, 1) }">
      {{ pullDistance > 50 ? '松开刷新' : '下拉刷新' }}
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading && allTasks.length === 0" class="skeleton-list">
      <div v-for="n in 5" :key="n" class="skeleton-card">
        <div class="skeleton-line w-40"></div>
        <div class="skeleton-line w-80"></div>
        <div class="skeleton-line w-60"></div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="state-box">
      <div class="state-icon">⚠️</div>
      <div class="state-text">{{ error }}</div>
      <button class="retry-btn" @click="fetchTasks()">重试</button>
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredTasks.length === 0" class="state-box">
      <div class="state-icon">📋</div>
      <div class="state-text">{{ emptyMessage }}</div>
    </div>

    <!-- Task cards -->
    <div
      v-else
      class="task-list"
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
    >
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="task-card"
        @click="openTask(task)"
      >
        <div class="card-top">
          <span class="task-no">{{ task.installation_no }}</span>
          <el-tag :type="statusColor(task.status)" size="small" effect="dark">
            {{ statusLabel(task.status) }}
          </el-tag>
        </div>
        <div class="task-name">{{ task.project_name }}</div>
        <div class="task-meta">
          <span v-if="task.address" class="meta-item">📍 {{ task.address }}</span>
        </div>
        <div class="task-footer">
          <span v-if="task.contact_name" class="meta-item">👤 {{ task.contact_name }}</span>
          <span v-if="task.scheduled_at" class="meta-item">📅 {{ formatDate(task.scheduled_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Task detail bottom sheet -->
    <el-drawer
      v-model="drawerVisible"
      :title="currentTask?.project_name || '任务详情'"
      direction="btt"
      size="92%"
      class="task-drawer"
    >
      <div v-if="currentTask" class="drawer-body">
        <!-- Status badge -->
        <div class="detail-status">
          <el-tag :type="statusColor(currentTask.status)" size="large" effect="dark">
            {{ statusLabel(currentTask.status) }}
          </el-tag>
          <span class="detail-no">{{ currentTask.installation_no }}</span>
        </div>

        <!-- Contact info -->
        <div class="info-section">
          <div class="info-row">
            <span class="info-label">项目地址</span>
            <span class="info-value">{{ currentTask.address || '未填写' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">联系人</span>
            <span class="info-value">{{ currentTask.contact_name || '未填写' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">联系电话</span>
            <a v-if="currentTask.contact_phone" :href="`tel:${currentTask.contact_phone}`" class="info-value phone-link">
              📞 {{ currentTask.contact_phone }}
            </a>
            <span v-else class="info-value">未填写</span>
          </div>
          <div class="info-row">
            <span class="info-label">计划安装日期</span>
            <span class="info-value">{{ formatDate(currentTask.scheduled_at) || '未指定' }}</span>
          </div>
        </div>

        <!-- 订单是资料源头，移动任务只传入任务作为权限上下文。 -->
        <OrderTaskAttachments
          v-if="currentTask"
          :order-id="currentTask.order_id"
          stage="installation"
          :task-id="currentTask.id"
          :refresh-key="currentTask.updated_at"
          :allow-upload="false"
          compact
          capture
        />

        <!-- 每条订单明细独立推进，不能用整张任务的状态覆盖其他明细。 -->
        <div class="item-action-section">
          <div class="item-action-heading">
            <span class="item-action-title">订单明细</span>
            <span class="item-action-hint">点击单条明细的操作按钮</span>
          </div>
          <div v-if="itemOptionsLoading" class="item-options-state">正在加载明细状态…</div>
          <div v-else-if="itemOptionsError" class="item-options-state item-options-error">
            {{ itemOptionsError }}
            <button class="inline-retry-btn" type="button" @click="loadCurrentItemOptions">重试</button>
          </div>
          <div v-else-if="!currentItemOptions.length" class="item-options-state">
            该任务暂无可显示的订单明细
          </div>
          <div v-for="item in currentItemOptions" :key="item.id" class="mobile-item-row">
            <div class="mobile-item-topline">
              <span class="mobile-item-name">{{ item.item_name }}</span>
              <el-tag size="small" :type="item.task_status_view?.tone || 'info'">
                {{ item.task_status_label || (item.is_linked ? '待分配' : '未关联') }}
              </el-tag>
            </div>
            <div class="mobile-item-meta">
              <span v-if="item.material_process">{{ item.material_process }}</span>
              <span v-if="item.assignee_name" class="mobile-item-assignee">执行人：{{ item.assignee_name }}</span>
              <span v-else-if="item.is_linked">执行人：待领取</span>
            </div>
            <div class="mobile-item-actions">
              <button
                v-for="action in itemActions(item)"
                :key="`${item.id}-${action.key}-${action.to_status}`"
                type="button"
                :class="['action-btn', action.kind === 'primary' ? 'primary' : 'secondary']"
                :disabled="!action.allowed || actionBusyItemId === item.id"
                @click="handleItemAction(item, action)"
              >
                {{ action.label }}
              </button>
            </div>
            <div v-if="itemDisabledReason(item)" class="mobile-item-reason">
              {{ itemDisabledReason(item) }}
            </div>
          </div>
        </div>

        <TaskCompletionAttachmentDialog
          v-model="completionDialogVisible"
          task-type="installation"
          :item-label="completionItem ? itemLabel(completionItem) : ''"
          :loading="completionBusy"
          @submit="handleCompletionSubmit"
        />
      </div>
    </el-drawer>

  </div>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  getInstallationTasks,
  getInstallationTask,
  changeInstallationTaskStatus,
  rollbackInstallationTaskItems,
  getTaskOrderItemOptions,
  completeTaskItem,
} from '@/api/tasks'
import OrderTaskAttachments from '@/components/orders/OrderTaskAttachments.vue'
import TaskCompletionAttachmentDialog from '@/components/tasks/TaskCompletionAttachmentDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { InstallationTaskResponse, TaskItemAction, TaskOrderItemOption } from '@/types/api'
import { getErrorMessage } from '@/utils/error'
import { getTaskItemActions } from '@/utils/taskItemActions'

const authStore = useAuthStore()
const route = useRoute()

// --- State ---
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')
const allTasks = ref<InstallationTaskResponse[]>([])
const currentTask = ref<InstallationTaskResponse | null>(null)
const drawerVisible = ref(false)
const activeTab = ref('')
const pullDistance = ref(0)
const currentItemOptions = ref<TaskOrderItemOption[]>([])
const itemOptionsLoading = ref(false)
const itemOptionsError = ref('')
const actionBusyItemId = ref<string | null>(null)
const completionDialogVisible = ref(false)
const completionBusy = ref(false)
const completionItem = ref<TaskOrderItemOption | null>(null)
let touchStartY = 0

// --- Status config ---
interface StatusTab {
  value: string
  label: string
  query: string
}

const statusTabs: StatusTab[] = [
  { value: '', label: '全部', query: 'pending,assigned,in_progress,pending_acceptance' },
  { value: 'pending', label: '待分配', query: 'pending' },
  { value: 'assigned', label: '已分配', query: 'assigned' },
  { value: 'in_progress', label: '安装中', query: 'in_progress' },
  { value: 'pending_acceptance', label: '待验收', query: 'pending_acceptance' },
]

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    pending: '待分配',
    assigned: '已分配',
    in_progress: '安装中',
    pending_acceptance: '待验收',
    completed: '已完成',
  }
  return map[s] || s
}

function statusColor(s: string) {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    pending: 'info',
    in_progress: 'warning',
    pending_acceptance: 'warning',
    completed: 'success',
  }
  return map[s] ?? 'info'
}

const INST_WORKFLOW: Record<string, string[]> = {
  pending: ['assigned', 'in_progress'],
  assigned: ['in_progress', 'pending'],
  in_progress: ['completed', 'pending_acceptance', 'pending'],
  pending_acceptance: ['completed', 'in_progress'],
  completed: [],
  cancelled: [],
}

// --- Computed ---
const statusCounts = computed(() => {
  const counts: Record<string, number> = { all: allTasks.value.length }
  for (const tab of statusTabs) {
    if (tab.value) {
      counts[tab.value] = allTasks.value.filter(t => t.status === tab.value).length
    }
  }
  // Also count completed for completeness even if not shown in tabs
  counts.completed = allTasks.value.filter(t => t.status === 'completed').length
  return counts
})

const filteredTasks = computed(() => {
  if (!activeTab.value) return allTasks.value
  return allTasks.value.filter(t => t.status === activeTab.value)
})

const emptyMessage = computed(() => {
  if (!activeTab.value) return '暂无安装任务'
  const tab = statusTabs.find(t => t.value === activeTab.value)
  return `暂无${tab?.label || ''}任务`
})

// --- Pull-to-refresh ---
function onTouchStart(e: TouchEvent) {
  if (window.scrollY > 0) return
  touchStartY = e.touches[0].clientY
}

function onTouchMove(e: TouchEvent) {
  if (touchStartY === 0) return
  const dy = e.touches[0].clientY - touchStartY
  if (dy > 0) {
    pullDistance.value = Math.min(dy * 0.5, 80)
  }
}

function onTouchEnd() {
  if (pullDistance.value > 50) {
    fetchTasks(true)
  }
  pullDistance.value = 0
  touchStartY = 0
}

// --- Data fetching ---
async function fetchTasks(isRefresh = false) {
  if (isRefresh) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  error.value = ''

  try {
    const query = statusTabs.find(t => t.value === '')!.query
    const data = await getInstallationTasks({ page_size: 100, status: query })
    allTasks.value = data.items || []
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '加载失败，请检查网络后重试')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function openTask(task: InstallationTaskResponse) {
  try {
    currentTask.value = await getInstallationTask(task.id)
    drawerVisible.value = true
    await loadCurrentItemOptions()
  } catch {
    ElMessage.error('加载任务详情失败')
  }
}

async function loadCurrentItemOptions() {
  if (!currentTask.value) return
  itemOptionsLoading.value = true
  itemOptionsError.value = ''
  try {
    currentItemOptions.value = await getTaskOrderItemOptions('installation', currentTask.value.id)
  } catch {
    currentItemOptions.value = []
    itemOptionsError.value = '订单明细加载失败，请重试'
  } finally {
    itemOptionsLoading.value = false
  }
}

function itemActions(item: TaskOrderItemOption) {
  return getTaskItemActions('installation', item, INST_WORKFLOW)
}

function itemDisabledReason(item: TaskOrderItemOption) {
  return itemActions(item).find(action => !action.allowed)?.disabled_reason
    || item.disabled_reason
    || ''
}

function itemStatusLabel(item: TaskOrderItemOption) {
  return item.task_status_label || item.task_status || '未关联'
}

function itemLabel(item: TaskOrderItemOption) {
  return item.material_process
    ? `${item.item_name} · ${item.material_process}`
    : item.item_name
}

// --- Per-item status change ---
async function handleItemAction(item: TaskOrderItemOption, action: TaskItemAction) {
  if (!currentTask.value) return
  if (!action.allowed) {
    ElMessage.info(action.disabled_reason || '当前账号不能操作该明细')
    return
  }
  if (actionBusyItemId.value) return

  let reason = ''
  try {
    if (action.to_status === 'cancelled') {
      ElMessage.info('设计、制作、安装明细不能取消，请使用退回上一阶段操作')
      return
    }
    if (action.operation === 'rollback') {
      const result = await ElMessageBox.prompt(
        `请输入将“${item.item_name}”退回制作的原因（可选）`,
        '退回上一阶段',
        { confirmButtonText: '确认退回', cancelButtonText: '返回', inputPlaceholder: '例如：尺寸需要重新确认' },
      )
      reason = result.value?.trim() || ''
    } else {
      await ElMessageBox.confirm(
        `确认将“${item.item_name}”从“${itemStatusLabel(item)}”变更为“${action.label}”吗？`,
        '变更明细状态',
        { confirmButtonText: '确认操作', cancelButtonText: '取消', type: action.kind === 'primary' ? 'warning' : 'info' },
      )
    }
  } catch {
    return
  }

  if (action.to_status === 'completed') {
    completionItem.value = item
    actionBusyItemId.value = item.id
    completionDialogVisible.value = true
    return
  }

  actionBusyItemId.value = item.id
  try {
    if (action.operation === 'rollback') {
      if (action.target_stage !== 'production') {
        ElMessage.error('回退目标阶段无效，请刷新页面后重试')
        return
      }
      await rollbackInstallationTaskItems(currentTask.value.id, {
        order_item_ids: [item.id],
        reason,
      })
    } else {
      await changeInstallationTaskStatus(currentTask.value.id, {
        to_status: action.to_status,
        reason,
        order_item_ids: [item.id],
      })
    }

    ElMessage.success(action.operation === 'rollback' ? '明细已退回制作' : '状态已更新')
    currentTask.value = await getInstallationTask(currentTask.value.id)
    await Promise.all([loadCurrentItemOptions(), fetchTasks()])
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '状态更新失败'))
  } finally {
    actionBusyItemId.value = null
  }
}

async function handleCompletionSubmit(files: File[], skipped: boolean) {
  if (!currentTask.value || !completionItem.value) return
  completionBusy.value = true
  try {
    await completeTaskItem(
      'installation',
      currentTask.value.id,
      completionItem.value.id,
      files,
      skipped,
    )
    ElMessage.success(skipped ? '安装已完成（已跳过资料上传）' : '安装已完成，现场资料已归档')
    completionDialogVisible.value = false
    currentTask.value = await getInstallationTask(currentTask.value.id)
    await Promise.all([loadCurrentItemOptions(), fetchTasks()])
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '完成明细失败'))
  } finally {
    completionBusy.value = false
    if (!completionDialogVisible.value) {
      completionItem.value = null
      actionBusyItemId.value = null
    }
  }
}

// --- Lifecycle ---
onMounted(() => {
  fetchTasks()
  // Deep linking: auto-open task from query param
  const taskId = route.query.task_id as string
  if (taskId) {
    const check = setInterval(async () => {
      const match = allTasks.value.find(t => t.id === taskId)
      if (match) {
        clearInterval(check)
        await openTask(match)
      }
    }, 300)
    setTimeout(() => clearInterval(check), 10000)
  }
})

// Re-fetch on window focus (user switched back to tab)
watch(() => document.visibilityState, (state) => {
  if (state === 'visible' && allTasks.value.length > 0) {
    fetchTasks(true)
  }
})

watch(completionDialogVisible, value => {
  if (!value && !completionBusy.value) {
    completionItem.value = null
    actionBusyItemId.value = null
  }
})
</script>

<style scoped>
.mobile-page {
  max-width: 480px;
  margin: 0 auto;
  padding: 0;
  min-height: 100vh;
  background: #0f0f1a;
  color: var(--ad-text, #e0e0e0);
  display: flex;
  flex-direction: column;
}

/* Header */
.mobile-header {
  padding: 16px 16px 8px;
  background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
  position: sticky;
  top: 0;
  z-index: 10;
}
.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  font-size: 22px;
  font-weight: 700;
}
.header-user {
  font-size: 14px;
  color: #888;
}
.header-subtitle {
  font-size: 13px;
  color: var(--ad-text-secondary);
  margin-top: 4px;
  display: flex;
  gap: 8px;
}
.refresh-hint {
  color: var(--ad-red, #e63946);
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Status tabs */
.status-tabs {
  display: flex;
  gap: 6px;
  padding: 8px 16px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  position: sticky;
  top: 72px;
  z-index: 10;
  background: #0f0f1a;
}
.status-tabs::-webkit-scrollbar { display: none; }
.status-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  white-space: nowrap;
  font-size: 13px;
  background: #1e1e30;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.status-tab.active {
  background: var(--ad-red, #e63946);
  color: #fff;
}
.tab-label { font-weight: 500; }
.tab-count {
  font-size: 11px;
  background: rgba(255,255,255,0.15);
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}
.status-tab.active .tab-count { background: rgba(255,255,255,0.3); }

/* Pull indicator */
.pull-indicator {
  text-align: center;
  font-size: 12px;
  color: #888;
  padding: 4px 0;
  transition: opacity 0.1s;
}

/* Skeleton */
.skeleton-list { padding: 8px 16px; }
.skeleton-card {
  background: #1e1e30;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 10px;
}
.skeleton-line {
  height: 14px;
  background: #2a2a3e;
  border-radius: 4px;
  margin-bottom: 8px;
  animation: shimmer 1.5s infinite;
}
.skeleton-line:last-child { margin-bottom: 0; }
.w-40 { width: 40%; }
.w-60 { width: 60%; }
.w-80 { width: 80%; }
@keyframes shimmer {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

/* State box */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}
.state-icon { font-size: 40px; margin-bottom: 12px; }
.state-text { font-size: 14px; color: #888; margin-bottom: 16px; }
.retry-btn {
  padding: 10px 32px;
  border-radius: 20px;
  border: 1px solid var(--ad-red, #e63946);
  background: transparent;
  color: var(--ad-red, #e63946);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.retry-btn:active { background: var(--ad-red, #e63946); color: #fff; }

/* Task list */
.task-list { padding: 4px 16px 80px; }

/* Task card */
.task-card {
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.task-card:active {
  border-color: var(--ad-red, #e63946);
  transform: scale(0.98);
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.task-no { font-size: 12px; color: var(--ad-text-secondary); }
.task-name {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 6px;
  line-height: 1.4;
}
.task-meta { margin-bottom: 4px; }
.task-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #888;
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

/* Drawer */
:deep(.el-drawer) {
  background: #1a1a2e !important;
  border-radius: 16px 16px 0 0 !important;
}
:deep(.el-drawer__header) {
  color: var(--ad-text, #e0e0e0);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 0;
  padding: 16px 16px 0;
}
:deep(.el-drawer__body) { padding: 8px 16px 80px; }
.drawer-body { padding-bottom: 40px; }

/* Detail sections */
.detail-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.detail-no { font-size: 13px; color: #888; }

.info-section {
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 16px;
}
.info-row {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px solid #2a2a3e;
}
.info-row:last-child { border-bottom: none; }
.info-label {
  width: 80px;
  flex-shrink: 0;
  color: #888;
  font-size: 13px;
}
.info-value {
  flex: 1;
  font-size: 13px;
  word-break: break-all;
}
.phone-link {
  color: #4fc3f7;
  text-decoration: none;
  font-weight: 500;
}

/* Per-item status actions */
.item-action-section {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  background: #1e1e30;
}
.item-action-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.item-action-title { font-size: 15px; font-weight: 600; }
.item-action-hint { color: #888; font-size: 12px; }
.item-options-state { padding: 16px 4px; color: #888; font-size: 13px; text-align: center; }
.item-options-error { color: #ff8a80; }
.inline-retry-btn {
  margin-left: 8px;
  border: 0;
  background: transparent;
  color: #4fc3f7;
  cursor: pointer;
  font-size: 13px;
}
.mobile-item-row { padding: 12px 0; border-top: 1px solid #2a2a3e; }
.mobile-item-row:first-of-type { border-top: 0; }
.mobile-item-topline { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.mobile-item-name { min-width: 0; font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.mobile-item-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: 6px; color: #888; font-size: 12px; line-height: 1.5; }
.mobile-item-assignee { color: #ff8a80; }
.mobile-item-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.action-btn {
  flex: 1 1 140px;
  min-width: 120px;
  padding: 11px 12px;
  border-radius: 10px;
  border: 1px solid #2a2a3e;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
  background: #1e1e30;
  color: var(--ad-text, #e0e0e0);
}
.action-btn:active { transform: scale(0.98); }
.action-btn:disabled { cursor: not-allowed; opacity: .45; transform: none; }
.action-btn.primary {
  background: var(--ad-red, #e63946);
  border-color: var(--ad-red, #e63946);
  color: #fff;
}
.action-btn.secondary {
  background: #292940;
  border-color: #464661;
  color: #e0e0e0;
}
.action-btn.success {
  background: #2e7d32;
  border-color: #2e7d32;
  color: #fff;
}
.action-btn.warning {
  background: #e65100;
  border-color: #e65100;
  color: #fff;
}
.mobile-item-reason { margin-top: 8px; color: #ffb74d; font-size: 12px; line-height: 1.5; }

/* Safe area for mobile */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .task-list { padding-bottom: calc(80px + env(safe-area-inset-bottom)); }
  .drawer-body { padding-bottom: calc(40px + env(safe-area-inset-bottom)); }
}
</style>
