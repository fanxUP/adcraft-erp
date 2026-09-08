<template>
  <div class="page" v-loading="loading">
    <h1 style="margin: 0 0 24px; color: var(--ad-text)">经营驾驶舱</h1>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日订单金额</div>
          <div class="stat-value">¥ {{ data.today_order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日收款金额</div>
          <div class="stat-value is-success">¥ {{ data.today_payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月订单金额</div>
          <div class="stat-value">¥ {{ data.month_order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月收款金额</div>
          <div class="stat-value is-success">¥ {{ data.month_payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
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

    <el-row :gutter="16">
      <el-col :span="12">
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
      <el-col :span="12">
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
      <div v-for="col in columns" :key="col.key" class="board-column">
        <div class="column-header">
          <span>{{ col.label }}</span>
          <el-tag size="small" type="danger">{{ columnCount(col.key) }}</el-tag>
        </div>
        <div class="column-body">
          <template v-if="col.key === 'queue'">
            <el-empty v-if="!queueCards().length" description="暂无项目" :image-size="56" />
            <el-card
              v-for="card in queueCards()"
              :key="card.id"
              shadow="hover"
              class="board-card"
              @click="handleOrderCardClick(card)"
            >
              <div class="card-no">{{ card.order_no }}</div>
              <div class="card-name">{{ card.project_name }}</div>
              <div class="card-meta">
                <span>{{ card.customer_name || '-' }}</span>
                <span>¥{{ card.total_amount?.toFixed(2) }}</span>
              </div>
            </el-card>
          </template>

          <template v-else>
            <el-empty v-if="!stageCards(col.key).length" description="暂无任务" :image-size="56" />
            <el-card
              v-for="task in stageCards(col.key)"
              :key="task.id"
              shadow="hover"
              class="board-card"
              @click="handleTaskCardClick(task)"
            >
              <div class="card-topline">
                <span class="card-no">{{ task.task_no }}</span>
                <div class="card-statuses">
                  <el-tag v-if="task.is_overdue" size="small" type="danger">逾期</el-tag>
                  <el-tag size="small" :type="statusColor(task.status)">{{ statusLabel(task) }}</el-tag>
                </div>
              </div>
              <div class="card-name">{{ task.project_name }}</div>
              <div class="card-item">明细：{{ task.item_name || '整单任务' }}</div>
              <div class="card-meta">
                <span>{{ task.order_no || '-' }}</span>
                <span>{{ task.customer_name || '-' }}</span>
              </div>
              <div class="card-progress">
                <div class="card-progress-header">
                  <span>任务进度</span>
                  <strong>{{ taskProgress(task) }}%</strong>
                </div>
                <el-progress
                  :percentage="taskProgress(task)"
                  :stroke-width="8"
                  :show-text="false"
                  :color="taskProgressColor(task.stage)"
                />
              </div>
              <div v-if="task.planned_end_at" class="planned-end">计划结束：{{ formatDateTimeFull(task.planned_end_at) }}</div>
              <div v-if="task.assigned_to_name" class="assignee">负责人：{{ task.assigned_to_name }}</div>
            </el-card>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { getDashboard } from '@/api/payments'
import { getOrders } from '@/api/orders'
import { getTaskQueue } from '@/api/tasks'
import { getQuotes } from '@/api/quotes'
import type { CustomerDebtItem, OrderListResponse, QuoteListResponse, TaskQueueItem } from '@/types/api'
import { formatDateTimeFull } from '@/utils/datetime'
import { isTaskVisible, TASK_BOARD_COLUMNS, taskProgress, taskProgressColor } from '@/utils/task-board'

const loading = ref(false)
const data = reactive({
  today_order_amount: 0, today_payment_amount: 0,
  month_order_amount: 0, month_payment_amount: 0,
  month_unpaid_amount: 0,
  pending_design_count: 0, pending_production_count: 0, pending_installation_count: 0,
  customer_debt_ranking: [] as CustomerDebtItem[],
})

const quoteList = ref<QuoteListResponse[]>([])

const boardLoading = ref(false)
const allProjects = ref<OrderListResponse[]>([])
const taskCards = ref<TaskQueueItem[]>([])

const columns = [
  { key: 'queue', label: '项目队列' },
  ...TASK_BOARD_COLUMNS,
] as const

type BoardColumnKey = (typeof columns)[number]['key']

function queueCards() {
  return allProjects.value.filter(project => ['pending_confirm', 'confirmed'].includes(project.status))
}

function stageCards(stage: string) {
  return taskCards.value.filter(task => task.stage === stage && isTaskVisible(task))
}

function columnCount(columnKey: BoardColumnKey) {
  return columnKey === 'queue' ? queueCards().length : stageCards(columnKey).length
}

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
    pending_acceptance: '待处理',
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

async function fetchBoardData() {
  boardLoading.value = true
  try {
    const [orders, tasks] = await Promise.all([
      getOrders({ page_size: 100 }),
      getTaskQueue({ page: 1, page_size: 200 }).catch(() => ({ items: [] as TaskQueueItem[] })),
    ])
    allProjects.value = orders.items
    taskCards.value = tasks.items
  } finally { boardLoading.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const d = await getDashboard()
    Object.assign(data, d)
  } finally { loading.value = false }
}

async function fetchQuotes() {
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
.board-card:hover { border-color: #e63946; }
.card-topline { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-statuses { display: flex; align-items: center; gap: 4px; }
.card-no { font-size: 12px; color: #888; }
.card-name { font-weight: bold; font-size: 16px; color: var(--ad-text); margin: 4px 0; }
.card-item { margin-bottom: 6px; color: var(--ad-primary, #409eff); font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-top: 8px; font-size: 12px; color: #888; }
.card-progress { margin-top: 12px; }
.card-progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; color: var(--ad-text-secondary); font-size: 12px; }
.card-progress-header strong { color: var(--ad-text); font-weight: 600; }
.planned-end { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); }
.assignee { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); }
.stat-card { background: var(--ad-card); border: 1px solid var(--ad-border); text-align: center; padding: 18px 12px; border-radius: 10px; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 10px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.stat-value.is-success { color: #16a34a; }
.stat-value.is-danger { color: #dc2626; }
.task-card .stat-value { font-size: 30px; margin-top: 4px; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
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
</style>
