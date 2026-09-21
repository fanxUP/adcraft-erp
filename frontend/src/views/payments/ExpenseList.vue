<template>
  <AppPage>
    <template #header>
      <PageHeader title="支出管理" description="统一登记和维护经营支出，金额与日期格式保持一致。">
        <template #actions><el-button @click="openCreate" type="danger">登记支出</el-button></template>
      </PageHeader>
    </template>

    <template #toolbar>
      <PageToolbar aria-label="支出筛选">
      <el-select v-model="filterCategory" placeholder="支出分类" clearable style="width: 160px" @change="fetchData">
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
      <el-button style="margin-left: 12px" @click="fetchData" type="primary">搜索</el-button>
      </PageToolbar>
    </template>

    <DataTableShell :state="tableState" aria-label="支出列表">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="list" stripe>
      <el-table-column prop="expense_no" label="编号" width="180" />
      <el-table-column prop="category" label="分类" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="总金额" width="120" align="right">
        <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
      </el-table-column>
      <el-table-column label="供应商" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.supplier_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="已支付" width="120" align="right">
        <template #default="{ row }">
          <span :class="{ 'text-success': expensePaidAmount(row) > 0 }">{{ formatMoney(expensePaidAmount(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="剩余欠款" width="120" align="right">
        <template #default="{ row }">
          <span :class="{ 'text-warning': expenseRemainingAmount(row) > 0 }">{{ formatMoney(expenseRemainingAmount(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="105" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="payableStatusType(expensePayableStatus(row))">
            {{ payableStatusLabel(expensePayableStatus(row)) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="日期" width="120">
        <template #default="{ row }">{{ formatDate(row.expense_date) || '-' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row as ExpenseResponse)">编辑</el-button>
          <el-button v-if="authStore.can('expense:delete')" text type="danger" size="small" @click="handleDelete(row as ExpenseResponse)">删除</el-button>
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

    <el-dialog
      v-model="showDialog"
      :title="isEditing ? '编辑支出' : '登记支出'"
      width="min(94vw, 620px)"
      :close-on-click-modal="false"
      @closed="handleExpenseDialogClosed"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="日期">
          <el-date-picker v-model="form.expense_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="canUseSupplier" label="供应商">
          <el-select
            v-model="form.supplier_id"
            clearable
            filterable
            placeholder="选择供应商（可选）"
            style="width: 100%"
          >
            <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
          </el-select>
          <div class="form-tip">可选；选择后将这笔支出关联到供应商。</div>
        </el-form-item>
        <el-form-item label="支付金额">
          <el-input-number v-model="form.paid_amount" :min="0" :precision="2" style="width: 100%" />
          <div class="form-tip">登记这笔支出时已经支付的金额，不会进入应付管理。</div>
        </el-form-item>
        <el-form-item label="欠款金额">
          <el-input-number v-model="form.payable_amount" :min="0" :precision="2" style="width: 100%" />
          <div class="form-tip">这部分会进入应付管理，后续付款在应付管理中登记。</div>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="选择分类" clearable style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="form.payment_method" placeholder="选择付款方式（可选）" clearable style="width: 100%">
            <el-option v-for="pm in PAYMENT_METHODS" :key="pm" :label="pm" :value="pm" />
          </el-select>
        </el-form-item>
        <el-form-item label="支出总额">
          <span class="form-total">{{ formatMoney(totalAmount) }}</span>
          <div class="form-tip">支出总额 = 支付金额 + 欠款金额。</div>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="支出说明…" />
        </el-form-item>
        <el-form-item label="凭证">
          <div
            class="expense-attachment-dropzone"
            :class="{ 'is-dragover': expenseAttachmentDragActive }"
            role="button"
            tabindex="0"
            @click="openExpenseAttachmentPicker"
            @keydown.enter.prevent="openExpenseAttachmentPicker"
            @keydown.space.prevent="openExpenseAttachmentPicker"
            @dragenter.prevent="handleExpenseAttachmentDragEnter"
            @dragover.prevent="handleExpenseAttachmentDragOver"
            @dragleave.prevent="handleExpenseAttachmentDragLeave"
            @drop.prevent="handleExpenseAttachmentDrop"
          >
            <input
              ref="expenseAttachmentInput"
              class="expense-attachment-input"
              type="file"
              multiple
              :accept="EXPENSE_ATTACHMENT_ACCEPT"
              @click.stop
              @change="handleExpenseAttachmentInputChange"
            />
            <el-icon class="expense-attachment-drop-icon"><UploadFilled /></el-icon>
            <div class="expense-attachment-drop-title">将凭证拖到这里上传</div>
            <div class="expense-attachment-drop-subtitle">或点击选择文件，支持批量上传</div>
            <div class="expense-attachment-drop-hint">
              支持 JPG、PNG、WEBP、PDF；{{ isEditing ? '上传后立即保存到这笔支出' : '保存支出后自动上传' }}
            </div>
          </div>

          <div v-if="expenseAttachmentUploadQueue.length" class="expense-attachment-upload-queue">
            <div v-for="item in expenseAttachmentUploadQueue" :key="item.id" class="expense-attachment-upload-row">
              <span class="expense-attachment-upload-name" :title="item.name">{{ item.name }}</span>
              <el-tag v-if="item.status === 'queued'" size="small" type="info">{{ isEditing ? '等待上传' : '待保存' }}</el-tag>
              <el-tag v-else-if="item.status === 'uploading'" size="small" type="warning">上传中</el-tag>
              <template v-else>
                <el-tag size="small" type="danger">{{ item.error || '上传失败' }}</el-tag>
                <el-button text type="primary" size="small" @click="retryExpenseAttachment(item)">重试</el-button>
              </template>
            </div>
          </div>

          <div v-if="dialogAttachments.length" class="expense-attachment-grid">
            <div v-for="attachment in dialogAttachments" :key="attachment.id" class="expense-attachment-item">
              <el-image
                v-if="expenseAttachmentKind(attachment) === 'image' && attachment.preview_url"
                class="expense-attachment-image"
                :src="attachment.preview_url"
                :alt="attachment.filename"
                fit="cover"
                lazy
                :preview-src-list="expenseImageAttachmentUrls"
                :initial-index="expenseImagePreviewIndex(attachment.id)"
                :zoom-rate="EXPENSE_ATTACHMENT_PREVIEW_ZOOM_RATE"
                preview-teleported
              />
              <button
                v-else
                type="button"
                class="expense-attachment-file"
                :title="`打开 ${attachment.filename || '凭证'}`"
                @click="previewExpenseAttachment(attachment)"
              >
                <span class="expense-attachment-file-ext">{{ expenseAttachmentExtension(attachment.filename) }}</span>
                <span class="expense-attachment-file-name">{{ attachment.filename || '凭证文件' }}</span>
              </button>
              <div class="expense-attachment-name" :title="attachment.filename">
                {{ attachment.filename || '未命名凭证' }} · {{ formatExpenseAttachmentSize(attachment.file_size) }}
              </div>
              <el-button
                v-if="authStore.can('expense:delete')"
                class="expense-attachment-delete"
                :icon="Delete"
                size="small"
                circle
                :aria-label="`删除凭证 ${attachment.filename || ''}`"
                @click="handleDeleteExpenseAttachment(attachment)"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" :disabled="expenseAttachmentUploading" @click="handleSave" type="primary">
          {{ isEditing ? '保存' : '登记' }}
        </el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  deleteExpense,
  deleteExpenseAttachment,
  createExpense,
  deleteExpenseConfirmed,
  downloadExpenseAttachment,
  getExpenseAttachments,
  getExpenses,
  updateExpense,
  uploadExpenseAttachment,
} from '@/api/payments'
import { getSuppliers } from '@/api/suppliers'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, UploadFilled } from '@element-plus/icons-vue'
import type { AttachmentResponse, ExpenseResponse, SupplierResponse } from '@/types/api'
import { normalizeExpenseAmounts, type ExpenseAmountResult } from '@/utils/expenseAmount'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel } from '@/components/ui'

const authStore = useAuthStore()
const canUseSupplier = computed(() => authStore.can('supplier:read'))

const CATEGORIES = ['房租', '水电', '材料采购', '外协加工', '运输', '办公', '工资', '税费', '其他']
const PAYMENT_METHODS = ['现金支付', '微信支付', '支付宝转账', '转账支付', '对公支付', '其它支付']

const loading = ref(false)
const saving = ref(false)
const list = ref<ExpenseResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loadError = ref(false)
const filterCategory = ref('')
const dateRange = ref<string[] | null>(null)
const suppliers = ref<SupplierResponse[]>([])
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const form = reactive({ category: '', payment_method: '', paid_amount: 0, supplier_id: '', payable_amount: 0, expense_date: '', description: '' })

const EXPENSE_ATTACHMENT_ACCEPT = 'image/jpeg,image/png,image/webp,.pdf'
const EXPENSE_ATTACHMENT_MAX_BYTES = 20 * 1024 * 1024
const EXPENSE_ATTACHMENT_PREVIEW_ZOOM_RATE = 1.05

type LocalExpenseAttachment = AttachmentResponse & {
  preview_url?: string
  preview_error?: boolean
}

type ExpenseAttachmentUploadItem = {
  id: string
  expenseId: string
  file: File
  name: string
  status: 'queued' | 'uploading' | 'error'
  error?: string
}

const dialogAttachments = ref<LocalExpenseAttachment[]>([])
const expenseAttachmentUploadQueue = ref<ExpenseAttachmentUploadItem[]>([])
const expenseAttachmentInput = ref<HTMLInputElement | null>(null)
const expenseAttachmentDragActive = ref(false)
const expenseAttachmentUploading = ref(false)
const expenseImageAttachmentUrls = computed(() => dialogAttachments.value
  .filter(attachment => expenseAttachmentKind(attachment) === 'image' && attachment.preview_url)
  .map(attachment => attachment.preview_url as string))
const attachmentObjectUrls = new Map<string, string>()
let expenseAttachmentDragDepth = 0
let expenseAttachmentQueueRunning = false
let expenseAttachmentSequence = 0

const totalAmount = computed(() => roundMoney(Number(form.paid_amount || 0) + Number(form.payable_amount || 0)))

const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return list.value.length ? 'ready' : 'empty'
})

function resetForm() {
  clearExpenseAttachmentState()
  Object.assign(form, { category: '', payment_method: '', paid_amount: 0, supplier_id: '', payable_amount: 0, expense_date: '', description: '' })
  isEditing.value = false
  editingId.value = ''
}

function openCreate() {
  resetForm()
  showDialog.value = true
}

function openEdit(row: ExpenseResponse) {
  resetForm()
  isEditing.value = true
  editingId.value = row.id
  form.category = row.category || ''
  form.payment_method = row.payment_method || ''
  form.paid_amount = row.initial_paid_amount ?? Math.max(0, row.amount - (row.payable_amount || 0))
  form.supplier_id = row.supplier_id || ''
  form.payable_amount = row.payable_amount || 0
  const formattedExpenseDate = formatDate(row.expense_date)
  form.expense_date = formattedExpenseDate === '-' ? '' : formattedExpenseDate
  form.description = row.description || ''
  showDialog.value = true
  void loadExpenseAttachments(row.id)
}

async function fetchSuppliers() {
  if (!canUseSupplier.value) return
  try {
    const data = await getSuppliers({ page: 1, page_size: 200, is_active: true })
    suppliers.value = data.items
  } catch {
    // A missing supplier directory should not block non-supplier expenses.
  }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filterCategory.value ? { category: filterCategory.value } : {}),
      ...(dateRange.value ? { start_date: dateRange.value[0], end_date: dateRange.value[1] } : {}),
    }
    const data = await getExpenses(params)
    list.value = data.items
    total.value = data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function roundMoney(value: number) {
  return Math.round((Number(value) + Number.EPSILON) * 100) / 100
}

function expensePaidAmount(row: ExpenseResponse) {
  return row.total_paid_amount ?? row.initial_paid_amount ?? Math.max(0, row.amount - (row.payable_amount || 0))
}

function expenseRemainingAmount(row: ExpenseResponse) {
  return row.remaining_payable_amount ?? row.payable_amount ?? 0
}

function expensePayableStatus(row: ExpenseResponse) {
  if (row.payable_status) return row.payable_status
  return expenseRemainingAmount(row) > 0 ? 'unpaid' : 'paid'
}

function payableStatusLabel(status: string) {
  return ({ unpaid: '待付款', partial: '部分付款', paid: '已付款' } as Record<string, string>)[status] || status
}

function payableStatusType(status: string) {
  return ({ unpaid: 'warning', partial: 'warning', paid: 'success' } as Record<string, string>)[status] || 'info'
}

function clearExpenseAttachmentState() {
  for (const url of attachmentObjectUrls.values()) URL.revokeObjectURL(url)
  attachmentObjectUrls.clear()
  dialogAttachments.value = []
  // If a dialog is closed while a request is in flight, keep that request's
  // item until the runner finishes so it cannot be started a second time.
  expenseAttachmentUploadQueue.value = expenseAttachmentQueueRunning
    ? expenseAttachmentUploadQueue.value.filter(item => item.status === 'uploading')
    : []
  expenseAttachmentDragActive.value = false
  expenseAttachmentDragDepth = 0
}

function handleExpenseDialogClosed() {
  clearExpenseAttachmentState()
  Object.assign(form, {
    category: '',
    paid_amount: 0,
    supplier_id: '',
    payable_amount: 0,
    expense_date: '',
    description: '',
  })
  isEditing.value = false
  editingId.value = ''
}

function expenseAttachmentKind(
  attachment: Pick<AttachmentResponse, 'filename' | 'file_type'>,
): 'image' | 'pdf' | 'file' {
  const type = attachment.file_type?.split(';', 1)[0].trim().toLowerCase() || ''
  const extension = attachment.filename?.trim().toLowerCase().match(/\.[a-z0-9]+$/)?.[0] || ''
  if (type.startsWith('image/') || ['.jpg', '.jpeg', '.png', '.webp'].includes(extension)) return 'image'
  if (type === 'application/pdf' || extension === '.pdf') return 'pdf'
  return 'file'
}

function expenseAttachmentExtension(filename?: string | null) {
  const extension = filename?.trim().split('.').pop()
  return extension ? extension.toUpperCase() : '文件'
}

function formatExpenseAttachmentSize(size?: number | null) {
  if (!size || size < 1024) return `${size || 0} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function openExpenseAttachmentPicker() {
  expenseAttachmentInput.value?.click()
}

function handleExpenseAttachmentDragEnter() {
  expenseAttachmentDragDepth += 1
  expenseAttachmentDragActive.value = true
}

function handleExpenseAttachmentDragOver() {
  expenseAttachmentDragActive.value = true
}

function handleExpenseAttachmentDragLeave() {
  expenseAttachmentDragDepth = Math.max(0, expenseAttachmentDragDepth - 1)
  if (expenseAttachmentDragDepth === 0) expenseAttachmentDragActive.value = false
}

function handleExpenseAttachmentDrop(event: DragEvent) {
  expenseAttachmentDragDepth = 0
  expenseAttachmentDragActive.value = false
  enqueueExpenseAttachments(Array.from(event.dataTransfer?.files || []))
}

function handleExpenseAttachmentInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  enqueueExpenseAttachments(files)
}

function validateExpenseAttachment(file: File) {
  const type = file.type.split(';', 1)[0].trim().toLowerCase()
  const extension = file.name.trim().toLowerCase().match(/\.[a-z0-9]+$/)?.[0] || ''
  const supportedExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.pdf']
  const supportedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
  if (!supportedExtensions.includes(extension)) return '无法识别文件格式，请使用 JPG、PNG、WEBP 或 PDF'
  if (type && type !== 'application/octet-stream' && !supportedTypes.includes(type)) {
    return '凭证仅支持 JPG、PNG、WEBP 或 PDF 文件'
  }
  if (file.size > EXPENSE_ATTACHMENT_MAX_BYTES) return '文件不能超过20MB'
  return null
}

function enqueueExpenseAttachments(files: File[]) {
  if (!files.length) return

  const accepted: File[] = []
  let rejectedCount = 0
  for (const file of files.slice(0, 20)) {
    if (validateExpenseAttachment(file)) rejectedCount += 1
    else accepted.push(file)
  }
  if (files.length > 20) ElMessage.warning('单次最多上传20个凭证，已忽略超出部分')
  if (rejectedCount) ElMessage.warning(`${rejectedCount} 个凭证格式或大小不支持`)
  if (!accepted.length) return

  const expenseId = editingId.value
  expenseAttachmentUploadQueue.value.push(...accepted.map(file => ({
    id: `expense-${Date.now()}-${expenseAttachmentSequence++}`,
    expenseId,
    file,
    name: file.name,
    status: 'queued' as const,
  })))
  if (expenseId) void startExpenseAttachmentUploadQueue()
}

async function startExpenseAttachmentUploadQueue() {
  if (expenseAttachmentQueueRunning || !editingId.value) return
  const expenseId = editingId.value
  expenseAttachmentQueueRunning = true
  expenseAttachmentUploading.value = true
  try {
    while (true) {
      const next = expenseAttachmentUploadQueue.value.find(item =>
        item.status === 'queued' && (!item.expenseId || item.expenseId === expenseId),
      )
      if (!next) break
      next.expenseId = expenseId
      next.status = 'uploading'
      try {
        const attachment = await uploadExpenseAttachment(expenseId, next.file)
        if (showDialog.value && isEditing.value && editingId.value === expenseId) {
          const localAttachment = { ...attachment }
          dialogAttachments.value.unshift(localAttachment)
          await loadExpenseAttachmentPreview(localAttachment, expenseId)
        }
        expenseAttachmentUploadQueue.value = expenseAttachmentUploadQueue.value.filter(item => item.id !== next.id)
        ElMessage.success(`${next.name} 上传成功`)
      } catch (error: unknown) {
        next.status = 'error'
        next.error = error instanceof Error ? error.message : '上传失败，请重试'
      }
    }
  } finally {
    expenseAttachmentQueueRunning = false
    expenseAttachmentUploading.value = false
  }
}

function retryExpenseAttachment(item: ExpenseAttachmentUploadItem) {
  if (item.status !== 'error' || !editingId.value) return
  item.status = 'queued'
  item.error = undefined
  item.expenseId = editingId.value
  void startExpenseAttachmentUploadQueue()
}

async function loadExpenseAttachments(expenseId: string) {
  try {
    const attachments = await getExpenseAttachments(expenseId)
    if (!showDialog.value || !isEditing.value || editingId.value !== expenseId) return
    dialogAttachments.value = attachments.map(attachment => ({ ...attachment }))
    await Promise.all(dialogAttachments.value.map(attachment => loadExpenseAttachmentPreview(attachment, expenseId)))
  } catch {
    ElMessage.warning('凭证加载失败，请稍后重试')
  }
}

async function loadExpenseAttachmentPreview(attachment: LocalExpenseAttachment, expenseId: string) {
  if (expenseAttachmentKind(attachment) !== 'image' || attachment.preview_url || attachment.preview_error) return
  try {
    const blob = await downloadExpenseAttachment(expenseId, attachment.id)
    if (!showDialog.value || !isEditing.value || editingId.value !== expenseId) return
    const url = URL.createObjectURL(blob)
    attachmentObjectUrls.set(attachment.id, url)
    attachment.preview_url = url
  } catch {
    attachment.preview_error = true
  }
}

async function previewExpenseAttachment(attachment: LocalExpenseAttachment) {
  if (!editingId.value) return
  try {
    const blob = await downloadExpenseAttachment(editingId.value, attachment.id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch {
    ElMessage.error('凭证预览失败，请稍后重试')
  }
}

async function handleDeleteExpenseAttachment(attachment: LocalExpenseAttachment) {
  if (!editingId.value) return
  try {
    await ElMessageBox.confirm(`确定删除凭证「${attachment.filename}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteExpenseAttachment(editingId.value, attachment.id)
    dialogAttachments.value = dialogAttachments.value.filter(item => item.id !== attachment.id)
    const url = attachmentObjectUrls.get(attachment.id)
    if (url) {
      URL.revokeObjectURL(url)
      attachmentObjectUrls.delete(attachment.id)
    }
    ElMessage.success('凭证已删除')
    void fetchData()
  } catch {
    // User cancelled or API error (handled by the interceptor).
  }
}

function expenseImagePreviewIndex(attachmentId: string) {
  return dialogAttachments.value
    .filter(attachment => expenseAttachmentKind(attachment) === 'image' && attachment.preview_url)
    .findIndex(attachment => attachment.id === attachmentId)
}

async function handleSave() {
  let normalizedAmounts: ExpenseAmountResult
  try {
    normalizedAmounts = normalizeExpenseAmounts(totalAmount.value, form.payable_amount)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '请填写有效的支出金额')
    return
  }

  saving.value = true
  try {
    let savedExpense: ExpenseResponse
    if (isEditing.value) {
      const payload = {
        ...(form.category ? { category: form.category } : {}),
        payment_method: form.payment_method || null,
        amount: normalizedAmounts.amount,
        paid_amount: form.paid_amount,
        supplier_id: form.supplier_id || null,
        payable_amount: normalizedAmounts.payable_amount,
        ...(form.expense_date ? { expense_date: form.expense_date } : {}),
        ...(form.description ? { description: form.description } : {}),
      }
      savedExpense = await updateExpense(editingId.value, payload)
      ElMessage.success('支出已更新')
    } else {
      savedExpense = await createExpense({
        amount: normalizedAmounts.amount,
        paid_amount: form.paid_amount,
        payable_amount: normalizedAmounts.payable_amount,
        category: form.category || undefined,
        payment_method: form.payment_method || undefined,
        supplier_id: form.supplier_id || undefined,
        expense_date: form.expense_date || undefined,
        description: form.description || undefined,
      })
      isEditing.value = true
      editingId.value = savedExpense.id
      ElMessage.success('支出登记成功')
    }

    // New expenses have no server id until the main record is saved. Upload
    // their queued vouchers immediately after that record is created.
    if (savedExpense.id) await startExpenseAttachmentUploadQueue()
    if (expenseAttachmentUploadQueue.value.some(item => item.status === 'error')) {
      ElMessage.warning('支出已保存，部分凭证上传失败，请重试')
      void fetchData()
      return
    }

    showDialog.value = false
    void fetchData()
  } catch {
    // API error handled by interceptor, cancel does nothing
  } finally { saving.value = false }
}

async function handleDelete(row: ExpenseResponse) {
  try {
    const payablePaymentCount = row.payable_payment_count ?? 0
    const payablePaidAmount = row.payable_paid_amount ?? 0
    if (payablePaymentCount > 0 || payablePaidAmount > 0) {
      if (!authStore.can('expense:update')) {
        await ElMessageBox.alert(
          '当前账号没有撤销应付付款流水的权限，请联系管理员处理。',
          '无法执行联动删除',
          { confirmButtonText: '知道了', type: 'warning' },
        )
        return
      }
      await ElMessageBox.confirm(
        `支出「${row.expense_no}」在应付管理中有 ${payablePaymentCount} 条有效付款流水，共 ${formatMoney(payablePaidAmount)}。确认后系统将先撤销这些付款流水（保留付款编号和审计记录），再删除支出。此操作不可由普通用户恢复，是否继续？`,
        '撤销应付并删除',
        {
          confirmButtonText: '撤销付款并删除',
          cancelButtonText: '取消',
          type: 'warning',
          distinguishCancelAndClose: true,
        },
      )
      const result = await deleteExpenseConfirmed(row.id, {
        expected_payment_count: payablePaymentCount,
        expected_paid_amount: payablePaidAmount,
      })
      ElMessage.success(`已撤销 ${result.payment_count} 条应付付款流水并删除支出`)
      await fetchData()
      return
    }
    await ElMessageBox.confirm(`确定删除支出「${row.expense_no}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消', type: 'warning',
    })
    await deleteExpense(row.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}

onMounted(() => {
  void fetchData()
  void fetchSuppliers()
})

onUnmounted(() => {
  clearExpenseAttachmentState()
})
</script>

<style scoped>
.muted { color: var(--ad-text-secondary, #888); }
.text-warning { color: var(--el-color-warning); font-weight: 600; }
.text-success { color: var(--el-color-success); font-weight: 600; }
.form-tip { color: var(--ad-text-secondary, #888); font-size: 12px; line-height: 1.5; }
.form-total { color: var(--ad-text); font-size: 18px; font-weight: 700; }
.expense-attachment-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 132px;
  padding: 16px;
  box-sizing: border-box;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
  color: var(--ad-text-secondary, #909399);
  cursor: pointer;
  transition: border-color .2s, background-color .2s;
}
.expense-attachment-dropzone:hover,
.expense-attachment-dropzone.is-dragover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.expense-attachment-dropzone:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}
.expense-attachment-input { display: none; }
.expense-attachment-drop-icon { margin-bottom: 8px; color: var(--el-color-primary); font-size: 30px; }
.expense-attachment-drop-title { color: var(--ad-text, #303133); font-size: 14px; font-weight: 600; }
.expense-attachment-drop-subtitle { margin-top: 4px; color: var(--el-color-primary); font-size: 13px; }
.expense-attachment-drop-hint { margin-top: 8px; font-size: 12px; line-height: 1.4; text-align: center; }
.expense-attachment-upload-queue { display: flex; flex-direction: column; gap: 6px; width: 100%; margin-top: 10px; }
.expense-attachment-upload-row { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 6px 8px; border-radius: 4px; background: var(--el-fill-color-light); font-size: 12px; }
.expense-attachment-upload-name { flex: 1; min-width: 0; overflow: hidden; color: var(--ad-text, #303133); text-overflow: ellipsis; white-space: nowrap; }
.expense-attachment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; width: 100%; margin-top: 14px; }
.expense-attachment-item { position: relative; min-width: 0; overflow: hidden; border: 1px solid var(--ad-border, #dcdfe6); border-radius: 8px; background: var(--ad-card, #fff); }
.expense-attachment-image,
.expense-attachment-file { display: flex; width: 100%; height: 112px; box-sizing: border-box; }
.expense-attachment-image { cursor: zoom-in; }
.expense-attachment-file { flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 12px; border: 0; background: var(--el-fill-color-lighter); color: var(--ad-text-secondary, #606266); cursor: pointer; text-align: center; }
.expense-attachment-file:hover { background: var(--el-fill-color-light); }
.expense-attachment-file-ext { color: var(--el-color-primary); font-size: 18px; font-weight: 700; }
.expense-attachment-file-name,
.expense-attachment-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.expense-attachment-file-name { width: 100%; font-size: 12px; }
.expense-attachment-name { padding: 7px 34px 7px 8px; color: var(--ad-text-secondary, #606266); font-size: 12px; }
.expense-attachment-delete { position: absolute; top: 2px; right: 2px; opacity: 0; transition: opacity .2s; }
.expense-attachment-item:hover .expense-attachment-delete,
.expense-attachment-delete:focus-visible { opacity: 1; }
@media (max-width: 760px) {
  .expense-attachment-grid { grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); }
}
</style>
