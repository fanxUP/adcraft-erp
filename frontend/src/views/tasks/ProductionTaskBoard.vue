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
          <template v-if="col.key === 'completed'">
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

  <CompletedProjectDetailDrawer
    v-model="completedDetailVisible"
    :project="completedDetail"
    :loading="completedDetailLoading"
    :error="completedDetailError"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getCompletedProject, getCompletedProjects, getTaskQueue } from '@/api/tasks'
import type { CompletedProjectCard as CompletedProjectCardType, CompletedProjectDetail, TaskQueueItem } from '@/types/api'
import TaskBoardCard from '@/components/ui/TaskBoardCard.vue'
import CompletedProjectCard from '@/components/ui/CompletedProjectCard.vue'
import CompletedProjectDetailDrawer from '@/components/ui/CompletedProjectDetailDrawer.vue'
import { isTaskVisible, TASK_BOARD_COLUMNS, taskProgress } from '@/utils/task-board'
import { useAuthStore } from '@/stores/auth'

const loading = ref(false)
const tasks = ref<TaskQueueItem[]>([])
const completedProjects = ref<CompletedProjectCardType[]>([])
const onlyOverdue = ref(false)
const completedDetailVisible = ref(false)
const completedDetailLoading = ref(false)
const completedDetail = ref<CompletedProjectDetail | null>(null)
const completedDetailError = ref('')
const authStore = useAuthStore()
const canViewCompleted = computed(() => authStore.can('task_completion:read'))

const columns = [
  ...TASK_BOARD_COLUMNS,
  { key: 'completed', label: '完成' },
] as const

const visibleColumns = computed(() => columns.filter(col => (
  col.key !== 'completed' || canViewCompleted.value
)))

type BoardColumnKey = TaskQueueItem['stage'] | 'completed'

function colCards(key: TaskQueueItem['stage']) {
  return visibleTasks.value.filter(task => task.stage === key)
}

function columnCount(key: BoardColumnKey) {
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
    const [taskData, completedData] = await Promise.all([
      getTaskQueue({ page: 1, page_size: 200 }),
      canViewCompleted.value
        ? getCompletedProjects({ page: 1, page_size: 200 }).catch(() => emptyCompleted)
        : Promise.resolve(emptyCompleted),
    ])
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

async function handleCompletedProjectClick(project: CompletedProjectCardType) {
  completedDetailVisible.value = true
  completedDetailLoading.value = true
  completedDetailError.value = ''
  completedDetail.value = null
  try {
    completedDetail.value = await getCompletedProject(project.project_id)
  } catch {
    completedDetailError.value = '完成项目详情暂时无法加载，请稍后重试'
  } finally {
    completedDetailLoading.value = false
  }
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
