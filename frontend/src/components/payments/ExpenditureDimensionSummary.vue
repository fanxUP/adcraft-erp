<template>
  <section class="dimension-summary" aria-label="支出维度汇总">
    <PageToolbar aria-label="维度汇总筛选">
      <el-form inline class="summary-filters" @submit.prevent="search">
        <el-form-item label="付款日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            range-separator="至"
            @change="search"
          />
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="sourceType" clearable placeholder="全部有权查看的来源" aria-label="支出来源" @change="search">
            <el-option v-for="source in availableSources" :key="source" :label="sourceLabels[source]" :value="source" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="keyword" clearable maxlength="128" placeholder="单号、项目或收款方" aria-label="汇总关键词" @keyup.enter="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="search">搜索</el-button>
          <el-button @click="reset">重置</el-button>
          <el-button text :aria-expanded="showAdvancedFilters" @click="showAdvancedFilters = !showAdvancedFilters">
            {{ showAdvancedFilters ? '收起筛选' : '更多筛选' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-collapse-transition>
        <el-form v-if="showAdvancedFilters" inline class="summary-filters summary-advanced-filters" @submit.prevent="search">
          <el-form-item label="项目">
            <el-input v-model="dimensionFilters.project_keyword" clearable maxlength="128" placeholder="项目名称或单据编号" @keyup.enter="search" />
          </el-form-item>
          <el-form-item label="部门/科室">
            <el-input v-model="dimensionFilters.department_keyword" clearable maxlength="128" placeholder="按部门/科室名称筛选" @keyup.enter="search" />
          </el-form-item>
          <el-form-item label="供应商/收款方">
            <el-input v-model="dimensionFilters.supplier_keyword" clearable maxlength="128" placeholder="按名称筛选" @keyup.enter="search" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="dimensionFilters.category_keyword" clearable maxlength="128" placeholder="分类名称" @keyup.enter="search" />
          </el-form-item>
        </el-form>
      </el-collapse-transition>
    </PageToolbar>

    <p class="dimension-note">
      按所选付款日期统计有实际付款日期的记录；业务总额和剩余待付请在“支出台账”查看。未关联的项目、部门或收款方不会根据其他资料推测。
    </p>

    <dl v-if="result && !loading && !loadError" class="dimension-totals" aria-label="当前筛选汇总">
      <div><dt>期间实际付款</dt><dd>{{ formatMoney(result.summary.period_paid_amount) }}</dd></div>
      <div><dt>付款笔数</dt><dd>{{ result.summary.payment_count }}</dd></div>
      <div><dt>涉及业务数</dt><dd>{{ result.summary.business_count }}</dd></div>
    </dl>

    <el-tabs v-model="groupBy" aria-label="汇总维度" @tab-change="changeDimension">
      <el-tab-pane label="项目" name="project" />
      <el-tab-pane label="部门/科室" name="department" />
      <el-tab-pane label="供应商/收款方" name="supplier" />
      <el-tab-pane label="分类" name="category" />
    </el-tabs>

    <DataTableShell :state="tableState" aria-label="维度汇总结果">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchSummary" /></template>
      <div class="dimension-table-scroll">
        <el-table :data="result?.items || []" row-key="dimension_key" stripe>
          <el-table-column label="维度名称" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">{{ displayLabel(row) }}</template>
          </el-table-column>
          <el-table-column label="期间实际付款" min-width="160" align="right">
            <template #default="{ row }">{{ formatMoney(row.period_paid_amount) }}</template>
          </el-table-column>
          <el-table-column prop="payment_count" label="付款笔数" width="110" align="right" />
          <el-table-column prop="business_count" label="涉及业务数" width="120" align="right" />
          <el-table-column label="占比" width="100" align="right">
            <template #default="{ row }">{{ expenditureDimensionShare(row.period_paid_amount, result?.summary.period_paid_amount || 0) }}%</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="openDetails(row)">查看明细</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="result?.total || 0"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="fetchSummary"
        />
      </template>
    </DataTableShell>

    <el-drawer
      v-model="detailsVisible"
      :title="detailsTitle"
      size="min(900px, 100vw)"
      @closed="clearDetails"
    >
      <p class="dimension-note">明细沿用汇总中的日期、来源及维度筛选；金额仅显示有实际付款日期的付款记录。</p>
      <DataTableShell :state="detailTableState" aria-label="分组付款明细">
        <template #error><StatePanel state="error" action-label="重试" @action="fetchDetails" /></template>
        <div class="dimension-table-scroll">
          <el-table :data="details?.items || []" row-key="row_key" stripe>
            <el-table-column label="付款日期" min-width="115">
              <template #default="{ row }">{{ expenditureDateLabel(row.paid_at) }}</template>
            </el-table-column>
            <el-table-column label="项目/单据" min-width="190" show-overflow-tooltip>
              <template #default="{ row }">
                <div>{{ row.project_name || '未关联项目' }}</div>
                <small class="dimension-secondary">{{ row.doc_no || row.source_no }}</small>
              </template>
            </el-table-column>
            <el-table-column prop="department" label="部门/科室" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.department || '未填写' }}</template>
            </el-table-column>
            <el-table-column label="供应商/收款方" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">{{ row.supplier_name || '未填写' }}</template>
            </el-table-column>
            <el-table-column label="分类" min-width="125" show-overflow-tooltip>
              <template #default="{ row }">{{ expenditureCategoryLabel(row.source_type, row.category) }}</template>
            </el-table-column>
            <el-table-column label="付款金额" width="140" align="right">
              <template #default="{ row }">
                <div>{{ formatMoney(row.amount) }}</div>
                <small class="dimension-secondary">{{ row.payment_no || '历史登记金额' }}</small>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" :disabled="!canOpenSource(row)" @click="openSource(row)">打开来源</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <template #footer>
          <el-pagination
            v-model:current-page="detailPage"
            v-model:page-size="detailPageSize"
            :total="details?.total || 0"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @change="fetchDetails"
          />
        </template>
      </DataTableShell>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getExpenditure, getExpenditureSummary, type ExpenditureDimension, type ExpenditureDimensionResult, type ExpenditureDimensionRow, type ExpenditureResult, type ExpenditureRow, type ExpenditureSource } from '@/api/payments'
