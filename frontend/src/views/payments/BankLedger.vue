<template>
  <AppPage>
    <template #header>
      <PageHeader title="银行台账" description="按银行、微信和支付宝账户查看收支流水与账面余额。" />
    </template>

    <el-tabs v-model="activeSection" aria-label="银行台账分类" class="bank-ledger-sections">
      <el-tab-pane v-if="canReadAccounts" label="账户流水" name="accounts" />
      <el-tab-pane v-if="canReadPayments" label="付款记录" name="payments" />
      <el-tab-pane v-if="canReadPayments" label="待归户付款" name="unassigned" />
      <el-tab-pane v-if="canReadPayments" label="日期待核实" name="undated" />
    </el-tabs>

    <template v-if="activeSection === 'accounts'">

    <StatePanel v-if="accountsLoading" state="loading" title="正在加载账户" />
    <StatePanel
      v-else-if="accountsError"
      state="error"
      title="账户加载失败"
      action-label="重试"
      @action="loadAccounts"
    />
    <StatePanel v-else-if="!accounts.length" title="暂无可用账户" description="请先在公司账户中登记银行、微信或支付宝账户。">
      <template #actions>
        <router-link :to="{ name: 'CompanyAccountList' }">查看公司账户</router-link>
      </template>
    </StatePanel>

    <el-tabs v-else :model-value="activeAccountId" class="bank-account-tabs" aria-label="资金账户" @update:model-value="selectAccount">
      <el-tab-pane v-for="account in accounts" :key="account.id" :name="account.id" lazy>
        <template #label>
          <span class="bank-account-label" :title="accountTabLabel(account)">{{ accountTabLabel(account) }}</span>
          <el-tag v-if="!account.is_active" class="bank-account-status" type="info" size="small">已停用</el-tag>
        </template>

        <template v-if="account.id === activeAccountId">
          <div class="bank-ledger-actions">
            <p class="bank-ledger-hint">
              期初日期及之后，归属此账户的业务收款、付款及手工流水参与余额计算。
            </p>
            <div class="bank-ledger-buttons">
              <el-button v-if="canSetOpeningBalance" :disabled="loading || !result" @click="openOpeningBalance(account)">期初余额</el-button>
              <el-button
                v-if="auth.can('expense:create')"
                :disabled="loading || !result?.opening_balance || !account.is_active"
                @click="openExpenseCreate(account)"
              >登记费用付款</el-button>
              <el-tooltip
                v-if="canCreateEntry && (!result?.opening_balance || !account.is_active)"
                :content="!account.is_active ? '停用账户不能登记新流水' : '请先设置期初余额后登记流水'"
                placement="top"
              >
                <span><el-button type="primary" disabled>登记台账</el-button></span>
              </el-tooltip>
              <el-button
                v-else-if="canCreateEntry"
                type="primary"
                @click="openEntry(account)"
              >登记台账</el-button>
            </div>
          </div>

          <dl class="bank-ledger-summary" aria-label="账户统计" :aria-busy="loading">
            <div><dt>期初余额</dt><dd>{{ result ? money(result.summary.opening_balance, '未设置') : '—' }}</dd></div>
            <div><dt>收入合计</dt><dd>{{ result ? formatMoney(result.summary.income_amount) : '—' }}</dd></div>
            <div><dt>支出合计</dt><dd>{{ result ? formatMoney(result.summary.expense_amount) : '—' }}</dd></div>
            <div><dt>账户余额</dt><dd>{{ result ? money(result.summary.balance, '未建账') : '—' }}</dd></div>
          </dl>

          <DataTableShell aria-label="账户流水">
            <el-table :data="result?.items ?? []" row-key="id" stripe>
              <el-table-column label="日期" width="115">
                <template #default="{ row }">{{ row.entry_date }}</template>
              </el-table-column>
              <el-table-column label="摘要" min-width="190" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="ledger-summary-cell">
                    <el-tag size="small" :type="row.entry_type === 'opening_balance' ? 'info' : row.entry_type === 'manual' ? 'warning' : 'success'">
                      {{ row.source_label }}
                    </el-tag>
                    <span>{{ row.summary || '' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="对方账号" min-width="135" show-overflow-tooltip>
                <template #default="{ row }">{{ row.counterparty_account || '—' }}</template>
              </el-table-column>
              <el-table-column label="对方户名" min-width="145" show-overflow-tooltip>
                <template #default="{ row }">{{ row.counterparty_name || '—' }}</template>
              </el-table-column>
              <el-table-column prop="category" label="分类" min-width="110" show-overflow-tooltip>
                <template #default="{ row }">{{ row.category || '—' }}</template>
              </el-table-column>
              <el-table-column label="收入金额" min-width="115" align="right">
                <template #default="{ row }">{{ row.income_amount ? formatMoney(row.income_amount) : '—' }}</template>
              </el-table-column>
              <el-table-column label="支出金额" min-width="115" align="right">
                <template #default="{ row }">{{ row.expense_amount ? formatMoney(row.expense_amount) : '—' }}</template>
              </el-table-column>
              <el-table-column label="余额" min-width="125" align="right">
                <template #default="{ row }">{{ money(row.balance, '—') }}</template>
              </el-table-column>
              <el-table-column label="项目" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">{{ row.project_name || '—' }}</template>
              </el-table-column>
              <el-table-column label="部门/科室" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.department || '—' }}</template>
              </el-table-column>
              <el-table-column label="操作" width="105" fixed="right">
                <template #default="{ row }">
                  <el-button v-if="canOpenCashSource(row)" text type="primary" @click="openCashSource(row)">查看来源</el-button>
                  <span v-else>—</span>
                </template>
              </el-table-column>
              <template #empty>
                <StatePanel v-if="loading" state="loading" title="正在加载账户流水" />
                <StatePanel v-else-if="loadError" state="error" title="账户流水加载失败" action-label="重试" @action="loadLedger" />
                <StatePanel v-else title="暂无账户流水" description="设置期初余额后，可登记或查看该账户的资金流水。" />
              </template>
            </el-table>
            <template v-if="result && result.total > pageSize" #footer>
              <el-pagination
                v-model:current-page="page"
                :page-size="pageSize"
                :total="result.total"
                :pager-count="5"
                layout="prev, pager, next"
              />
            </template>
          </DataTableShell>
          <p class="bank-ledger-note">
            已归属此账户的业务收付款会自动列入。登记前请先核对账户流水，避免重复入账。
          </p>
        </template>
      </el-tab-pane>
    </el-tabs>
    </template>

    <section v-else-if="canReadPayments" aria-label="待核对付款">
      <el-alert
        v-if="activeSection === 'payments'"
        title="按实际付款流水查看费用、项目成本和外协付款，包含现金及其他公司账户；各银行账户余额仍以账户流水为准。"
        type="info"
        :closable="false"
        show-icon
      />
      <el-alert
        v-else
        :title="activeSection === 'unassigned' ? '这些已付款尚未关联公司账户，不参与账户余额计算。补录付款账户后会进入对应账户。' : '这些历史已付款缺少可核实的日期，不参与账户余额计算。核实实际付款日期后会进入对应账户。'"
        type="info"
        :closable="false"
        show-icon
      />
      <ExpenditureTable
        view="disbursements"
        :refresh-key="0"
        :payment-queue="activeSection === 'unassigned' ? 'unassigned' : activeSection === 'undated' ? 'undated' : undefined"
        @manage-expense="openExpenseSource"
      />
    </section>

    <el-dialog
      v-model="openingDialogVisible"
      :title="(openingTarget?.name || '') + ' · 期初余额'"
      width="min(94vw, 520px)"
      :close-on-click-modal="false"
    >
      <el-alert
        class="dialog-note"
        type="info"
        :closable="false"
        title="期初余额是所选日期开始时的账户余额。该日期及之后的流水会参与计算；此前 ERP 记录不会重复叠加，也不会被修改。"
      />
      <el-form ref="openingFormRef" :model="openingForm" :rules="openingRules" label-position="top">
        <el-form-item label="期初日期" prop="entry_date" required>
          <el-date-picker v-model="openingForm.entry_date" type="date" value-format="YYYY-MM-DD" :clearable="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="期初余额" prop="amount" required>
          <el-input-number v-model="openingForm.amount" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="openingDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="mutating" @click="saveOpeningBalance">保存期初余额</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="entryDialogVisible"
      :title="(entryTarget?.name || '') + ' · 登记台账'"
      width="min(94vw, 680px)"
      :close-on-click-modal="false"
      @closed="resetEntryForm"
    >
      <el-alert
        class="dialog-note"
        :type="entryPurpose === 'manual' ? 'warning' : 'info'"
        :closable="false"
        :title="entryPurposeHint"
      />
      <el-form ref="entryFormRef" :model="entryForm" :rules="entryRules" label-position="top" class="entry-form">
        <el-form-item label="登记类型" required>
          <el-select v-model="entryPurpose" style="width: 100%" @change="resetEntryPurposeFields">
            <el-option label="手工收支" value="manual" />
            <el-option v-if="canCreateProjectCost" label="项目成本付款" value="project_cost" />
            <el-option v-if="canCreateReceipt" label="客户收款" value="receipt" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item :label="entryPurpose === 'receipt' ? '收款日期' : entryPurpose === 'project_cost' ? '付款日期' : '日期'" prop="entry_date" required>
              <el-date-picker v-model="entryForm.entry_date" type="date" value-format="YYYY-MM-DD" :clearable="false" :disabled-date="isEntryDateDisabled" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col v-if="entryPurpose === 'manual'" :xs="24" :sm="12">
            <el-form-item label="收支方向" prop="direction" required>
              <el-select v-model="entryForm.direction" style="width: 100%">
                <el-option label="收入" value="income" />
                <el-option label="支出" value="expense" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="金额" prop="amount" required>
              <el-input-number v-model="entryForm.amount" :min="0.01" :precision="2" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col v-if="entryPurpose !== 'receipt'" :xs="24" :sm="12">
            <el-form-item label="分类" prop="category" :required="entryPurpose === 'project_cost'" :rules="entryPurpose === 'project_cost' ? categoryRules : []">
              <el-select v-model="entryForm.category" filterable allow-create default-first-option clearable placeholder="选择或填写分类" style="width: 100%">
                <el-option v-for="category in categoryOptions" :key="category" :label="category" :value="category" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="摘要（选填）" prop="summary">
          <el-input v-model="entryForm.summary" maxlength="255" placeholder="自行填写；不填写则留空" />
        </el-form-item>
        <el-row v-if="entryPurpose !== 'receipt'" :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="对方户名">
              <el-autocomplete
                v-model="entryForm.counterparty_name"
                :fetch-suggestions="fetchSupplierSuggestions"
                :trigger-on-focus="false"
                :debounce="250"
                clearable
                :maxlength="entryPurpose === 'project_cost' ? 200 : 255"
                placeholder="搜索并选择供应商，或直接输入户名"
                style="width: 100%"
                @input="handleCounterpartyNameInput"
                @select="selectSupplier"
              >
                <template #default="{ item }">
                  <div class="supplier-option">
                    <span>{{ item.name }}</span>
                    <span>{{ item.vendor_no }}</span>
                  </div>
                </template>
              </el-autocomplete>
              <div class="form-hint">选择供应商可建立关联；直接输入的户名按自定义文本保存。</div>
            </el-form-item>
          </el-col>
          <el-col v-if="entryPurpose === 'manual'" :xs="24" :sm="12">
            <el-form-item label="对方账号">
              <el-input v-model="entryForm.counterparty_account" maxlength="200" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="关联订单" prop="order_id" :required="entryPurpose !== 'manual'" :rules="entryPurpose === 'manual' ? [] : orderRules">
              <el-select
                v-model="entryForm.order_id"
                filterable
                remote
                clearable
                :remote-method="searchOrderOptions"
                :loading="ordersLoading"
                placeholder="搜索订单编号或项目名称"
                style="width: 100%"
                @change="selectOrder"
                @visible-change="open => { if (open && !orderOptions.length) void searchOrderOptions('') }"
              >
                <el-option v-for="order in orderOptions" :key="order.id" :label="`${order.doc_no} · ${order.project_name}`" :value="order.id">
                  <div class="order-option">
                    <strong>{{ order.doc_no }}</strong>
                    <span>{{ order.project_name }} · {{ order.department || '未设置部门/科室' }}</span>
                  </div>
                </el-option>
              </el-select>
              <div class="form-hint">{{ entryPurpose === 'manual' ? '选择订单后自动带入项目和部门/科室。' : '项目和部门/科室由所选订单带入。' }}</div>
            </el-form-item>
          </el-col>
          <el-col v-if="entryPurpose === 'manual'" :xs="24" :sm="12">
            <el-form-item label="项目">
              <el-input v-model="entryForm.project_name" maxlength="255" :disabled="!!entryForm.order_id" />
            </el-form-item>
          </el-col>
          <el-col v-if="entryPurpose === 'manual'" :xs="24" :sm="12">
            <el-form-item label="部门/科室">
              <el-input v-model="entryForm.department" maxlength="255" :disabled="!!entryForm.order_id" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="entryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="mutating" @click="submitEntry">{{ entryPurpose === 'receipt' ? '登记收款' : entryPurpose === 'project_cost' ? '登记付款' : '登记流水' }}</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  accountTypeLabels,
  createBankCustomerReceipt,
  createBankLedgerEntry,
  createBankProjectCost,
  getBankLedger,
  getBankLedgerOrderOptions,
  getBankLedgerSupplierOptions,
  getCompanyAccountOptions,
  setBankLedgerOpeningBalance,
  type BankLedgerResult,
  type BankLedgerOrderOption,
  type BankLedgerPurpose,
  type BankLedgerSupplierOption,
  type CompanyAccount,
  type BankLedgerRow,
} from '@/api/companyAccounts'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { useAuthStore } from '@/stores/auth'
import { businessToday } from '@/utils/datetime'
import { getErrorMessage } from '@/utils/error'
import { newRequestId } from '@/utils/requestId'
import { latestRequest } from '@/utils/expenditure'
import { expenditureSourceTarget } from '@/utils/expenditure'
import { formatMoney } from '@/utils/format'
import ExpenditureTable from '@/components/payments/ExpenditureTable.vue'

