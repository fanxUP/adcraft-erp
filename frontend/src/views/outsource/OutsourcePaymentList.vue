<template>
  <div class="page">
    <div class="page-header">
      <h2>外协任务付款</h2>
    </div>

    <div class="search-bar">
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
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <!-- 任务付款汇总列表 -->
    <el-table :data="taskList" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无外协任务">
      <el-table-column prop="task_no" label="任务编号" width="140" />
      <el-table-column prop="vendor_name" label="外协商" width="140" />
      <el-table-column label="项目" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.related_project_name">{{ row.related_project_name }}</span>
          <span v-else style="color: #999">-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total_amount" label="总金额" width="120" align="right">
        <template #default="{ row }">¥{{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="已付金额" width="120" align="right">
        <template #default="{ row }">
          <span style="color: var(--el-color-success)">¥{{ row.paid_amount?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="未付金额" width="120" align="right">
        <template #default="{ row }">
          <span v-if="row.unpaid_amount > 0" style="color: var(--el-color-danger); font-weight: 600">¥{{ row.unpaid_amount?.toFixed(2) }}</span>
          <span v-else style="color: var(--el-color-success)">已结清</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button v-if="row.unpaid_amount > 0 && row.status !== 'cancelled' && row.status !== 'settled'" type="warning" size="small" @click="handlePay(row)">付款</el-button>
          <el-button text type="primary" @click="handleViewPayments(row)">付款记录</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

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
        <div class="pay-summary-row">
          <span class="label">总金额：</span>
          <span class="value total">¥{{ payTask.total_amount?.toFixed(2) }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">已付金额：</span>
          <span class="value paid">¥{{ payTask.paid_amount?.toFixed(2) }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">待付金额：</span>
          <span class="value unpaid">¥{{ payTask.unpaid_amount?.toFixed(2) }}</span>
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
        <el-button type="danger" :loading="paySaving" @click="handlePaySubmit">确认付款</el-button>
      </template>
    </el-dialog>

    <!-- 付款记录对话框 -->
    <el-dialog v-model="recordDialogVisible" :title="'付款记录 - ' + (recordTask?.task_no || '')" width="700px" :close-on-click-modal="false">
      <el-table :data="paymentRecords" stripe empty-text="暂无付款记录">
        <el-table-column prop="payment_no" label="付款编号" width="160" />
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template #default="{ row }">¥{{ row.amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="付款方式" width="120">
          <template #default="{ row }">{{ paymentMethodLabel(row.payment_method) }}</template>
        </el-table-column>
        <el-table-column prop="paid_at" label="付款日期" width="120" />
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button @click="recordDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getOutsourceVendors, getOutsourceTasks, getOutsourceTaskPaymentSummary,
  createOutsourcePayment,
} from '@/api/outsource'
import { ElMessage } from 'element-plus'
import { OutsourceTaskResponse } from '@/types/api'

const loading = ref(false)
const taskList = ref<OutsourceTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const vendorFilter = ref('')
const vendors = ref<{id: string; name: string}[]>([])

// 付款对话框
const payDialogVisible = ref(false)
const paySaving = ref(false)
const payTask = ref<OutsourceTaskResponse | null>(null)
const payForm = ref({ amount: 0, payment_method: 'bank_transfer', paid_at: '', remark: '' })
const payRules = { amount: [{ required: true, message: '请输入付款金额', trigger: 'blur' }] }

// 付款记录对话框
const recordDialogVisible = ref(false)
const recordTask = ref<OutsourceTaskResponse | null>(null)
const paymentRecords = ref<{payment_no: string; amount: number; payment_method: string; paid_at: string; remark: string}[]>([])

function paymentMethodLabel(val: string | null) {
  const map: Record<string, string> = { bank_transfer: '银行转账', wechat: '微信', alipay: '支付宝', cash: '现金' }
  return map[val || ''] || val || '-'
}

function statusType(val: string) {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', settled: '', cancelled: 'danger' }
  return (map[val] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function statusLabel(val: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消' }
  return map[val] || val
}

async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 100 })
    vendors.value = data.items
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getOutsourceTasks({
      page: page.value, page_size: pageSize.value,
      status: statusFilter.value || undefined,
      vendor_id: vendorFilter.value || undefined,
    })
    taskList.value = data.items
    total.value = data.total
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
    payTask.value = row
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
      task_id: payTask.value.id,
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
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }

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