import { DataTableShell, PageToolbar, StatePanel } from '@/components/ui'
import { useAuthStore } from '@/stores/auth'
import { expenditureCategoryLabel, expenditureDateLabel, expenditureDefaultDateRange, expenditureDimensionCategoryLabel, expenditureDimensionShare, expenditureSourceTarget, latestRequest } from '@/utils/expenditure'
import { formatMoney } from '@/utils/format'

const emit = defineEmits<{ manageExpense: [id: string] }>()
const router = useRouter()
const authStore = useAuthStore()
const sourceLabels: Record<ExpenditureSource, string> = {
  expense: '经营支出', project_cost: '项目实际费用', outsource: '外协',
}
const groupBy = ref<ExpenditureDimension>('project')
const sourceType = ref<ExpenditureSource | ''>('')
const keyword = ref('')
const dimensionFilters = reactive({
  project_keyword: '', department_keyword: '', supplier_keyword: '', category_keyword: '',
})
const dateRange = ref<string[] | null>(expenditureDefaultDateRange())
const showAdvancedFilters = ref(false)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const loadError = ref(false)
const result = ref<ExpenditureDimensionResult | null>(null)
const summaryRequests = latestRequest()
const availableSources = computed(() => result.value?.available_sources || (
  authStore.canAll(['outsource_center:read', 'outsource_task:read', 'outsource_payment:read', 'finance:view_cost'])
    ? ['expense', 'project_cost', 'outsource'] as ExpenditureSource[]
    : ['expense', 'project_cost'] as ExpenditureSource[]
))
const tableState = computed(() => loading.value ? 'loading' : loadError.value ? 'error' : result.value?.items.length ? 'ready' : 'empty')

const selectedGroup = ref<ExpenditureDimensionRow | null>(null)
const detailsVisible = ref(false)
const details = ref<ExpenditureResult | null>(null)
const detailLoading = ref(false)
const detailError = ref(false)
const detailPage = ref(1)
const detailPageSize = ref(20)
const detailRequests = latestRequest()
const detailTableState = computed(() => detailLoading.value ? 'loading' : detailError.value ? 'error' : details.value?.items.length ? 'ready' : 'empty')
const detailsTitle = computed(() => selectedGroup.value ? `${displayLabel(selectedGroup.value)} · 付款明细` : '付款明细')

function dimensionLabel(row: ExpenditureDimensionRow) {
  if (groupBy.value === 'category') return expenditureDimensionCategoryLabel(row.source_type || '', row.category)
  return row.label
}

function displayLabel(row: ExpenditureDimensionRow) {
  return dimensionLabel(row)
}

function queryFilters() {
  return {
    ...(sourceType.value ? { source_type: sourceType.value } : {}),
    ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
    ...(dimensionFilters.project_keyword.trim() ? { project_keyword: dimensionFilters.project_keyword.trim() } : {}),
    ...(dimensionFilters.department_keyword.trim() ? { department_keyword: dimensionFilters.department_keyword.trim() } : {}),
    ...(dimensionFilters.supplier_keyword.trim() ? { supplier_keyword: dimensionFilters.supplier_keyword.trim() } : {}),
    ...(dimensionFilters.category_keyword.trim() ? { category_keyword: dimensionFilters.category_keyword.trim() } : {}),
    ...(dateRange.value?.length === 2 ? { start_date: dateRange.value[0], end_date: dateRange.value[1] } : {}),
  }
}

