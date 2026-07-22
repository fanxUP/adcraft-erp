<template>
  <div class="page">
    <div class="page-header">
      <h2>合同管理</h2>
      <div>
        <el-button type="primary" @click="handleCreate">新建合同</el-button>
      </div>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="合同编号/项目名称/客户" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="草稿" value="draft" />
            <el-option label="已生效" value="active" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="contract_no" label="合同编号" width="180" />
      <el-table-column prop="contract_type" label="合同类型" width="100" />
      <el-table-column prop="customer_name" label="客户名称" width="160" />
      <el-table-column prop="department" label="部门/科室" width="120" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column prop="source" label="来源" width="100" />
      <el-table-column label="合同金额" width="140">
        <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="已收金额" width="120">
        <template #default="{ row }">¥ {{ row.paid_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="未收金额" width="120">
        <template #default="{ row }">
          <span v-if="row.unpaid_amount > 0" style="color: #f56c6c">¥ {{ row.unpaid_amount?.toFixed(2) }}</span>
          <span v-else>¥ {{ row.unpaid_amount?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="签约日期" width="120">
        <template #default="{ row }">{{ row.sign_date?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="100">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleDetail(row)">详情</el-button>
          <el-button text type="success" @click="handleEdit(row)">编辑</el-button>
          <el-button
            text type="warning"
            :disabled="!canChangeStatus(row)"
            @click="handleStatusChange(row)"
          >状态</el-button>
          <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新建/编辑合同对话框 -->
    <el-dialog
      v-model="formVisible"
      :title="isEditing ? '编辑合同' : '新建合同'"
      width="680px"
      :close-on-click-modal="false"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px" v-loading="formLoading">
        <el-form-item label="客户" prop="customer_id">
          <el-select v-model="form.customer_id" filterable placeholder="搜索选择客户" style="width: 100%" @change="onCustomerChange">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="项目名称" prop="project_name">
              <el-select v-model="form.project_name" allow-create filterable placeholder="输入或选择项目名称" style="width: 100%">
                <el-option v-for="p in projectOptions" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同类型">
              <el-select v-model="form.contract_type" clearable placeholder="请选择" style="width: 100%">
                <el-option label="制作合同" value="制作合同" />
                <el-option label="安装合同" value="安装合同" />
                <el-option label="综合合同" value="综合合同" />
                <el-option label="设计合同" value="设计合同" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="合同金额">
              <el-input-number v-model="form.total_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="已收金额">
              <el-input-number v-model="form.paid_amount" :min="0" :precision="2" :disabled="true" style="width: 100%" />
              <div style="font-size: 12px; color: #999; margin-top: 2px;">自动从关联订单的收款计算，不可编辑</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="签约日期">
              <el-date-picker v-model="form.sign_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="生效日期">
              <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="我方签约人">
              <el-input v-model="form.our_signatory" placeholder="我方签约人" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="客户签约人">
              <el-input v-model="form.customer_signatory" placeholder="客户签约人" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="关联订单">
          <el-select v-model="form.order_id" filterable clearable placeholder="选择关联订单" style="width: 100%" @change="onOrderChange">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} — ${o.department || '-'} — ${o.project_name} — ¥${(o.total_amount || 0).toFixed(2)}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联报价">
          <el-select v-model="form.quote_id" filterable clearable placeholder="选择关联报价" style="width: 100%" @change="onQuoteChange">
            <el-option v-for="q in quoteOptions" :key="q.id" :label="`${q.quote_no} — ${q.department || '-'} — ${q.project_name} — ¥${(q.total_amount || 0).toFixed(2)}`" :value="q.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="条款内容">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="合同主要条款内容" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="备注" />
        </el-form-item>
        <el-form-item label="合同原件">
          <div>
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".pdf,.doc,.docx,image/*"
              :on-change="onAttachmentChange"
            >
              <el-button :loading="uploadingAtt">
                <el-icon><Plus /></el-icon> 上传合同原件
              </el-button>
              <template #tip>
                <div class="el-upload__tip">支持 PDF / Word / 图片，最大 10MB</div>
              </template>
            </el-upload>
            <div v-if="attFileName" style="margin-top: 8px; display: flex; align-items: center; gap: 8px">
              <span style="color: var(--el-color-primary)">{{ attFileName }}</span>
              <el-button text type="danger" size="small" @click="handleDeleteAtt">删除</el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="formLoading" @click="saveForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="合同详情" width="680px">
      <el-descriptions v-if="currentDetail" :column="2" border>
        <el-descriptions-item label="合同编号" :span="2">{{ currentDetail.contract_no }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ currentDetail.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="项目名称">{{ currentDetail.project_name }}</el-descriptions-item>
        <el-descriptions-item label="合同类型">{{ currentDetail.contract_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同金额">¥ {{ currentDetail.total_amount?.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="已收金额">¥ {{ currentDetail.paid_amount?.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="未收金额">¥ {{ currentDetail.unpaid_amount?.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusColor(currentDetail.status)" size="small">{{ statusLabel(currentDetail.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="我方签约人">{{ currentDetail.our_signatory || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户签约人">{{ currentDetail.customer_signatory || '-' }}</el-descriptions-item>
        <el-descriptions-item label="签约日期">{{ currentDetail.sign_date?.slice(0, 10) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="生效日期">{{ currentDetail.start_date?.slice(0, 10) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ currentDetail.end_date?.slice(0, 10) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="条款内容" :span="2">
          <pre style="white-space: pre-wrap; margin: 0">{{ currentDetail.content || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="合同原件" :span="2">
          <template v-if="currentDetail?.attachment_name">
            <a :href="'/api/v1/contracts/' + currentDetail.id + '/attachment'" target="_blank" style="color: var(--el-color-primary)">{{ currentDetail.attachment_name }}</a>
          </template>
          <template v-else>-</template>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentDetail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <h4 style="margin: 20px 0 10px">关联订单</h4>
      <el-table v-if="currentDetail?.orders?.length" :data="currentDetail.orders" size="small">
        <el-table-column prop="order_no" label="订单编号" width="180" />
        <el-table-column prop="project_name" label="项目名称" min-width="150" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无关联订单" />

      <h4 style="margin: 16px 0 10px">关联报价</h4>
      <el-table v-if="currentDetail?.quotes?.length" :data="currentDetail.quotes" size="small">
        <el-table-column prop="quote_no" label="报价编号" width="180" />
        <el-table-column prop="project_name" label="项目名称" min-width="150" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无关联报价" />
    </el-dialog>

    <!-- 状态变更对话框 -->
    <el-dialog v-model="statusDialogVisible" title="合同状态变更" width="400px">
      <el-form :model="statusForm" label-width="80px">
        <el-form-item label="当前状态">
          <el-tag :type="statusColor(statusForm.current_status)" size="small">{{ statusLabel(statusForm.current_status) }}</el-tag>
        </el-form-item>
        <el-form-item label="目标状态">
          <el-select v-model="statusForm.to_status" placeholder="请选择目标状态" style="width: 100%">
            <el-option v-for="s in availableTransitions" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="statusForm.reason" type="textarea" :rows="2" placeholder="状态变更原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="statusLoading" @click="confirmStatusChange">确认变更</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { getContracts, getContract, createContract, updateContract, deleteContract, changeContractStatus, uploadContractAttachment, deleteContractAttachment, getContractAvailableResources } from '@/api/contracts'
import { getCustomers } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ContractListResponse, ContractDetailResponse, ContractResourceItem } from '@/types/api'
import type { FormInstance } from 'element-plus'

// ── Status helpers ──
const statusMap: Record<string, string> = {
  draft: '草稿',
  active: '已生效',
  completed: '已完成',
}
const statusColorMap: Record<string, string> = {
  draft: 'info',
  active: 'success',
  completed: '',
}
function statusLabel(s: string) { return statusMap[s] || s }
function statusColor(s: string) { return statusColorMap[s] || 'info' }

// ── List state ──
const loading = ref(false)
const list = ref<ContractListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', status: '' })

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value, exclude_contract_type: '框架合同' }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.status) params.status = filters.status
    const data = await getContracts(params)
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() { page.value = 1; fetchData() }
function handleReset() { filters.keyword = ''; filters.status = ''; page.value = 1; fetchData() }

onMounted(fetchData)

// ── Create / Edit form ──
const formVisible = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const formLoading = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({
  customer_id: '',
  customer_name: '',
  project_name: '',
  contract_type: '',
  total_amount: 0,
  paid_amount: 0,
  sign_date: null as string | null,
  start_date: null as string | null,
  end_date: null as string | null,
  our_signatory: '',
  customer_signatory: '',
  content: '',
  remark: '',
  order_id: '' as string,
  quote_id: '' as string,
})
const formRules = {
  customer_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}
const customerOptions = ref<Array<{ id: string; name: string }>>([])
const orderOptions = ref<ContractResourceItem[]>([])
const quoteOptions = ref<ContractResourceItem[]>([])
const projectOptions = ref<string[]>([])

// Attachment
const attFileName = ref('')
const uploadingAtt = ref(false)
let pendingContractFile: File | null = null

function onAttachmentChange(uploadFile: unknown) {
  const file = (uploadFile as { raw?: File }).raw || uploadFile as File
  if ((file as File).size > 10 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 10MB')
    return
  }
  handleUploadAtt(file as File)
}

async function handleUploadAtt(file: File) {
  if (!editingId.value) {
    // New contract: just remember the file for now
    attFileName.value = file.name; pendingContractFile = file
    return
  }
  uploadingAtt.value = true
  try {
    const detail = await uploadContractAttachment(editingId.value, file)
    attFileName.value = detail.attachment_name || file.name
    ElMessage.success('上传成功')
  } catch { /* handled by interceptor */ } finally {
    uploadingAtt.value = false
  }
}

async function handleDeleteAtt() {
  if (editingId.value) {
    try {
      await deleteContractAttachment(editingId.value)
      ElMessage.success('已删除')
    } catch { /* ignore */ }
  }
  attFileName.value = ''
  ;pendingContractFile = null
}

function resetForm() {
  form.customer_id = ''
  form.customer_name = ''
  form.project_name = ''
  form.contract_type = ''
  form.total_amount = 0
  form.paid_amount = 0
  form.sign_date = null
  form.start_date = null
  form.end_date = null
  form.our_signatory = ''
  form.customer_signatory = ''
  form.content = ''
  form.remark = ''
  form.order_id = ''
  form.quote_id = ''
  attFileName.value = ''
  ;pendingContractFile = null
  isEditing.value = false
  editingId.value = ''
}

async function loadAllCustomers() {
  try {
    const data = await getCustomers({ page_size: 9999 })
    customerOptions.value = data.items.map((c: { id: string; name: string }) => ({ id: c.id, name: c.name }))
  } catch { /* ignore */ }
}

async function loadResources(customerId?: string, contractId?: string) {
  try {
    const data = await getContractAvailableResources(customerId, contractId)
    orderOptions.value = data.orders || []
    quoteOptions.value = data.quotes || []
    // 从可用订单/报价中提取项目名称列表，排除已被其他合同使用的
    const used = new Set(data.used_project_names || [])
    const names = new Set<string>()
    for (const o of data.orders || []) {
      if (o.project_name && !used.has(o.project_name)) names.add(o.project_name)
    }
    for (const q of data.quotes || []) {
      if (q.project_name && !used.has(q.project_name)) names.add(q.project_name)
    }
    projectOptions.value = Array.from(names).sort()
  } catch { /* ignore */ }
}

async function onCustomerChange(val: string) {
  const c = customerOptions.value.find(c => c.id === val)
  if (c) form.customer_name = c.name
  if (val) {
    await loadResources(val, isEditing.value ? editingId.value : undefined)
    // 清除不在新客户下的已选项
    if (form.order_id && !orderOptions.value.find(o => o.id === form.order_id)) {
      form.order_id = ''
    }
    if (form.quote_id && !quoteOptions.value.find(q => q.id === form.quote_id)) {
      form.quote_id = ''
    }
  }
}

async function onOrderChange(val: string) {
  if (!val) return
  const selected = orderOptions.value.find(o => o.id === val)
  if (selected) {
    // 未选客户时，从订单自动填充客户
    if (!form.customer_id && selected.customer_id) {
      form.customer_id = selected.customer_id
      form.customer_name = selected.customer_name || ''
      await loadResources(selected.customer_id, isEditing.value ? editingId.value : undefined)
    }
    if (!form.project_name) form.project_name = selected.project_name
    if (!form.total_amount) form.total_amount = selected.total_amount || 0
  }
}

async function onQuoteChange(val: string) {
  if (!val) return
  const selected = quoteOptions.value.find(q => q.id === val)
  if (selected) {
    // 未选客户时，从报价自动填充客户
    if (!form.customer_id && selected.customer_id) {
      form.customer_id = selected.customer_id
      form.customer_name = selected.customer_name || ''
      await loadResources(selected.customer_id, isEditing.value ? editingId.value : undefined)
    }
    if (!form.project_name) form.project_name = selected.project_name
    if (!form.total_amount) form.total_amount = selected.total_amount || 0
  }
}

async function handleCreate() {
  resetForm()
  isEditing.value = false
  await Promise.all([
    loadAllCustomers(),
    loadResources(),
  ])
  formVisible.value = true
}

async function handleEdit(row: ContractListResponse) {
  resetForm()
  isEditing.value = true
  editingId.value = row.id
  formLoading.value = true
  try {
    const detail = await getContract(row.id)
    form.customer_id = detail.customer_id
    form.customer_name = detail.customer_name
    // Populate customerOptions so el-select shows the name, not UUID
    if (detail.customer_id && detail.customer_name) {
      customerOptions.value = [{ id: detail.customer_id, name: detail.customer_name }]
    }
    form.project_name = detail.project_name
    form.contract_type = detail.contract_type || ''
    form.total_amount = detail.total_amount
    form.paid_amount = detail.paid_amount
    form.sign_date = detail.sign_date || null
    form.start_date = detail.start_date || null
    form.end_date = detail.end_date || null
    form.our_signatory = detail.our_signatory || ''
    form.customer_signatory = detail.customer_signatory || ''
    form.content = detail.content || ''
    form.remark = detail.remark || ''
    form.order_id = detail.orders?.[0]?.id || ''
    form.quote_id = detail.quotes?.[0]?.id || ''
    attFileName.value = detail.attachment_name || ''
    await Promise.all([
      loadAllCustomers(),
      loadResources(form.customer_id, editingId.value),
    ])
  } finally {
    formLoading.value = false
  }
  formVisible.value = true
}

async function saveForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  formLoading.value = true
  try {
    const payload = {
      customer_id: form.customer_id || null,
      customer_name: form.customer_name,
      project_name: form.project_name,
      contract_type: form.contract_type || null,
      total_amount: form.total_amount,
      paid_amount: form.paid_amount,
      unpaid_amount: form.total_amount - form.paid_amount,
      sign_date: form.sign_date || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      our_signatory: form.our_signatory || null,
      customer_signatory: form.customer_signatory || null,
      content: form.content || null,
      remark: form.remark || null,
      order_ids: form.order_id ? [form.order_id] : [],
      quote_ids: form.quote_id ? [form.quote_id] : [],
    }
    if (isEditing.value) {
      await updateContract(editingId.value, payload)
      ElMessage.success('合同更新成功')
    } else {
      const created = await createContract(payload)
      // After creating, upload attachment if there is a pending file
      const pendingFile = pendingContractFile as File | null
      if (pendingFile && created?.id) {
        await uploadContractAttachment(created.id, pendingFile)
        ;pendingContractFile = null
      }
      ElMessage.success('合同创建成功')
    }
    formVisible.value = false
    fetchData()
  } catch { /* error handled by interceptor */ } finally {
    formLoading.value = false
  }
}

// ── Detail dialog ──
const detailVisible = ref(false)
const currentDetail = ref<ContractDetailResponse | null>(null)

async function handleDetail(row: ContractListResponse) {
  try {
    const detail = await getContract(row.id)
    currentDetail.value = detail
    detailVisible.value = true
  } catch { /* ignore */ }
}

// ── Status change ──
const statusDialogVisible = ref(false)
const statusLoading = ref(false)
const statusForm = reactive({
  current_status: '',
  to_status: '',
  reason: '',
  contract_id: '',
})
const STATUS_TRANSITIONS: Record<string, string[]> = {
  draft: ['active', 'completed'],
  active: ['draft', 'completed'],
  completed: ['draft'],
}

const availableTransitions = computed(() => {
  return STATUS_TRANSITIONS[statusForm.current_status] || []
})

function canChangeStatus(row: ContractListResponse) {
  return (STATUS_TRANSITIONS[row.status] || []).length > 0
}

function handleStatusChange(row: ContractListResponse) {
  statusForm.current_status = row.status
  statusForm.to_status = ''
  statusForm.reason = ''
  statusForm.contract_id = row.id
  statusDialogVisible.value = true
}

async function confirmStatusChange() {
  if (!statusForm.to_status) {
    ElMessage.warning('请选择目标状态')
    return
  }
  statusLoading.value = true
  try {
    await changeContractStatus(statusForm.contract_id, {
      to_status: statusForm.to_status,
      reason: statusForm.reason || null,
    })
    ElMessage.success('状态变更成功')
    statusDialogVisible.value = false
    fetchData()
  } catch { /* handled by interceptor */ } finally {
    statusLoading.value = false
  }
}

// ── Delete ──
async function handleDelete(row: ContractListResponse) {
  try {
    await ElMessageBox.confirm(`确定将合同「${row.contract_no}」删除？`, '删除合同', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }
  await deleteContract(row.id)
  ElMessage.success('合同已删除')
  fetchData()
}
</script>
