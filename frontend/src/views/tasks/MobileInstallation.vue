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
          <span v-if="task.scheduled_at" class="meta-item">📅 {{ task.scheduled_at.slice(0, 10) }}</span>
          <span v-if="task.attachments?.length" class="meta-item photo-count">📷 {{ task.attachments.length }}</span>
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
            <span class="info-value">{{ currentTask.scheduled_at?.slice(0, 10) || '未指定' }}</span>
          </div>
        </div>

        <!-- Photo section -->
        <div class="section-title">现场照片</div>
        <div class="photo-actions">
          <button class="photo-btn primary" @click="takePhoto" :disabled="uploadLoading">
            <span>📷</span> 拍照
          </button>
          <button class="photo-btn" @click="uploadPhoto" :disabled="uploadLoading">
            <span>🖼️</span> 相册
          </button>
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            capture="environment"
            style="display:none"
            @change="onFileChange"
          />
        </div>
        <div v-if="uploadLoading" class="upload-progress">上传中…</div>

        <div v-if="currentTask.attachments?.length" class="photo-grid">
          <div
            v-for="att in currentTask.attachments"
            :key="att.id"
            class="photo-item"
            @click="previewImage = `/uploads/${att.file_path}`"
          >
            <img :src="`/uploads/${att.file_path}`" :alt="att.filename" class="photo-img" />
            <button class="photo-delete" @click.stop="deletePhoto(att.id)">×</button>
          </div>
        </div>
        <div v-else class="photo-empty">暂无现场照片，请拍摄或上传</div>

        <!-- Installation notes (for completion/acceptance) -->
        <div class="section-title">安装备注</div>
        <textarea
          v-model="installationNotes"
          class="notes-input"
          rows="3"
          placeholder="填写安装完成情况、验收备注等…"
        ></textarea>

        <!-- Status actions -->
        <div class="status-actions">
          <button
            v-for="s in nextStatuses"
            :key="s.value"
            :class="['action-btn', s.type]"
            @click="changeStatus(s.value)"
          >
            {{ s.label }}
          </button>
        </div>
      </div>
    </el-drawer>

    <!-- Image preview overlay -->
    <div v-if="previewImage" class="preview-overlay" @click="previewImage = ''">
      <img :src="previewImage" class="preview-img" @click.stop />
      <button class="preview-close" @click="previewImage = ''">×</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  getInstallationTasks,
  getInstallationTask,
  changeInstallationTaskStatus,
  updateInstallationTask,
  uploadAttachment,
  deleteAttachment,
} from '@/api/tasks'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InstallationTaskResponse } from '@/types/api'
import { getErrorMessage } from '@/utils/error'

const authStore = useAuthStore()

// --- State ---
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')
const allTasks = ref<InstallationTaskResponse[]>([])
const currentTask = ref<InstallationTaskResponse | null>(null)
const drawerVisible = ref(false)
const activeTab = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const uploadLoading = ref(false)
const previewImage = ref('')
const installationNotes = ref('')
const pullDistance = ref(0)
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

const statusTransitions: Record<string, { value: string; label: string; type: string }[]> = {
  pending: [
    { value: 'assigned', label: '确认分配', type: 'primary' },
    { value: 'in_progress', label: '开始安装', type: 'primary' },
  ],
  assigned: [
    { value: 'in_progress', label: '开始安装', type: 'primary' },
  ],
  in_progress: [
    { value: 'pending_acceptance', label: '提交验收', type: 'success' },
  ],
  pending_acceptance: [
    { value: 'completed', label: '验收通过', type: 'success' },
    { value: 'in_progress', label: '返回修改', type: 'warning' },
  ],
  completed: [],
}

// --- Computed ---
const nextStatuses = computed(() =>
  currentTask.value ? (statusTransitions[currentTask.value.status] || []) : []
)

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
    installationNotes.value = currentTask.value.acceptance_result || ''
    drawerVisible.value = true
  } catch {
    ElMessage.error('加载任务详情失败')
  }
}

// --- Photos ---
function takePhoto() {
  if (fileInput.value) {
    fileInput.value.setAttribute('capture', 'environment')
    fileInput.value.click()
  }
}

function uploadPhoto() {
  if (fileInput.value) {
    fileInput.value.removeAttribute('capture')
    fileInput.value.click()
  }
}

async function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !currentTask.value) return

  uploadLoading.value = true
  try {
    // Compress large images before upload (max 1920px)
    const compressed = await compressImage(file, 1920, 0.8)
    await uploadAttachment('installation_task', currentTask.value.id, compressed, 'photo')
    ElMessage.success('上传成功')
    currentTask.value = await getInstallationTask(currentTask.value.id)
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploadLoading.value = false
  }
  input.value = ''
}

