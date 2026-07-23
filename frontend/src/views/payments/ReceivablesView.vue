<template>
  <div class="page">
    <div class="page-header">
      <h2>应收管理</h2>
    </div>

    <el-tabs v-model="activeTab">
      <!-- ===== Tab 1: 客户欠款总览 ===== -->
      <el-tab-pane label="客户欠款总览" name="debt">
        <!-- 统计卡片 -->
        <el-row :gutter="16" style="margin-bottom: 16px">
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">合同总金额</div>
              <div class="stat-value">¥ {{ stats.totalOrder.toFixed(2) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">已收金额</div>
              <div class="stat-value" style="color: #67c23a">¥ {{ stats.totalPaid.toFixed(2) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="stat-card">
              <div class="stat-label">待收欠款</div>
              <div class="stat-value" style="color: #e63946">¥ {{ stats.totalDebt.toFixed(2) }}</div>
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
                          <el-table-column prop="project_name" label="项目名称" min-width="150" />
                          <el-table-column label="订单金额" width="120">
                            <template #default="{ row: o }">¥ {{ o.total_amount?.toFixed(2) }}</template>
                          </el-table-column>
                          <el-table-column label="已收" width="120">
                            <template #default="{ row: o }">¥ {{ o.paid_amount?.toFixed(2) }}</template>
                          </el-table-column>
                          <el-table-column label="欠款" width="120">
                            <template #default="{ row: o }">
                              <span style="color: #e63946; font-weight: 600">¥ {{ o.unpaid_amount?.toFixed(2) }}</span>
                            </template>
                          </el-table-column>
                          <el-table-column label="状态" width="90">
                            <template #default="{ row: o }">
                              <el-tag size="small" :type="orderStatusTag(o.status)">{{ orderStatusLabel(o.status) }}</el-tag>
                            </template>
                          </el-table-column>
                        </el-table>
                      </template>
                      <template v-if="ct.quotes?.length">
                        <div style="margin: 4px 0 4px 24px; font-weight: 600; font-size: 13px;">关联报价</div>
                        <el-table :data="ct.quotes" size="small" stripe style="margin: 2px 0 8px 24px; width: calc(100% - 48px)">
                          <el-table-column prop="quote_no" label="报价编号" width="180" />
                          <el-table-column prop="project_name" label="项目名称" min-width="150" />
                          <el-table-column label="金额" width="120">
                            <template #default="{ row: q }">¥ {{ q.total_amount?.toFixed(2) }}</template>
                          </el-table-column>
                          <el-table-column label="状态" width="90">
                            <template #default="{ row: q }">
                              <el-tag size="small" :type="quoteStatusTag(q.status)">{{ quoteStatusLabel(q.status) }}</el-tag>
                            </template>
                          </el-table-column>
                        </el-table>
                      </template>
                    </template>
                  </el-table-column>
                  <el-table-column prop="contract_no" label="合同编号" width="180" />
                  <el-table-column prop="project_name" label="合同名称" min-width="180" />
                  <el-table-column prop="contract_type" label="合同类型" width="100" />
                  <el-table-column label="合同金额" width="130">
                    <template #default="{ row: ct }">¥ {{ ct.total_amount?.toFixed(2) }}</template>
                  </el-table-column>
                  <el-table-column label="已收" width="130">
                    <template #default="{ row: ct }">¥ {{ ct.paid_amount?.toFixed(2) }}</template>
                  </el-table-column>
                  <el-table-column label="欠款" width="130">
                    <template #default="{ row: ct }">
                      <span style="color: #e63946; font-weight: 600">¥ {{ ct.unpaid_amount?.toFixed(2) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="类型" width="80">
                    <template #default="{ row: ct }">
                      <el-tag v-if="ct.contract_type === '框架合同'" type="warning" size="small">框架</el-tag>
                      <el-tag v-else type="primary" size="small">常规</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" width="80">
                    <template #default="{ row: ct }">
                      <el-tag size="small" :type="contractStatusTag(ct.status)">{{ contractStatusLabel(ct.status) }}</el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </template>
              <!-- 该客户下未被合同关联的订单和报价 -->
              <template v-if="row.orders?.length || row.quotes?.length">
                <div style="margin: 8px 0 4px 48px; font-weight: 600; color: var(--ad-text-secondary);">独立订单 / 报价（未关联合同）</div>
                <template v-if="row.orders?.length">
                  <el-table :data="row.orders" size="small" stripe style="margin: 4px 0 8px 48px; width: calc(100% - 48px)">
                    <el-table-column prop="order_no" label="订单编号" width="180" />
                    <el-table-column prop="project_name" label="项目名称" min-width="180" />
                    <el-table-column label="订单金额" width="130">
                      <template #default="{ row: o }">¥ {{ o.total_amount?.toFixed(2) }}</template>
                    </el-table-column>
                    <el-table-column label="已收" width="130">
                      <template #default="{ row: o }">¥ {{ o.paid_amount?.toFixed(2) }}</template>
                    </el-table-column>
                    <el-table-column label="欠款" width="130">
                      <template #default="{ row: o }">
                        <span style="color: #e63946; font-weight: 600">¥ {{ o.unpaid_amount?.toFixed(2) }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="状态" width="100">
                      <template #default="{ row: o }">
                        <el-tag size="small" :type="orderStatusTag(o.status)">{{ orderStatusLabel(o.status) }}</el-tag>
                      </template>
                    </el-table-column>
                  </el-table>
                </template>
                <template v-if="row.quotes?.length">
                  <el-table :data="row.quotes" size="small" stripe style="margin: 4px 0 8px 48px; width: calc(100% - 48px)">
                    <el-table-column prop="quote_no" label="报价编号" width="180" />
                    <el-table-column prop="project_name" label="项目名称" min-width="180" />
                    <el-table-column label="金额" width="130">
                      <template #default="{ row: q }">¥ {{ q.total_amount?.toFixed(2) }}</template>
                    </el-table-column>
                    <el-table-column label="状态" width="100">
                      <template #default="{ row: q }">
                        <el-tag size="small" :type="quoteStatusTag(q.status)">{{ quoteStatusLabel(q.status) }}</el-tag>
                      </template>
                    </el-table-column>
                  </el-table>
                </template>
              </template>
            </template>
          </el-table-column>
          <el-table-column prop="customer_name" label="客户名称" min-width="180" />
          <el-table-column label="合同" width="60" align="center">
            <template #default="{ row }">{{ row.contract_count }}</template>
          </el-table-column>
          <el-table-column label="订单" width="60" align="center">
            <template #default="{ row }">{{ row.order_count }}</template>
          </el-table-column>
          <el-table-column label="报价" width="60" align="center">
            <template #default="{ row }">{{ row.quote_count }}</template>
          </el-table-column>
          <el-table-column label="合同总额" width="140">
            <template #default="{ row }">¥ {{ row.total_order_amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="已收金额" width="140">
            <template #default="{ row }">¥ {{ row.total_paid?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="欠款金额" width="140">
            <template #default="{ row }">
              <span style="color: #e63946; font-weight: 600">¥ {{ row.debt_amount?.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最后收款" width="120">
            <template #default="{ row }">{{ row.last_payment_date?.slice(0, 10) || '-' }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ===== Tab 2: 收款记录 ===== -->
      <el-tab-pane label="收款记录" name="payments">
        <div class="search-bar">
          <el-select v-model="filterOrderId" placeholder="筛选订单" clearable filterable style="width: 240px" @change="fetchPayments">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} — ${o.department || '-'} — ${o.project_name} — ¥${(o.total_amount || 0).toFixed(2)}`" :value="o.id" />
          </el-select>
          <el-select v-model="filterCustomerId" placeholder="筛选客户" clearable filterable style="width: 200px; margin-left: 12px" @change="fetchPayments">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button style="margin-left: 12px" @click="fetchPayments">搜索</el-button>
          <el-button type="danger" style="margin-left: auto" @click="openPaymentDialog()">登记收款</el-button>
        </div>

        <el-table :data="paymentList" v-loading="paymentLoading" stripe style="margin-top: 16px">
          <el-table-column prop="payment_no" label="收款编号" width="180" />
          <el-table-column prop="order_no" label="订单编号" width="160" />
          <el-table-column prop="customer_name" label="客户名称" width="140" />
          <el-table-column prop="project_name" label="项目名称" min-width="180" />
          <el-table-column label="金额" width="120">
            <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="payment_method" label="方式" width="100" />
          <el-table-column label="收款日期" width="120">
            <template #default="{ row }">{{ row.paid_at?.slice(0, 10) || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_voided ? 'danger' : 'success'" size="small">{{ row.is_voided ? '已作废' : '有效' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="160" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="!row.is_voided" text type="danger" size="small" @click="handleVoid(row)">作废</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="payPage"
          v-model:page-size="payPageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="payTotal"
          layout="total, sizes, prev, pager, next"
          style="margin-top: 16px; justify-content: flex-end"
          @change="fetchPayments"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 登记收款对话框（Tab 1 和 Tab 2 共用） -->
    <el-dialog v-model="showDialog" title="登记收款" width="480px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="订单">
          <el-select v-model="form.order_id" placeholder="选择订单" filterable style="width: 100%" @change="onOrderSelect">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} — ${o.department || '-'} — ${o.project_name} — ¥${(o.total_amount || 0).toFixed(2)}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款金额">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
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
        <el-button type="danger" :loading="saving" @click="handleCreate">确认收款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { getPayments, createPayment, voidPayment, getCustomerDebt } from '@/api/payments'
import { getOrders } from '@/api/orders'
import { getCustomers } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { PaymentResponse, OrderListResponse, CustomerResponse, CustomerDebtItem, CustomerDebtOrder } from '@/types/api'

// ── Tab state ──

const activeTab = ref('debt')

// ── Tab 1: 客户欠款 ──

const debtLoading = ref(false)
const debtList = ref<CustomerDebtItem[]>([])

const stats = computed(() => {
  const totalOrder = debtList.value.reduce((s, c) => s + c.total_order_amount, 0)
  const totalPaid = debtList.value.reduce((s, c) => s + c.total_paid, 0)
  const totalDebt = debtList.value.reduce((s, c) => s + c.debt_amount, 0)
  return { totalOrder, totalPaid, totalDebt }
})

function contractStatusTag(status: string): "" | "success" | "warning" | "info" | "danger" | "primary" {
  const map: Record<string, "" | "success" | "warning" | "info" | "danger" | "primary"> = {
    draft: 'info', pending_sign: 'warning', active: 'success', completed: 'success', terminated: 'danger',
  }
  return map[status] || 'info'
}

function contractStatusLabel(status: string) {
  const map: Record<string, string> = {
    draft: '草稿', pending_sign: '待签约', active: '执行中', completed: '已完成', terminated: '已终止',
  }
  return map[status] || status
}

function orderStatusTag(status: string) {
  const map: Record<string, string> = {
    pending_confirm: 'warning', confirmed: 'primary', in_progress: 'warning',
    in_production: '', in_installation: '', completed: 'success', cancelled: 'danger',
  }
  return map[status] || 'info'
}

function orderStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  return map[status] || status
}

function quoteStatusTag(status: string): "" | "success" | "warning" | "info" | "danger" | "primary" {
  const map: Record<string, "" | "success" | "warning" | "info" | "danger" | "primary"> = {
    draft: 'info', confirmed: 'success', converted: 'info', cancelled: 'danger',
  }
  return map[status] || 'info'
}

function quoteStatusLabel(status: string) {
  const map: Record<string, string> = {
    draft: '草稿', confirmed: '已确认', converted: '已转订单', cancelled: '已取消',
  }
  return map[status] || status
}

async function fetchDebts() {
  debtLoading.value = true
  try {
    debtList.value = await getCustomerDebt()
  } catch {
    // handled by interceptor
  } finally { debtLoading.value = false }
}

// ── Tab 2: 收款记录 ──

const paymentLoading = ref(false)
const saving = ref(false)
const paymentList = ref<PaymentResponse[]>([])
const payTotal = ref(0)
const payPage = ref(1)
const payPageSize = ref(20)
const filterOrderId = ref('')
const filterCustomerId = ref('')
const orderOptions = ref<OrderListResponse[]>([])
const customerOptions = ref<CustomerResponse[]>([])

async function fetchPayments() {
  paymentLoading.value = true
  try {
    const data = await getPayments({
      page: payPage.value,
      page_size: payPageSize.value,
      order_id: filterOrderId.value || undefined,
      customer_id: filterCustomerId.value || undefined,
    })
    paymentList.value = data.items
    payTotal.value = data.total
  } finally { paymentLoading.value = false }
}

async function loadOptions() {
  const [oRes, cRes] = await Promise.all([
    getOrders({ page_size: 200 }),
    getCustomers({ page_size: 200 }),
  ])
  orderOptions.value = oRes.items
  customerOptions.value = cRes.items
}

// ── Shared: 登记收款对话框 ──

const showDialog = ref(false)
const form = reactive({
  order_id: '',
  customer_id: '',
  amount: 0,
  payment_method: '',
  paid_at: '',
  remark: '',
})

function onOrderSelect(oid: string) {
  const o = orderOptions.value.find(o => o.id === oid)
  if (o) form.customer_id = o.customer_id
}

/** Open the payment dialog, optionally pre-filling the order from Tab 1's expanded row */
function openPaymentDialog(order?: CustomerDebtOrder | OrderListResponse) {
  if (order) {
    form.order_id = order.id
    onOrderSelect(order.id)
  }
  showDialog.value = true
}

async function handleCreate() {
  saving.value = true
  try {
    const o = orderOptions.value.find(o => o.id === form.order_id)
    await createPayment({
      ...form,
      customer_id: form.customer_id || o?.customer_id,
    })
    ElMessage.success('收款登记成功')
    showDialog.value = false
    Object.assign(form, { order_id: '', customer_id: '', amount: 0, payment_method: '', paid_at: '', remark: '' })
    // Refresh both tabs
    fetchPayments()
    fetchDebts()
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
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }

.stat-card { text-align: center; border: 1px solid var(--ad-border); }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--ad-text); }

/* Fix input-number width in dialog */
:deep(.el-dialog .el-input-number) { width: 100%; }
</style>
