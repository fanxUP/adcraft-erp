<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2>项目看板</h2>
        <p class="page-hint">同一订单的设计、制作、安装任务可以同时出现在不同阶段，进度互不覆盖。</p>
      </div>
      <el-button :loading="loading" @click="fetchData">刷新</el-button>
    </div>

    <div class="summary-bar">
      <span>共 {{ tasks.length }} 个任务</span>
      <span>平均进度 {{ averageProgress }}%</span>
    </div>

    <div class="board" v-loading="loading">
      <div v-for="col in columns" :key="col.key" class="board-column">
        <div class="column-header">
          <span>{{ col.label }}</span>
          <el-tag size="small" type="danger">{{ colCards(col.key).length }}</el-tag>
        </div>
        <div class="column-body">
          <el-empty v-if="colCards(col.key).length === 0" description="暂无任务" :image-size="56" />
          <el-card
            v-for="card in colCards(col.key)"
            :key="card.id"
            shadow="hover"
            class="board-card"
            @click="handleCardClick(card)"
          >
            <div class="card-topline">
              <span class="card-no">{{ card.task_no }}</span>
              <div class="card-statuses">
                <el-tag v-if="card.is_blocked" size="small" type="warning">阻塞</el-tag>
                <el-tag size="small" :type="statusColor(card.status)">{{ statusLabel(card) }}</el-tag>
              </div>
            </div>
            <div class="card-name">{{ card.project_name }}</div>
            <div class="card-meta">
              <span>{{ card.order_no || '-' }}</span>
              <span>{{ card.customer_name || '-' }}</span>
            </div>
            <div class="progress-row">
              <el-progress :percentage="progress(card)" :stroke-width="8" />
              <span>{{ progress(card) }}%</span>
            </div>
            <div v-if="card.is_blocked" class="blocked-reason">{{ card.blocked_reason }}</div>
            <div v-if="card.assigned_to_name" class="assignee">负责人：{{ card.assigned_to_name }}</div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getTaskQueue } from '@/api/tasks'
import type { TaskQueueItem } from '@/types/api'

const loading = ref(false)
const tasks = ref<TaskQueueItem[]>([])

const columns = [
  { key: 'design', label: '设计' },
  { key: 'production', label: '制作' },
  { key: 'installation', label: '安装' },
] as const

function colCards(key: TaskQueueItem['stage']) {
  return tasks.value.filter(task => task.stage === key)
}

const averageProgress = computed(() => {
  const activeTasks = tasks.value.filter(task => task.status !== 'cancelled')
  if (!activeTasks.length) return 0
  return Math.round(activeTasks.reduce((sum, task) => sum + progress(task), 0) / activeTasks.length)
})

function progress(task: TaskQueueItem) {
  return Math.min(100, Math.max(0, Number(task.progress_pct ?? 0)))
}

function statusLabel(task: TaskQueueItem) {
  const labels: Record<string, string> = {
    pending: task.stage === 'design' ? '待分配' : task.stage === 'production' ? '待制作' : '待分配',
    designing: '设计中',
    pending_review: '待确认',
    revision: '需修改',
    confirmed: '已完成',
    queued: '排队中',
    in_progress: task.stage === 'installation' ? '安装中' : '制作中',
    qc_check: '待质检',
    rework: '返工',
    assigned: '已分配',
    pending_acceptance: '待验收',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[task.status] || task.status
}

function statusColor(status: string) {
  const colors: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    confirmed: 'success',
    completed: 'success',
    pending_review: 'warning',
    qc_check: 'warning',
    pending_acceptance: 'warning',
    rework: 'danger',
    cancelled: 'info',
  }
  return colors[status] || 'primary'
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getTaskQueue({ page: 1, page_size: 200 })
    tasks.value = data.items
  } finally {
    loading.value = false
  }
}

function handleCardClick(card: TaskQueueItem) {
  const routeByType: Record<TaskQueueItem['task_type'], string> = {
    design: '/design-tasks/',
    production: '/production-tasks/',
    installation: '/installation-tasks/',
  }
  window.location.href = routeByType[card.task_type] + card.id
}

function handlePageShow(event: PageTransitionEvent) {
  if (event.persisted) void fetchData()
}

onMounted(() => {
  void fetchData()
  window.addEventListener('pageshow', handlePageShow)
})

onBeforeUnmount(() => {
  window.removeEventListener('pageshow', handlePageShow)
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.page-hint { margin: 6px 0 0; color: var(--ad-text-secondary); font-size: 13px; }
.summary-bar { display: flex; gap: 20px; margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 13px; }
.board { display: flex; gap: 12px; overflow-x: auto; min-height: 60vh; }
.board-column { flex: 1; min-width: 280px; background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 6px; display: flex; flex-direction: column; }
.column-header { padding: 12px; font-weight: bold; font-size: 16px; color: var(--ad-text); border-bottom: 1px solid var(--ad-border); display: flex; justify-content: center; gap: 8px; align-items: center; }
.column-body { padding: 8px; flex: 1; overflow-y: auto; }
.board-card { margin-bottom: 8px; cursor: pointer; background: var(--ad-card); border: 1px solid var(--ad-border); }
.board-card:hover { border-color: #e63946; }
.card-topline { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-statuses { display: flex; align-items: center; gap: 4px; }
.card-no { font-size: 12px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-name { font-weight: bold; font-size: 16px; color: var(--ad-text); margin: 8px 0 4px; }
.card-meta { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: #888; }
.progress-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.progress-row :deep(.el-progress) { flex: 1; }
.progress-row > span { width: 38px; text-align: right; font-size: 12px; color: var(--ad-text-secondary); }
.assignee { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); }
.blocked-reason { margin-top: 8px; padding: 6px 8px; color: #b88230; background: rgba(230, 162, 60, 0.12); border-radius: 4px; font-size: 12px; line-height: 1.4; }
</style>