const EXPENSE_CATEGORIES = ['手续费', '房租', '水电', '材料采购', '外协加工', '运输', '办公', '工资', '税费', '其他支出']
const INCOME_CATEGORIES = ['利息收入', '其他收入']
const COST_CATEGORIES = ['人工/工时费', '材料费', '租赁费', '运输/物流费', '安装杂费', '办公费', '餐费/交通费', '差旅费', '其他']

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const canReadPayments = computed(() => auth.can('expense:read'))
const canReadAccounts = computed(() => auth.canAll(['company_account:read', 'expense:read', 'company_account:ledger_read']))
type LedgerSection = 'accounts' | 'payments' | 'unassigned' | 'undated'
const activeSection = computed<LedgerSection>({
  get: () => {
    const section = route.query.section
    if (!canReadAccounts.value && section !== 'unassigned' && section !== 'undated') return 'payments'
    return section === 'payments' || section === 'unassigned' || section === 'undated' ? section : 'accounts'
  },
  set: section => { void router.replace({ path: '/bank-ledger', query: section === 'accounts' ? {} : { section } }) },
})
function openExpenseSource(id: string) {
  void router.push({ path: '/expenses', query: { expense_id: id, return_to: 'bank' } })
}
function openExpenseCreate(account: CompanyAccount) {
  void router.push({ path: '/expenses', query: { action: 'create', account_id: account.id, return_to: 'bank' } })
}
function canOpenCashSource(row: BankLedgerRow) {
  if (row.source_kind === 'receipt') return !!row.document_id && auth.canAll(['order:read', 'payment:read'])
  return row.source_kind === 'expense' && !!row.source_id
    || !!(row.source_kind && row.source_id && expenditureSourceTarget(row as BankLedgerRow & { source_kind: string }))
}
function openCashSource(row: BankLedgerRow) {
  if (row.source_kind === 'receipt' && row.document_id) {
    void router.push({ name: 'OrderDetail', params: { id: row.document_id }, query: { tab: 'changes' } })
    return
  }
  if (row.source_kind === 'expense' && row.source_id) return openExpenseSource(row.source_id)
  const target = row.source_kind && row.source_id ? expenditureSourceTarget(row as BankLedgerRow & { source_kind: string }) : null
  if (target) void router.push(target)
}
const canCreateEntry = computed(() => auth.can('company_account:ledger_create'))
const canCreateProjectCost = computed(() => auth.canAll(['company_account:select', 'expense:create']))
const canCreateReceipt = computed(() => auth.canAll(['company_account:select', 'payment:create']))
const canSetOpeningBalance = computed(() => auth.can('company_account:opening_balance_set'))
const accounts = shallowRef<CompanyAccount[]>([])
const accountsLoading = ref(true)
const accountsError = ref(false)
const activeAccountId = ref('')
const page = ref(1)
const pageSize = 20
const result = shallowRef<BankLedgerResult | null>(null)
const loading = ref(false)
const loadError = ref(false)
const requests = latestRequest()
const mutating = ref(false)
const openingDialogVisible = ref(false)
const openingTarget = ref<CompanyAccount | null>(null)
const openingFormRef = ref<FormInstance>()
const openingForm = reactive({ entry_date: '', amount: null as number | null })
const entryDialogVisible = ref(false)
const entryTarget = ref<CompanyAccount | null>(null)
const entryFormRef = ref<FormInstance>()
const entryPurpose = ref<BankLedgerPurpose>('manual')
const entryForm = reactive({
  request_id: newRequestId(),
  entry_date: businessToday(),
  direction: 'expense' as 'income' | 'expense',
  amount: null as number | null,
  summary: '',
  counterparty_account: '',
  counterparty_name: '',
  counterparty_supplier_id: '',
  category: '',
  project_name: '',
  department: '',
  order_id: '',
})
const selectedSupplierName = ref('')
const ordersLoading = ref(false)
const orderOptions = shallowRef<BankLedgerOrderOption[]>([])
let orderSearchSequence = 0
const categoryOptions = computed(() => {
  if (entryPurpose.value === 'project_cost') return COST_CATEGORIES
  return entryForm.direction === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES
})
const entryPurposeHint = computed(() => ({
  manual: '适用于手续费、利息等独立流水。已在系统登记的业务收付款请勿重复补录。',
  project_cost: '按实际已付款金额登记，同时计入所选订单的项目成本。已有应付款请从应付账款登记付款。',
  receipt: '登记后增加账户收入，并冲减所选订单及其合同的待收金额。',
})[entryPurpose.value])
const categoryRules = [{ required: true, whitespace: true, message: '请选择或填写成本分类', trigger: 'change' }]
const orderRules = [{ required: true, message: '请选择关联订单', trigger: 'change' }]
const openingRules = {
  entry_date: [{ required: true, message: '请选择期初日期', trigger: 'change' }],
  amount: [{ required: true, type: 'number', min: 0, message: '请填写不小于零的期初余额', trigger: 'change' }],
}
const entryRules = {
  entry_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  direction: [{ required: true, message: '请选择收支方向', trigger: 'change' }],
  amount: [{ required: true, type: 'number', min: 0.01, message: '金额必须大于零', trigger: 'change' }],
}

