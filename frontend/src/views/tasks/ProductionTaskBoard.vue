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
      <span>逾期 {{ overdueCount }} 个</span>
      <span v-if="onlyOverdue">当前显示 {{ visibleTasks.length }} 个</span>
      <span>平均进度 {{ averageProgress }}%</span>
      <el-switch
        v-model="onlyOverdue"
        inline-prompt
        active-text="逾期"
        inactive-text="全部"
        aria-label="仅查看逾期任务"
      />
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
                <el-tag v-if="card.is_overdue" size="small" type="danger">逾期</el-tag>
                <el-tag size="small" :type="statusColor(card.status)">{{ statusLabel(card) }}</el-tag>
              </div>
            </div>
            <div class="card-name">{{ card.project_name }}</div>
            <div class="card-item">明细：{{ card.item_name || '未关联订单明细' }}</div>
            <div class="card-meta">
              <span>{{ card.order_no || '-' }}</span>
              <span>{{ card.customer_name || '-' }}</span>
            </div>
            <div class="progress-row">
              <el-progress :percentage="taskProgress(card)" :stroke-width="8" />
              <span>{{ taskProgress(card) }}%</span>
            </div>
            <div v-if="card.planned_end_at" class="planned-end">计划结束：{{ formatDateTimeFull(card.planned_end_at) }}</div>
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
import { formatDateTimeFull } from '@/utils/datetime'
import { isTaskVisible, TASK_BOARD_COLUMNS, taskProgress } from '@/utils/task-board'

const loading = ref(false)
const tasks = ref<TaskQueueItem[]>([])
const onlyOverdue = ref(false)

const columns = TASK_BOARD_COLUMNS

function colCards(key: TaskQueueItem['stage']) {
  return visibleTasks.value.filter(task => task.stage === key)
}

const unfinishedTasks = computed(() => tasks.value.filter(task => (
  isTaskVisible(task)
)))
const overdueCount = computed(() => unfinishedTasks.value.filter(task => task.is_overdue).length)
const visibleTasks = computed(() => unfinishedTasks.value.filter(task => (
  !onlyOverdue.value || task.is_overdue
)))

const averageProgress = computed(() => {
  const activeTasks = unfinishedTasks.value
  if (!activeTasks.length) return 0
  return Math.round(activeTasks.reduce((sum, task) => sum + taskProgress(task), 0) / activeTasks.length)
})

function statusLabel(task: TaskQueueItem) {
  const labels: Record<string, string> = {
    pending: task.stage === 'design' ? '待分配' : task.stage === 'production' ? '待制作' : '待分配',
    designing: '设计中',
    pending_review: '待处理',
    revision: '需调整',
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
.summary-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 13px; }
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
.card-item { margin-bottom: 6px; color: var(--ad-primary, #409eff); font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: #888; }
.progress-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.progress-row :deep(.el-progress) { flex: 1; }
.progress-row > span { width: 38px; text-align: right; font-size: 12px; color: var(--ad-text-secondary); }
.assignee { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); }
.planned-end { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); }
</style>
