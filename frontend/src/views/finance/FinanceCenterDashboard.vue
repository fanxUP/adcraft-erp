<template>
  <AppPage>
    <template #header>
      <PageHeader
        title="财务总览"
        description="按实际收款日和付款日查看资金变动；没有可靠日期的历史金额单独列示。"
      >
        <template #actions>
          <el-button v-if="canReadReceipts" @click="goTo('/receivables')">客户收款</el-button>
          <el-button v-if="canReadDisbursements" @click="goToExpense('expense')">登记经营支出</el-button>
          <el-button v-if="canReadDisbursements" type="primary" @click="goToExpense('disbursements')">
            查看付款流水
          </el-button>
        </template>
      </PageHeader>
    </template>

    <template #toolbar>
      <div class="finance-toolbar">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :clearable="false"
          unlink-panels
          aria-label="选择收付款统计期间"
          @change="fetchSummary"
        />
        <span class="finance-toolbar-note">只按实际登记的收款/付款日期计入所选期间</span>
      </div>
    </template>

    <el-alert
      v-if="!canReadReceipts || !canReadDisbursements"
      class="finance-alert"
      type="info"
      :closable="false"
      show-icon
      title="当前账号仅能查看有权限的数据模块；未授权部分不会计入净收支。"
    />
    <el-alert
      v-if="canReadDisbursements && expenditureData && !expenditureData.available_sources.includes('outsource')"
      class="finance-alert"
      type="warning"
      :closable="false"
      show-icon
      title="当前付款统计未包含外协付款来源，因此不显示整体净收支。"
    />

    <el-tabs v-model="activeSection" class="finance-tabs" aria-label="财务总览内容">
      <el-tab-pane label="期间收支" name="cashflow">
        <div class="finance-summary-grid">
          <el-card v-if="canReadReceipts" shadow="never" class="finance-summary-card">
            <div class="finance-card-label">本期实际收款</div>
            <div class="finance-card-value">{{ receiptData ? formatMoney(receiptData.period.amount) : '—' }}</div>
            <div class="finance-card-detail">
              {{ receiptLoading ? '读取中…' : receiptData ? `${receiptData.period.count} 笔收款` : receiptError ? '读取失败' : '暂无数据' }}
            </div>
          </el-card>

          <el-card v-if="canReadDisbursements" shadow="never" class="finance-summary-card">
            <div class="finance-card-label">本期有日期付款</div>
            <div class="finance-card-value">
              {{ expenditureData ? formatMoney(expenditureData.summary.confirmed_paid_amount ?? 0) : '—' }}
            </div>
            <div class="finance-card-detail">
              {{ expenditureLoading ? '读取中…' : expenditureData ? `${expenditureData.total} 笔付款 · 当前可见来源` : expenditureError ? '读取失败' : '暂无数据' }}
            </div>
          </el-card>

          <el-card v-if="canShowNet" shadow="never" class="finance-summary-card finance-net-card">
            <div class="finance-card-label">本期净收支（收款 − 付款）</div>
            <div class="finance-card-value" :class="netAmount >= 0 ? 'is-positive' : 'is-negative'">
              {{ formatMoney(netAmount) }}
            </div>
            <div class="finance-card-detail">收款与全部可见付款来源均已加载</div>
          </el-card>
        </div>

        <div class="finance-undated-grid">
          <el-card v-if="canReadReceipts" shadow="never" class="finance-undated-card">
            <div class="finance-undated-heading">
              <span>收款日期待核实</span>
              <el-tag type="warning" effect="plain" size="small">不计入本期</el-tag>
            </div>
            <div class="finance-undated-value">{{ receiptData ? formatMoney(receiptData.undated.amount) : '—' }}</div>
            <p>{{ receiptLoading ? '读取中…' : receiptData ? `${receiptData.undated.count} 笔历史收款 · 全部历史累计，不受所选期间影响` : receiptError ? '读取失败，请重试' : '暂无数据' }}</p>
          </el-card>

          <el-card v-if="canReadDisbursements" shadow="never" class="finance-undated-card">
            <div class="finance-undated-heading">
              <span>付款日期待核实</span>
              <el-tag type="warning" effect="plain" size="small">不计入本期</el-tag>
            </div>
            <div class="finance-undated-value">
              {{ expenditureData ? formatMoney(expenditureData.summary.unverified_paid_amount ?? 0) : '—' }}
            </div>
            <p>{{ expenditureLoading ? '读取中…' : expenditureData ? `${expenditureData.summary.unverified_count ?? 0} 笔历史付款 · 全部历史累计，不受所选期间影响` : expenditureError ? '读取失败，请重试' : '暂无数据' }}</p>
          </el-card>
        </div>

        <el-alert
          class="finance-policy-note"
          type="info"
          :closable="false"
          show-icon
          title="日期口径：不会用业务日期或系统创建时间推测收付款日期。核对凭证后，应在原业务记录补全或更正日期；不要重复登记一笔收付款。"
        />
        <div v-if="summaryError" class="finance-retry-row">
          <span>部分汇总暂时无法读取。</span>
          <el-button link type="primary" @click="fetchSummary">重试</el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="疑似重复成本" name="overlaps">
        <el-alert
          class="finance-policy-note"
          type="warning"
          :closable="false"
          show-icon
          title="这里仅列出人工项目成本与已完成外协任务的高相似候选。命中规则不代表重复，不会自动合并、删除或改账，请结合合同、任务和凭证逐笔核实。"
        />

        <div v-if="!canReviewOverlaps" class="finance-permission-note">
          查看候选需同时具备成本查看、外协任务及供应商读取权限。
        </div>
        <template v-else>
          <el-alert
            v-if="overlapError"
            class="finance-alert"
            type="error"
            :closable="false"
            title="疑似重复成本暂时无法读取。"
          >
            <el-button link type="primary" @click="fetchOverlaps">重试</el-button>
          </el-alert>
          <el-table
            :data="overlapItems"
            v-loading="overlapLoading"
            row-key="row_key"
            stripe
            empty-text="没有命中当前核查规则的候选记录"
          >
            <el-table-column prop="document_no" label="业务单号" width="150" />
            <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="supplier_name" label="供应商" min-width="150" show-overflow-tooltip />
            <el-table-column prop="cost_no" label="项目成本编号" width="160" />
            <el-table-column prop="category" label="成本分类" width="110" />
            <el-table-column label="项目成本金额" width="140" align="right">
              <template #default="{ row }">{{ formatMoney(row.cost_amount) }}</template>
            </el-table-column>
            <el-table-column prop="task_no" label="外协任务编号" width="165" />
            <el-table-column label="任务金额" width="130" align="right">
              <template #default="{ row }">{{ formatMoney(row.task_amount) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="115">
              <template #default="{ row }">
                <el-tag type="warning" effect="plain" size="small">{{ row.review_status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="overlapTotal > overlapPageSize"
            v-model:current-page="overlapPage"
            :page-size="overlapPageSize"
            :total="overlapTotal"
            layout="total, prev, pager, next"
            class="finance-pagination"
            @current-change="fetchOverlaps"
          />
        </template>
      </el-tab-pane>
    </el-tabs>
  </AppPage>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { AppPage, PageHeader } from '@/components/ui'
import { getExpenditure, getFinanceCashflow, getFinanceCostOverlaps } from '@/api/payments'
import type {
  ExpenditureResult,
  FinanceCashflowSummary,
  FinanceCostOverlapCandidate,
} from '@/api/payments'
import { useAuthStore } from '@/stores/auth'
import { formatMoney } from '@/utils/format'

type DateRange = [string, string]

function localDateString(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const router = useRouter()
const authStore = useAuthStore()
const today = new Date()
const dateRange = ref<DateRange>([
  localDateString(new Date(today.getFullYear(), today.getMonth(), 1)),
  localDateString(today),
])
const activeSection = ref<'cashflow' | 'overlaps'>('cashflow')

const canReadReceipts = computed(() => authStore.can('payment:read'))
const canReadDisbursements = computed(() => authStore.can('expense:read'))
const canReviewOverlaps = computed(() => authStore.canAll([
  'finance:view_cost',
  'outsource_center:read',
  'outsource_task:read',
  'outsource_vendor:read',
]))

const receiptData = ref<FinanceCashflowSummary | null>(null)
const expenditureData = ref<ExpenditureResult | null>(null)
const receiptLoading = ref(false)
const expenditureLoading = ref(false)
const receiptError = ref(false)
const expenditureError = ref(false)
const summaryRequestId = ref(0)
const summaryError = computed(() => receiptError.value || expenditureError.value)

const canShowNet = computed(() =>
  canReadReceipts.value
  && canReadDisbursements.value
  && !!receiptData.value
  && !!expenditureData.value?.available_sources.includes('outsource'),
)
const netAmount = computed(() =>
  (receiptData.value?.period.amount ?? 0)
  - (expenditureData.value?.summary.confirmed_paid_amount ?? 0),
)

const overlapItems = ref<FinanceCostOverlapCandidate[]>([])
const overlapPage = ref(1)
const overlapPageSize = 20
const overlapTotal = ref(0)
const overlapLoading = ref(false)
const overlapError = ref(false)
let overlapRequestId = 0

function goTo(path: string) {
  void router.push(path)
}

function goToExpense(view: 'expense' | 'disbursements') {
  void router.push({ path: '/expenses', query: { view } })
}

async function fetchSummary() {
  if (!dateRange.value || dateRange.value[0] > dateRange.value[1]) return
  const requestId = ++summaryRequestId.value
  receiptData.value = null
  expenditureData.value = null
  receiptError.value = false
  expenditureError.value = false
  receiptLoading.value = canReadReceipts.value
  expenditureLoading.value = canReadDisbursements.value

  const [startDate, endDate] = dateRange.value
  const requests: Promise<void>[] = []
  if (canReadReceipts.value) {
    requests.push((async () => {
      try {
        const result = await getFinanceCashflow({ start_date: startDate, end_date: endDate })
        if (requestId === summaryRequestId.value) receiptData.value = result
      } catch {
        if (requestId === summaryRequestId.value) receiptError.value = true
      } finally {
        if (requestId === summaryRequestId.value) receiptLoading.value = false
      }
    })())
  }
  if (canReadDisbursements.value) {
    requests.push((async () => {
      try {
        const result = await getExpenditure('disbursements', {
          page: 1,
          page_size: 1,
          start_date: startDate,
          end_date: endDate,
        })
        if (requestId === summaryRequestId.value) expenditureData.value = result
      } catch {
        if (requestId === summaryRequestId.value) expenditureError.value = true
      } finally {
        if (requestId === summaryRequestId.value) expenditureLoading.value = false
      }
    })())
  }
  await Promise.all(requests)
}

async function fetchOverlaps() {
  if (!canReviewOverlaps.value) return
  const requestId = ++overlapRequestId
  overlapLoading.value = true
  overlapError.value = false
  overlapItems.value = []
  overlapTotal.value = 0
  try {
    const result = await getFinanceCostOverlaps({ page: overlapPage.value, page_size: overlapPageSize })
    if (requestId !== overlapRequestId) return
    overlapItems.value = result.items
    overlapTotal.value = result.total
  } catch {
    if (requestId === overlapRequestId) overlapError.value = true
  } finally {
    if (requestId === overlapRequestId) overlapLoading.value = false
  }
}

watch(activeSection, section => {
  if (section === 'overlaps') void fetchOverlaps()
})

onMounted(() => {
  void fetchSummary()
})
</script>

<style scoped>
.finance-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.finance-toolbar-note,
.finance-card-detail,
.finance-undated-card p {
  color: var(--ad-text-secondary, #667085);
  font-size: 13px;
}

.finance-alert,
.finance-policy-note {
  margin-bottom: 16px;
}

.finance-tabs {
  margin-top: 12px;
}

.finance-summary-grid,
.finance-undated-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.finance-summary-card,
.finance-undated-card {
  border-color: var(--ad-border, #e5e7eb);
  background: var(--ad-card, #fff);
}

.finance-card-label,
.finance-undated-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--ad-text-secondary, #667085);
  font-size: 14px;
}

.finance-card-value,
.finance-undated-value {
  margin-top: 10px;
  color: var(--ad-text, #101828);
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.finance-card-detail {
  margin-top: 8px;
}

.finance-net-card {
  background: var(--ad-success-soft, #f2fbf5);
}

.is-positive {
  color: var(--el-color-success);
}

.is-negative {
  color: var(--el-color-danger);
}

.finance-undated-card p {
  margin: 8px 0 0;
  line-height: 1.5;
}

.finance-permission-note,
.finance-retry-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ad-text-secondary, #667085);
  padding: 18px 0;
}

.finance-pagination {
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 640px) {
  .finance-toolbar :deep(.el-date-editor) {
    width: 100%;
  }

  .finance-tabs :deep(.el-tabs__nav-wrap) {
    width: 100%;
  }
}
</style>