function accountTabLabel(account: CompanyAccount) {
  const label = account.label
  return account.account_type === 'bank' ? label : accountTypeLabels[account.account_type] + ' · ' + label
}

function money(value: number | null | undefined, emptyLabel: string) {
  return value === null || value === undefined ? emptyLabel : formatMoney(value)
}

function isEntryDateDisabled(value: Date) {
  const candidate = [value.getFullYear(), String(value.getMonth() + 1).padStart(2, '0'), String(value.getDate()).padStart(2, '0')].join('-')
  const openingDate = result.value?.opening_balance?.entry_date
  return candidate > businessToday() || (!!openingDate && candidate < openingDate)
}

function selectAccount(id: string | number) {
  page.value = 1
  activeAccountId.value = String(id)
}

async function loadAccounts() {
  accountsLoading.value = true
  accountsError.value = false
  try {
    accounts.value = (await getCompanyAccountOptions()).filter(account =>
      ['bank', 'wechat', 'alipay'].includes(account.account_type),
    )
    const firstAccount = accounts.value.find(account => account.is_active) ?? accounts.value[0]
    if (firstAccount) selectAccount(firstAccount.id)
  } catch {
    accountsError.value = true
  } finally {
    accountsLoading.value = false
  }
}

async function loadLedger() {
  if (!activeAccountId.value) return
  const request = requests.begin()
  loading.value = true
  loadError.value = false
  result.value = null
  try {
    const data = await getBankLedger(activeAccountId.value, { page: page.value, page_size: pageSize })
    if (requests.isCurrent(request)) result.value = data
  } catch {
    if (requests.isCurrent(request)) loadError.value = true
  } finally {
    if (requests.isCurrent(request)) loading.value = false
  }
}