async function deletePhoto(attId: string) {
  if (!currentTask.value) return
  await ElMessageBox.confirm('确定删除此照片？删除后无法恢复。', '删除照片', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  try {
    await deleteAttachment(attId)
    ElMessage.success('已删除')
    currentTask.value = await getInstallationTask(currentTask.value.id)
  } catch {
    ElMessage.error('删除失败')
  }
}

// --- Status change ---
async function changeStatus(toStatus: string) {
  if (!currentTask.value) return
  await ElMessageBox.confirm(`确定将安装状态变更为「${toStatus}」？`, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  try {
    await changeInstallationTaskStatus(currentTask.value.id, {
      to_status: toStatus,
      reason: installationNotes.value || undefined,
    })

    // If completing, also save acceptance_result
    if (toStatus === 'completed' && installationNotes.value) {
      await updateInstallationTask(currentTask.value.id, {
        acceptance_result: installationNotes.value,
      })
    }

    ElMessage.success('状态已更新')
    currentTask.value = await getInstallationTask(currentTask.value.id)
    fetchTasks()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '状态更新失败'))
  }
}

// --- Image compression ---
function compressImage(file: File, maxDim: number, quality: number): Promise<File> {
  return new Promise((resolve) => {
    // Skip non-image files or already small files
    if (!file.type.startsWith('image/') || file.size < 500 * 1024) {
      resolve(file)
      return
    }

    const img = new Image()
    const url = URL.createObjectURL(file)

    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = (height / width) * maxDim
          width = maxDim
        } else {
          width = (width / height) * maxDim
          height = maxDim
        }
      }

      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) { resolve(file); return }

      ctx.drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(new File([blob], file.name, { type: 'image/jpeg' }))
          } else {
            resolve(file)
          }
        },
        'image/jpeg',
        quality
      )
    }

    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(file)
    }

    img.src = url
  })
}

// --- Lifecycle ---
onMounted(() => {
  fetchTasks()
})

// Re-fetch on window focus (user switched back to tab)
watch(() => document.visibilityState, (state) => {
  if (state === 'visible' && allTasks.value.length > 0) {
    fetchTasks(true)
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
  color: #666;
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
.task-no { font-size: 12px; color: #666; }
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
.photo-count { color: var(--ad-red, #e63946); }

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

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  margin-top: 4px;
}

/* Photo actions */
.photo-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.photo-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid #2a2a3e;
  background: #1e1e30;
  color: var(--ad-text, #e0e0e0);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.photo-btn:active { background: #2a2a3e; }
.photo-btn.primary {
  background: var(--ad-red, #e63946);
  border-color: var(--ad-red, #e63946);
  color: #fff;
}
.photo-btn.primary:active { opacity: 0.85; }
.photo-btn:disabled { opacity: 0.5; }

.upload-progress {
  text-align: center;
  font-size: 13px;
  color: var(--ad-red, #e63946);
  margin-bottom: 8px;
}

/* Photo grid */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}
.photo-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 1;
}
.photo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
}
.photo-delete {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 14px;
  line-height: 22px;
  text-align: center;
  cursor: pointer;
  display: none;
}
.photo-item:hover .photo-delete,
.photo-item:active .photo-delete {
  display: block;
}

/* Mobile-friendly: always show delete on mobile */
@media (pointer: coarse) {
  .photo-delete { display: block; }
}

.photo-empty {
  text-align: center;
  color: #555;
  font-size: 13px;
  padding: 20px 0;
  margin-bottom: 16px;
}

/* Notes textarea */
.notes-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  background: #1e1e30;
  color: var(--ad-text, #e0e0e0);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 16px;
  outline: none;
  transition: border-color 0.2s;
}
.notes-input:focus { border-color: var(--ad-red, #e63946); }
.notes-input::placeholder { color: #555; }

/* Status action buttons */
.status-actions { margin-top: 4px; }
.action-btn {
  display: block;
  width: 100%;
  padding: 14px;
  margin-bottom: 10px;
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
.action-btn.primary {
  background: var(--ad-red, #e63946);
  border-color: var(--ad-red, #e63946);
  color: #fff;
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

/* Image preview overlay */
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0,0,0,0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.preview-img {
  max-width: 95vw;
  max-height: 90vh;
  object-fit: contain;
}
.preview-close {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.15);
  color: #fff;
  font-size: 22px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Safe area for mobile */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .task-list { padding-bottom: calc(80px + env(safe-area-inset-bottom)); }
  .drawer-body { padding-bottom: calc(40px + env(safe-area-inset-bottom)); }
}
</style>
