<template>
  <div class="page">
    <div class="page-header">
      <div class="page-header-main">
        <el-button text class="back-button" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回工作台
        </el-button>
        <h2>完成统计</h2>
        <p>查看设计、制作、安装各阶段的完成项目和工作明细。</p>
      </div>
      <div class="page-header-actions">
        <span class="filter-label">统计范围</span>
        <el-radio-group v-model="period" size="small" @change="handlePeriodChange">
          <el-radio-button label="month">当月</el-radio-button>
          <el-radio-button label="all">全部</el-radio-button>
        </el-radio-group>
        <el-button :loading="summaryLoading || detailsLoading" @click="fetchData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="summaryError"
      type="warning"
      :closable="false"
      show-icon
      class="page-alert"
    >
      <span>{{ summaryError }}</span>
      <el-button link type="warning" size="small" @click="fetchData">重试</el-button>
    </el-alert>

    <el-card shadow="never" class="info-card" v-loading="summaryLoading">
      <template #header>
        <div class="card-header">
          <span>完成概览</span>
          <el-tag v-if="summary" size="small" type="info" effect="plain">
            {{ summary.scope === 'all' ? '全员可见' : '仅本人' }}
          </el-tag>
        </div>
      </template>

      <el-alert
        v-if="summary?.message"
        :title="summary.message"
        type="info"
        :closable="false"
        show-icon
        class="page-alert"
      />

      <template v-if="summary">
        <div class="period-note">统计范围：{{ periodLabel }}<span v-if="summary.period_start">（{{ summary.period_start }} 至 {{ summary.period_end || '现在' }}）</span></div>
        <el-row :gutter="12" class="stat-grid">
          <el-col :xs="12" :sm="6">
            <div class="stat-card">
              <span>{{ canViewAll ? '整单完成项目' : '我完成的项目' }}</span>
              <strong>{{ canViewAll ? summary.organization?.completed_order_project_count || 0 : summary.own.completed_project_count }}</strong>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="stat-card">
              <span>{{ canViewAll ? '最终交付明细' : '我完成的明细' }}</span>
              <strong>{{ canViewAll ? summary.organization?.completed_detail_count || 0 : summary.own.completed_work_unit_count }}</strong>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="stat-card">
              <span>{{ canViewAll ? '完成工作明细' : '我的工作明细' }}</span>
              <strong>{{ activeStats?.completed_work_unit_count || 0 }}</strong>
            </div>
          </el-col>
          <el-col :xs="12" :sm="6">
            <div class="stat-card stat-card--stages">
              <span>阶段完成明细</span>
              <div class="stage-counts">
                <span v-for="stage in stages" :key="stage.key">{{ stage.label }} {{ activeStats?.stage_breakdown?.[stage.key] || 0 }}</span>
              </div>
            </div>
          </el-col>
        </el-row>
      </template>
    </el-card>

    <el-card v-if="canViewAll && summary" shadow="never" class="info-card">
      <template #header>
        <div class="card-header">
          <span>员工完成统计</span>
          <span class="card-hint">点击员工查看该员工的完成明细</span>
        </div>
      </template>
      <el-table
        :data="summary.employees"
        stripe
        size="small"
        highlight-current-row
        row-key="employee_id"
        @row-click="handleEmployeeRowClick"
      >
        <el-table-column label="员工" min-width="160">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <el-tag v-if="!row.is_active" size="small" type="info" effect="plain" class="inactive-tag">非在职</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="completed_project_count" label="完成项目" width="110" align="right" />
        <el-table-column prop="completed_work_unit_count" label="完成工作明细" width="130" align="right" />
        <el-table-column label="设计" width="90" align="right">
          <template #default="{ row }">{{ row.stage_breakdown.design || 0 }}</template>
        </el-table-column>
        <el-table-column label="制作" width="90" align="right">
          <template #default="{ row }">{{ row.stage_breakdown.production || 0 }}</template>
        </el-table-column>
        <el-table-column label="安装" width="90" align="right">
          <template #default="{ row }">{{ row.stage_breakdown.installation || 0 }}</template>
        </el-table-column>
      </el-table>
      <div v-if="summary.unassigned.completed_work_unit_count" class="unassigned-note">
        未分配：{{ summary.unassigned.completed_work_unit_count }} 条（不归属到任何员工）
      </div>
      <div v-if="!summary.employees.length" class="empty-inline">当前范围暂无已绑定员工的完成记录</div>
    </el-card>

    <el-card v-if="summary" shadow="never" class="info-card detail-card" v-loading="detailsLoading">
      <template #header>
        <div class="card-header detail-header">
          <div>
            <span>{{ selectedEmployeeName ? `${selectedEmployeeName}的完成明细` : (canViewAll ? '全员完成明细' : '我的完成明细') }}</span>
            <span v-if="selectedEmployeeName" class="selected-filter">已按员工筛选</span>
          </div>
          <div class="detail-filters">
            <el-radio-group v-model="kind" size="small" @change="handleDetailsFilterChange">
              <el-radio-button label="detail">按明细</el-radio-button>
              <el-radio-button label="project">按项目</el-radio-button>
            </el-radio-group>
            <el-select
              v-if="canViewAll"
              v-model="selectedEmployeeId"
              clearable
              size="small"
              placeholder="全部员工"
              class="employee-select"
              @change="handleDetailsFilterChange"
            >
              <el-option label="全部员工" value="" />
              <el-option
                v-for="employee in summary.employees"
                :key="employee.employee_id || employee.user_id || employee.name"
                :label="employee.name"
                :value="employee.employee_id || ''"
              />
            </el-select>
            <el-select v-model="taskType" size="small" class="stage-select" @change="handleDetailsFilterChange">
              <el-option label="全部阶段" value="" />
              <el-option v-for="stage in stages" :key="stage.key" :label="stage.label" :value="stage.key" />
            </el-select>
          </div>
        </div>
      </template>

      <el-alert
        v-if="detailsError"
        type="warning"
        :closable="false"
        show-icon
        class="page-alert"
      >
        <span>{{ detailsError }}</span>
        <el-button link type="warning" size="small" @click="fetchDetails">重试</el-button>
      </el-alert>

      <el-table v-if="kind === 'detail'" :data="detailRows" stripe size="small">
        <el-table-column prop="project_no" label="订单编号" width="180" />
        <el-table-column prop="project_name" label="项目名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="item_name" label="订单明细" min-width="150" show-overflow-tooltip />
        <el-table-column label="阶段" width="90">
          <template #default="{ row }">{{ stageLabel(row.task_type) }}</template>
        </el-table-column>
        <el-table-column prop="task_no" label="任务编号" width="180" />
        <el-table-column prop="employee_name" label="完成执行人" width="120" />
        <el-table-column label="完成时间" width="120">
          <template #default="{ row }">{{ formatDate(row.completed_at) }}</template>
        </el-table-column>
      </el-table>

      <el-table v-else :data="projectRows" stripe size="small">
        <el-table-column prop="project_no" label="订单编号" width="180" />
        <el-table-column prop="project_name" label="项目名称" min-width="240" show-overflow-tooltip />
        <el-table-column prop="completed_detail_count" label="完成明细" width="110" align="right" />
        <el-table-column prop="completed_work_unit_count" label="完成工作数" width="120" align="right" />
        <el-table-column label="完成阶段" min-width="150">
          <template #default="{ row }">
            <span class="stage-tags">
              <el-tag v-for="stage in row.stages" :key="stage" size="small" type="success" effect="plain">{{ stageLabel(stage) }}</el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最后完成时间" width="140">
          <template #default="{ row }">{{ formatDate(row.last_completed_at) }}</template>
        </el-table-column>
      </el-table>

      <div v-if="!detailsLoading && !detailsError && !details?.items.length" class="empty-inline">当前筛选条件下暂无完成记录</div>
      <div v-if="details && details.total > pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="details.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { getTaskCompletionDetails, getTaskCompletionSummary } from '@/api/payments'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/datetime'
