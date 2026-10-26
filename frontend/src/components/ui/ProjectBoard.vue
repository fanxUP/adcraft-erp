<template>
  <section aria-label="项目看板">
    <div class="board-toolbar">
      <div>
        <p class="board-hint">待确认订单先留在队列；设计、制作、安装按任务分别推进。</p>
        <span>本页可见订单 {{ visibleOrderCount }} 个 · 已加载任务 {{ loadedTasks.length }} 个</span>
      </div>
      <div class="board-actions">
        <el-switch v-if="hasTaskColumns" v-model="onlyOverdue" active-text="仅逾期任务" aria-label="仅查看逾期任务" />
        <el-button :loading="loading" @click="refresh">刷新</el-button>
      </div>
    </div>
    <el-empty v-if="!visibleColumns.length" description="当前账号暂无可查看的项目数据" />
    <div class="board">
      <section v-for="col in visibleColumns" :key="col.key" class="board-column" :aria-label="col.label" :aria-busy="col.loading">
        <header class="column-header"><span>{{ col.label }}</span><el-tag size="small">{{ col.error ? '读取失败' : col.total }}</el-tag></header>
        <div v-loading="col.loading" class="column-body">
          <el-alert v-if="col.error" :title="col.error" type="error" :closable="false" show-icon>
            <el-button text type="primary" @click="loadColumn(col)">重试</el-button>
          </el-alert>
          <template v-else>
            <el-empty v-if="!col.orders.length && !col.tasks.length && !col.projects.length && !col.loading" description="暂无记录" :image-size="56" />
            <ProjectQueueCard v-for="order in col.orders" :key="order.id" :order="order" @open="router.push(`/orders/${order.id}`)" />
            <TaskBoardCard v-for="task in col.tasks" :key="`${task.task_type}:${task.id}`" :task="task" @open="openTask(task)" />
            <CompletedProjectCard v-for="project in col.projects" :key="project.project_id" :project="project" @open="router.push({ name: 'CompletedProjectDetail', params: { projectId: project.project_id } })" />
          </template>
        </div>
        <el-pagination v-if="!col.error && col.total > pageSize" small layout="prev, pager, next" :pager-count="3" :total="col.total" :page-size="pageSize" :current-page="col.page" :disabled="col.loading" @current-change="changePage(col, $event)" />
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getProjectQueuePage } from '@/api/orders'
import { getTaskQueue, getCompletedProjects } from '@/api/tasks'
import type { OrderListResponse, TaskQueueItem, CompletedProjectCard as CompletedProject } from '@/types/api'
import { TASK_BOARD_COLUMNS } from '@/utils/task-board'
import TaskBoardCard from './TaskBoardCard.vue'
import ProjectQueueCard from './ProjectQueueCard.vue'
import CompletedProjectCard from './CompletedProjectCard.vue'

