<template>
  <div class="page">
    <div class="page-header">
      <h2>外协任务</h2>
      <div style="display: flex; gap: 8px;">
        <el-button type="danger" @click="handleCreate">新建外协任务</el-button>
        <el-button v-if="isAdmin" @click="$router.push('/outsource/tasks/recycle')">回收站</el-button>
      </div>
    </div>

    <div class="search-bar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已结算" value="settled" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无外协任务">
      <el-table-column prop="task_no" label="任务编号" width="140" />
      <el-table-column prop="vendor_name" label="外协商" width="140" />
      <el-table-column label="任务" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.related_project_name">{{ row.related_project_name }}</span>
          <span v-else style="color: #999">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
      <el-table-column prop="total_amount" label="总金额" width="110" align="right">
        <template #default="{ row }">¥{{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="已付" width="100" align="right">
        <template #default="{ row }">
          <span style="color: var(--el-color-success)">¥{{ row.paid_amount?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="未付" width="100" align="right">
        <template #default="{ row }">
          <span v-if="row.unpaid_amount > 0" style="color: var(--el-color-danger)">¥{{ row.unpaid_amount?.toFixed(2) }}</span>
          <span v-else style="color: var(--el-color-success)">已结清</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="240">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row as OutsourceTaskResponse)">编辑</el-button>
          <el-button v-if="row.status === 'pending'" text type="primary" @click="handleUpdateStatus(row as OutsourceTaskResponse, 'in_progress')">开始</el-button>
          <el-button v-if="row.status === 'in_progress'" text type="success" @click="handleUpdateStatus(row as OutsourceTaskResponse, 'completed')">完成</el-button>
          <el-button v-if="row.unpaid_amount > 0 && row.status !== 'cancelled' && row.status !== 'settled'" text type="warning" @click="handlePay(row as OutsourceTaskResponse)">付款</el-button>
          <el-button v-if="isAdmin && row.status === 'completed'" text type="warning" @click="handleRevert(row as OutsourceTaskResponse)">退回</el-button>
          <el-button v-if="isAdmin && !['completed', 'settled', 'cancelled'].includes(row.status)" text type="danger" @click="handleCancel(row as OutsourceTaskResponse)">取消</el-button>
          <el-button v-if="isAdmin && row.status === 'cancelled'" text type="danger" @click="handleDelete(row as OutsourceTaskResponse)">删除</el-button>
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

    <!-- 新建/编辑任务对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑外协任务' : '新建外协任务'" width="550px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="外协商" prop="vendor_id">
          <el-select v-model="form.vendor_id" filterable clearable style="width: 100%">
            <el-option v-for="v in vendors" :key="v.id" :label="v.name" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联任务" prop="related_doc_id">
          <el-select v-model="form.related_doc_id" filterable clearable placeholder="请选择关联的报价单或订单" style="width: 100%" @change="onRelatedDocChange">
            <el-option-group label="报价单">
              <el-option v-for="q in quotes" :key="'q_' + q.id" :label="q.label" :value="q.id" />
            </el-option-group>
            <el-option-group label="订单">
              <el-option v-for="o in orders" :key="'o_' + o.id" :label="o.label" :value="o.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" clearable style="width: 100%">
            <el-option label="制作" value="production" />
            <el-option label="安装" value="installation" />
            <el-option label="设计" value="design" />
            <el-option label="运输" value="transport" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价" prop="unit_price">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  getOutsourceVendors, getOutsourceTasks, getOutsourceTaskPaymentSummary,
  createOutsourceTask, updateOutsourceTask, createOutsourcePayment,
  cancelOutsourceTask, revertOutsourceTask, deleteOutsourceTask,
  getQuotesForDropdown, getOrdersForDropdown,
} from '@/api/outsource'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { OutsourceTaskResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<OutsourceTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const vendors = ref<{id: string; name: string}[]>([])
const quotes = ref<{id: string; label: string; project_name: string}[]>([])
const orders = ref<{id: string; label: string; project_name: string}[]>([])

const form = reactive({
  vendor_id: '', related_doc_id: '', related_doc_type: '', task_type: 'production',
  description: '', quantity: 1, unit_price: 0, remark: '',
})
const rules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  related_doc_id: [{ required: true, message: '请选择关联任务', trigger: 'change' }],
}