function openOpeningBalance(account: CompanyAccount) {
  openingTarget.value = account
  openingForm.entry_date = result.value?.opening_balance?.entry_date || ''
  openingForm.amount = result.value?.opening_balance?.amount ?? null
  openingDialogVisible.value = true
  openingFormRef.value?.clearValidate()
}

async function saveOpeningBalance() {
  if (!openingTarget.value || !await openingFormRef.value?.validate().catch(() => false)) return
  if (openingForm.amount === null || openingForm.amount < 0) return
  const current = result.value?.opening_balance
  if (current && (current.entry_date !== openingForm.entry_date || current.amount !== openingForm.amount)) {
    const confirmed = await ElMessageBox.confirm(
      '修改期初余额或日期后，该日期之后的账户流水余额会重新计算。',
      '确认调整期初余额',
      { type: 'warning', confirmButtonText: '确认保存', cancelButtonText: '取消' },
    ).then(() => true).catch(() => false)
    if (!confirmed) return
  }
  mutating.value = true
  try {
    await setBankLedgerOpeningBalance(openingTarget.value.id, {
      entry_date: openingForm.entry_date,
      amount: openingForm.amount,
    })
    ElMessage.success('期初余额已保存')
    openingDialogVisible.value = false
    page.value = 1
    await loadLedger()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存期初余额失败'))
  } finally {
    mutating.value = false
  }
}