type ColumnKey = 'queue' | TaskQueueItem['stage'] | 'completed'
interface BoardColumn {
  key: ColumnKey; label: string; page: number; total: number; loading: boolean; error: string; request: number
  orders: OrderListResponse[]; tasks: TaskQueueItem[]; projects: CompletedProject[]
}
const auth = useAuthStore(), router = useRouter(), onlyOverdue = ref(false)
const pageSize = 20
const definitions: Array<{ key: ColumnKey; label: string }> = [
  { key: 'queue', label: '待确认 / 待安排' }, ...TASK_BOARD_COLUMNS, { key: 'completed', label: '已完成项目' },
]
const columns = reactive<BoardColumn[]>(definitions.map(col => ({ ...col, page: 1, total: 0, loading: false, error: '', request: 0, orders: [], tasks: [], projects: [] })))
const stagePermissions = TASK_BOARD_COLUMNS.map(col => `${col.key}_task:read`)
const visibleColumns = computed(() => columns.filter(col => {
  if (col.key === 'queue') return auth.can('order:read')
  if (col.key === 'completed') return auth.can('task_completion:read') && auth.canAny(stagePermissions)
  return auth.canAll(['task_queue:read', `${col.key}_task:read`])
}))
const hasTaskColumns = computed(() => visibleColumns.value.some(col => !['queue', 'completed'].includes(col.key)))
const loading = computed(() => visibleColumns.value.some(col => col.loading))
const loadedTasks = computed(() => visibleColumns.value.filter(col => !col.error).flatMap(col => col.tasks))
const visibleOrderCount = computed(() => new Set(visibleColumns.value.filter(col => !col.error).flatMap(col => [
  ...col.orders.map(order => order.id), ...col.tasks.map(task => task.document_id), ...col.projects.map(project => project.project_id),
])).size)
let mounted = false
async function loadColumn(col: BoardColumn) {
  const request = ++col.request
  col.loading = true; col.error = ''
  try {
    const data = col.key === 'queue' ? await getProjectQueuePage(col.page, pageSize)
      : col.key === 'completed' ? await getCompletedProjects({ page: col.page, page_size: pageSize })
        : await getTaskQueue({ page: col.page, page_size: pageSize, stage: col.key, overdue: onlyOverdue.value ? true : undefined })
    if (request !== col.request) return
    if (col.page > 1 && !data.items.length && data.total > 0) {
      col.page = Math.ceil(data.total / pageSize)
      await loadColumn(col)
      return
    }
    col.total = data.total
    col.orders = col.key === 'queue' ? data.items as OrderListResponse[] : []
    col.tasks = !['queue', 'completed'].includes(col.key) ? data.items as TaskQueueItem[] : []
    col.projects = col.key === 'completed' ? data.items as CompletedProject[] : []
  } catch {
    if (request === col.request) col.error = `${col.label}加载失败，请重试`
  } finally { if (request === col.request) col.loading = false }
}
async function refresh() { await Promise.all(visibleColumns.value.map(loadColumn)) }
function changePage(col: BoardColumn, page: number) { col.page = page; void loadColumn(col) }
function openTask(task: TaskQueueItem) {
  const paths = { design: 'design-tasks', production: 'production-tasks', installation: 'installation-tasks' }
  void router.push(`/${paths[task.task_type]}/${task.id}`)
}
function focusRefresh() { if (document.visibilityState === 'visible' && !loading.value) void refresh() }
function pageShow(event: PageTransitionEvent) { if (event.persisted) focusRefresh() }
watch(onlyOverdue, () => {
  visibleColumns.value.filter(col => !['queue', 'completed'].includes(col.key)).forEach(col => { col.page = 1; void loadColumn(col) })
})
watch(() => auth.permissions.join(','), () => {
  for (const col of columns) if (!visibleColumns.value.includes(col)) {
    col.request++; col.loading = false; col.orders = []; col.tasks = []; col.projects = []; col.total = 0
  }
  if (mounted) void refresh()
})
onMounted(() => {
  mounted = true; void refresh()
  window.addEventListener('focus', focusRefresh); window.addEventListener('pageshow', pageShow)
  document.addEventListener('visibilitychange', focusRefresh)
})
onBeforeUnmount(() => {
  mounted = false
  columns.forEach(col => col.request++)
  window.removeEventListener('focus', focusRefresh); window.removeEventListener('pageshow', pageShow)
  document.removeEventListener('visibilitychange', focusRefresh)
})
</script>

<style scoped>
.board-toolbar, .board-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.board-toolbar { margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 13px; flex-wrap: wrap; }
.board-hint { margin: 0 0 6px; }
.board { display: flex; gap: 12px; overflow-x: auto; min-height: 40vh; }
.board-column { flex: 1; min-width: 280px; background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 6px; display: flex; flex-direction: column; height: 70vh; min-height: 420px; }
.column-header { padding: 12px; font-weight: 600; color: var(--ad-text); border-bottom: 1px solid var(--ad-border); display: flex; justify-content: center; gap: 8px; align-items: center; }
.column-body { padding: 8px; flex: 1; min-height: 0; overflow-y: auto; }
.el-pagination { justify-content: center; padding: 8px; }
</style>
