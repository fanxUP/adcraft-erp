<template>
  <AppPage>
    <template #header>
      <PageHeader
        title="应付管理"
        description="统一查看项目成本和经营支出的待付款金额，并登记实际付款流水。"
      >
        <template #meta>
          <div class="summary-bar">
            <span class="text-warning">当前页待付款：{{ formatMoney(pendingTotal) }}</span>
          </div>
        </template>
      </PageHeader>
    </template>

    <template #toolbar>
      <PageToolbar aria-label="应付管理筛选">
        <el-form :model="filters" inline>
          <el-form-item label="关键词">
            <el-input
              v-model="filters.keyword"
              placeholder="编号/订单/项目/应付对象"
              clearable
              style="width: 230px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="来源">
            <el-select v-model="filters.source_type" clearable placeholder="全部来源" style="width: 140px" @change="handleSearch">
              <el-option label="项目成本" value="project_cost" />
              <el-option label="经营支出" value="expense" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px" @change="handleSearch">
              <el-option label="待付款" value="unpaid" />
              <el-option label="部分付款" value="partial" />
              <el-option label="已付款" value="paid" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </PageToolbar>
    </template>

    <DataTableShell :state="tableState" aria-label="应付管理列表">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="list" stripe>
        <el-table-column label="来源" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.source_type === 'project_cost' ? 'primary' : 'info'">
              {{ row.source_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_no" label="来源编号" width="185" />
        <el-table-column prop="order_no" label="订单编号" width="180" show-overflow-tooltip />
        <el-table-column prop="project_name" label="项目名称" min-width="190" show-overflow-tooltip />
        <el-table-column prop="customer_name" label="客户" min-width="150" show-overflow-tooltip />
        <el-table-column prop="payee_name" label="应付对象" min-width="150" show-overflow-tooltip />
        <el-table-column prop="category" label="支出类别" width="120" show-overflow-tooltip />
        <el-table-column label="支出总额" width="125" align="right">
          <template #default="{ row }">{{ formatMoney(row.source_total_amount) }}</template>
        </el-table-column>
        <el-table-column label="应付总额" width="125" align="right">
          <template #default="{ row }">{{ formatMoney(row.payable_total_amount) }}</template>
        </el-table-column>
        <el-table-column label="已付款" width="125" align="right">
          <template #default="{ row }">{{ formatMoney(row.paid_amount) }}</template>
        </el-table-column>
        <el-table-column label="待付款" width="125" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-warning': row.remaining_amount > 0 }">{{ formatMoney(row.remaining_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="105" align="center">
          <template #default="{ row }"><StatusTag :status="row.status_view || row.status" size="sm" /></template>
        </el-table-column>
        <el-table-column label="日期" width="120">
          <template #default="{ row }">{{ formatDate(row.source_date) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.capabilities?.pay?.allowed ?? (row.remaining_amount > 0)"
              size="small"
              type="primary"
              @click="openPayment(row as PayableResponse)"
            >
              登记付款
            </el-button>
            <el-button size="small" text type="primary" @click="openHistory(row as PayableResponse)">付款流水</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </template>
    </DataTableShell>

    <el-dialog v-model="showPayment" title="登记付款" width="500px" :close-on-click-modal="false">
      <el-form :model="paymentForm" label-width="100px">
        <el-form-item label="应付来源">
          <div>{{ paymentTarget?.source_label }} · {{ paymentTarget?.source_no }}</div>
        </el-form-item>
        <el-form-item label="应付对象">
          <div>{{ paymentTarget?.payee_name || '-' }}</div>
        </el-form-item>
        <el-form-item label="待付款">
          <span class="text-warning">{{ formatMoney(paymentTarget?.remaining_amount || 0) }}</span>
        </el-form-item>
        <el-form-item label="本次付款" required>
          <el-input-number
            v-model="paymentForm.amount"
            :min="0.01"
            :max="paymentTarget?.remaining_amount || 0.01"
            :precision="2"
            :controls="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="付款方式" required>
          <el-select v-model="paymentForm.payment_method" style="width: 100%">
            <el-option v-for="method in PAYMENT_METHODS" :key="method" :label="method" :value="method" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款日期" required>
          <el-date-picker v-model="paymentForm.paid_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="paymentForm.remark" type="textarea" :rows="2" placeholder="付款备注…" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPayment = false">取消</el-button>
        <el-button type="primary" :loading="savingPayment" @click="handlePayment">确认登记</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showHistory" title="付款流水" width="720px">
      <div v-if="historyTarget" class="history-summary">
        <span>{{ historyTarget.source_label }} · {{ historyTarget.source_no }}</span>
        <span>应付 {{ formatMoney(historyTarget.payable_total_amount) }}</span>
        <span>已付 {{ formatMoney(historyTarget.paid_amount) }}</span>
        <span class="text-warning">待付 {{ formatMoney(historyTarget.remaining_amount) }}</span>
      </div>
      <el-empty v-if="!historyLoading && !historyRows.length" description="暂无付款流水" />
      <el-table v-else v-loading="historyLoading" :data="historyRows" stripe>
        <el-table-column prop="payment_no" label="付款编号" width="190" />
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="payment_method" label="付款方式" width="120" />
        <el-table-column label="付款日期" width="120">
          <template #default="{ row }">{{ formatDate(row.paid_at) || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :status="row.is_voided ? 'cancelled' : 'paid'" :label="row.is_voided ? '已撤销' : '有效'" size="sm" />
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="110">
          <template #default="{ row }">
            <el-button v-if="!row.is_voided" text type="danger" size="small" @click="handleVoid(row.id)">撤销</el-button>
            <span v-else class="muted">{{ row.void_reason || '已撤销' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel, StatusTag } from '@/components/ui'
import { createPayablePayment, getPayable, getPayables, voidPayablePayment } from '@/api/payments'
import type { PayablePaymentResponse, PayableResponse } from '@/types/api'
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'

const PAYMENT_METHODS = ['现金支付', '微信支付', '转账支付', '对公支付', '其它支付']

const loading = ref(false)
const savingPayment = ref(false)
const historyLoading = ref(false)
const loadError = ref(false)
const list = ref<PayableResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const showPayment = ref(false)
const showHistory = ref(false)
const paymentTarget = ref<PayableResponse | null>(null)
const historyTarget = ref<PayableResponse | null>(null)
const historyRows = ref<PayablePaymentResponse[]>([])

const filters = reactive({
  keyword: '',
  source_type: undefined as string | undefined,
  status: undefined as string | undefined,
})

const paymentForm = reactive({
  amount: 0,
  payment_method: '转账支付',
  paid_at: new Date().toISOString().slice(0, 10),
  remark: '',
})

const pendingTotal = computed(() => list.value.reduce((sum, row) => sum + (row.remaining_amount || 0), 0))
const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return list.value.length ? 'ready' : 'empty'
})

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const data = await getPayables({
      page: page.value,
      page_size: pageSize.value,
      ...(filters.keyword ? { keyword: filters.keyword } : {}),
      ...(filters.source_type ? { source_type: filters.source_type } : {}),
      ...(filters.status ? { status: filters.status } : {}),
    })
    list.value = data.items
    total.value = data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleReset() {
  filters.keyword = ''
  filters.source_type = undefined
  filters.status = undefined
  page.value = 1
  fetchData()
}

function openPayment(row: PayableResponse) {
  paymentTarget.value = row
  paymentForm.amount = row.remaining_amount
  paymentForm.payment_method = '转账支付'
  paymentForm.paid_at = new Date().toISOString().slice(0, 10)
  paymentForm.remark = ''
  showPayment.value = true
}

async function handlePayment() {
  if (!paymentTarget.value || paymentForm.amount <= 0) return
  savingPayment.value = true
  try {
    await createPayablePayment(paymentTarget.value.source_type, paymentTarget.value.source_id, {
      amount: paymentForm.amount,
      payment_method: paymentForm.payment_method,
      paid_at: paymentForm.paid_at,
      remark: paymentForm.remark || undefined,
    })
    ElMessage.success('付款已登记，应付余额已重新计算')
    showPayment.value = false
    await fetchData()
  } catch {
    // API interceptor displays the server-side business message.
  } finally {
    savingPayment.value = false
  }
}

async function openHistory(row: PayableResponse) {
  historyTarget.value = row
  historyRows.value = []
  showHistory.value = true
  historyLoading.value = true
  try {
    const data = await getPayable(row.source_type, row.source_id)
    historyTarget.value = data
    historyRows.value = data.payments || []
  } catch {
    // API interceptor displays the error.
  } finally {
    historyLoading.value = false
  }
}

async function handleVoid(paymentId: string) {
  if (!historyTarget.value) return
  try {
    const result = await ElMessageBox.prompt('请输入撤销原因', '撤销付款流水', {
      confirmButtonText: '确认撤销',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：付款金额录入错误',
      inputValidator: value => value?.trim() ? true : '撤销原因不能为空',
    })
    await voidPayablePayment(
      historyTarget.value.source_type,
      historyTarget.value.source_id,
      paymentId,
      { void_reason: result.value },
    )
    ElMessage.success('付款流水已撤销，应付余额已重新计算')
    await openHistory(historyTarget.value)
    await fetchData()
  } catch {
    // User cancellation and API errors are intentionally silent here.
  }
}

onMounted(fetchData)
</script>

<style scoped>
.summary-bar { display: flex; align-items: center; gap: 8px; }
.text-warning { color: var(--el-color-warning); font-weight: 600; }
.history-summary { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 16px; color: var(--ad-text-secondary); }
.muted { color: var(--ad-text-secondary); font-size: 12px; }
</style>
