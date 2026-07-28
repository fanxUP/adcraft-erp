<template>
  <div class="mobile-page">
    <!-- Header -->
    <div class="home-header">
      <div class="header-top">
        <div class="header-greeting">
          <span class="greeting-text">你好，{{ authStore.user?.real_name || authStore.user?.username }}</span>
          <span class="greeting-role">{{ roleLabel }}</span>
        </div>
        <div class="header-date">{{ todayStr }}</div>
      </div>
      <div class="header-quote">
        <span v-if="isInstaller" class="quote-text">今日现场任务：</span>
        <span v-else-if="isProduction" class="quote-text">今日车间任务：</span>
        <span v-else class="quote-text">今日待办：</span>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="skeleton-list">
      <div v-for="n in 4" :key="n" class="skeleton-card">
        <div class="skeleton-line w-40"></div>
        <div class="skeleton-line w-80"></div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="state-box">
      <div class="state-icon">⚠️</div>
      <div class="state-text">{{ error }}</div>
      <button class="retry-btn" @click="fetchData()">重试</button>
    </div>

    <template v-else>
      <!-- Task stat cards -->
      <div class="stat-grid">
        <div class="stat-card" @click="goToInstallation">
          <div class="stat-number accent">{{ stats.installation }}</div>
          <div class="stat-label">待安装</div>
        </div>
        <div class="stat-card" @click="goToInstallation">
          <div class="stat-number warning">{{ stats.inProgress }}</div>
          <div class="stat-label">安装中</div>
        </div>
        <div class="stat-card" @click="goToInstallation">
          <div class="stat-number info">{{ stats.pendingAcceptance }}</div>
          <div class="stat-label">待验收</div>
        </div>
        <div class="stat-card">
          <div class="stat-number success">{{ stats.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="section-title">快捷操作</div>
      <div class="quick-actions">
        <div class="action-item" @click="$router.push('/mobile/installation')">
          <div class="action-icon photo-icon">📋</div>
          <div class="action-name">查看任务</div>
        </div>
        <div class="action-item" @click="openCamera">
          <div class="action-icon camera-icon">📷</div>
          <div class="action-name">现场拍照</div>
        </div>
        <div class="action-item" @click="$router.push('/mobile/installation')">
          <div class="action-icon check-icon">✅</div>
          <div class="action-name">状态更新</div>
        </div>
      </div>

      <!-- Recent tasks -->
      <div class="section-title">最近任务</div>
      <div v-if="recentTasks.length === 0" class="state-box small">
        <div class="state-text">暂无最近任务</div>
      </div>
      <div v-else class="task-list">
        <div
          v-for="task in recentTasks"
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
            <span v-if="task.attachments?.length" class="meta-item photo-count">📷 {{ task.attachments.length }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getInstallationTasks, getInstallationTask } from '@/api/tasks'
import type { InstallationTaskResponse } from '@/types/api'
import { getErrorMessage } from '@/utils/error'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const error = ref('')
const allTasks = ref<InstallationTaskResponse[]>([])
const recentTasks = ref<InstallationTaskResponse[]>([])

const todayStr = computed(() => {
  const d = new Date()
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 周${weekdays[d.getDay()]}`
})

const roleLabel = computed(() => {
  const roles = authStore.user?.roles || []
  if (roles.includes('admin')) return '管理员'
  if (roles.includes('installer')) return '安装师傅'
  if (roles.includes('production')) return '制作人员'
  if (roles.includes('designer')) return '设计师'
  if (roles.includes('sales')) return '销售'
  if (roles.includes('finance')) return '财务'
  return ''
})

const isInstaller = computed(() => (authStore.user?.roles || []).includes('installer'))
const isProduction = computed(() => (authStore.user?.roles || []).includes('production'))

const stats = computed(() => {
  const tasks = allTasks.value
  return {
    installation: tasks.filter(t => t.status === 'pending' || t.status === 'assigned').length,
    inProgress: tasks.filter(t => t.status === 'in_progress').length,
    pendingAcceptance: tasks.filter(t => t.status === 'pending_acceptance').length,
    completed: tasks.filter(t => t.status === 'completed').length,
  }
})

function statusColor(s: string) {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    pending: 'info',
    assigned: 'primary',
    in_progress: 'warning',
    pending_acceptance: 'warning',
    completed: 'success',
  }
  return map[s] ?? 'info'
}

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

function goToInstallation() {
  router.push('/mobile/installation')
}

function openCamera() {
  // Navigate to installation tasks - user can take photos from there
  router.push('/mobile/installation')
}

async function openTask(task: InstallationTaskResponse) {
  // Navigate to installation with task detail — use query param
  router.push(`/mobile/installation?task_id=${task.id}`)
}

async function fetchData() {
  loading.value = true
  error.value = ''

  try {
    const data = await getInstallationTasks({ page_size: 100, status: 'pending,assigned,in_progress,pending_acceptance' })
    allTasks.value = data.items || []

    // Recent: get the 5 most recently updated tasks
    const sorted = [...(data.items || [])].sort(
      (a, b) => new Date(b.updated_at || b.created_at || '').getTime() - new Date(a.updated_at || a.created_at || '').getTime()
    )
    recentTasks.value = sorted.slice(0, 5)
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.mobile-page {
  max-width: 480px;
  margin: 0 auto;
  min-height: calc(100vh - 64px);
  padding: 0 0 16px;
  background: #0f0f1a;
  color: var(--ad-text, #e0e0e0);
}

/* Header */
.home-header {
  padding: 20px 16px 12px;
  background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
}
.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.header-greeting {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.greeting-text {
  font-size: 20px;
  font-weight: 700;
}
.greeting-role {
  font-size: 13px;
  color: #888;
}
.header-date {
  font-size: 13px;
  color: #666;
  text-align: right;
  white-space: nowrap;
}
.header-quote {
  margin-top: 8px;
}
.quote-text {
  font-size: 14px;
  color: #aaa;
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
.state-box.small { padding: 30px 20px; }
.state-icon { font-size: 40px; margin-bottom: 12px; }
.state-text { font-size: 14px; color: #888; margin-bottom: 16px; }
.state-box.small .state-text { margin-bottom: 0; }
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

/* Stat grid */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 12px 16px;
}
.stat-card {
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 12px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.stat-card:active {
  border-color: var(--ad-red, #e63946);
  transform: scale(0.96);
}
.stat-number {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-number.accent { color: var(--ad-red, #e63946); }
.stat-number.warning { color: #f97316; }
.stat-number.info { color: #60a5fa; }
.stat-number.success { color: #22c55e; }
.stat-label {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

/* Section title */
.section-title {
  font-size: 16px;
  font-weight: 600;
  padding: 12px 16px 8px;
}

/* Quick actions */
.quick-actions {
  display: flex;
  gap: 10px;
  padding: 0 16px 8px;
}
.action-item {
  flex: 1;
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 14px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.action-item:active {
  border-color: var(--ad-red, #e63946);
  transform: scale(0.96);
}
.action-icon {
  font-size: 28px;
  margin-bottom: 6px;
}
.action-name {
  font-size: 12px;
  color: #ccc;
}

/* Task list */
.task-list { padding: 0 16px; }
.task-card {
  background: #1e1e30;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 8px;
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
  margin-bottom: 4px;
}
.task-no { font-size: 12px; color: #666; }
.task-name {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  line-height: 1.4;
}
.task-meta {
  font-size: 12px;
  color: #888;
  display: flex;
  gap: 10px;
}
.meta-item { display: inline-flex; align-items: center; gap: 2px; }
.photo-count { color: var(--ad-red, #e63946); }
</style>
