<template>
  <div class="page">
    <div class="page-header">
      <h2>框架合同管理</h2>
      <el-button type="primary" @click="handleCreate">新建框架合同</el-button>
    </div>

    <el-card class="filter-card">
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="合同编号/客户" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
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

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="contract_no" label="合同编号" min-width="160" />
        <el-table-column prop="customer_name" label="客户名称" min-width="140" />
        <el-table-column label="合同类型" width="100">
          <template #default>框架合同</template>
        </el-table-column>
        <el-table-column label="合同金额" width="130" align="right">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="已收金额" width="120" align="right">
          <template #default="{ row }">¥ {{ row.paid_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="未收金额" width="120" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.unpaid_amount > 0 }">¥ {{ row.unpaid_amount?.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusColor(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签约日期" width="120">
          <template #default="{ row }">{{ row.sign_date?.slice(0, 10) || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="100">
          <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="$router.push(`/framework-contracts/${row.id}`)">详情</el-button>
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="warning" size="small" @click="handleStatusChange(row)">状态</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @change="fetchData"
      />
    </el-card>

    <!-- 新建 / 编辑 对话框 -->
    <el-dialog v-model="formVisible" :title="isEditing ? '编辑框架合同' : '新建框架合同'" width="650px" :close-on-click-modal="false" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户" required>
          <el-select v-model="form.customer_id" placeholder="请选择客户" filterable style="width: 100%" @change="onCustomerChange">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="合同名称">
          <el-input v-model="form.project_name" placeholder="框架合同名称" />
        </el-form-item>
        <el-form-item label="签约日期">
          <el-date-picker v-model="form.sign_date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="form.start_date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="我方签约人">
          <el-input v-model="form.our_signatory" placeholder="我方签约人" />
        </el-form-item>
        <el-form-item label="客户签约人">
          <el-input v-model="form.customer_signatory" placeholder="客户签约人" />
        </el-form-item>
        <el-form-item label="条款内容">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="合同条款内容" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="备注" />
        </el-form-item>
        <el-form-item label="合同原件">
          <div>
            <el-upload
              :auto-upload="false"
              :limit="1"
              :on-change="onAttachmentChange"
              :on-remove="handleRemoveAtt"
              :file-list="attFileList"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            >
              <el-button type="primary" plain>选择文件</el-button>
              <template #tip><div class="el-upload__tip">PDF/Word/图片，不超过10MB</div></template>
            </el-upload>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 状态变更对话框 -->
    <el-dialog v-model="statusDialogVisible" title="合同状态变更" width="450px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="当前状态">
          <el-tag :type="statusColor(statusForm.current_status)">{{ statusLabel(statusForm.current_status) }}</el-tag>
        </el-form-item>
        <el-form-item label="目标状态">
          <el-select v-model="statusForm.to_status" style="width: 100%">
            <el-option v-for="s in availableTransitions" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="statusForm.reason" type="textarea" :rows="2" placeholder="变更原因（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="statusSaving" @click="confirmStatusChange">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFrameworkContracts } from '@/api/framework-contracts'
import {
  getContract, createContract, updateContract, deleteContract,
  changeContractStatus, uploadContractAttachment, deleteContractAttachment,
  getContractAttachmentUrl,
} from '@/api/contracts'
import { getCustomers } from '@/api/customers'
import type { ContractListResponse, ContractDetailResponse } from '@/types/api'

// ── 列表 ──
const loading = ref(false)
const list = ref<ContractListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', status: '' })

const statusLabel = (s: string) => {
  const map: Record<string, string> = { draft: '草稿', active: '已生效', completed: '已完成', terminated: '已终止' }
  return map[s] || s
}

const statusColor = (s: string): '' | 'success' | 'warning' | 'info' | 'danger' => {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    draft: 'info', active: 'success', completed: '', terminated: 'danger',
  }
  return map[s] || ''
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getFrameworkContracts({ page: page.value, page_size: pageSize.value, ...filters })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function handleSearch() { page.value = 1; fetchData() }
function handleReset() { filters.keyword = ''; filters.status = ''; page.value = 1; fetchData() }

async function handleDelete(row: ContractListResponse) {
  await ElMessageBox.confirm('确定删除该框架合同？', '提示', { type: 'warning' })
  await deleteContract(row.id)
  ElMessage.success('已删除')
  fetchData()
}

// ── 新建 / 编辑表单 ──
const formVisible = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const saving = ref(false)
const customerOptions = ref<{ id: string; name: string }[]>([])