function openEntry(account: CompanyAccount) {
  if (!result.value?.opening_balance) {
    ElMessage.warning('请先设置该账户的期初余额')
    return
  }
  if (!account.is_active) {
    ElMessage.warning('已停用账户不能登记新流水')
    return
  }
  entryTarget.value = account
  resetEntryForm()
  entryDialogVisible.value = true
  entryFormRef.value?.clearValidate()
}

function resetEntryForm() {
  entryPurpose.value = 'manual'
  entryForm.request_id = newRequestId()
  entryForm.entry_date = businessToday()
  entryForm.direction = 'expense'
  entryForm.amount = null
  entryForm.summary = ''
  entryForm.counterparty_account = ''
  entryForm.counterparty_name = ''
  entryForm.counterparty_supplier_id = ''
  selectedSupplierName.value = ''
  resetEntryPurposeFields()
}

function resetEntryPurposeFields() {
  entryForm.request_id = newRequestId()
  entryForm.category = ''
  entryForm.project_name = ''
  entryForm.department = ''
  entryForm.order_id = ''
  orderSearchSequence++
  ordersLoading.value = false
  orderOptions.value = []
  entryFormRef.value?.clearValidate(['category', 'order_id'])
}

async function fetchSupplierSuggestions(query: string, callback: (items: Array<BankLedgerSupplierOption & { value: string }>) => void) {
  try {
    const suppliers = await getBankLedgerSupplierOptions(query.trim() || undefined)
    callback(suppliers.map(supplier => ({ ...supplier, value: supplier.name })))
  } catch {
    callback([])
  }
}

