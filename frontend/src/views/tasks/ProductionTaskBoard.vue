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
      <span>未完成任务 {{ unfinishedTasks.length }} 个</span>
      <span v-if="canViewCompleted">完成项目 {{ completedProjects.length }} 个</span>
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
      <div v-for="col in visibleColumns" :key="col.key" class="board-column">
        <div class="column-header">
          <span>{{ col.label }}</span>
          <el-tag size="small" :type="col.key === 'completed' ? 'success' : 'danger'">{{ columnCount(col.key) }}</el-tag>
        </div>
        <div class="column-body">
          <template v-if="col.key === 'queue'">
            <el-empty v-if="!queueCards().length" description="暂无项目" :image-size="56" />
            <ProjectQueueCard
              v-for="order in queueCards()"
              :key="order.id"
              :order="order"
              @open="handleOrderCardClick(order)"
            />
          </template>
          <template v-else-if="col.key === 'completed'">
            <el-empty v-if="!completedProjects.length" description="暂无完成项目" :image-size="56" />
            <CompletedProjectCard
              v-for="project in completedProjects"
              :key="project.project_id"
              :project="project"
              @open="handleCompletedProjectClick(project)"
            />
          </template>
          <template v-else>
            <el-empty v-if="!colCards(col.key).length" description="暂无任务" :image-size="56" />
            <TaskBoardCard
              v-for="card in colCards(col.key)"
              :key="card.id"
              :task="card"
              @open="handleCardClick(card)"
            />
          </template>
        </div>
      </div>
    </div>
  </div>

</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getProjectQueueOrders } from '@/api/orders'
import { getCompletedProjects, getTaskQueue } from '@/api/tasks'
import type { CompletedProjectCard as CompletedProjectCardType, OrderListResponse, TaskQueueItem } from '@/types/api'
import TaskBoardCard from '@/components/ui/TaskBoardCard.vue'
import CompletedProjectCard from '@/components/ui/CompletedProjectCard.vue'
import ProjectQueueCard from '@/components/ui/ProjectQueueCard.vue'
import { isProjectQueueStatus } from '@/utils/project-queue'
import { isTaskVisible, TASK_BOARD_COLUMNS, taskProgress } from '@/utils/task-board'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const loading = ref(false)
const tasks = ref<TaskQueueItem[]>([])
const projectQueueOrders = ref<OrderListResponse[]>([])
const completedProjects = ref<CompletedProjectCardType[]>([])
const onlyOverdue = ref(false)
const authStore = useAuthStore()
const router = useRouter()
const canViewCompleted = computed(() => authStore.can('task_completion:read'))
const canViewProjectQueue = computed(() => authStore.can('order:read'))

const columns = [
  { key: 'queue', label: '项目队列' },
  ...TASK_BOARD_COLUMNS,
  { key: 'completed', label: '完成' },
] as const

const visibleColumns = computed(() => columns.filter(col => (
  (col.key !== 'queue' || canViewProjectQueue.value)
  && (col.key !== 'completed' || canViewCompleted.value)
)))

type BoardColumnKey = (typeof columns)[number]['key']

function queueCards() {
  return projectQueueOrders.value.filter(order => isProjectQueueStatus(order.status))
}

function colCards(key: TaskQueueItem['stage']) {
  return visibleTasks.value.filter(task => task.stage === key)
}

function columnCount(key: BoardColumnKey) {
  if (key === 'queue') return queueCards().length
  return key === 'completed' ? completedProjects.value.length : colCards(key).length
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

async function fetchData() {
  loading.value = true
  try {
    const emptyCompleted = { items: [] as CompletedProjectCardType[], total: 0, page: 1, page_size: 200 }
    const [queueData, taskData, completedData] = await Promise.all([
      canViewProjectQueue.value
        ? getProjectQueueOrders().catch(() => [] as OrderListResponse[])
        : Promise.resolve([] as OrderListResponse[]),
      getTaskQueue({ page: 1, page_size: 200 }),
      canViewCompleted.value
        ? getCompletedProjects({ page: 1, page_size: 200 }).catch(() => emptyCompleted)
        : Promise.resolve(emptyCompleted),
    ])
    projectQueueOrders.value = queueData
    tasks.value = taskData.items
    completedProjects.value = completedData.items
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

function handleOrderCardClick(order: OrderListResponse) {
  window.location.href = `/orders/${order.id}`
}

function handleCompletedProjectClick(project: CompletedProjectCardType) {
  router.push({ name: 'CompletedProjectDetail', params: { projectId: project.project_id } })
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
</style>
