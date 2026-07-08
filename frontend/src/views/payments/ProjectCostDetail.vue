<template>
  <div class="page">
    <!-- Order info header -->
    <div class="order-header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
      <el-card v-if="order" shadow="never" class="order-card" style="margin-top: 12px">
        <div class="order-info-row">
          <div class="order-info-item">
            <span class="label">订单编号</span>
            <span class="value">{{ order.order_no }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">项目名称</span>
            <span class="value">{{ order.project_name }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">客户</span>
            <span class="value">{{ order.customer_name || '-' }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">状态</span>
            <el-tag :type="statusColor(order.status)" size="small">{{ statusLabel(order.status) }}</el-tag>
          </div>
          <div class="order-info-item">
            <span class="label">项目成本合计</span>
            <span class="value" style="color: #e6a23c; font-weight: bold; font-size: 18px">
              ¥ {{ totalCost.toFixed(2) }}
            </span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Actions -->
    <div style="display: flex; gap: 8px; margin: 16px 0">
      <el-button @click="openImport">导入Excel</el-button>
      <el-button type="danger" @click="openCreate">登记成本</el-button>
    </div>

    <!-- Filters -->
    <div class="search-bar">
      <el-select
        v-model="filterCategory"
        placeholder="成本类别"
        clearable
        style="width: 160px"
        @change="fetchData"
      >
        <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px; margin-left: 12px"
        @change="fetchData"
      />
      <el-button style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <!-- Cost table -->
    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="cost_no" label="编号" width="180" />
      <el-table-column label="类别" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分项" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.order_item_name">{{ row.order_item_name }}</span>
          <span v-else style="color: #c0c4cc">-</span>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="140" align="right">
        <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="欠款" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_debt && !row.is_settled" type="danger" size="small">欠款</el-tag>
          <el-tag v-else-if="row.is_debt && row.is_settled" type="success" size="small">已结清</el-tag>
          <span v-else style="color: #c0c4cc">-</span>
        </template>
      </el-table-column>
      <el-table-column label="日期" width="120">
        <template #default="{ row }">
          {{ row.cost_date?.slice(0, 10) || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="凭证" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.attachment_count > 0" size="small" type="success">{{ row.attachment_count }}</el-tag>
          <span v-else style="color: #c0c4cc">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row as ProjectCostResponse)">编辑</el-button>
          <el-button
            v-if="authStore.isAdmin"
            text
            type="danger"
            size="small"
            @click="handleDelete(row as ProjectCostResponse)"
          >
            删除
          </el-button>
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

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing ? '编辑成本' : '登记成本'" width="520px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="isQuote ? '报价单' : '订单'">
          <el-input :value="(isQuote ? (order?.quote_no || '') : (order?.order_no || '')) + ' ' + (order?.project_name || '')" disabled />
        </el-form-item>
        <el-form-item label="分项">
          <el-select v-model="form.order_item_id" placeholder="选择分项（可选）" clearable filterable style="width: 100%">
            <el-option
              v-for="item in orderItems"
              :key="item.id"
              :label="item.item_name"
              :value="item.id"
            >
              <span>{{ item.item_name }}</span>
              <span v-if="item.group_name" style="float: right; color: #909399; font-size: 12px">{{ item.group_name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="成本类别" required>
          <el-select
            v-model="form.category"
            placeholder="选择类别"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="form.payment_method" placeholder="选择付款方式" clearable style="width: 100%">
            <el-option v-for="pm in PAYMENT_METHODS" :key="pm" :label="pm" :value="pm" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款公司">
          <el-input v-model="form.payee_company_name" placeholder="输入对方收款公司名称" clearable />
          <div style="font-size: 12px; color: #909399; margin-top: 2px">对方收款公司名称（可选）</div>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="欠款金额">
          <el-input-number v-model="form.debt_amount" :min="0" :precision="2" style="width: 100%" placeholder="0 表示无欠款" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px">大于0时自动记为欠款</div>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="form.cost_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="成本说明…" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="备注…" />
        </el-form-item>
        <el-form-item label="凭证">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*,.pdf"
            multiple
            :on-change="onUploadChange"
          >
            <el-button :loading="uploadingAtt" :disabled="!isEditing">
              <el-icon><Plus /></el-icon> 上传凭证
            </el-button>
            <template #tip>
              <div class="el-upload__tip">支持 jpg/png/pdf，编辑模式下可上传</div>
            </template>
          </el-upload>
          <div v-if="dialogAttachments.length" style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px">
            <div
              v-for="att in dialogAttachments"
              :key="att.id"
              class="att-thumb"
              @click="handlePreviewAtt(att)"
            >
              <img
                v-if="att.file_type?.startsWith('image/')"
                :src="`/uploads/${att.file_path}`"
                class="att-img"
              />
              <div v-else class="att-file">
                <span>{{ att.filename?.split('.').pop()?.toUpperCase() }}</span>
              </div>
              <el-button
                class="att-del"
                type="danger"
                :icon="Delete"
                size="small"
                circle
                @click.stop="handleDeleteAtt(att)"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">
          {{ isEditing ? '保存' : '登记' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="showImport" title="导入Excel" width="480px" :close-on-click-modal="false">
      <p style="margin-bottom: 12px; color: var(--ad-text-secondary)">
        Excel 需包含以下列：<br />
        <b>成本类别、金额、描述(可选)、成本日期(可选)、备注(可选)</b>
      </p>
      <p style="margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 13px">
        导入的成本将自动关联到 <b>{{ isQuote ? (order?.quote_no || '报价单') : (order?.order_no || '订单') }}</b>
      </p>
      <div style="margin-bottom: 12px;">
        <el-button size="small" @click="downloadTemplate">
          <el-icon><Download /></el-icon> 下载导入模板
        </el-button>
      </div>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="onFileChange"
      >
        <el-button type="primary">选择Excel文件</el-button>
      </el-upload>
      <div v-if="importResult" style="margin-top: 12px">
        <el-alert
          :type="importResult.errors.length === 0 ? 'success' : 'warning'"
          :closable="false"
        >
          <template #title>
            导入完成：成功 {{ importResult.created }} 条
            <span v-if="importResult.errors.length">，失败 {{ importResult.errors.length }} 条</span>
          </template>
          <ul v-if="importResult.errors.length" style="margin-top: 6px; padding-left: 16px">
            <li v-for="e in importResult.errors" :key="e.row">
              第 {{ e.row }} 行：{{ e.error }}
            </li>
          </ul>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="showImport = false">关闭</el-button>
        <el-button type="danger" :loading="importing" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- Image Preview Dialog -->
    <el-dialog v-model="previewVisible" title="凭证预览" width="600px" destroy-on-close>
      <img :src="previewUrl" style="width: 100%; object-fit: contain" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getProjectCosts, createProjectCost, updateProjectCost, deleteProjectCost, importProjectCosts,
  getProjectCostAttachments, uploadProjectCostAttachment, deleteProjectCostAttachment,
} from '@/api/payments'
import { getOrder } from '@/api/orders'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus, Delete, Download } from '@element-plus/icons-vue'
import type { ProjectCostResponse, ProjectCostImportResponse, OrderDetailResponse, AttachmentResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const CATEGORIES = ['人工/工时费', '运输/物流费', '安装杂费', '其他']
const PAYMENT_METHODS = ['现金支付', '微信支付', '转账支付', '对公支付', '其它支付']

const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const list = ref<ProjectCostResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterCategory = ref('')
const dateRange = ref<string[] | null>(null)
const showDialog = ref(false)
const showImport = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const order = ref<OrderDetailResponse | null>(null)
const selectedFile = ref<File | null>(null)
const importResult = ref<ProjectCostImportResponse | null>(null)
const dialogAttachments = ref<AttachmentResponse[]>([])
const uploadingAtt = ref(false)
const previewVisible = ref(false)
const previewUrl = ref('')

// Detect source type: order or quote
const isQuote = computed(() => route.path.includes('/quote-costs/'))
const sourceId = computed(() => {
  if (isQuote.value) return route.params.quoteId as string
  return route.params.orderId as string
})

const totalCost = computed(() => {
  return list.value.reduce((sum, c) => sum + (c.amount || 0), 0)
})

const orderItems = computed(() => order.value?.items || [])

const form = reactive({
  category: '',
  amount: 0,
  payment_method: '',
  payee_company_name: '',
  debt_amount: 0,
  cost_date: '',
  description: '',
  remark: '',
  order_item_id: '',
})

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function resetForm() {
  Object.assign(form, { category: '', amount: 0, payment_method: '', payee_company_name: '', debt_amount: 0, cost_date: '', description: '', remark: '', order_item_id: '' })
  isEditing.value = false
  editingId.value = ''
  dialogAttachments.value = []
}

function openCreate() {
  resetForm()
  showDialog.value = true
}

function openEdit(row: ProjectCostResponse) {
  isEditing.value = true
  editingId.value = row.id
  form.category = row.category
  form.amount = row.amount
  form.payment_method = row.payment_method || ''
  form.payee_company_name = row.payee_company_name || ''
  form.debt_amount = row.debt_amount || 0
  form.cost_date = row.cost_date?.slice(0, 10) || ''
  form.description = row.description || ''
  form.remark = row.remark || ''
  form.order_item_id = row.order_item_id || ''
  dialogAttachments.value = []
  showDialog.value = true
  loadAttachments(row.id)
}

function openImport() {
  showImport.value = true
  selectedFile.value = null
  importResult.value = null
}

function onFileChange(file: unknown) {
  selectedFile.value = file.raw
}

function downloadTemplate() {
  const token = localStorage.getItem('token')
  const url = '/api/v1/project-costs/template'
  fetch(url, { headers: { Authorization: 'Bearer ' + token } })
    .then(function(res) {
      if (!res.ok) throw new Error('Download failed')
      return res.blob()
    })
    .then(function(blob) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = '项目成本导入模板.xlsx'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    })
    .catch(function() {
      ElMessage.error('下载模板失败')
    })
}

async function fetchOrder() {
  try {
    if (isQuote.value) {
      const { getQuote } = await import('@/api/quotes')
      order.value = await getQuote(sourceId.value)
    } else {
      order.value = await getOrder(sourceId.value)
    }
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (isQuote.value) {
      params.quote_id = sourceId.value
      params.source_type = 'quote'
    } else {
      params.order_id = sourceId.value
    }
    if (filterCategory.value) params.category = filterCategory.value
    if (dateRange.value) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const data = await getProjectCosts(params)
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      const payload: Record<string, unknown> = {}
      if (form.category) payload.category = form.category
      if (form.amount > 0) payload.amount = form.amount
      if (form.payment_method) payload.payment_method = form.payment_method
      if (form.payee_company_name) payload.payee_company_name = form.payee_company_name
      if (form.debt_amount > 0) payload.debt_amount = form.debt_amount
      else payload.debt_amount = 0
      if (form.cost_date) payload.cost_date = form.cost_date
      if (form.description) payload.description = form.description
      if (form.remark) payload.remark = form.remark
      if (form.order_item_id) payload.order_item_id = form.order_item_id
      await updateProjectCost(editingId.value, payload)
      ElMessage.success('成本已更新')
    } else {
      if (isQuote.value) {
        await createProjectCost({
          source_type: 'quote',
          quote_id: sourceId.value,
          category: form.category,
          amount: form.amount,
          cost_date: form.cost_date || undefined,
          description: form.description || undefined,
          remark: form.remark || undefined,
          order_item_id: form.order_item_id || undefined,
          payment_method: form.payment_method || undefined,
          payee_company_name: form.payee_company_name || undefined,
          debt_amount: form.debt_amount > 0 ? form.debt_amount : undefined,
        })
      } else {
        await createProjectCost({
          source_type: 'order',
          order_id: sourceId.value,
          category: form.category,
          amount: form.amount,
          cost_date: form.cost_date || undefined,
          description: form.description || undefined,
          remark: form.remark || undefined,
          order_item_id: form.order_item_id || undefined,
          payment_method: form.payment_method || undefined,
          payee_company_name: form.payee_company_name || undefined,
          debt_amount: form.debt_amount > 0 ? form.debt_amount : undefined,
        })
      }
      ElMessage.success('成本登记成功')
    }
    showDialog.value = false
    resetForm()
    fetchData()
  } catch {
    // API error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: ProjectCostResponse) {
  try {
    await ElMessageBox.confirm(`确定删除成本「${row.cost_no}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProjectCost(row.id)
    ElMessage.success('已删除')
    fetchData()
  } catch {
    // User cancelled or API error
  }
}

function goBack() {
  if (isQuote.value && window.history.length > 1) {
    history.back()
  } else {
    router.push('/project-costs')
  }
}

async function handleImport() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择Excel文件')
    return
  }
  importing.value = true
  try {
    const result = await importProjectCosts(selectedFile.value, isQuote.value ? undefined : sourceId.value, isQuote.value ? sourceId.value : undefined, isQuote.value ? 'quote' : 'order')
    importResult.value = result
    if (result.created > 0) {
      fetchData()
    }
  } catch {
    // API error handled by interceptor
  } finally {
    importing.value = false
  }
}

async function loadAttachments(costId: string) {
  try {
    dialogAttachments.value = await getProjectCostAttachments(costId)
  } catch { /* ignore */ }
}

async function handleUploadAtt(file: File) {
  if (!editingId.value) return
  uploadingAtt.value = true
  try {
    const att = await uploadProjectCostAttachment(editingId.value, file)
    dialogAttachments.value.unshift(att)
    fetchData()
  } catch {
    // handled by interceptor
  } finally {
    uploadingAtt.value = false
  }
}

function onUploadChange(uploadFile: unknown) {
  handleUploadAtt(uploadFile.raw || uploadFile)
  return false // prevent el-upload auto upload
}

async function handleDeleteAtt(att: AttachmentResponse) {
  try {
    await ElMessageBox.confirm(`确定删除凭证「${att.filename}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProjectCostAttachment(att.id)
    dialogAttachments.value = dialogAttachments.value.filter(a => a.id !== att.id)
    ElMessage.success('已删除')
    fetchData()
  } catch { /* cancelled */ }
}

function handlePreviewAtt(att: AttachmentResponse) {
  const url = `/uploads/${att.file_path}`
  if (att.file_type?.startsWith('image/')) {
    previewUrl.value = url
    previewVisible.value = true
  } else {
    window.open(url, '_blank')
  }
}

onMounted(() => {
  fetchOrder()
  fetchData()
})
</script>

<style scoped>
.page { padding: 0; }
.order-header { margin-bottom: 8px; }
.order-card { background: var(--ad-card); border: 1px solid var(--ad-border); }
.order-info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: center;
}
.order-info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.order-info-item .label {
  font-size: 12px;
  color: var(--ad-text-secondary, #888);
}
.order-info-item .value {
  font-size: 14px;
  color: var(--ad-text);
}
.search-bar { display: flex; align-items: center; }
.att-thumb {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--ad-border, #dcdfe6);
  cursor: pointer;
}
.att-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.att-file {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  font-size: 12px;
  color: #909399;
  font-weight: bold;
}
.att-del {
  position: absolute;
  top: 2px;
  right: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}
.att-thumb:hover .att-del {
  opacity: 1;
}
</style>
