<template>
  <AppPage class="page">
    <PageHeader title="应收管理" description="统一查看客户欠款、收款记录和订单回款状态">
      <template #actions>
        <el-button
          v-if="activeTab === 'payments' && canRegisterInLedger"
          data-ai-target="receivable-register-payment"
          type="primary"
          @click="openLedgerRegistration"
        >
          去银行台账登记
        </el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab">
      <!-- ===== Tab 1: 客户欠款总览 ===== -->
      <el-tab-pane label="客户欠款总览" name="debt">
        <!-- 统计卡片 -->
        <el-row :gutter="16" style="margin-bottom: 16px">
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">业务总金额</div>
              <div class="stat-value">{{ formatMoney(stats.totalOrder) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">已收金额</div>
              <div class="stat-value text-success">{{ formatMoney(stats.totalPaid) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">待收欠款</div>
              <div class="stat-value text-danger">{{ formatMoney(stats.totalDebt) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">客户总数</div>
              <div class="stat-value">{{ debtList.length }} 个</div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 客户欠款表（可展开） -->
        <DataTableShell :state="debtTableState" aria-label="客户欠款总览">
          <template #error><StatePanel state="error" action-label="重试" @action="fetchDebts" /></template>
          <el-table
            :data="debtList"
            v-loading="debtLoading"
            stripe
            empty-text="暂无欠款客户"
            row-key="customer_id"
          >
          <el-table-column type="expand">
            <template #default="{ row }">
              <div v-if="row.standalone_orders?.length" style="padding: 12px 24px">
                <strong>独立订单应收</strong>
                <el-table :data="row.standalone_orders" border style="margin-top: 10px">
                  <el-table-column prop="order_no" label="订单编号" min-width="180" />
                  <el-table-column prop="project_name" label="项目" min-width="180" />
                  <el-table-column prop="total_amount" label="结算金额" width="130" />
                  <el-table-column prop="unpaid_amount" label="待收" width="130" />
                  <el-table-column label="操作" width="160"><template #default="{ row: direct }"><el-button text type="primary" @click="router.push(`/orders/${direct.id}?tab=changes`)">查看订单及收付款</el-button></template></el-table-column>
                </el-table>
              </div>
              <!-- 合同（主要） -->
              <template v-if="row.contracts?.length">
                <div style="margin: 8px 0 4px 48px; font-weight: 600; color: var(--ad-text);">合同</div>
                <el-table :data="row.contracts" size="small" stripe style="margin: 4px 0 12px 48px; width: calc(100% - 48px)">
                  <el-table-column type="expand">
                    <template #default="{ row: ct }">
                      <div v-if="!ct.orders?.length && !ct.quotes?.length" style="padding: 8px 16px; color: #999">暂无关联单据</div>
                      <template v-if="ct.orders?.length">
                        <div style="margin: 4px 0 4px 24px; font-weight: 600; font-size: 13px;">关联订单</div>
                        <el-table :data="ct.orders" size="small" stripe style="margin: 2px 0 8px 24px; width: calc(100% - 48px)">
                          <el-table-column prop="order_no" label="订单编号" width="180" />
                          <el-table-column label="部门/科室" width="120">
                            <template #default="{ row: o }">{{ o.department || '-' }}</template>
                          </el-table-column>
                          <el-table-column prop="project_name" label="项目名称" min-width="200" />
                          <el-table-column label="订单金额" width="120">
                              <template #default="{ row: o }">{{ formatMoney(o.total_amount) }}</template>
                          </el-table-column>
                          <el-table-column label="已收" width="120">
                              <template #default="{ row: o }">{{ formatMoney(o.paid_amount) }}</template>
                          </el-table-column>
                          <el-table-column label="欠款" width="120">
                            <template #default="{ row: o }">
                              <span class="text-danger">{{ formatMoney(o.unpaid_amount) }}</span>
                            </template>
                          </el-table-column>
                          <el-table-column label="状态" width="100">
                            <template #default="{ row: o }">
                              <StatusTag :status="o.status_view || o.status" size="sm" />
                            </template>
                          </el-table-column>
                        </el-table>
                      </template>
                      <template v-if="ct.quotes?.length">
                        <div style="margin: 4px 0 4px 24px; font-weight: 600; font-size: 13px;">关联报价</div>
                        <el-table :data="ct.quotes" size="small" stripe style="margin: 2px 0 8px 24px; width: calc(100% - 48px)">
                          <el-table-column prop="quote_no" label="报价编号" width="180" />
                          <el-table-column label="部门/科室" width="120">
                            <template #default="{ row: o }">{{ o.department || '-' }}</template>
                          </el-table-column>
                          <el-table-column prop="project_name" label="项目名称" min-width="200" />
                          <el-table-column label="金额" width="120">
                              <template #default="{ row: q }">{{ formatMoney(q.total_amount) }}</template>
                          </el-table-column>
                          <el-table-column label="状态" width="100">
                            <template #default="{ row: q }">
                              <StatusTag :status="q.status_view || q.status" size="sm" />
                            </template>
                          </el-table-column>
                        </el-table>
                      </template>
                    </template>
                  </el-table-column>
                  <el-table-column prop="contract_no" label="合同编号" width="180" />
                  <el-table-column prop="project_name" label="合同名称" min-width="180" />
                  <el-table-column prop="contract_type" label="合同类型" width="100" />
                  <el-table-column label="合同金额" width="120">
                    <template #default="{ row: ct }">{{ formatMoney(ct.total_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="已收" width="120">
                    <template #default="{ row: ct }">{{ formatMoney(ct.paid_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="欠款" width="120">
                    <template #default="{ row: ct }">
                      <span class="text-danger">{{ formatMoney(ct.unpaid_amount) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="类型" width="100">
                    <template #default="{ row: ct }">
                      <el-tag v-if="ct.contract_type === '框架合同'" type="warning" size="small">框架</el-tag>
                      <el-tag v-else type="primary" size="small">常规</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" width="100">
                    <template #default="{ row: ct }">
                      <StatusTag :status="ct.status_view || ct.status" size="sm" />
                    </template>
                  </el-table-column>
                </el-table>
              </template>
            </template>
          </el-table-column>
          <el-table-column prop="customer_name" label="客户名称" min-width="160" />
          <el-table-column label="合同" width="60" align="center">
            <template #default="{ row }">{{ row.contract_count }}</template>
          </el-table-column>
          <el-table-column label="合同总额" width="120">
            <template #default="{ row }">{{ formatMoney(row.total_order_amount) }}</template>
          </el-table-column>
          <el-table-column label="已收金额" width="120">
            <template #default="{ row }">{{ formatMoney(row.total_paid) }}</template>
          </el-table-column>
          <el-table-column label="欠款金额" width="120">
            <template #default="{ row }">
              <span class="text-danger">{{ formatMoney(row.debt_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最后收款" width="120">
            <template #default="{ row }">{{ formatDate(row.last_payment_date) || '-' }}</template>
          </el-table-column>
          </el-table>
        </DataTableShell>
      </el-tab-pane>

      <el-tab-pane label="收款记录" name="payments">
        <PageToolbar aria-label="收款记录筛选">
          <el-select v-model="receiptView" aria-label="收款来源" style="width: 135px" @change="changeView">
            <el-option v-if="canReadBank" label="银行台账" value="bank" />
            <el-option :label="canReadBank ? '其他收款' : '收款明细'" value="payments" />
            <el-option label="历史归档" value="archive" />
          </el-select>
          <template v-if="receiptView === 'bank'">
            <el-select v-model="filters.account" placeholder="收款账户" clearable filterable style="width: 200px" @change="search">
              <el-option v-for="account in accounts" :key="account.id" :label="account.label" :value="account.id" />
            </el-select>
            <el-select v-model="filters.status" placeholder="关联状态" clearable style="width: 130px" @change="search">
              <el-option label="待关联" value="unlinked" />
              <el-option label="已关联" value="linked" />
              <el-option label="待核对" value="review" />
            </el-select>
            <el-date-picker
              v-model="filters.period"
              type="daterange"
              value-format="YYYY-MM-DD"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="search"
            />
            <el-input
              v-model="filters.keyword"
              placeholder="户名、摘要、合同编号"
              clearable
              maxlength="120"
              style="width: 205px"
              @keyup.enter="search"
              @clear="search"
            />
          </template>
          <el-select
            v-if="contractOptions.length"
            v-model="filters.contract"
            placeholder="筛选合同"
            clearable
            filterable
            style="width: 230px"
            @change="search"
          >
            <el-option v-for="c in contractOptions" :key="c.id" :label="formatContractOption(c)" :value="c.id" />
          </el-select>
          <el-select v-if="orderOptions.length || filters.order" v-model="filters.order" placeholder="筛选订单" clearable filterable style="width: 190px" @change="search">
            <el-option v-for="o in orderOptions" :key="o.id" :label="formatOrderOption(o)" :value="o.id" />
          </el-select>
          <el-select v-if="debtList.length" v-model="filters.customer" placeholder="筛选客户" clearable filterable style="width: 175px" @change="search">
            <el-option v-for="customer in debtList" :key="customer.customer_id" :label="customer.customer_name" :value="customer.customer_id" />
          </el-select>
          <el-button type="primary" @click="search">搜索</el-button>
          <el-button v-if="hasFilters" @click="clearFilters">清空</el-button>
        </PageToolbar>

        <p v-if="associationOrder && receiptView === 'bank'" class="form-hint">从下方选择到账流水，关联时可分配给当前订单。</p>
        <p v-if="receiptView === 'archive'" class="form-hint">历史收款及原分配供查账使用，当前应收按有效收款重新计算。</p>

        <DataTableShell :state="paymentTableState" aria-label="收款记录">
          <template #error><StatePanel state="error" action-label="重试" @action="fetchPayments" /></template>
          <el-table v-if="receiptView === 'bank'" :data="bankReceipts" v-loading="paymentLoading" stripe row-key="id" empty-text="暂无符合条件的主营业务收入">
            <el-table-column prop="entry_date" label="到账日期" width="115" />
            <el-table-column label="收款账户" min-width="175">
              <template #default="{ row }">{{ accountLabel(row) }}</template>
            </el-table-column>
            <el-table-column prop="counterparty_name" label="对方户名" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.counterparty_name || '—' }}</template>
            </el-table-column>
            <el-table-column prop="summary" label="摘要" min-width="165" show-overflow-tooltip />
            <el-table-column label="金额" width="135" align="right">
              <template #default="{ row }">{{ formatMoney(Number(row.amount)) }}</template>
            </el-table-column>
            <el-table-column label="关联合同" min-width="165">
              <template #default="{ row }">
                <router-link v-if="row.contract_id && auth.can('contract:read')" :to="{ name: 'ContractDetail', params: { id: row.contract_id } }">
                  {{ row.contract_no }}
                </router-link>
                <span v-else>{{ row.contract_no || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'linked'" size="small" type="success">已关联</el-tag>
                <el-tag v-else-if="row.status === 'review'" size="small" type="warning" title="涉及历史退款或预收转分配">待核对</el-tag>
                <el-tag v-else size="small" type="info">待关联</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'unlinked' && canAssociate" text type="primary" size="small" @click="openAssociation(row)">关联</el-button>
                <el-button v-if="row.status === 'linked' && canUnlink" text type="danger" size="small" :disabled="saving" @click="handleUnlink(row)">解除关联</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-table v-else :data="paymentList" v-loading="paymentLoading" stripe row-key="id">
            <el-table-column prop="payment_no" label="收款编号" width="180" />
            <el-table-column prop="contract_no" label="合同编号" width="160" />
            <el-table-column label="分配订单" min-width="160">
              <template #default="{ row }">{{ formatPaymentAllocation(row) }}</template>
            </el-table-column>
            <el-table-column prop="customer_name" label="客户名称" min-width="160" />
            <el-table-column label="金额" width="135" align="right">
              <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="收款日期" width="120">
              <template #default="{ row }">{{ formatDate(row.paid_at) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="receiptView === 'archive'" size="small" type="info">已归档</el-tag>
                <StatusTag v-else :status="row.status_view || (row.is_voided ? 'voided' : 'active')" size="sm" />
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="摘要" min-width="175" />
            <el-table-column v-if="receiptView === 'archive'" label="凭证" width="95">
              <template #default="{ row }">
                <a v-if="receiptFileUrl(row.receipt_url)" :href="receiptFileUrl(row.receipt_url)" target="_blank" rel="noopener noreferrer">查看</a>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column v-if="receiptView !== 'archive' && canUnlink" label="操作" width="95" fixed="right">
              <template #default="{ row }">
                <el-button v-if="!row.is_voided && !row.bank_sourced" text type="danger" size="small" @click="handleVoid(row)">作废</el-button>
              </template>
            </el-table-column>
          </el-table>
          <template #footer>
            <el-pagination
              v-if="payTotal > 0"
              v-model:current-page="payPage"
              v-model:page-size="payPageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="payTotal"
              layout="total, sizes, prev, pager, next"
              @change="fetchPayments"
            />
          </template>
        </DataTableShell>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showDialog" title="关联合同" width="min(640px, 94vw)" :close-on-click-modal="false">
      <template v-if="selectedReceipt">
        <el-descriptions :column="2" border size="small" class="receipt-description">
          <el-descriptions-item label="到账日期">{{ selectedReceipt.entry_date }}</el-descriptions-item>
          <el-descriptions-item label="收款账户">{{ accountLabel(selectedReceipt) }}</el-descriptions-item>
          <el-descriptions-item label="对方户名">{{ selectedReceipt.counterparty_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="本次关联金额">{{ formatMoney(Number(selectedReceipt.amount)) }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedReceipt.summary" label="摘要" :span="2">{{ selectedReceipt.summary }}</el-descriptions-item>
        </el-descriptions>
        <el-form label-position="top">
          <el-form-item label="收款合同" required>
            <el-select v-model="form.contract" placeholder="搜索合同编号、合同名称或客户" filterable clearable :loading="debtLoading" style="width: 100%" @change="chooseContract">
              <el-option v-for="contract in associationContracts" :key="contract.id" :label="formatContractOption(contract)" :value="contract.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="selectedContract" label="分配订单">
            <el-select v-model="form.order" placeholder="按合同自动分配" filterable clearable style="width: 100%">
              <el-option v-for="order in selectedContractOrders" :key="order.id" :label="formatOrderOption(order)" :value="order.id" />
            </el-select>
            <div class="form-hint">未指定订单时，系统按合同关联订单分配，余款记在合同下。</div>
          </el-form-item>
          <el-descriptions v-if="selectedContract" :column="2" border size="small">
            <el-descriptions-item label="合同金额">{{ formatMoney(selectedContract.total_amount) }}</el-descriptions-item>
            <el-descriptions-item label="累计已收">{{ formatMoney(selectedContract.paid_amount) }}</el-descriptions-item>
            <el-descriptions-item label="当前待收">{{ formatMoney(selectedContract.unpaid_amount) }}</el-descriptions-item>
            <el-descriptions-item label="关联后待收">{{ associationError ? '—' : formatMoney(remainingAfterLink) }}</el-descriptions-item>
          </el-descriptions>
          <el-alert v-if="associationError" :title="associationError" type="warning" :closable="false" class="association-alert" />
        </el-form>
      </template>
      <template #footer>
        <el-button :disabled="saving" @click="showDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedContract || !!associationError" :loading="saving" @click="confirmAssociation">确认关联</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBankReceipts, getPayments, voidPayment, getCustomerDebt, linkBankReceipt, unlinkBankReceipt, type BankReceipt, type BankReceiptStatus } from '@/api/payments'
import { getCompanyAccountOptions, type CompanyAccount } from '@/api/companyAccounts'
import type { CustomerDebtContract, CustomerDebtItem, CustomerDebtOrder, PaymentResponse } from '@/types/api'
import { useAuthStore } from '@/stores/auth'
import { getErrorMessage } from '@/utils/error'
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel, StatusTag } from '@/components/ui'

type ContractOption = CustomerDebtContract & { customer_name: string }
type ReceiptView = 'bank' | 'payments' | 'archive'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canReadBank = computed(() => auth.can('company_account:ledger_read'))
const canRegisterInLedger = computed(() => auth.canAll(['company_account:ledger_read', 'company_account:ledger_create']))
const canAssociate = computed(() => canReadBank.value && auth.canAll(['payment:create', 'report:view_financial']))
const canUnlink = computed(() => auth.can('payment:void'))

const activeTab = ref('debt')
const debtLoading = ref(false)
const debtError = ref(false)
const debtList = ref<CustomerDebtItem[]>([])
const debtTableState = computed(() => {
  if (debtError.value) return 'error' as const
  if (debtLoading.value) return 'loading' as const
  return debtList.value.length ? 'ready' as const : 'empty' as const
})
const stats = computed(() => ({
  totalOrder: debtList.value.reduce((sum, customer) => sum + customer.total_order_amount, 0),
  totalPaid: debtList.value.reduce((sum, customer) => sum + customer.total_paid, 0),
  totalDebt: debtList.value.reduce((sum, customer) => sum + customer.debt_amount, 0),
}))

async function fetchDebts() {
  if (!auth.can('report:view_financial')) return
  debtLoading.value = true
  debtError.value = false
  try {
    debtList.value = await getCustomerDebt()
  } catch {
    debtError.value = true
  } finally {
    debtLoading.value = false
  }
}

const receiptView = ref<ReceiptView>(canReadBank.value ? 'bank' : 'payments')
const accounts = ref<CompanyAccount[]>([])
const filters = reactive({
  account: '', contract: '', order: '', customer: '', entry: '', keyword: '',
  status: '' as BankReceiptStatus | '',
  period: null as [string, string] | null,
})
const associationOrder = ref('')
const paymentLoading = ref(false)
const paymentError = ref(false)
const bankReceipts = ref<BankReceipt[]>([])
const paymentList = ref<PaymentResponse[]>([])
const payTotal = ref(0)
const payPage = ref(1)
const payPageSize = ref(20)
let requestSequence = 0

const contractOptions = computed<ContractOption[]>(() => debtList.value.flatMap(customer =>
  (customer.contracts || []).map(contract => ({ ...contract, customer_name: customer.customer_name })),
))
const orderOptions = computed(() => Array.from(new Map(
  debtList.value.flatMap(customer => [
    ...(customer.standalone_orders || []), ...(customer.contracts || []).flatMap(contract => contract.orders || []),
  ]).map(order => [order.id, order]),
).values()))
const hasFilters = computed(() => Object.values(filters).some(Boolean) || !!associationOrder.value)
const paymentTableState = computed(() => {
  if (paymentError.value) return 'error' as const
  if (paymentLoading.value) return 'loading' as const
  const rows = receiptView.value === 'bank' ? bankReceipts.value : paymentList.value
  return rows.length ? 'ready' as const : 'empty' as const
})

async function fetchPayments() {
  const sequence = ++requestSequence
  paymentLoading.value = true
  paymentError.value = false
  try {
    const common = {
      page: payPage.value, page_size: payPageSize.value,
      order_id: filters.order || undefined, contract_id: filters.contract || undefined,
      customer_id: filters.customer || undefined,
    }
    if (receiptView.value === 'bank') {
      const result = await getBankReceipts({
        ...common, account_id: filters.account || undefined, status: filters.status || undefined,
        start_date: filters.period?.[0], end_date: filters.period?.[1],
        keyword: filters.keyword.trim() || undefined, entry_id: filters.entry || undefined,
      })
      if (sequence !== requestSequence) return
      bankReceipts.value = result.items
      payTotal.value = result.total
    } else {
      const result = await getPayments({
        ...common, archived: receiptView.value === 'archive',
        exclude_bank_receipts: receiptView.value !== 'archive' && canReadBank.value,
      })
      if (sequence !== requestSequence) return
      paymentList.value = result.items
      payTotal.value = result.total
    }
  } catch {
    if (sequence === requestSequence) paymentError.value = true
  } finally {
    if (sequence === requestSequence) paymentLoading.value = false
  }
}

function search() {
  payPage.value = 1
  void fetchPayments()
}

function changeView() {
  payTotal.value = 0
  search()
}

function clearFilters() {
  associationOrder.value = ''
  Object.assign(filters, { account: '', contract: '', order: '', customer: '', entry: '', keyword: '', status: '', period: null })
  search()
}

function applyRoute() {
  const orderId = typeof route.query.order_id === 'string' ? route.query.order_id : ''
  associationOrder.value = typeof route.query.associate_order_id === 'string' ? route.query.associate_order_id : ''
  filters.entry = typeof route.query.bank_entry_id === 'string' ? route.query.bank_entry_id : ''
  filters.order = orderId
  if (route.query.section === 'payments' || orderId || associationOrder.value || filters.entry) {
    activeTab.value = 'payments'
  }
  if (associationOrder.value && canReadBank.value) filters.status = 'unlinked'
  search()
}

function openLedgerRegistration() {
  void router.push({ name: 'BankLedger', query: {
    action: 'register_income',
    ...(filters.account ? { account_id: filters.account } : {}),
    ...(associationOrder.value || filters.order ? { order_id: associationOrder.value || filters.order } : {}),
  } })
}

function accountLabel(row: BankReceipt) {
  return row.account_last_four ? `${row.account_name}（尾号 ${row.account_last_four}）` : row.account_name
}

function formatContractOption(contract: ContractOption) {
  return `${contract.contract_no} · ${contract.customer_name} · ${contract.project_name}`
}

function formatOrderOption(order: CustomerDebtOrder) {
  return `${order.order_no} · ${order.project_name} · 待收 ${formatMoney(order.unpaid_amount)}`
}

function formatPaymentAllocation(row: PaymentResponse) {
  if (!row.allocations?.length) return row.order_no || '—'
  return row.allocations.map(allocation => {
    if (!allocation.document_id) return '合同级'
    return orderOptions.value.find(order => order.id === allocation.document_id)?.order_no || row.order_no || '订单'
  }).join('、')
}

function receiptFileUrl(path?: string) {
  const relative = path?.replace(/^\/?uploads\//, '')
  if (!relative || relative.startsWith('/') || /^[a-z]+:/i.test(relative)) return ''
  const segments = relative.split('/')
  if (segments.some(segment => !segment || segment === '.' || segment === '..' || segment.includes('\\'))) return ''
  return '/uploads/' + segments.map(encodeURIComponent).join('/')
}

const showDialog = ref(false)
const saving = ref(false)
const selectedReceipt = ref<BankReceipt | null>(null)
const form = reactive({ contract: '', order: '' })
const selectedContract = computed(() => contractOptions.value.find(contract => contract.id === form.contract))
const selectedContractOrders = computed(() => (selectedContract.value?.orders || []).filter(order =>
  order.status !== 'pending_confirm' && order.status !== 'cancelled' && order.unpaid_amount > 0,
))
const hintOrder = computed(() => associationOrder.value || selectedReceipt.value?.order_id || '')
const associationContracts = computed(() => {
  const counterparty = selectedReceipt.value?.counterparty_name?.trim()
  const score = (contract: ContractOption) =>
    (hintOrder.value && contract.orders?.some(order => order.id === hintOrder.value) ? 2 : 0)
    + (counterparty && counterparty === contract.customer_name ? 1 : 0)
  return contractOptions.value.filter(contract => !['cancelled', 'terminated'].includes(contract.status))
    .sort((a, b) => score(b) - score(a))
})
const associationError = computed(() => {
  if (!selectedReceipt.value || !selectedContract.value) return ''
  const amount = Number(selectedReceipt.value.amount)
  if (amount > selectedContract.value.unpaid_amount) return '流水金额超过合同待收，请核对合同或款项归属。'
  const order = selectedContractOrders.value.find(item => item.id === form.order)
  return order && amount > order.unpaid_amount ? '流水金额超过所选订单待收，请调整分配方式。' : ''
})
const remainingAfterLink = computed(() => Math.max(0,
  (selectedContract.value?.unpaid_amount || 0) - Number(selectedReceipt.value?.amount || 0),
))

function chooseContract() {
  form.order = selectedContractOrders.value.some(order => order.id === hintOrder.value) ? hintOrder.value : ''
}

function openAssociation(row: BankReceipt) {
  selectedReceipt.value = row
  form.contract = ''
  form.order = ''
  showDialog.value = true
  if (debtError.value || !contractOptions.value.length) void fetchDebts()
}

async function confirmAssociation() {
  const entry = selectedReceipt.value
  if (!entry || !selectedContract.value || associationError.value || saving.value) return
  saving.value = true
  try {
    await linkBankReceipt(entry.id, {
      contract_id: form.contract, order_id: form.order || undefined,
      expected_amount: entry.amount, expected_date: entry.entry_date,
    })
    ElMessage.success('已关联合同')
    showDialog.value = false
    await Promise.all([fetchDebts(), fetchPayments()])
  } catch (error) {
    if (!error || typeof error !== 'object' || !('status' in error)) {
      ElMessage.error(getErrorMessage(error, '关联合同失败'))
    }
  } finally {
    saving.value = false
  }
}

async function handleUnlink(row: BankReceipt) {
  if (!row.payment_id || saving.value) return
  try {
    const { value } = await ElMessageBox.prompt('解除后，本笔金额将恢复为合同待收。请输入原因。', '解除关联', {
      confirmButtonText: '解除关联', cancelButtonText: '取消',
      inputValidator: value => (!!value?.trim() && value.trim().length <= 500) || '请输入不超过 500 字的原因',
    })
    saving.value = true
    await unlinkBankReceipt(row.id, { payment_id: row.payment_id, reason: value.trim() })
    ElMessage.success('已解除关联')
    await Promise.all([fetchDebts(), fetchPayments()])
  } catch {
    // Cancellation and response failures are handled by the dialog or API client.
  } finally {
    saving.value = false
  }
}

async function handleVoid(row: PaymentResponse) {
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '作废收款', {
      confirmButtonText: '确定', cancelButtonText: '取消',
      inputValidator: value => !!value?.trim() || '请输入作废原因',
    })
    await voidPayment(row.id, { void_reason: value.trim() })
    ElMessage.success('已作废')
    await Promise.all([fetchDebts(), fetchPayments()])
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error, '作废收款失败'))
  }
}

onMounted(() => {
  if (!auth.can('report:view_financial')) activeTab.value = 'payments'
  void fetchDebts()
  if (canReadBank.value) {
    void getCompanyAccountOptions().then(rows => { accounts.value = rows }).catch(() => {})
  }
  applyRoute()
})
watch(() => [route.query.section, route.query.order_id, route.query.associate_order_id, route.query.bank_entry_id], applyRoute)
</script>

<style scoped>
.stat-card { text-align: center; border: 1px solid var(--ad-border); }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.form-hint { margin-top: 4px; color: var(--ad-text-secondary); font-size: 12px; line-height: 1.5; }
.receipt-description { margin-bottom: 16px; }
.association-alert { margin-top: 12px; }
</style>
