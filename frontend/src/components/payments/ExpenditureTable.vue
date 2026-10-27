<template>
  <section class="expenditure-view" :aria-label="view === 'ledger' ? '支出台账' : '付款记录'">
    <PageToolbar aria-label="支出筛选">
      <el-form inline class="expenditure-filters" @submit.prevent="search">
        <el-form-item label="搜索">
          <el-input v-model="keyword" clearable maxlength="128" placeholder="单号、项目或供应商" aria-label="支出搜索" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="付款日期">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" range-separator="至" @change="search" />
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
        <el-form v-if="showAdvancedFilters" inline class="expenditure-filters expenditure-advanced-filters" @submit.prevent="search">
          <el-form-item label="来源">
            <el-select v-model="sourceType" clearable placeholder="全部有权查看的来源" aria-label="支出来源" @change="search">
              <el-option v-for="source in availableSources" :key="source" :label="sourceLabels[source]" :value="source" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="view === 'disbursements'" label="日期状态">
            <el-select v-model="dateStatus" aria-label="付款日期状态" @change="changeDateStatus">
              <el-option label="全部" value="all" />
              <el-option label="有付款日期" value="confirmed" />
              <el-option label="日期待核实" value="unverified" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-collapse-transition>
    </PageToolbar>

    <p class="expenditure-note">
      {{ view === 'ledger'
        ? '按最近付款日期筛选；业务总额、累计已付和剩余待付为来源当前汇总，不等于所选期间现金支出。'
        : '按实际付款日期筛选；历史记录可按日期状态查看并核对。' }}
      当前汇总支出登记、项目费用及账号有权查看的外协费用；不含库存领用等未接入模块，也不代表公司全部现金流。
    </p>
    <dl v-if="result && !loading && !loadError" class="expenditure-summary" aria-label="当前筛选全量汇总">
      <div><dt>筛选结果</dt><dd>{{ result.total }} {{ view === 'ledger' ? '笔业务' : '条记录' }}</dd></div>
      <template v-if="view === 'ledger'">
        <div><dt>业务总额</dt><dd>{{ formatMoney(result.summary.amount) }}</dd></div>
        <div><dt>累计已付</dt><dd>{{ formatMoney(result.summary.paid_amount || 0) }}</dd></div>
        <div><dt>剩余待付</dt><dd>{{ formatMoney(result.summary.remaining_amount || 0) }}</dd></div>
      </template>
      <template v-else>
        <div><dt>{{ dateRange ? '期间有日期付款' : '有日期付款合计' }}</dt><dd>{{ formatMoney(result.summary.confirmed_paid_amount || 0) }}</dd></div>
      </template>
    </dl>

    <DataTableShell :state="tableState" aria-label="支出查询结果">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="result?.items || []" row-key="row_key" stripe>
        <el-table-column label="付款日期" min-width="145">
          <template #default="{ row }">
            <div>{{ view === 'ledger' ? expenditureLastPaymentDateLabel(row.last_payment_date, row.paid_amount) : expenditureDateLabel(row.paid_at) }}</div>
            <small v-if="view === 'ledger' && row.last_payment_date && row.undated_paid_amount > 0" class="expenditure-secondary">
              另有 {{ formatMoney(row.undated_paid_amount) }} 日期待核实
            </small>
          </template>
        </el-table-column>
        <el-table-column label="项目" min-width="190">
          <template #default="{ row }">
            <div>{{ row.project_name || '未关联项目' }}</div>
            <small class="expenditure-secondary">{{ row.doc_no || row.source_no }}</small>
            <el-tag
              v-if="view === 'ledger' && ['cancelled', 'deleted'].includes(row.source_status)"
              size="small"
              type="warning"
            >{{ recordStatus(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门/科室" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.department || '—' }}</template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商 / 收款方" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="分类" min-width="100">
          <template #default="{ row }">{{ expenditureCategoryLabel(row.source_type, row.category) }}</template>
        </el-table-column>
        <el-table-column v-if="view === 'ledger'" label="业务总额" min-width="140" align="right">
          <template #default="{ row }">
            {{ formatMoney(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column v-else label="本次付款" min-width="140" align="right">
          <template #default="{ row }">
            <div>{{ formatMoney(row.amount) }}</div>
            <small class="expenditure-secondary">{{ row.payment_no || '历史金额（非逐笔流水）' }}</small>
          </template>
        </el-table-column>
        <el-table-column v-if="view === 'ledger'" label="累计已付" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.paid_amount || 0) }}</template>
        </el-table-column>
        <el-table-column v-if="view === 'ledger'" label="剩余待付" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.remaining_amount || 0) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canReconcile(row)" text type="primary" @click="openReconciliation(row)">核实付款日期</el-button>
            <el-button v-if="canVoidReconciliation(row)" text type="warning" @click="voidReconciliation(row)">撤销核对</el-button>
            <template v-if="view === 'ledger' && row.source_kind === 'expense'">
              <el-button text type="primary" @click="manageExpenseSource(row.source_id)">{{ authStore.can('expense:update') ? '编辑' : '查看' }}</el-button>
              <el-button v-if="authStore.can('expense:delete')" text type="danger" @click="emit('deleteExpense', row.source_id)">删除</el-button>
            </template>
            <el-button v-else text type="primary" @click="selected = row">查看来源</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="result?.total || 0" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @size-change="search" @current-change="fetchData" />
      </template>
    </DataTableShell>

    <el-drawer :model-value="!!selected" title="支出来源（只读）" size="min(560px, 100vw)" @close="selected = null">
      <template v-if="selected">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="来源">{{ sourceLabels[selected.source_type] }}</el-descriptions-item>
          <el-descriptions-item label="来源编号">{{ selected.source_no }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ selected.project_name || '未关联项目' }}</el-descriptions-item>
          <el-descriptions-item label="关联单据">{{ selected.doc_no || '—' }}</el-descriptions-item>
          <el-descriptions-item label="部门/科室">{{ selected.department || '—' }}</el-descriptions-item>
          <el-descriptions-item label="供应商 / 收款方">{{ selected.supplier_name || '未关联供应商' }}</el-descriptions-item>
          <el-descriptions-item label="说明">{{ selected.description || '—' }}</el-descriptions-item>
          <el-descriptions-item v-if="view === 'ledger'" label="业务日期">{{ selected.source_date?.slice(0, 10) || '未填写业务日期' }}</el-descriptions-item>
          <el-descriptions-item v-if="view === 'ledger'" label="最后付款日期">{{ expenditureLastPaymentDateLabel(selected.last_payment_date, selected.paid_amount) }}</el-descriptions-item>
          <el-descriptions-item :label="view === 'ledger' ? '业务总额' : '本次付款金额'">{{ formatMoney(selected.amount) }}</el-descriptions-item>
          <el-descriptions-item v-if="view === 'ledger'" label="累计已付">{{ formatMoney(selected.paid_amount || 0) }}</el-descriptions-item>
          <el-descriptions-item v-if="view === 'ledger'" label="剩余待付">{{ formatMoney(selected.remaining_amount || 0) }}</el-descriptions-item>
          <template v-else>
            <el-descriptions-item v-if="selected.payment_no" label="付款编号">{{ selected.payment_no }}</el-descriptions-item>
            <el-descriptions-item label="付款日期">{{ expenditureDateLabel(selected.paid_at) }}</el-descriptions-item>
            <el-descriptions-item label="来源业务总额">{{ formatMoney(selected.business_amount || 0) }}</el-descriptions-item>
            <el-descriptions-item label="来源当前累计已付">{{ formatMoney(selected.paid_amount || 0) }}</el-descriptions-item>
            <el-descriptions-item label="来源当前剩余待付">{{ formatMoney(selected.remaining_amount || 0) }}</el-descriptions-item>
            <el-descriptions-item v-if="selected.undated_paid_amount" label="来源待核实金额">{{ formatMoney(selected.undated_paid_amount) }}</el-descriptions-item>
          </template>
          <el-descriptions-item v-if="selected.evidence_reference" label="核对凭证参考">{{ selected.evidence_reference }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.evidence_type" label="凭证类型">{{ evidenceTypeLabel(selected.evidence_type) }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.reconciliation_note" label="核对说明">{{ selected.reconciliation_note }}</el-descriptions-item>
          <el-descriptions-item label="记录状态">{{ recordStatus(selected) }}</el-descriptions-item>
        </el-descriptions>
        <p class="expenditure-note">可打开支出详情查看分类、金额和凭证；项目费用和外协费用可进入对应记录处理。</p>
        <el-button v-if="selected.source_kind === 'expense'" @click="manageExpenseSource(selected.source_id)">{{ authStore.can('expense:update') ? '编辑支出' : '查看支出' }}</el-button>
        <el-button v-else-if="sourceTarget && selected.source_status !== 'deleted'" type="primary" @click="router.push(sourceTarget)">打开来源页面</el-button>
        <p v-else class="expenditure-secondary">原记录未关联单据或已删除；保留此处的只读财务事实。</p>
      </template>
    </el-drawer>

    <el-dialog v-model="reconciliationVisible" title="核实付款日期" width="min(560px, 94vw)" :close-on-click-modal="false">
      <template v-if="reconciliationRow">
        <el-alert
          class="reconciliation-policy"
          type="warning"
          :closable="false"
          show-icon
          title="此操作只为已有已付款金额补充凭证日期，不会新增付款或改变来源金额。"
        />
        <el-descriptions :column="1" border class="reconciliation-source">
          <el-descriptions-item label="来源编号">{{ reconciliationRow.source_no }}</el-descriptions-item>
          <el-descriptions-item label="当前待核实金额">{{ formatMoney(reconciliationRow.amount) }}</el-descriptions-item>
        </el-descriptions>
        <el-form label-width="110px" class="reconciliation-form">
          <el-form-item label="本次核实金额" required>
            <el-input-number
              v-model="reconciliationForm.amount"
              :min="0.01"
              :max="reconciliationRow.amount"
              :precision="2"
              :step="100"
              :controls="false"
            />
          </el-form-item>
          <el-form-item label="实际付款日期" required>
            <el-date-picker
              v-model="reconciliationForm.paid_at"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="按银行/付款凭证选择"
              :disabled-date="disableFutureDate"
            />
          </el-form-item>
          <el-form-item label="凭证类型" required>
            <el-select v-model="reconciliationForm.evidence_type" placeholder="请选择凭证类型">
              <el-option label="银行流水" value="bank_statement" />
              <el-option label="付款凭证" value="payment_voucher" />
              <el-option label="其他可核验证据" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="凭证参考" required>
            <el-input v-model="reconciliationForm.evidence_reference" maxlength="255" placeholder="流水号、凭证编号或档案位置" />
          </el-form-item>
          <el-form-item label="核对说明">
            <el-input v-model="reconciliationForm.note" type="textarea" :rows="3" maxlength="2000" show-word-limit />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="reconciliationVisible = false">取消</el-button>
        <el-button type="primary" :loading="reconciliationSaving" @click="saveReconciliation">保存核对</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  createFinancePaymentDateReconciliation,
  getExpenditure,
  voidFinancePaymentDateReconciliation,
  type ExpenditureResult,
  type ExpenditureRow,
  type ExpenditureSource,
  type ExpenditureView,
  type FinanceEvidenceType,
} from '@/api/payments'
import { PageToolbar, DataTableShell, StatePanel } from '@/components/ui'
import { useAuthStore } from '@/stores/auth'
import { formatMoney } from '@/utils/format'
import { expenditureDateLabel, expenditureLastPaymentDateLabel, expenditureCategoryLabel, expenditureSourceTarget, latestRequest } from '@/utils/expenditure'
import { getErrorMessage } from '@/utils/error'

const props = defineProps<{ view: ExpenditureView; refreshKey: number }>()
const emit = defineEmits<{ manageExpense: [id: string]; deleteExpense: [id: string] }>()
const router = useRouter()
const authStore = useAuthStore()
const sourceLabels: Record<ExpenditureSource, string> = { expense: '支出', project_cost: '项目实际费用', outsource: '外协' }
const sourceType = ref<ExpenditureSource | ''>('')
const keyword = ref('')
const dateRange = ref<string[] | null>(null)
const dateStatus = ref<'all' | 'confirmed' | 'unverified'>('all')
const showAdvancedFilters = ref(false)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const loadError = ref(false)
const result = ref<ExpenditureResult | null>(null)
const selected = ref<ExpenditureRow | null>(null)
const reconciliationVisible = ref(false)
const reconciliationSaving = ref(false)
const reconciliationRow = ref<ExpenditureRow | null>(null)
const reconciliationForm = reactive<{
  amount: number | null
  paid_at: string
  evidence_type: FinanceEvidenceType | ''
  evidence_reference: string
  note: string
}>({ amount: null, paid_at: '', evidence_type: '', evidence_reference: '', note: '' })
const requests = latestRequest()
const availableSources = computed<ExpenditureSource[]>(() => result.value?.available_sources || (authStore.canAll(['outsource_center:read', 'outsource_task:read', 'outsource_payment:read', 'finance:view_cost']) ? ['expense', 'project_cost', 'outsource'] : ['expense', 'project_cost']))
const tableState = computed(() => loading.value ? 'loading' : loadError.value ? 'error' : result.value?.items.length ? 'ready' : 'empty')
const sourceTarget = computed(() => selected.value ? expenditureSourceTarget(selected.value) : null)

function recordStatus(row: ExpenditureRow) {
  if (props.view === 'disbursements') return row.date_status === 'unverified' ? '付款日期待核实' : '有付款日期'
  return ({ active: '实际登记费用', pending: '未完成（含预付款）', in_progress: '进行中（含预付款）', completed: '已完成', settled: '已结算', cancelled: '已取消（保留已付）', deleted: '已删除（保留已付）', standalone: '未关联任务付款' } as Record<string, string>)[row.source_status] || row.source_status
}

function canReconcile(row: ExpenditureRow) {
  if (props.view !== 'disbursements' || row.date_status !== 'unverified' || row.source_status === 'deleted') return false
  if (!row.reconciliation_source_type || !row.reconciliation_source_id) return false
  if (!authStore.canAll(['expense:read', 'expense:update'])) return false
  return row.source_type !== 'outsource' || authStore.canAll([
    'finance:view_cost', 'outsource_center:read', 'outsource_task:read',
    'outsource_payment:read', 'outsource_vendor:read',
  ])
}

function manageExpenseSource(sourceId: string) {
  selected.value = null
  emit('manageExpense', sourceId)
}

function canVoidReconciliation(row: ExpenditureRow) {
  return props.view === 'disbursements'
    && !!row.reconciliation_id
    && authStore.canAll(['expense:read', 'expense:update'])
    && (row.source_type !== 'outsource' || authStore.canAll([
      'finance:view_cost', 'outsource_center:read', 'outsource_task:read',
      'outsource_payment:read', 'outsource_vendor:read',
    ]))
}

function evidenceTypeLabel(type: FinanceEvidenceType) {
  return ({ bank_statement: '银行流水', payment_voucher: '付款凭证', other: '其他证据' } as const)[type]
}

function openReconciliation(row: ExpenditureRow) {
  reconciliationRow.value = row
  Object.assign(reconciliationForm, {
    amount: Number(row.amount), paid_at: '', evidence_type: '', evidence_reference: '', note: '',
  })
  reconciliationVisible.value = true
}

function disableFutureDate(value: Date) {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return value.getTime() > today.getTime()
}

async function saveReconciliation() {
  const row = reconciliationRow.value
  if (!row?.reconciliation_source_type || !row.reconciliation_source_id) return
  if (!reconciliationForm.amount || reconciliationForm.amount <= 0 || reconciliationForm.amount > row.amount) {
    ElMessage.warning('核实金额必须大于0且不能超过当前待核实金额')
    return
  }
  if (!reconciliationForm.paid_at || !reconciliationForm.evidence_type || !reconciliationForm.evidence_reference.trim()) {
    ElMessage.warning('请填写实际付款日期、凭证类型和凭证参考')
    return
  }
  reconciliationSaving.value = true
  try {
    await createFinancePaymentDateReconciliation({
      source_type: row.reconciliation_source_type,
      source_id: row.reconciliation_source_id,
      amount: reconciliationForm.amount,
      paid_at: reconciliationForm.paid_at,
      evidence_type: reconciliationForm.evidence_type,
      evidence_reference: reconciliationForm.evidence_reference.trim(),
      ...(reconciliationForm.note.trim() ? { note: reconciliationForm.note.trim() } : {}),
    })
    ElMessage.success('付款日期核对已保存')
    reconciliationVisible.value = false
    await fetchData()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存核对失败，请稍后重试'))
  } finally {
    reconciliationSaving.value = false
  }
}

async function voidReconciliation(row: ExpenditureRow) {
  if (!row.reconciliation_id) return
  const answer = await ElMessageBox.prompt('请说明撤销此日期核对的原因。撤销后金额会重新回到“付款日期待核实”。', '撤销付款日期核对', {
    inputValidator: value => value?.trim() ? true : '撤销原因不能为空',
    inputErrorMessage: '撤销原因不能为空',
    confirmButtonText: '确认撤销',
    cancelButtonText: '取消',
    type: 'warning',
  }).catch(() => null)
  if (!answer?.value) return
  try {
    await voidFinancePaymentDateReconciliation(row.reconciliation_id, { reason: answer.value.trim() })
    ElMessage.success('核对已撤销，金额已恢复为待核实')
    await fetchData()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '撤销核对失败，请稍后重试'))
  }
}