async function fetchSummary() {
  const requestId = summaryRequests.begin()
  loading.value = true
  loadError.value = false
  try {
    const data = await getExpenditureSummary({
      page: page.value,
      page_size: pageSize.value,
      group_by: groupBy.value,
      ...queryFilters(),
    })
    if (summaryRequests.isCurrent(requestId)) result.value = data
  } catch {
    if (summaryRequests.isCurrent(requestId)) {
      result.value = null
      loadError.value = true
    }
  } finally {
    if (summaryRequests.isCurrent(requestId)) loading.value = false
  }
}

function search() {
  page.value = 1
  detailsVisible.value = false
  selectedGroup.value = null
  void fetchSummary()
}

function reset() {
  sourceType.value = ''
  keyword.value = ''
  dimensionFilters.project_keyword = ''
  dimensionFilters.department_keyword = ''
  dimensionFilters.supplier_keyword = ''
  dimensionFilters.category_keyword = ''
  dateRange.value = expenditureDefaultDateRange()
  showAdvancedFilters.value = false
  search()
}

function changeDimension() {
  page.value = 1
  detailsVisible.value = false
  selectedGroup.value = null
  void fetchSummary()
}

async function fetchDetails() {
  const group = selectedGroup.value
  if (!group) return
  const requestId = detailRequests.begin()
  detailLoading.value = true
  detailError.value = false
  try {
    const data = await getExpenditure('disbursements', {
      page: detailPage.value,
      page_size: detailPageSize.value,
      date_status: 'confirmed',
      group_by: groupBy.value,
      group_key: group.dimension_key,
      ...queryFilters(),
    })
    if (detailRequests.isCurrent(requestId)) details.value = data
  } catch {
    if (detailRequests.isCurrent(requestId)) {
      details.value = null
      detailError.value = true
    }
  } finally {
    if (detailRequests.isCurrent(requestId)) detailLoading.value = false
  }
}

function openDetails(group: ExpenditureDimensionRow) {
  selectedGroup.value = group
  detailsVisible.value = true
  detailPage.value = 1
  details.value = null
  void fetchDetails()
}

function clearDetails() {
  selectedGroup.value = null
  details.value = null
  detailRequests.begin()
}

function canOpenSource(row: ExpenditureRow) {
  return row.source_kind === 'expense' || !!expenditureSourceTarget(row)
}

function openSource(row: ExpenditureRow) {
  if (row.source_kind === 'expense') {
    detailsVisible.value = false
    emit('manageExpense', row.source_id)
    return
  }
  const target = expenditureSourceTarget(row)
  if (target) {
    detailsVisible.value = false
    void router.push(target)
  }
}

onMounted(() => { void fetchSummary() })
onUnmounted(() => {
  summaryRequests.begin()
  detailRequests.begin()
})
</script>

<style scoped>
.dimension-summary { min-width: 0; }
.summary-filters { display: flex; flex-wrap: wrap; align-items: center; gap: var(--ui-space-3); min-width: 0; }
.summary-filters :deep(.el-form-item) { margin: 0; }
.summary-filters :deep(.el-select), .summary-filters :deep(.el-input) { width: 220px; }
.summary-advanced-filters { margin-top: var(--ui-space-3); padding-top: var(--ui-space-3); border-top: 1px solid var(--ui-border); }
.dimension-note, .dimension-secondary { color: var(--ui-text-secondary); }
.dimension-note { line-height: 1.7; margin: var(--ui-space-3) 0; }
.dimension-secondary { font-size: var(--ui-font-size-small); }
.dimension-totals { display: flex; flex-wrap: wrap; gap: var(--ui-space-6); margin: var(--ui-space-4) 0; padding: var(--ui-space-4); background: var(--ui-surface); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-sm); }
.dimension-totals dt { color: var(--ui-text-secondary); margin-bottom: var(--ui-space-2); }
.dimension-totals dd { margin: 0; color: var(--ui-text); font-size: var(--ui-font-size-title); font-weight: var(--ui-font-weight-semibold); font-variant-numeric: tabular-nums; }
.dimension-table-scroll { min-width: 0; overflow-x: auto; }
.dimension-table-scroll :deep(.el-table) { min-width: 760px; }
@media (max-width: 768px) {
  .summary-filters { width: 100%; }
  .summary-filters :deep(.el-form-item) { width: 100%; min-width: 0; }
  .summary-filters :deep(.el-form-item__content) { min-width: 0; }
  .summary-filters :deep(.el-select), .summary-filters :deep(.el-input), .summary-filters :deep(.el-date-editor) { width: 100%; min-width: 0; }
  .dimension-totals { gap: var(--ui-space-4); }
}
</style>