function selectSupplier(item: BankLedgerSupplierOption) {
  entryForm.counterparty_name = item.name
  entryForm.counterparty_supplier_id = item.id
  selectedSupplierName.value = item.name
}

function handleCounterpartyNameInput(value: string) {
  if (entryForm.counterparty_supplier_id && value !== selectedSupplierName.value) {
    entryForm.counterparty_supplier_id = ''
    selectedSupplierName.value = ''
  }
}

async function searchOrderOptions(keyword: string) {
  const sequence = ++orderSearchSequence
  ordersLoading.value = true
  try {
    const orders = await getBankLedgerOrderOptions(keyword.trim(), entryPurpose.value)
    if (sequence !== orderSearchSequence) return
    const selectedOrder = orderOptions.value.find(order => order.id === entryForm.order_id)
    orderOptions.value = selectedOrder && !orders.some(order => order.id === selectedOrder.id)
      ? [selectedOrder, ...orders]
      : orders
  } catch {
    if (sequence === orderSearchSequence) orderOptions.value = orderOptions.value.filter(order => order.id === entryForm.order_id)
  } finally {
    if (sequence === orderSearchSequence) ordersLoading.value = false
  }
}

function selectOrder(orderId: string | undefined) {
  if (!orderId) {
    entryForm.project_name = ''
    entryForm.department = ''
    return
  }
  const order = orderOptions.value.find(item => item.id === orderId)
  if (!order) return
  entryForm.project_name = order.project_name
  entryForm.department = order.department || ''
}