import type {
  TaskCompletionDetailRow,
  TaskCompletionDetailsResponse,
  TaskCompletionKind,
  TaskCompletionPeriod,
  TaskCompletionProjectRow,
  TaskCompletionStats,
  TaskCompletionSummary,
  TaskCompletionType,
} from '@/types/api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const period = ref<TaskCompletionPeriod>(route.query.period === 'all' ? 'all' : 'month')
const kind = ref<TaskCompletionKind>('detail')
const taskType = ref<TaskCompletionType | ''>('')
const selectedEmployeeId = ref('')
const page = ref(1)
const pageSize = 20

const summary = ref<TaskCompletionSummary | null>(null)
const details = ref<TaskCompletionDetailsResponse | null>(null)
const summaryLoading = ref(false)
const detailsLoading = ref(false)
const summaryError = ref('')
const detailsError = ref('')

const stages: Array<{ key: TaskCompletionType; label: string }> = [
  { key: 'design', label: '设计' },
  { key: 'production', label: '制作' },
  { key: 'installation', label: '安装' },
]

const canViewAll = computed(() => authStore.canAll(['task_completion:read', 'task_completion:view_all']))
const activeStats = computed<TaskCompletionStats | null>(() => {
  if (!summary.value) return null
  return canViewAll.value ? summary.value.organization : summary.value.own
})
const periodLabel = computed(() => period.value === 'all' ? '全部' : '当月')
const selectedEmployeeName = computed(() => {
  if (!selectedEmployeeId.value || !summary.value) return ''
  return summary.value.employees.find(employee => employee.employee_id === selectedEmployeeId.value)?.name || ''
})
const detailRows = computed<TaskCompletionDetailRow[]>(() => (
  details.value?.items.filter((row): row is TaskCompletionDetailRow => row.kind === 'detail') || []
))
const projectRows = computed<TaskCompletionProjectRow[]>(() => (
  details.value?.items.filter((row): row is TaskCompletionProjectRow => row.kind === 'project') || []
))

