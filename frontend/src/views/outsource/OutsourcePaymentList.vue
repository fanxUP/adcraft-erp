<template>
  <AppPage>
    <template #header>
      <PageHeader title="外协任务付款" description="统一查看外协应付金额、付款状态和付款记录。" />
    </template>

    <template #toolbar>
      <PageToolbar aria-label="外协付款筛选">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已结算" value="settled" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="vendorFilter" placeholder="外协商" filterable clearable style="width: 180px; margin-left: 8px;">
        <el-option v-for="v in vendors" :key="v.id" :label="v.name" :value="v.id" />
      </el-select>
      <el-button @click="fetchData" style="margin-left: 12px" type="primary">搜索</el-button>
      </PageToolbar>
    </template>

    <!-- 任务付款汇总列表 -->
    <DataTableShell :state="tableState" aria-label="外协任务付款列表">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="taskList" stripe>
      <el-table-column prop="task_no" label="任务编号" width="180" />
      <el-table-column prop="vendor_name" label="外协商" width="140" />
      <el-table-column label="项目" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.related_project_name">{{ row.related_project_name }}</span>
          <span v-else style="color: #999">-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusTag :status="row.status_view || row.status" size="sm" />
        </template>
      </el-table-column>
      <el-table-column v-if="canViewOutsourceCost" prop="total_amount" label="总金额" width="120" align="right">
        <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column v-if="canViewOutsourceCost" label="已付金额" width="120" align="right">
        <template #default="{ row }">
          <span class="text-success">{{ formatMoney(row.paid_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="canViewOutsourceCost" label="未付金额" width="120" align="right">
        <template #default="{ row }">
          <span v-if="row.unpaid_amount > 0" class="text-danger">{{ formatMoney(row.unpaid_amount) }}</span>
          <span v-else class="text-success">已结清</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button v-if="canCreatePayment && row.unpaid_amount > 0 && row.status !== 'cancelled' && row.status !== 'settled'" size="small" @click="handlePay(row)">付款</el-button>
          <el-button text type="primary" @click="handleViewPayments(row)">付款记录</el-button>
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

    <!-- 付款对话框 -->
    <el-dialog v-model="payDialogVisible" title="外协付款" width="500px" :close-on-click-modal="false">
      <div v-if="payTask" class="pay-summary">
        <div class="pay-summary-row">
          <span class="label">外协商：</span>
          <span class="value">{{ payTask.vendor_name }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">任务编号：</span>
          <span class="value">{{ payTask.task_no }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">项目名称：</span>
          <span class="value">{{ payTask.related_project_name || '-' }}</span>
        </div>
        <div class="pay-divider"></div>
        <div v-if="canViewOutsourceCost" class="pay-summary-row">
          <span class="label">总金额：</span>
          <span class="value total">{{ formatMoney(payTask.total_amount) }}</span>
        </div>
        <div v-if="canViewOutsourceCost" class="pay-summary-row">
          <span class="label">已付金额：</span>
          <span class="value paid">{{ formatMoney(payTask.paid_amount) }}</span>
        </div>
        <div v-if="canViewOutsourceCost" class="pay-summary-row">
          <span class="label">待付金额：</span>
          <span class="value unpaid">{{ formatMoney(payTask.unpaid_amount) }}</span>
        </div>
        <div class="pay-divider"></div>
      </div>
      <el-form ref="payFormRef" :model="payForm" :rules="payRules" label-width="100px">
        <el-form-item label="付款金额" prop="amount">
          <el-input-number v-model="payForm.amount" :min="0.01" :max="payTask?.unpaid_amount || 0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="付款方式" prop="payment_method">
          <el-select v-model="payForm.payment_method" clearable style="width: 100%">
            <el-option label="银行转账" value="bank_transfer" />
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="现金" value="cash" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款公司">
          <el-input v-model="payForm.payee_company_name" placeholder="收款公司名称（可选）" />
        </el-form-item>
        <el-form-item label="付款日期">
          <el-date-picker v-model="payForm.paid_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="payForm.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payDialogVisible = false">取消</el-button>
        <el-button v-if="canCreatePayment" :loading="paySaving" @click="handlePaySubmit" type="primary">确认付款</el-button>
      </template>
    </el-dialog>

    <!-- 付款记录对话框 -->
    <el-dialog v-model="recordDialogVisible" :title="'付款记录 - ' + (recordTask?.task_no || '')" width="700px" :close-on-click-modal="false">
      <el-table :data="paymentRecords" stripe empty-text="暂无付款记录">
        <el-table-column prop="payment_no" label="付款编号" width="180" />
        <el-table-column v-if="canViewOutsourceCost" prop="amount" label="金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column label="付款方式" width="120">
          <template #default="{ row }">{{ paymentMethodLabel(row.payment_method) }}</template>
        </el-table-column>
        <el-table-column prop="payee_company_name" label="收款公司" min-width="150" show-overflow-tooltip />
        <el-table-column prop="paid_at" label="付款日期" width="120" />
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button @click="recordDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { computed } from 'vue'
import { formatMoney } from '@/utils/format'
import {
  getOutsourceVendors, getOutsourceTasks, getOutsourceTaskPaymentSummary,
  createOutsourcePayment,
} from '@/api/outsource'
import type { OutsourcePaymentSummaryItem, OutsourceTaskPaymentSummary } from '@/api/outsource'
import { ElMessage } from 'element-plus'
import { OutsourceTaskResponse } from '@/types/api'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel, StatusTag } from '@/components/ui'
import { useAuthStore } from '@/stores/auth'

const loading = ref(false)
const taskList = ref<OutsourceTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const vendorFilter = ref('')
const vendors = ref<{id: string; name: string}[]>([])
const loadError = ref(false)
const authStore = useAuthStore()
const canViewOutsourceCost = computed(() => authStore.hasPermission('finance:view_cost'))
const canCreatePayment = computed(() => authStore.hasPermission('outsource_payment:create'))

const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return taskList.value.length ? 'ready' : 'empty'
})

// 付款对话框
const payDialogVisible = ref(false)
const paySaving = ref(false)
type PaymentTarget = Omit<OutsourceTaskPaymentSummary, 'payments'>
const payTask = ref<PaymentTarget | null>(null)
const payForm = ref({ amount: 0, payment_method: 'bank_transfer', payee_company_name: '', paid_at: '', remark: '' })
const payRules = { amount: [{ required: true, message: '请输入付款金额', trigger: 'blur' }] }

// 付款记录对话框
const recordDialogVisible = ref(false)
const recordTask = ref<OutsourceTaskResponse | null>(null)
const paymentRecords = ref<OutsourcePaymentSummaryItem[]>([])

function paymentMethodLabel(val: string | null) {
  const map: Record<string, string> = { bank_transfer: '银行转账', wechat: '微信', alipay: '支付宝', cash: '现金' }
  return map[val || ''] || val || '-'
}

async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 100 })
    vendors.value = data.items
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const data = await getOutsourceTasks({
      page: page.value, page_size: pageSize.value,
      status: statusFilter.value || undefined,
      vendor_id: vendorFilter.value || undefined,
    })
    taskList.value = data.items
    total.value = data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function handlePay(row: OutsourceTaskResponse) {
  try {
    const summary = await getOutsourceTaskPaymentSummary(row.id)
    payTask.value = summary
    payForm.value = {
      amount: summary.unpaid_amount > 0 ? summary.unpaid_amount : 0,
      payment_method: 'bank_transfer',
      paid_at: '',
      remark: '',
      payee_company_name: '',
    }
    payDialogVisible.value = true
  } catch {
    payTask.value = {
      task_id: row.id,
      task_no: row.task_no,
      vendor_id: row.vendor_id,
      vendor_name: row.vendor_name || null,
      related_project_name: row.related_project_name || null,
      total_amount: row.total_amount,
      paid_amount: row.paid_amount,
      unpaid_amount: row.unpaid_amount,
    }
    payForm.value = {
      amount: row.unpaid_amount > 0 ? row.unpaid_amount : 0,
      payment_method: 'bank_transfer',
      paid_at: '',
      remark: '',
      payee_company_name: '',
    }
    payDialogVisible.value = true
  }
}

