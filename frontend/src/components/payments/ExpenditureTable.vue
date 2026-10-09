<template>
  <section class="expenditure-view" :aria-label="view === 'ledger' ? '统一支出台账' : '付款流水'">
    <PageToolbar aria-label="统一支出筛选">
      <el-form inline class="expenditure-filters" @submit.prevent="search">
        <el-form-item label="来源">
          <el-select v-model="sourceType" clearable placeholder="全部有权查看的来源" aria-label="支出来源" @change="search">
            <el-option v-for="source in availableSources" :key="source" :label="sourceLabels[source]" :value="source" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="keyword" clearable maxlength="128" placeholder="来源编号 / 项目 / 供应商" aria-label="支出关键词" @keyup.enter="search" />
        </el-form-item>
        <el-form-item :label="view === 'ledger' ? '业务日期' : '付款日期'">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" range-separator="至" @change="search" />
        </el-form-item>
        <el-form-item v-if="view === 'disbursements'" label="日期状态">
          <el-select v-model="dateStatus" aria-label="付款日期状态" @change="changeDateStatus">
            <el-option label="全部" value="all" />
            <el-option label="有付款日期" value="confirmed" />
            <el-option label="付款日期待核实" value="unverified" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="search">搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </PageToolbar>

    <p class="expenditure-note">
      {{ view === 'ledger'
        ? '按业务日期筛选，已付为这些业务的累计付款；业务总额不是当期资金支出。外协未完成但已付款的任务包含预付款。'
        : '按实际付款日期统计有日期的付款；历史推算已付及无日期流水单独列示，不计入指定日期期间。' }}
      本页仅覆盖经营支出、实际登记项目费用及有权查看的外协；不含库存领用、报价预计成本，也不代表公司完整现金流量表。
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
        <div><dt>同来源范围待核实（不受日期筛选）</dt><dd>{{ formatMoney(result.summary.unverified_paid_amount || 0) }}</dd></div>
      </template>
    </dl>
    <el-alert v-if="result && !loading && !loadError && unverifiedAmount > 0" type="warning" :closable="false" show-icon class="expenditure-warning">
      <template #title>付款日期待核实 {{ formatMoney(unverifiedAmount) }}，未计入有日期付款统计</template>
      登记时已付和历史结清金额保留原值，不用业务日期或创建时间推测付款日期。
      <el-button v-if="view === 'disbursements'" text type="primary" @click="showUnverified">查看待核实记录</el-button>
    </el-alert>

    <DataTableShell :state="tableState" aria-label="统一支出结果">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="result?.items || []" row-key="row_key" stripe>
        <el-table-column label="来源" width="120">
          <template #default="{ row }"><el-tag size="small">{{ sourceLabels[row.source_type as ExpenditureSource] }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="source_no" label="来源编号" min-width="180" />
        <el-table-column v-if="view === 'disbursements'" label="付款编号" min-width="170">
          <template #default="{ row }">{{ row.payment_no || '历史已付（非逐笔流水）' }}</template>
        </el-table-column>
        <el-table-column label="项目 / 单据" min-width="210">
          <template #default="{ row }">
            <div>{{ row.project_name || '未关联项目' }}</div><small class="expenditure-secondary">{{ row.doc_no || '—' }}</small>
          </template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商 / 收款方" min-width="160" show-overflow-tooltip />
        <el-table-column label="分类" min-width="100">
          <template #default="{ row }">{{ expenditureCategoryLabel(row.source_type, row.category) }}</template>
        </el-table-column>
        <el-table-column :label="view === 'ledger' ? '业务日期' : '付款日期'" min-width="160">
          <template #default="{ row }">
            <span v-if="view === 'ledger'">{{ row.source_date?.slice(0, 10) || '未填写业务日期' }}</span>
            <span v-else>{{ expenditureDateLabel(row.paid_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="view === 'ledger' ? '业务总额' : '本次付款 / 历史已付'" min-width="160" align="right">
          <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column v-if="view === 'ledger'" label="累计已付" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.paid_amount || 0) }}</template>
        </el-table-column>
        <el-table-column v-if="view === 'ledger'" label="剩余待付" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.remaining_amount || 0) }}</template>
        </el-table-column>
        <el-table-column label="记录状态" min-width="150">
          <template #default="{ row }">{{ recordStatus(row) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canReconcile(row)" text type="primary" @click="openReconciliation(row)">核实付款日期</el-button>
            <el-button v-if="canVoidReconciliation(row)" text type="warning" @click="voidReconciliation(row)">撤销核对</el-button>
            <el-button text type="primary" @click="selected = row">查看来源</el-button>
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
          <el-descriptions-item label="供应商 / 收款方">{{ selected.supplier_name || '未关联供应商' }}</el-descriptions-item>
          <el-descriptions-item label="说明">{{ selected.description || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="view === 'ledger' ? '业务总额' : '本次付款 / 历史已付'">{{ formatMoney(selected.amount) }}</el-descriptions-item>
          <el-descriptions-item v-if="view === 'ledger'" label="累计已付 / 剩余待付">{{ formatMoney(selected.paid_amount || 0) }} / {{ formatMoney(selected.remaining_amount || 0) }}</el-descriptions-item>
          <el-descriptions-item v-else label="付款日期">{{ expenditureDateLabel(selected.paid_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.evidence_reference" label="核对凭证参考">{{ selected.evidence_reference }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.evidence_type" label="凭证类型">{{ evidenceTypeLabel(selected.evidence_type) }}</el-descriptions-item>
          <el-descriptions-item v-if="selected.reconciliation_note" label="核对说明">{{ selected.reconciliation_note }}</el-descriptions-item>
          <el-descriptions-item label="记录状态">{{ recordStatus(selected) }}</el-descriptions-item>
        </el-descriptions>
        <p class="expenditure-note">金额、凭证和删除操作仍在原始业务页面维护，此处不新建第二份记录。</p>
        <el-button v-if="selected.source_kind === 'expense'" @click="emit('manageExpense', selected.source_id)">查看经营支出原记录与凭证</el-button>
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
import { expenditureDateLabel, expenditureCategoryLabel, expenditureSourceTarget, latestRequest } from '@/utils/expenditure'
import { getErrorMessage } from '@/utils/error'

const props = defineProps<{ view: ExpenditureView }>()
const emit = defineEmits<{ manageExpense: [id: string] }>()
const router = useRouter()
const authStore = useAuthStore()
const sourceLabels: Record<ExpenditureSource, string> = { expense: '经营支出', project_cost: '项目实际费用', outsource: '外协' }
const sourceType = ref<ExpenditureSource | ''>('')
const keyword = ref('')
const dateRange = ref<string[] | null>(null)
const dateStatus = ref<'all' | 'confirmed' | 'unverified'>('all')
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
const unverifiedAmount = computed(() => props.view === 'ledger' ? result.value?.summary.undated_paid_amount || 0 : result.value?.summary.unverified_paid_amount || 0)
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
function reset() { sourceType.value = ''; keyword.value = ''; dateRange.value = null; dateStatus.value = 'all'; search() }
function showUnverified() { dateRange.value = null; dateStatus.value = 'unverified'; search() }
function changeDateStatus() { if (dateStatus.value === 'unverified') dateRange.value = null; search() }
watch(() => props.view, () => { result.value = null; reset() }, { immediate: true })
onUnmounted(() => requests.begin())
</script>

<style scoped>
.expenditure-view { min-width: 0; }
.expenditure-filters { display: flex; flex-wrap: wrap; align-items: center; gap: var(--ui-space-3); min-width: 0; }
.expenditure-filters :deep(.el-form-item) { margin: 0; }
.expenditure-filters :deep(.el-select), .expenditure-filters :deep(.el-input) { width: 220px; }
.expenditure-note { color: var(--ui-text-secondary); line-height: 1.7; margin: var(--ui-space-3) 0; }
.expenditure-secondary { color: var(--ui-text-secondary); }
.expenditure-summary { display: flex; flex-wrap: wrap; gap: var(--ui-space-6); margin: var(--ui-space-4) 0; padding: var(--ui-space-4); background: var(--ui-surface); border: 1px solid var(--ui-border); border-radius: var(--ui-radius-sm); }
.expenditure-summary dt { color: var(--ui-text-secondary); margin-bottom: var(--ui-space-2); }
.expenditure-summary dd { margin: 0; color: var(--ui-text); font-size: var(--ui-font-size-title); font-weight: var(--ui-font-weight-semibold); font-variant-numeric: tabular-nums; }
.expenditure-warning { margin-bottom: var(--ui-space-4); }
@media (max-width: 768px) {
  .expenditure-filters { width: 100%; }
  .expenditure-filters :deep(.el-form-item) { width: 100%; min-width: 0; }
  .expenditure-filters :deep(.el-form-item__content) { min-width: 0; }
  .expenditure-filters :deep(.el-select), .expenditure-filters :deep(.el-input), .expenditure-filters :deep(.el-date-editor) { width: 100%; min-width: 0; }
}
</style>