function stageLabel(type: TaskCompletionType) {
  return stages.find(stage => stage.key === type)?.label || type
}

async function fetchSummary() {
  summaryLoading.value = true
  summaryError.value = ''
  try {
    summary.value = await getTaskCompletionSummary(period.value)
  } catch {
    summary.value = null
    summaryError.value = '完成统计暂时无法加载，请稍后重试'
  } finally {
    summaryLoading.value = false
  }
}

async function fetchDetails() {
  detailsLoading.value = true
  detailsError.value = ''
  try {
    details.value = await getTaskCompletionDetails({
      period: period.value,
      kind: kind.value,
      employee_id: canViewAll.value ? (selectedEmployeeId.value || undefined) : undefined,
      task_type: taskType.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
  } catch {
    details.value = null
    detailsError.value = '完成明细暂时无法加载，请稍后重试'
  } finally {
    detailsLoading.value = false
  }
}

async function fetchData() {
  await Promise.all([fetchSummary(), fetchDetails()])
}

async function handlePeriodChange() {
  page.value = 1
  await router.replace({ name: 'TaskCompletionStats', query: { period: period.value } })
  await fetchData()
}

function handleDetailsFilterChange() {
  page.value = 1
  void fetchDetails()
}

function handleEmployeeRowClick(row: { employee_id: string | null }) {
  if (!row.employee_id) return
  selectedEmployeeId.value = row.employee_id
  handleDetailsFilterChange()
}

function handlePageChange(nextPage: number) {
  page.value = nextPage
  void fetchDetails()
}

function goBack() {
  router.push({ name: 'Home' })
}

onMounted(() => {
  void fetchData()
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.page-header-main { min-width: 0; }
.back-button { padding-left: 0; color: var(--ad-text-secondary); }
.page-header h2 { margin: 4px 0 4px; color: var(--ad-text); }
.page-header p { margin: 0; color: var(--ad-text-secondary); font-size: 13px; }
.page-header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.filter-label { color: var(--ad-text-secondary); font-size: 13px; }
.page-alert { margin-bottom: 12px; }
.info-card { margin-bottom: 16px; background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--ad-text); font-weight: 700; }
.card-hint,
.period-note,
.selected-filter { color: var(--ad-text-secondary); font-size: 12px; font-weight: 400; }
.period-note { margin-bottom: 12px; }
.stat-grid { margin-bottom: 0; }
.stat-card { min-height: 82px; padding: 14px 16px; border: 1px solid var(--ad-border); border-radius: 8px; background: color-mix(in srgb, var(--ad-card) 88%, var(--ad-primary) 12%); }
.stat-card > span { display: block; margin-bottom: 8px; color: var(--ad-text-secondary); font-size: 13px; }
.stat-card strong { color: var(--ad-text); font-size: 26px; line-height: 1; }
.stat-card--stages { min-height: 82px; }
.stage-counts { display: flex; flex-wrap: wrap; gap: 6px 12px; color: var(--ad-text); font-size: 13px; }
.inactive-tag { margin-left: 6px; }
.unassigned-note { margin-top: 12px; color: var(--ad-text-secondary); font-size: 12px; }
.empty-inline { padding: 24px 12px; color: var(--ad-text-secondary); text-align: center; }
.detail-card { overflow: hidden; }
.detail-header { align-items: flex-start; }
.detail-header > div:first-child { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
.detail-filters { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
.employee-select { width: 140px; }
.stage-select { width: 110px; }
.stage-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }

@media (max-width: 760px) {
  .page-header,
  .detail-header { flex-direction: column; }
  .page-header-actions,
  .detail-filters { width: 100%; justify-content: flex-start; }
  .detail-filters .el-radio-group { order: -1; }
  .card-hint { display: none; }
}
</style>