async function fetchData() {
  const id = requests.begin()
  loading.value = true
  loadError.value = false
  selected.value = null
  try {
    const data = await getExpenditure(props.view, {
      page: page.value, page_size: pageSize.value,
      ...(sourceType.value ? { source_type: sourceType.value } : {}),
      ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
      ...(dateRange.value?.length === 2 ? { start_date: dateRange.value[0], end_date: dateRange.value[1] } : {}),
      ...(props.view === 'disbursements' ? { date_status: dateStatus.value } : {}),
    })
    if (requests.isCurrent(id)) result.value = data
  } catch {
    if (requests.isCurrent(id)) { result.value = null; loadError.value = true }
  } finally {
    if (requests.isCurrent(id)) loading.value = false
  }
}
function search() { page.value = 1; void fetchData() }
function reset() {
  sourceType.value = ''
  keyword.value = ''
  dateRange.value = null
  dateStatus.value = 'all'
  showAdvancedFilters.value = false
  search()
}
function changeDateStatus() { if (dateStatus.value === 'unverified') dateRange.value = null; search() }
watch(() => props.view, () => { result.value = null; reset() }, { immediate: true })
watch(() => props.refreshKey, (value, previous) => {
  if (value === previous) return
  page.value = 1
  void fetchData()
})
onUnmounted(() => requests.begin())
</script>