async function submitEntry() {
  if (mutating.value || !entryTarget.value || !await entryFormRef.value?.validate().catch(() => false)) return
  if (entryForm.amount === null || entryForm.amount <= 0) return
  const accountId = entryTarget.value.id
  const payload = {
    request_id: entryForm.request_id,
    entry_date: entryForm.entry_date,
    amount: entryForm.amount,
    summary: entryForm.summary.trim(),
    order_id: entryForm.order_id,
  }
  mutating.value = true
  try {
    if (entryPurpose.value === 'project_cost') {
      await createBankProjectCost(accountId, {
        ...payload,
        category: entryForm.category.trim(),
        supplier_id: entryForm.counterparty_supplier_id || undefined,
        counterparty_name: entryForm.counterparty_name.trim() || undefined,
      })
      ElMessage.success('付款已登记，项目成本已更新')
    } else if (entryPurpose.value === 'receipt') {
      await createBankCustomerReceipt(accountId, payload)
      ElMessage.success('收款已登记，应收账款已更新')
    } else {
      await createBankLedgerEntry(accountId, {
        ...payload,
        direction: entryForm.direction,
        counterparty_account: entryForm.counterparty_account.trim() || undefined,
        counterparty_name: entryForm.counterparty_name.trim() || undefined,
        counterparty_supplier_id: entryForm.counterparty_supplier_id || undefined,
        category: entryForm.category.trim() || undefined,
        project_name: entryForm.project_name.trim() || undefined,
        department: entryForm.department.trim() || undefined,
        order_id: payload.order_id || undefined,
      })
      ElMessage.success('台账流水已登记')
    }
    entryDialogVisible.value = false
    page.value = 1
    await loadLedger()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '登记台账失败'))
  } finally {
    mutating.value = false
  }
}

watch([activeAccountId, page], loadLedger)
onMounted(() => { if (canReadAccounts.value) void loadAccounts() })
</script>

<style scoped>
.bank-account-tabs { min-width: 0; }
.bank-account-tabs :deep(.el-tabs__item) { height: 44px; }
.bank-account-label {
  display: inline-block;
  max-width: clamp(125px, 48vw, 260px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bank-account-status { margin-left: var(--ui-space-2); }
.bank-ledger-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ui-space-4);
  margin-bottom: var(--ui-space-4);
}
.bank-ledger-buttons { display: flex; flex: 0 0 auto; gap: var(--ui-space-2); }
.bank-ledger-hint, .bank-ledger-note {
  margin: 0;
  color: var(--ui-text-secondary);
  line-height: 1.6;
}
.bank-ledger-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr));
  gap: var(--ui-space-4);
  margin: 0 0 var(--ui-space-4);
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-surface);
}
.bank-ledger-summary dt { color: var(--ui-text-secondary); margin-bottom: var(--ui-space-2); }
.bank-ledger-summary dd {
  margin: 0;
  color: var(--ui-text);
  font-size: var(--ui-font-size-title);
  font-weight: var(--ui-font-weight-semibold);
  font-variant-numeric: tabular-nums;
}
.ledger-summary-cell { display: flex; align-items: center; gap: var(--ui-space-2); min-width: 0; }
.ledger-summary-cell span { overflow: hidden; text-overflow: ellipsis; }
.bank-ledger-note { margin-top: var(--ui-space-3); }
.dialog-note { margin-bottom: var(--ui-space-4); }
.entry-form :deep(.el-input-number) { width: 100%; }
.form-hint {
  margin-top: var(--ui-space-1);
  color: var(--ui-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}
.supplier-option, .order-option {
  display: flex;
  justify-content: space-between;
  gap: var(--ui-space-3);
  min-width: 0;
}
.supplier-option span:last-child, .order-option span {
  overflow: hidden;
  color: var(--ui-text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 768px) {
  .bank-ledger-actions { align-items: flex-start; flex-direction: column; }
  .bank-ledger-buttons { width: 100%; }
  .bank-ledger-buttons :deep(.el-button) { flex: 1; }
}
</style>
