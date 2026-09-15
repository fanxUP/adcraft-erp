<template>
  <AppPage class="page">
    <PageHeader title="应收管理" description="统一查看客户欠款、收款记录和订单回款状态">
      <template #actions>
        <el-button
          v-if="activeTab === 'payments'"
          data-ai-target="receivable-register-payment"
          type="primary"
          @click="openPaymentDialog()"
        >
          登记收款
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
              <div class="stat-label">合同总金额</div>
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

      <!-- ===== Tab 2: 收款记录 ===== -->
      <el-tab-pane label="收款记录" name="payments">
        <PageToolbar aria-label="收款记录筛选">
          <el-select v-model="filterContractId" placeholder="筛选合同" clearable filterable style="width: 260px" @change="fetchPayments">
            <el-option v-for="c in contractOptions" :key="c.id" :label="`${c.contract_no} — ${c.customer_name} — ${c.project_name}`" :value="c.id" />
          </el-select>
          <el-select v-model="filterOrderId" placeholder="筛选订单" clearable filterable style="width: 240px" @change="fetchPayments">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} — ${o.department || '-'} — ${o.project_name} — ${formatMoney(o.total_amount)}`" :value="o.id" />
          </el-select>
          <el-select v-model="filterCustomerId" placeholder="筛选客户" clearable filterable style="width: 200px" @change="fetchPayments">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button @click="fetchPayments" type="primary">搜索</el-button>
        </PageToolbar>

        <DataTableShell :state="paymentTableState" aria-label="收款记录">
          <template #error><StatePanel state="error" action-label="重试" @action="fetchPayments" /></template>
          <el-table :data="paymentList" v-loading="paymentLoading" stripe>
          <el-table-column prop="payment_no" label="收款编号" width="180" />
          <el-table-column prop="contract_no" label="合同编号" width="180" />
          <el-table-column label="分配订单" min-width="180">
            <template #default="{ row }">{{ formatPaymentAllocation(row) }}</template>
          </el-table-column>
          <el-table-column prop="customer_name" label="客户名称" width="160" />
          <el-table-column prop="project_name" label="项目名称" min-width="200" />
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="payment_method" label="方式" width="100" />
          <el-table-column label="收款日期" width="120">
            <template #default="{ row }">{{ formatDate(row.paid_at) || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <StatusTag :status="row.status_view || (row.is_voided ? 'voided' : 'active')" size="sm" />
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button v-if="!row.is_voided" text type="danger" size="small" @click="handleVoid(row)">作废</el-button>
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

    <!-- 登记收款对话框（Tab 1 和 Tab 2 共用） -->
    <el-dialog v-model="showDialog" title="登记收款" width="640px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="收款合同" required>
          <el-select v-model="form.contract_id" placeholder="选择收款合同" filterable clearable style="width: 100%" @change="onContractSelect">
            <el-option v-for="c in contractOptions" :key="c.id" :label="formatContractOption(c)" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分配订单">
          <el-select v-model="form.order_id" placeholder="不指定，按合同自动分配" clearable filterable :disabled="!form.contract_id" style="width: 100%">
            <el-option v-for="o in selectedContractOrders" :key="o.id" :label="formatOrderOption(o)" :value="o.id" />
          </el-select>
          <div class="form-hint">不指定订单时，系统按合同关联订单顺序自动分配；超出订单合计的部分保留为合同级收款。</div>
        </el-form-item>
        <el-form-item label="收款金额">
          <el-input-number v-model="form.amount" :min="0.01" :max="selectedContract ? selectedContract.unpaid_amount : undefined" :precision="2" style="width: 100%" />
          <div v-if="selectedContract" class="form-hint">合同未收：{{ formatMoney(selectedContract.unpaid_amount) }}</div>
        </el-form-item>
        <el-form-item label="收款方式">
          <el-select v-model="form.payment_method" style="width: 100%">
            <el-option label="银行转账" value="银行转账" />
            <el-option label="微信" value="微信" />
            <el-option label="支付宝" value="支付宝" />
            <el-option label="现金" value="现金" />
            <el-option label="支票" value="支票" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款日期">
          <el-date-picker v-model="form.paid_at" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" @click="handleCreate" type="primary">确认收款</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getPayments, createPayment, voidPayment, getCustomerDebt } from '@/api/payments'
import { getOrders } from '@/api/orders'
import { getCustomers } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import type {
  PaymentResponse,
  OrderListResponse,
  CustomerResponse,
  CustomerDebtItem,
  CustomerDebtOrder,
  ContractListResponse,
  ContractDetailResponse,
  SimpleOrderRef,
} from '@/types/api'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel, StatusTag } from '@/components/ui'

const route = useRoute()
const aiStore = useAiAssistantStore()

// ── Tab state ──

const activeTab = ref('debt')

// ── Tab 1: 客户欠款 ──

const debtLoading = ref(false)
const debtList = ref<CustomerDebtItem[]>([])
const debtError = ref(false)

const debtTableState = computed(() => {
  if (debtError.value) return 'error' as const
  if (debtLoading.value) return 'loading' as const
  return debtList.value.length ? 'ready' as const : 'empty' as const
})

const stats = computed(() => {
  const totalOrder = debtList.value.reduce((s, c) => s + c.total_order_amount, 0)
  const totalPaid = debtList.value.reduce((s, c) => s + c.total_paid, 0)
  const totalDebt = debtList.value.reduce((s, c) => s + c.debt_amount, 0)
  return { totalOrder, totalPaid, totalDebt }
})

async function fetchDebts() {
  debtLoading.value = true
  debtError.value = false
  try {
    debtList.value = await getCustomerDebt()
    syncContractOptions()
  } catch {
    debtError.value = true
  } finally { debtLoading.value = false }
}

// ── Tab 2: 收款记录 ──

const paymentLoading = ref(false)
const saving = ref(false)
const paymentList = ref<PaymentResponse[]>([])
const paymentError = ref(false)
const payTotal = ref(0)
const payPage = ref(1)
const payPageSize = ref(20)
const filterOrderId = ref('')
const filterContractId = ref('')
const filterCustomerId = ref('')
const orderOptions = ref<OrderListResponse[]>([])
const customerOptions = ref<CustomerResponse[]>([])
const contractOptions = ref<ContractListResponse[]>([])
const contractDetails = ref<Record<string, ContractDetailResponse>>({})

const paymentTableState = computed(() => {
  if (paymentError.value) return 'error' as const
  if (paymentLoading.value) return 'loading' as const
  return paymentList.value.length ? 'ready' as const : 'empty' as const
})

async function fetchPayments() {
  paymentLoading.value = true
  paymentError.value = false
  try {
    const data = await getPayments({
      page: payPage.value,
      page_size: payPageSize.value,
      order_id: filterOrderId.value || undefined,
      contract_id: filterContractId.value || undefined,
      customer_id: filterCustomerId.value || undefined,
    })
    paymentList.value = data.items
    payTotal.value = data.total
  } catch {
    paymentError.value = true
  } finally { paymentLoading.value = false }
}

async function loadOptions() {
  const [oRes, cRes] = await Promise.all([
    getOrders({ page_size: 100 }),
    getCustomers({ page_size: 100 }),
  ])
  orderOptions.value = oRes.items
  customerOptions.value = cRes.items
  syncContractOptions()
  applyGuidedOrder()
}

// ── Shared: 登记收款对话框 ──

const showDialog = ref(false)
const form = reactive({
  contract_id: '',
  order_id: '',
  customer_id: '',
  amount: 0,
  payment_method: '',
  paid_at: '',
  remark: '',
})

const selectedContract = computed(() => (
  contractOptions.value.find(contract => contract.id === form.contract_id) || null
))

const selectedContractOrders = computed<SimpleOrderRef[]>(() => (
  form.contract_id ? contractDetails.value[form.contract_id]?.orders || [] : []
))

function formatContractOption(contract: ContractListResponse) {
  return `${contract.contract_no} — ${contract.customer_name} — ${contract.project_name} — 未收 ${formatMoney(contract.unpaid_amount)}`
}

function formatOrderOption(order: SimpleOrderRef) {
  const unpaid = order.unpaid_amount === undefined
    ? ''
    : ` — 未收 ${formatMoney(order.unpaid_amount)}`
  return `${order.order_no} — ${order.department || '-'} — ${order.project_name}${unpaid}`
}

function formatPaymentAllocation(row: PaymentResponse) {
  if (!row.allocations?.length) return row.order_no || '历史收款'
  return row.allocations.map(allocation => {
    if (allocation.allocation_type === 'contract' || !allocation.document_id) return '合同级'
    const order = orderOptions.value.find(item => item.id === allocation.document_id)
    return order?.order_no || allocation.order_id || '订单'
  }).join('、')
}

function syncContractOptions() {
  contractOptions.value = debtList.value.flatMap(customer => (
    customer.contracts || []
  ).map(contract => ({
    ...contract,
    customer_name: customer.customer_name,
  } as ContractListResponse)))
}

function findDebtContract(contractId: string) {
  for (const customer of debtList.value) {
    const contract = customer.contracts?.find(item => item.id === contractId)
    if (contract) return { customer, contract }
  }
  return null
}

async function onContractSelect(contractId: string) {
  form.order_id = ''
  form.customer_id = ''
  if (!contractId) return
  const source = findDebtContract(contractId)
  if (!source) return
  const detail = {
    ...source.contract,
    customer_id: source.customer.customer_id,
    customer_name: source.customer.customer_name,
    orders: source.contract.orders || [],
  } as ContractDetailResponse
  contractDetails.value[contractId] = detail
  form.customer_id = detail.customer_id
}

function guidedOrderId() {
  return typeof route.query.order_id === 'string'
    ? route.query.order_id
    : ''
}

function applyGuidedOrder() {
  const orderId = guidedOrderId()
  if (!orderId || !orderOptions.value.some(order => order.id === orderId)) return
  activeTab.value = 'payments'
  filterOrderId.value = orderId
  void fetchPayments()
}

function findContractForOrder(orderId: string) {
  for (const customer of debtList.value) {
    const contract = customer.contracts?.find(item => item.orders?.some(order => order.id === orderId))
    if (contract) return contract
  }
  return null
}

/** Open the dialog, optionally pre-filling the contract/order from the current view. */
async function openPaymentDialog(order?: CustomerDebtOrder | OrderListResponse) {
  const selectedOrder = order || orderOptions.value.find(
    item => item.id === (filterOrderId.value || guidedOrderId()),
  )
  const contract = selectedOrder ? findContractForOrder(selectedOrder.id) : null
  const contractId = contract?.id || filterContractId.value
  if (contractId) {
    form.contract_id = contractId
    await onContractSelect(contractId)
    if (selectedOrder) form.order_id = selectedOrder.id
  }
  showDialog.value = true
}

async function handleCreate() {
  saving.value = true
  try {
    if (!form.contract_id) {
      ElMessage.warning('请选择收款合同')
      return
    }
    if (!form.customer_id) {
      const source = findDebtContract(form.contract_id)
      if (!source) {
        ElMessage.warning('合同信息加载失败，请刷新后重试')
        return
      }
      form.customer_id = source.customer.customer_id
    }
    const paidOrderId = form.order_id
    await createPayment({
      ...form,
      order_id: form.order_id || undefined,
    })
    ElMessage.success('收款登记成功')
    showDialog.value = false
    Object.assign(form, { contract_id: '', order_id: '', customer_id: '', amount: 0, payment_method: '', paid_at: '', remark: '' })
    // Refresh both tabs
    fetchPayments()
    fetchDebts()
    if (paidOrderId) await aiStore.requestWorkflowGuidance('order', paidOrderId, true)
  } catch {
    // handled by interceptor
  } finally { saving.value = false }
}

async function handleVoid(row: PaymentResponse) {
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '作废收款', {
      confirmButtonText: '确定', cancelButtonText: '取消',
    })
    if (value) {
      await voidPayment(row.id, { void_reason: value })
      ElMessage.success('已作废')
      fetchPayments()
      fetchDebts()
    }
  } catch { /* cancelled */ }
}

// ── Init ──

onMounted(() => {
  fetchDebts()
  fetchPayments()
  loadOptions()
})

watch(
  () => route.query.order_id,
  applyGuidedOrder,
)
</script>

<style scoped>

.stat-card { text-align: center; border: 1px solid var(--ad-border); }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.form-hint { margin-top: 4px; color: var(--ad-text-secondary); font-size: 12px; line-height: 1.5; }

/* Fix input-number width in dialog */
:deep(.el-dialog .el-input-number) { width: 100%; }
</style>