const form = reactive({
  customer_id: '' as string,
  project_name: '',
  sign_date: null as string | null,
  start_date: null as string | null,
  end_date: null as string | null,
  our_signatory: '',
  customer_signatory: '',
  content: '',
  remark: '',
})

function onCustomerChange() {
  // 客户已选，无需额外操作
}

const pendingAttFile = ref<File | null>(null)
const attFileList = ref<{ name: string; url?: string }[]>([])
const existingAtt = ref<{ path?: string; name?: string }>({})

function onAttachmentChange(file: { raw: File }) {
  pendingAttFile.value = file.raw
}
function handleRemoveAtt() {
  pendingAttFile.value = null
}

function resetForm() {
  Object.assign(form, {
    customer_id: '', project_name: '', sign_date: null, start_date: null, end_date: null,
    our_signatory: '', customer_signatory: '', content: '', remark: '',
  })
  pendingAttFile.value = null
  attFileList.value = []
  existingAtt.value = {}
  isEditing.value = false
  editingId.value = ''
}

async function loadCustomers() {
  try {
    const data = await getCustomers({ page_size: 500 })
    customerOptions.value = data.items.map((c: { id: string; name: string }) => ({ id: c.id, name: c.name }))
  } catch { /* ignore */ }
}

async function handleCreate() {
  resetForm()
  formVisible.value = true
  await loadCustomers()
}

async function handleEdit(row: ContractListResponse) {
  isEditing.value = true
  editingId.value = row.id
  try {
    const detail: ContractDetailResponse = await getContract(row.id)
    form.customer_id = detail.customer_id
    form.project_name = detail.project_name || ''
    form.sign_date = detail.sign_date || null
    form.start_date = detail.start_date || null
    form.end_date = detail.end_date || null
    form.our_signatory = detail.our_signatory || ''
    form.customer_signatory = detail.customer_signatory || ''
    form.content = detail.content || ''
    form.remark = detail.remark || ''
    existingAtt.value = { path: detail.attachment_path, name: detail.attachment_name }
    if (detail.attachment_name) {
      attFileList.value = [{ name: detail.attachment_name, url: getContractAttachmentUrl(row.id) }]
    }
  } catch { /* ignore */ }
  await loadCustomers()
  formVisible.value = true
}

async function saveForm() {
  if (!form.customer_id) { ElMessage.warning('请选择客户'); return }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      customer_id: form.customer_id,
      customer_name: customerOptions.value.find(c => c.id === form.customer_id)?.name || '',
      project_name: form.project_name || null,
      contract_type: '框架合同',
      sign_date: form.sign_date || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      our_signatory: form.our_signatory || null,
      customer_signatory: form.customer_signatory || null,
      content: form.content || null,
      remark: form.remark || null,
    }
    let contract: ContractDetailResponse
    if (isEditing.value) {
      contract = await updateContract(editingId.value, payload)
    } else {
      contract = await createContract(payload)
    }
    // 上传附件
    if (pendingAttFile.value) {
      await uploadContractAttachment(contract.id, pendingAttFile.value)
    }
    if (isEditing.value && !pendingAttFile.value && attFileList.value.length === 0 && existingAtt.value.path) {
      await deleteContractAttachment(contract.id)
    }
    ElMessage.success(isEditing.value ? '已更新' : '已创建')
    formVisible.value = false
    fetchData()
  } catch { /* handled by interceptor */ } finally { saving.value = false }
}

// ── 状态变更 ──
const statusDialogVisible = ref(false)
const statusSaving = ref(false)
const statusForm = reactive({ current_status: '', to_status: '', reason: '' })
const statusContractId = ref('')

const TRANSITIONS: Record<string, string[]> = {
  draft: ['active', 'completed'],
  active: ['draft', 'completed'],
  completed: ['draft'],
}
const availableTransitions = computed(() => TRANSITIONS[statusForm.current_status] || [])

function handleStatusChange(row: ContractListResponse) {
  statusContractId.value = row.id
  statusForm.current_status = row.status
  statusForm.to_status = ''
  statusForm.reason = ''
  statusDialogVisible.value = true
}

async function confirmStatusChange() {
  if (!statusForm.to_status) { ElMessage.warning('请选择目标状态'); return }
  statusSaving.value = true
  try {
    await changeContractStatus(statusContractId.value, { to_status: statusForm.to_status, reason: statusForm.reason || undefined })
    ElMessage.success('状态已变更')
    statusDialogVisible.value = false
    fetchData()
  } catch { /* handled by interceptor */ } finally { statusSaving.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { margin-bottom: 16px; }
.text-danger { color: var(--el-color-danger); font-weight: 500; }
</style>