async function handlePaySubmit() {
  if (!payTask.value) return
  paySaving.value = true
  try {
    await createOutsourcePayment({
      vendor_id: payTask.value.vendor_id,
      task_id: payTask.value.task_id,
      amount: payForm.value.amount,
      payment_method: payForm.value.payment_method || undefined,
      payee_company_name: payForm.value.payee_company_name || undefined,
      paid_at: payForm.value.paid_at || undefined,
      remark: payForm.value.remark || undefined,
    })
    ElMessage.success('付款成功')
    payDialogVisible.value = false
    await fetchData()
  } finally {
    paySaving.value = false
  }
}

async function handleViewPayments(row: OutsourceTaskResponse) {
  recordTask.value = row
  try {
    const summary = await getOutsourceTaskPaymentSummary(row.id)
    paymentRecords.value = summary.payments || []
  } catch {
    paymentRecords.value = []
  }
  recordDialogVisible.value = true
}

onMounted(() => { fetchData(); loadVendors() })
</script>

<style scoped>
.pay-summary {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.pay-summary-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 14px;
}
.pay-summary-row .label { color: var(--el-text-color-secondary); }
.pay-summary-row .value { font-weight: 500; }
.pay-summary-row .value.total { font-weight: 600; color: var(--el-color-primary); }
.pay-summary-row .value.paid { color: var(--el-color-success); }
.pay-summary-row .value.unpaid { color: var(--el-color-danger); font-weight: 600; }
.pay-divider {
  height: 1px;
  background: var(--el-border-color-light);
  margin: 8px 0;
}
</style>