// 付款对话框
const payDialogVisible = ref(false)
const paySaving = ref(false)
const payTask = ref<OutsourceTaskResponse | null>(null)
const payForm = reactive({
  amount: 0, payment_method: 'bank_transfer', paid_at: '', remark: '',
})
const payRules = {
  amount: [{ required: true, message: '请输入付款金额', trigger: 'blur' }],
}

// 是否管理员（从 localStorage 取角色）
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

function statusType(val: string) {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', settled: '', cancelled: 'danger' }
  return (map[val] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function statusLabel(val: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消' }
  return map[val] || val
}

async function loadQuotes() {
  try { quotes.value = await getQuotesForDropdown() } catch { /* ignore */ }
}
async function loadOrders() {
  try { orders.value = await getOrdersForDropdown() } catch { /* ignore */ }
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
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onRelatedDocChange(val: string) {
  if (!val) { form.related_doc_type = ''; return }
  const foundQuote = quotes.value.find(q => q.id === val)
  form.related_doc_type = foundQuote ? 'quote' : 'order'
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { vendor_id: '', related_doc_id: '', related_doc_type: '', task_type: 'production', description: '', quantity: 1, unit_price: 0, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: OutsourceTaskResponse) {
  editingId.value = row.id
  Object.assign(form, {
    vendor_id: row.vendor_id, related_doc_id: row.related_doc_id || '', related_doc_type: row.related_doc_type || '',
    task_type: row.task_type, description: row.description,
    quantity: row.quantity, unit_price: row.unit_price, remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateOutsourceTask(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createOutsourceTask(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleUpdateStatus(row: OutsourceTaskResponse, status: string) {
  try {
    await updateOutsourceTask(row.id, { status })
    ElMessage.success(`已更新为：${statusLabel(status)}`)
    await fetchData()
  } catch { /* ignore */ }
}

async function handlePay(row: OutsourceTaskResponse) {
  // 先刷新最新的付款摘要
  try {
    const summary = await getOutsourceTaskPaymentSummary(row.id)
    payTask.value = { ...summary, id: summary.task_id }
    payForm.amount = summary.unpaid_amount > 0 ? summary.unpaid_amount : 0
    payForm.payment_method = 'bank_transfer'
    payForm.paid_at = ''
    payForm.remark = ''
    payForm.payee_company_name = ''
    payDialogVisible.value = true
  } catch {
    // fallback: use row data
    payTask.value = row
    payForm.amount = row.unpaid_amount > 0 ? row.unpaid_amount : 0
    payForm.payment_method = 'bank_transfer'
    payForm.paid_at = ''
    payForm.remark = ''
    payForm.payee_company_name = ''
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
      amount: payForm.amount,
      payment_method: payForm.payment_method || undefined,
      payee_company_name: payForm.payee_company_name || undefined,
      paid_at: payForm.paid_at || undefined,
      remark: payForm.remark || undefined,
    })
    ElMessage.success('付款成功')
    payDialogVisible.value = false
    await fetchData()
  } finally {
    paySaving.value = false
  }
}

async function handleCancel(row: OutsourceTaskResponse) {
  try {
    await ElMessageBox.confirm(`确认取消外协任务「${row.task_no}」？`, '确认', {
      confirmButtonText: '确认取消', cancelButtonText: '取消', type: 'warning',
    })
    await cancelOutsourceTask(row.id)
    ElMessage.success('外协任务已取消')
    await fetchData()
  } catch { /* ignore */ }
}

async function handleRevert(row: OutsourceTaskResponse) {
  try {
    await ElMessageBox.confirm(`确认退回外协任务「${row.task_no}」为进行中？`, '确认', {
      confirmButtonText: '确认退回', cancelButtonText: '取消', type: 'warning',
    })
    await revertOutsourceTask(row.id)
    ElMessage.success('外协任务已退回为进行中')
    await fetchData()
  } catch { /* ignore */ }
}

async function handleDelete(row: OutsourceTaskResponse) {
  try {
    await ElMessageBox.confirm(`确认删除外协任务「${row.task_no}」？删除后不可恢复。`, '确认', {
      confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteOutsourceTask(row.id)
    ElMessage.success('外协任务已删除')
    await fetchData()
  } catch { /* ignore */ }
}

onMounted(() => {
  fetchData(); loadVendors(); loadQuotes(); loadOrders()
})
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