<style scoped>
.expenditure-view { min-width: 0; }
.expenditure-filters { display: flex; flex-wrap: wrap; align-items: center; gap: var(--ui-space-3); min-width: 0; }
.expenditure-filters :deep(.el-form-item) { margin: 0; }
.expenditure-filters :deep(.el-select), .expenditure-filters :deep(.el-input) { width: 220px; }
.expenditure-advanced-filters { margin-top: var(--ui-space-3); padding-top: var(--ui-space-3); border-top: 1px solid var(--ui-border); }
.expenditure-note { color: var(--ui-text-secondary); line-height: 1.7; margin: var(--ui-space-3) 0; }
.expenditure-secondary { color: var(--ui-text-secondary); }
.expenditure-summary { display: flex; flex-wrap: wrap; gap: var(--ui-space-6); margin: var(--ui-space-4) 0; padding: var(--ui-space-4); background: var(--ui-surface); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-sm); }
.expenditure-summary dt { color: var(--ui-text-secondary); margin-bottom: var(--ui-space-2); }
.expenditure-summary dd { margin: 0; color: var(--ui-text); font-size: var(--ui-font-size-title); font-weight: var(--ui-font-weight-semibold); font-variant-numeric: tabular-nums; }
@media (max-width: 768px) {
  .expenditure-filters { width: 100%; }
  .expenditure-filters :deep(.el-form-item) { width: 100%; min-width: 0; }
  .expenditure-filters :deep(.el-form-item__content) { min-width: 0; }
  .expenditure-filters :deep(.el-select), .expenditure-filters :deep(.el-input), .expenditure-filters :deep(.el-date-editor) { width: 100%; min-width: 0; }
}
</style>
