<template>
  <div class="page">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2>框架合同详情</h2>
      </div>
      <el-button type="primary" @click="openEditContract">编辑合同</el-button>
    </div>

    <!-- 合同信息 -->
    <el-card class="info-card">
      <template #header><span>合同信息</span></template>
      <el-descriptions :column="2" border v-loading="loadingContract">
        <el-descriptions-item label="合同编号">{{ contract?.contract_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户名称">{{ contract?.customer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="合同类型">框架合同</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="contract" :type="statusColor(contract.status)">{{ statusLabel(contract.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="合同金额">¥ {{ (contract?.total_amount || 0).toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="已收金额">¥ {{ (contract?.paid_amount || 0).toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="未收金额">
          <span :class="{ 'text-danger': (contract?.unpaid_amount || 0) > 0 }">¥ {{ (contract?.unpaid_amount || 0).toFixed(2) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="签约日期">{{ contract?.sign_date?.slice(0, 10) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="生效日期">{{ contract?.start_date?.slice(0, 10) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ contract?.end_date?.slice(0, 10) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="我方签约人">{{ contract?.our_signatory || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户签约人">{{ contract?.customer_signatory || '-' }}</el-descriptions-item>
        <el-descriptions-item label="条款内容" :span="2">
          <pre v-if="contract?.content" style="white-space: pre-wrap; margin: 0;">{{ contract.content }}</pre>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="合同原件" :span="2">
          <a v-if="contract?.attachment_name && contract" :href="getContractAttachmentUrl(contract.id)" target="_blank">{{ contract.attachment_name }}</a>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ contract?.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 项目列表 -->
    <el-card class="project-card">
      <template #header>
        <div class="card-header">
          <span>项目列表</span>
          <el-button type="primary" size="small" @click="openAddProject">添加项目</el-button>
        </div>
      </template>

      <el-table :data="projects" v-loading="loadingProjects" stripe>
        <el-table-column prop="department" label="部门/科室" width="130" />
        <el-table-column prop="project_name" label="项目名称" min-width="160" />
        <el-table-column label="项目金额" width="130" align="right">
          <template #default="{ row }">¥ {{ row.project_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="关联订单" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="o in row.orders" :key="o.id" size="small" style="margin:2px">{{ o.order_no }}</el-tag>
            <span v-if="!row.orders?.length" style="color:#999">-</span>
          </template>
        </el-table-column>
        <el-table-column label="关联报价" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="q in row.quotes" :key="q.id" size="small" style="margin:2px">{{ q.quote_no }}</el-tag>
            <span v-if="!row.quotes?.length" style="color:#999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
        <el-table-column label="附件" width="100">
          <template #default="{ row }">
            <a v-if="row.attachment_name" :href="getContractProjectAttachmentUrl(row.id)" target="_blank">下载</a>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEditProject(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDeleteProject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="projectTotal > 0"
        v-model:current-page="projectPage"
        v-model:page-size="projectPageSize"
        :page-sizes="[10, 20, 50]"
        :total="projectTotal"
        layout="total, sizes, prev, pager, next"
        style="margin-top:16px; justify-content:flex-end"
        @change="fetchProjects"
      />
    </el-card>

    <!-- 编辑合同对话框 -->
    <el-dialog v-model="editVisible" title="编辑框架合同" width="650px" :close-on-click-modal="false" @closed="resetEditForm">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="客户" required>
          <el-select v-model="editForm.customer_id" placeholder="请选择客户" filterable style="width:100%">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="合同名称">
          <el-input v-model="editForm.project_name" placeholder="框架合同名称" />
        </el-form-item>
        <el-form-item label="签约日期">
          <el-date-picker v-model="editForm.sign_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="editForm.start_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="editForm.end_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="我方签约人">
          <el-input v-model="editForm.our_signatory" />
        </el-form-item>
        <el-form-item label="客户签约人">
          <el-input v-model="editForm.customer_signatory" />
        </el-form-item>
        <el-form-item label="条款内容">
          <el-input v-model="editForm.content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑项目对话框 -->
    <el-dialog v-model="projectVisible" :title="projectEditingId ? '编辑项目' : '添加项目'" width="600px" :close-on-click-modal="false" @closed="resetProjectForm">
      <el-form :model="projectForm" label-width="100px">
        <el-form-item label="客户">
          <el-input :model-value="contract?.customer_name" disabled />
        </el-form-item>
        <el-form-item label="部门/科室">
          <el-input v-model="projectForm.department" placeholder="部门/科室" />
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-select v-model="projectForm.project_name" placeholder="选择或输入项目名称" filterable allow-create style="width:100%">
            <el-option v-for="n in availableProjectNames" :key="n" :label="n" :value="n" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目金额">
          <el-input-number v-model="projectForm.project_amount" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="关联订单">
          <el-select v-model="projectForm.order_id" filterable clearable style="width:100%">
            <el-option v-for="o in availableOrders" :key="o.id" :label="`${o.order_no} — ${o.department || '-'} — ${o.project_name} — ¥${(o.total_amount || 0).toFixed(2)}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联报价">
          <el-select v-model="projectForm.quote_id" filterable clearable style="width:100%">
            <el-option v-for="q in availableQuotes" :key="q.id" :label="`${q.quote_no} — ${q.department || '-'} — ${q.project_name} — ¥${(q.total_amount || 0).toFixed(2)}`" :value="q.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="projectForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onProjectAttChange"
            :on-remove="onProjectAttRemove"
            :file-list="projectAttFileList"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
          >
            <el-button type="primary" plain>选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectVisible = false">取消</el-button>
        <el-button type="primary" :loading="projectSaving" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getContract, updateContract, getContractAttachmentUrl } from '@/api/contracts'
import {
  getContractProjects, getContractProject,
  createContractProject, updateContractProject, deleteContractProject,
  uploadContractProjectAttachment, deleteContractProjectAttachment,
  getContractProjectAttachmentUrl, getAvailableResources,
} from '@/api/framework-contracts'
import { getCustomers } from '@/api/customers'
import type {
  ContractDetailResponse,
  FrameworkContractProjectDetailResponse,
  ContractResourceItem,
} from '@/types/api'

const route = useRoute()
const contractId = route.params.id as string

const STATUS_MAP: Record<string, string> = { draft: '草稿', active: '已生效', completed: '已完成', terminated: '已终止' }
const STATUS_COLOR: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
  draft: 'info', active: 'success', completed: '', terminated: 'danger',
}
function statusLabel(s: string) { return STATUS_MAP[s] || s }
function statusColor(s: string): '' | 'success' | 'warning' | 'info' | 'danger' { return STATUS_COLOR[s] || '' }

// ── 合同信息 ──
const loadingContract = ref(false)
const contract = ref<ContractDetailResponse | null>(null)

async function loadContract() {
  loadingContract.value = true
  try {
    contract.value = await getContract(contractId)
  } finally { loadingContract.value = false }
}

// ── 项目列表 ──
const loadingProjects = ref(false)
const projects = ref<FrameworkContractProjectDetailResponse[]>([])
const projectTotal = ref(0)
const projectPage = ref(1)
const projectPageSize = ref(20)

async function fetchProjects() {
  loadingProjects.value = true
  try {
    const data = await getContractProjects(contractId, { page: projectPage.value, page_size: projectPageSize.value })
    const details = await Promise.all(
      data.items.map(p => getContractProject(p.id).catch(() => ({ ...p, orders: [], quotes: [] } as FrameworkContractProjectDetailResponse)))
    )
    projects.value = details
    projectTotal.value = data.total
  } finally { loadingProjects.value = false }
}

async function handleDeleteProject(row: FrameworkContractProjectDetailResponse) {
  try {
    await ElMessageBox.confirm('确定删除该项目？', '提示', { type: 'warning' })
    await deleteContractProject(row.id)
    ElMessage.success('已删除')
    fetchProjects()
    loadContract()
  } catch { /* canceled */ }
}

// ── 编辑合同 ──
const editVisible = ref(false)
const editSaving = ref(false)
const customerOptions = ref<{ id: string; name: string }[]>([])

const editForm = reactive({
  customer_id: '',
  project_name: '',
  sign_date: null as string | null,
  start_date: null as string | null,
  end_date: null as string | null,
  our_signatory: '',
  customer_signatory: '',
  content: '',
  remark: '',
})

function resetEditForm() {
  Object.assign(editForm, {
    customer_id: '', project_name: '', sign_date: null, start_date: null, end_date: null,
    our_signatory: '', customer_signatory: '', content: '', remark: '',
  })
}

async function loadCustomersForEdit() {
  try {
    const data = await getCustomers({ page_size: 500 })
    customerOptions.value = (data.items as { id: string; name: string }[]).map(c => ({ id: c.id, name: c.name }))
  } catch { /* ignore */ }
}

function openEditContract() {
  if (!contract.value) return
  editForm.customer_id = contract.value.customer_id
  editForm.project_name = contract.value.project_name || ''
  editForm.sign_date = contract.value.sign_date || null
  editForm.start_date = contract.value.start_date || null
  editForm.end_date = contract.value.end_date || null
  editForm.our_signatory = contract.value.our_signatory || ''
  editForm.customer_signatory = contract.value.customer_signatory || ''
  editForm.content = contract.value.content || ''
  editForm.remark = contract.value.remark || ''
  loadCustomersForEdit()
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.customer_id) { ElMessage.warning('请选择客户'); return }
  editSaving.value = true
  try {
    const customer = customerOptions.value.find(c => c.id === editForm.customer_id)
    await updateContract(contractId, {
      customer_id: editForm.customer_id,
      customer_name: customer?.name || '',
      project_name: editForm.project_name || null,
      sign_date: editForm.sign_date || null,
      start_date: editForm.start_date || null,
      end_date: editForm.end_date || null,
      our_signatory: editForm.our_signatory || null,
      customer_signatory: editForm.customer_signatory || null,
      content: editForm.content || null,
      remark: editForm.remark || null,
    })
    ElMessage.success('已更新')
    editVisible.value = false
    loadContract()
  } catch { /* handled */ } finally { editSaving.value = false }
}

// ── 添加/编辑项目 ──
const projectVisible = ref(false)
const projectSaving = ref(false)
const projectEditingId = ref('')

const projectForm = reactive({
  department: '',
  project_name: '',
  project_amount: 0,
  order_id: '' as string,
  quote_id: '' as string,
  remark: '',
})

const availableOrders = ref<ContractResourceItem[]>([])
const availableQuotes = ref<ContractResourceItem[]>([])
const availableProjectNames = ref<string[]>([])
const pendingProjectAtt = ref<File | null>(null)
const projectAttFileList = ref<{ name: string; url?: string }[]>([])
const existingProjectAtt = ref<{ path?: string; name?: string }>({})

function onProjectAttChange(file: { raw?: File }) { pendingProjectAtt.value = file.raw ?? null }
function onProjectAttRemove() { pendingProjectAtt.value = null }

function resetProjectForm() {
  Object.assign(projectForm, { department: '', project_name: '', project_amount: 0, order_id: '', quote_id: '', remark: '' })
  pendingProjectAtt.value = null
  projectAttFileList.value = []
  existingProjectAtt.value = {}
  projectEditingId.value = ''
}

async function loadAvailableResources() {
  if (!contract.value) return
  try {
    const data = await getAvailableResources(contract.value.customer_id, contractId)
    availableOrders.value = data.orders
    availableQuotes.value = data.quotes
    availableProjectNames.value = data.project_names || []
  } catch { /* ignore */ }
}

async function openAddProject() {
  resetProjectForm()
  await loadAvailableResources()
  projectVisible.value = true
}

async function openEditProject(row: FrameworkContractProjectDetailResponse) {
  resetProjectForm()
  projectEditingId.value = row.id
  const detail = await getContractProject(row.id).catch(() => null)
  if (!detail) return
  projectForm.department = detail.department || ''
  projectForm.project_name = detail.project_name
  projectForm.project_amount = detail.project_amount
  projectForm.order_id = detail.orders?.[0]?.id || ''
  projectForm.quote_id = detail.quotes?.[0]?.id || ''
  projectForm.remark = detail.remark || ''
  existingProjectAtt.value = { path: detail.attachment_path, name: detail.attachment_name }
  if (detail.attachment_name) {
    projectAttFileList.value = [{ name: detail.attachment_name }]
  }
  await loadAvailableResources()
  // 编辑时把已关联但不在 available 中的资源加回来
  if (detail.orders) {
    availableOrders.value = [...availableOrders.value, ...detail.orders.map(o => ({
      id: o.id, order_no: o.order_no, project_name: o.project_name,
    } as ContractResourceItem))]
  }
  if (detail.quotes) {
    availableQuotes.value = [...availableQuotes.value, ...detail.quotes.map(q => ({
      id: q.id, quote_no: q.quote_no, project_name: q.project_name,
    } as ContractResourceItem))]
  }
  projectVisible.value = true
}

async function saveProject() {
  if (!projectForm.project_name) { ElMessage.warning('请输入项目名称'); return }
  if (!contract.value) return
  projectSaving.value = true
  try {
    const payload = {
      contract_id: contractId,
      customer_id: contract.value.customer_id,
      customer_name: contract.value.customer_name,
      department: projectForm.department || null,
      project_name: projectForm.project_name,
      project_amount: projectForm.project_amount || 0,
      order_ids: projectForm.order_id ? [projectForm.order_id] : [],
      quote_ids: projectForm.quote_id ? [projectForm.quote_id] : [],
      remark: projectForm.remark || null,
    }
    let project: FrameworkContractProjectDetailResponse
    if (projectEditingId.value) {
      project = await updateContractProject(projectEditingId.value, {
        department: payload.department,
        project_name: payload.project_name,
        project_amount: payload.project_amount,
        order_ids: projectForm.order_id ? [projectForm.order_id] : [],
        quote_ids: projectForm.quote_id ? [projectForm.quote_id] : [],
        remark: payload.remark,
      })
      if (pendingProjectAtt.value) {
        await uploadContractProjectAttachment(project.id, pendingProjectAtt.value)
      } else if (projectAttFileList.value.length === 0 && existingProjectAtt.value.path) {
        await deleteContractProjectAttachment(project.id)
      }
    } else {
      project = await createContractProject(contractId, payload)
      if (pendingProjectAtt.value) {
        await uploadContractProjectAttachment(project.id, pendingProjectAtt.value)
      }
    }
    ElMessage.success(projectEditingId.value ? '已更新' : '已添加')
    projectVisible.value = false
    fetchProjects()
    loadContract()
  } catch { /* handled */ } finally { projectSaving.value = false }
}

onMounted(() => {
  loadContract()
  fetchProjects()
})
</script>

<style scoped>
.page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0 0 0 12px; color: var(--ad-text); }
.header-left { display: flex; align-items: center; }
.info-card { margin-bottom: 16px; }
.project-card { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.text-danger { color: var(--el-color-danger); font-weight: 500; }
</style>
