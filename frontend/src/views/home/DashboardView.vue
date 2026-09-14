<template>
  <div class="page" v-loading="loading">
    <h1 style="margin: 0 0 24px; color: var(--ad-text)">经营驾驶舱</h1>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col v-if="canViewFinancial" :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日订单金额</div>
          <div class="stat-value">¥ {{ data.today_order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col v-if="canViewFinancial" :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日收款金额</div>
          <div class="stat-value is-success">¥ {{ data.today_payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col v-if="canViewFinancial" :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月订单金额</div>
          <div class="stat-value">¥ {{ data.month_order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col v-if="canViewFinancial" :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月收款金额</div>
          <div class="stat-value is-success">¥ {{ data.month_payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col v-if="canViewFinancial" :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月未收金额</div>
          <div class="stat-value is-danger">¥ {{ data.month_unpaid_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card task-card">
          <div class="stat-label">待设计任务</div>
          <div class="stat-value">{{ data.pending_design_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card task-card">
          <div class="stat-label">待制作任务</div>
          <div class="stat-value">{{ data.pending_production_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card task-card">
          <div class="stat-label">待安装任务</div>
          <div class="stat-value">{{ data.pending_installation_count }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="canViewTaskCompletion" shadow="never" class="completion-card" v-loading="completionLoading">
      <template #header>
        <div class="completion-header">
          <div>
            <span class="completion-title">项目完成统计</span>
            <el-tag v-if="completionSummary" size="small" type="info" effect="plain">
              {{ completionSummary.scope === 'all' ? '全员可见' : '仅本人' }}
            </el-tag>
          </div>
          <el-radio-group v-model="completionPeriod" size="small" @change="handleCompletionPeriodChange">
            <el-radio-button label="month">当月</el-radio-button>
            <el-radio-button label="all">全部</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-alert
        v-if="completionError"
        type="warning"
        :closable="false"
        show-icon
        class="completion-alert"
      >
        <span>{{ completionError }}</span>
        <el-button link type="warning" size="small" @click="fetchTaskCompletion">重试</el-button>
      </el-alert>
      <el-alert
        v-if="completionSummary?.message"
        :title="completionSummary.message"
        type="info"
        :closable="false"
        show-icon
        class="completion-alert"
      />

      <template v-if="completionSummary">
        <div class="completion-kpis">
          <div class="completion-kpi">
            <span class="completion-kpi-label">{{ canViewCompletionAll ? '整单完成项目' : '我完成的项目' }}</span>
            <strong>{{ canViewCompletionAll ? completionSummary.organization?.completed_order_project_count || 0 : completionSummary.own.completed_project_count }}</strong>
          </div>
          <div class="completion-kpi">
            <span class="completion-kpi-label">{{ canViewCompletionAll ? '最终交付明细' : '我完成的明细' }}</span>
            <strong>{{ canViewCompletionAll ? completionSummary.organization?.completed_detail_count || 0 : completionSummary.own.completed_work_unit_count }}</strong>
          </div>
          <div v-if="canViewCompletionAll" class="completion-kpi">
            <span class="completion-kpi-label">完成工作明细</span>
            <strong>{{ completionSummary.organization?.completed_work_unit_count || 0 }}</strong>
          </div>
          <div class="completion-kpi completion-kpi--stages">
            <span class="completion-kpi-label">阶段完成明细</span>
            <div class="stage-counts">
              <span v-for="stage in completionStages" :key="stage.key">
                {{ stage.label }} {{ (canViewCompletionAll ? completionSummary.organization?.stage_breakdown : completionSummary.own.stage_breakdown)?.[stage.key] || 0 }}
              </span>
            </div>
          </div>
        </div>

        <button type="button" class="completion-entry-card" @click="handleCompletionStatsClick">
          <span class="completion-entry-icon" aria-hidden="true">✓</span>
          <span class="completion-entry-content">
            <span class="completion-entry-heading">
              <span class="completion-entry-title">{{ canViewCompletionAll ? '员工完成统计' : '我的完成统计' }}</span>
              <span class="completion-entry-action">查看详细统计</span>
            </span>
            <span class="completion-entry-summary">
              <template v-if="canViewCompletionAll">{{ completionSummary.employees.length }} 名员工 · </template>
              {{ canViewCompletionAll ? '完成工作明细' : '我完成的明细' }} {{ completionEntryStats?.completed_work_unit_count || 0 }} 条
            </span>
            <span class="completion-entry-stages">
              <span v-for="stage in completionStages" :key="stage.key">
                {{ stage.label }} {{ completionEntryStats?.stage_breakdown?.[stage.key] || 0 }}
              </span>
              <span v-if="canViewCompletionAll && completionSummary.unassigned.completed_work_unit_count" class="completion-entry-unassigned">
                未分配 {{ completionSummary.unassigned.completed_work_unit_count }} 条
              </span>
            </span>
          </span>
          <el-icon class="completion-entry-arrow" aria-hidden="true"><ArrowRight /></el-icon>
        </button>
      </template>
    </el-card>

    <el-row :gutter="16">
      <el-col v-if="canViewPricedOrders" :span="12">
        <el-card shadow="never" class="info-card">
          <template #header><span>报价单</span></template>
          <div v-if="!quoteList.length" style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无报价单</div>
          <div v-for="item in quoteList" :key="item.id" class="debt-row quote-row" @click="goQuote(item)">
            <el-tag size="small" :type="quoteStatusColor(item.status)" class="quote-status">{{ quoteStatusLabel(item.status) }}</el-tag>
            <span class="quote-col quote-no-customer">
              <div class="quote-no">{{ item.quote_no }}</div>
              <div class="quote-sub">{{ item.customer_name || '—' }}</div>
            </span>
            <span class="quote-col quote-project-col">{{ item.project_name }}</span>
            <span class="debt-amount" style="color: var(--ad-text)">¥ {{ item.total_amount?.toFixed(2) }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col v-if="canViewFinancial" :span="12">
        <el-card shadow="never" class="info-card">
          <template #header><span>客户欠款排行</span></template>
          <div v-if="!data.customer_debt_ranking?.length" style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无欠款</div>
          <div v-for="(item, idx) in data.customer_debt_ranking" :key="item.customer_id" class="debt-row">
            <span class="debt-rank">{{ idx + 1 }}</span>
            <span class="debt-name">{{ item.customer_name }}</span>
            <span class="debt-amount">¥ {{ item.debt_amount?.toFixed(2) }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>

  <!-- 项目看板 -->
  <div class="page" style="margin-top: 24px">
    <h2 style="margin: 0 0 16px; color: var(--ad-text)">项目看板</h2>
    <div class="board" v-loading="boardLoading">
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
            <el-empty v-if="!stageCards(col.key).length" description="暂无任务" :image-size="56" />
            <TaskBoardCard
              v-for="task in stageCards(col.key)"
              :key="task.id"
              :task="task"
              @open="handleTaskCardClick(task)"
            />
          </template>
        </div>
      </div>
    </div>
  </div>

</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import { getDashboard, getTaskCompletionSummary } from '@/api/payments'
import { getProjectQueueOrders } from '@/api/orders'
import { getCompletedProjects, getTaskQueue } from '@/api/tasks'
import { getQuotes } from '@/api/quotes'
import type {
  CustomerDebtItem,
  OrderListResponse,
  QuoteListResponse,
  TaskCompletionPeriod,
  TaskCompletionSummary,
  TaskCompletionType,
  TaskQueueItem,
  CompletedProjectCard as CompletedProjectCardType,
} from '@/types/api'
import TaskBoardCard from '@/components/ui/TaskBoardCard.vue'
import CompletedProjectCard from '@/components/ui/CompletedProjectCard.vue'
import ProjectQueueCard from '@/components/ui/ProjectQueueCard.vue'
import { isTaskVisible, TASK_BOARD_COLUMNS } from '@/utils/task-board'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const canViewFinancial = computed(() => authStore.hasPermission('report:view_financial'))
const canViewPricedOrders = computed(() => (
  authStore.canAll(['order:read', 'order:view_price'])
))
const canViewProjectQueue = computed(() => authStore.can('order:read'))
const canViewTaskCompletion = computed(() => authStore.can('task_completion:read'))
const canViewCompletionAll = computed(() => authStore.can('task_completion:view_all'))

const loading = ref(false)
const data = reactive({
  today_order_amount: 0, today_payment_amount: 0,
  month_order_amount: 0, month_payment_amount: 0,
  month_unpaid_amount: 0,
  pending_design_count: 0, pending_production_count: 0, pending_installation_count: 0,
  customer_debt_ranking: [] as CustomerDebtItem[],
})

const quoteList = ref<QuoteListResponse[]>([])

const completionPeriod = ref<TaskCompletionPeriod>('month')
const completionSummary = ref<TaskCompletionSummary | null>(null)
const completionLoading = ref(false)
const completionError = ref('')
const completionStages: Array<{ key: TaskCompletionType; label: string }> = [
  { key: 'design', label: '设计' },
  { key: 'production', label: '制作' },
  { key: 'installation', label: '安装' },
]
const completionEntryStats = computed(() => (
  canViewCompletionAll.value
    ? completionSummary.value?.organization
    : completionSummary.value?.own
))

const boardLoading = ref(false)
const projectQueueOrders = ref<OrderListResponse[]>([])
const taskCards = ref<TaskQueueItem[]>([])
const completedProjects = ref<CompletedProjectCardType[]>([])
const router = useRouter()

const columns = [
  { key: 'queue', label: '项目队列' },
  ...TASK_BOARD_COLUMNS,
  { key: 'completed', label: '完成' },
] as const

const visibleColumns = computed(() => columns.filter(col => (
  (col.key !== 'queue' || canViewProjectQueue.value)
  && (col.key !== 'completed' || canViewTaskCompletion.value)
)))

type BoardColumnKey = (typeof columns)[number]['key']

function queueCards() {
  return projectQueueOrders.value
}

function stageCards(stage: string) {
  return taskCards.value.filter(task => task.stage === stage && isTaskVisible(task))
}

function columnCount(columnKey: BoardColumnKey) {
  if (columnKey === 'queue') return queueCards().length
  if (columnKey === 'completed') return completedProjects.value.length
  return stageCards(columnKey).length
}

async function fetchBoardData() {
  boardLoading.value = true
  try {
    const emptyCompleted = { items: [] as CompletedProjectCardType[], total: 0, page: 1, page_size: 200 }
    const [orders, tasks, completed] = await Promise.all([
      canViewProjectQueue.value
        ? getProjectQueueOrders().catch(() => [] as OrderListResponse[])
        : Promise.resolve([] as OrderListResponse[]),
      getTaskQueue({ page: 1, page_size: 200 }).catch(() => ({ items: [] as TaskQueueItem[] })),
      canViewTaskCompletion.value
        ? getCompletedProjects({ page: 1, page_size: 200 }).catch(() => emptyCompleted)
        : Promise.resolve(emptyCompleted),
    ])
    projectQueueOrders.value = orders
    taskCards.value = tasks.items
    completedProjects.value = completed.items
  } finally { boardLoading.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const d = await getDashboard()
    Object.assign(data, d)
  } finally { loading.value = false }
}

async function fetchCompletionSummary() {
  completionLoading.value = true
  try {
    completionSummary.value = await getTaskCompletionSummary(completionPeriod.value)
  } catch {
    completionError.value = '完成统计暂时无法加载，请稍后重试'
  } finally {
    completionLoading.value = false
  }
}

async function fetchTaskCompletion() {
  if (!canViewTaskCompletion.value) return
  completionError.value = ''
  await fetchCompletionSummary()
}

function handleCompletionPeriodChange() {
  fetchTaskCompletion()
}

function handleCompletionStatsClick() {
  router.push({
    name: 'TaskCompletionStats',
    query: { period: completionPeriod.value },
  })
}

async function fetchQuotes() {
  if (!canViewPricedOrders.value) {
    quoteList.value = []
    return
  }
  try {
    const r = await getQuotes({ page_size: 5 })
    quoteList.value = r.items || []
  } catch { /* 报价单拉取失败不阻塞驾驶舱 */ }
}

function quoteStatusLabel(s: string) {
  const map: Record<string, string> = { draft: '草稿', confirmed: '已确认', converted: '已转订单', cancelled: '已作废' }
  return map[s] || s
}

function quoteStatusColor(s: string) {
  const map: Record<string, string> = { draft: 'info', confirmed: 'success', converted: 'primary', cancelled: 'danger' }
  return map[s] || 'info'
}

function goQuote(item: QuoteListResponse) {
  window.location.href = `/quotes/${item.id}/edit`
}

function handleOrderCardClick(card: OrderListResponse) {
  window.location.href = '/orders/' + card.id
}

function handleTaskCardClick(task: TaskQueueItem) {
  const routeByType: Record<TaskQueueItem['task_type'], string> = {
    design: '/design-tasks/',
    production: '/production-tasks/',
    installation: '/installation-tasks/',
  }
  window.location.href = routeByType[task.task_type] + task.id
}

function handleCompletedProjectClick(project: CompletedProjectCardType) {
  router.push({ name: 'CompletedProjectDetail', params: { projectId: project.project_id } })
}

// 从详情页返回时浏览器可能走 bfcache 恢复页面（onMounted 不再触发），
// 需要监听 pageshow 在恢复时重新拉取看板数据，避免删除任务后卡片仍显示旧数据。
function handlePageShow(e: PageTransitionEvent) {
  if (e.persisted) {
    fetchBoardData()
  }
}

onMounted(() => {
  fetchData()
  fetchQuotes()
  fetchBoardData()
  fetchTaskCompletion()
  window.addEventListener('pageshow', handlePageShow)
})

onBeforeUnmount(() => {
  window.removeEventListener('pageshow', handlePageShow)
})
</script>

<style scoped>
.page { padding: 0; }
.board { display: flex; gap: 12px; overflow-x: auto; min-height: 40vh; }
.board-column { flex: 1; min-width: 200px; background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 6px; display: flex; flex-direction: column; }
.column-header { padding: 12px; font-weight: bold; font-size: 16px; color: var(--ad-text); border-bottom: 1px solid var(--ad-border); display: flex; justify-content: center; gap: 8px; align-items: center; }
.column-body { padding: 8px; flex: 1; overflow-y: auto; }
.board-card { margin-bottom: 8px; cursor: pointer; background: var(--ad-card); border: 1px solid var(--ad-border); }
.card-meta { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-top: 8px; font-size: 12px; color: #888; }
.stat-card { background: var(--ad-card); border: 1px solid var(--ad-border); text-align: center; padding: 18px 12px; border-radius: 10px; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 10px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.stat-value.is-success { color: #16a34a; }
.stat-value.is-danger { color: #dc2626; }
.task-card .stat-value { font-size: 30px; margin-top: 4px; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.completion-card { margin-bottom: 16px; background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.completion-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.completion-title { font-size: 16px; font-weight: 700; margin-right: 10px; }
.completion-alert { margin-bottom: 12px; }
.completion-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
.completion-kpi { min-height: 82px; padding: 14px 16px; border: 1px solid var(--ad-border); border-radius: 8px; background: color-mix(in srgb, var(--ad-card) 88%, var(--ad-primary) 12%); }
.completion-kpi-label { display: block; color: var(--ad-text-secondary); font-size: 13px; margin-bottom: 8px; }
.completion-kpi strong { color: var(--ad-text); font-size: 26px; line-height: 1; }
.completion-kpi--stages { min-width: 0; }
.stage-counts { display: flex; flex-wrap: wrap; gap: 6px 12px; color: var(--ad-text); font-size: 13px; }
.completion-entry-card { width: 100%; display: flex; align-items: center; gap: 12px; padding: 14px 16px; border: 1px solid var(--ad-border); border-radius: 10px; background: color-mix(in srgb, var(--ad-card) 92%, var(--ad-primary) 8%); color: var(--ad-text); text-align: left; cursor: pointer; font: inherit; transition: border-color 0.2s ease, background 0.2s ease; }
.completion-entry-card:hover,
.completion-entry-card:focus-visible { border-color: var(--ad-primary); background: color-mix(in srgb, var(--ad-card) 86%, var(--ad-primary) 14%); outline: none; }
.completion-entry-icon { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; flex: 0 0 34px; border-radius: 50%; background: var(--ad-primary); color: #fff; font-size: 18px; font-weight: 700; }
.completion-entry-content { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 5px; }
.completion-entry-heading { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.completion-entry-title { font-size: 15px; font-weight: 700; }
.completion-entry-action { color: var(--ad-primary); font-size: 12px; }
.completion-entry-summary { color: var(--ad-text); font-size: 13px; font-weight: 600; }
.completion-entry-stages { display: flex; flex-wrap: wrap; gap: 6px 14px; color: var(--ad-text-secondary); font-size: 12px; }
.completion-entry-unassigned { color: var(--ad-text-secondary); }
.completion-entry-arrow { flex: 0 0 auto; color: var(--ad-primary); font-size: 18px; }
.debt-row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--ad-border); }
.quote-row { cursor: pointer; }
.quote-row:hover { background: var(--ad-border); }
.quote-status { width: 60px; justify-content: center; margin-right: 12px; flex-shrink: 0; }
.quote-sub { font-size: 12px; color: var(--ad-text-secondary); }
.quote-col { flex: 1; min-width: 0; }
.quote-no-customer { flex: 1.2; }
.quote-no { color: var(--ad-text); font-size: 14px; }
.quote-project-col { flex: 1.6; font-size: 13px; color: var(--ad-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.debt-rank { width: 28px; height: 28px; background: #e63946; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; font-size: 16px; margin-right: 12px; }
.debt-name { flex: 1; color: var(--ad-text); }
.debt-amount { font-weight: bold; font-size: 16px; color: #e63946; }

@media (max-width: 1100px) {
  .completion-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 720px) {
  .completion-header { align-items: flex-start; flex-direction: column; }
  .completion-kpis { grid-template-columns: 1fr 1fr; }
 }
</style>
