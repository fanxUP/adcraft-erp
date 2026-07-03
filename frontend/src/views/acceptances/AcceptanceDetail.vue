<template>
  <div class="page">
    <div class="page-header">
      <el-button text @click="$router.push('/acceptances')" style="font-size: 16px;">← 返回</el-button>
      <h2>{{ isCreate ? '新建验收单' : form.acceptance_no }}</h2>
      <div class="header-actions" v-if="!isCreate">
        <el-button
          v-if="form.status === 'draft'"
          type="primary" @click="handleSubmit"
        >提交验收</el-button>
        <el-button
          v-if="form.status === 'pending'"
          type="success" @click="handleAccept"
        >确认验收</el-button>
        <el-button
          v-if="form.status === 'pending'"
          type="danger" @click="handleReject"
        >驳回</el-button>
        <el-button
          v-if="form.status === 'rejected'"
          type="warning" @click="handleBackToDraft"
        >退回草稿</el-button>
        <el-button
          v-if="form.status === 'accepted' || form.status === 'rejected'"
          @click="showPrint = true"
        >
          <el-icon><Printer /></el-icon> 打印
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <el-card>
          <el-form :model="form" label-width="100px" :disabled="!canEdit">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="关联订单" required>
                  <el-select
                    v-model="form.order_id"
                    filterable
                    remote
                    :remote-method="searchOrders"
                    :loading="orderSearching"
                    placeholder="搜索订单"
                    :disabled="!isCreate"
                  >
                    <el-option
                      v-for="o in orderOptions"
                      :key="o.id"
                      :label="`${o.order_no} - ${o.customer_name || ''}`"
                      :value="o.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="客户签收人">
                  <el-input v-model="form.accepted_by" placeholder="客户方签收人姓名" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="我方负责人">
                  <el-select v-model="form.our_acceptor_id" placeholder="选择负责人" clearable filterable>
                    <el-option
                      v-for="u in userOptions"
                      :key="u.id"
                      :label="u.real_name || u.username"
                      :value="u.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="备注">
                  <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="备注信息" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <!-- 只读详情 -->
          <el-descriptions v-if="!isCreate && !canEdit" :column="2" border style="margin-top: 16px;">
            <el-descriptions-item label="状态">
              <el-tag :type="statusColor(form.status)">{{ statusLabel(form.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="验收日期">{{ form.accepted_at?.slice(0, 10) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="客户签收人">{{ form.accepted_by || '-' }}</el-descriptions-item>
            <el-descriptions-item label="我方负责人">{{ form.our_acceptor_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="驳回原因" :span="2" v-if="form.reject_reason">
              <span style="color: var(--el-color-danger);">{{ form.reject_reason }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ form.remark || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ form.created_at?.slice(0, 16) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ form.updated_at?.slice(0, 16) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- 验收明细 -->
      <el-tab-pane label="验收明细" name="items">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>验收明细（已选 {{ selectedCount }}/{{ form.items.length }} 项）</span>
              <div v-if="canEdit" style="display: flex; gap: 8px;">
                <el-button size="small" @click="toggleSelectAll">{{ selectedCount === form.items.length ? '取消全选' : '全选' }}</el-button>
                <el-button type="primary" size="small" @click="addItem">手动添加</el-button>
              </div>
            </div>
          </template>

          <el-table ref="itemsTableRef" :data="form.items" border @selection-change="handleSelectionChange">
            <el-table-column v-if="canEdit" type="selection" width="45" :selectable="() => true" />
            <el-table-column v-else type="index" label="#" width="50" />
            <el-table-column label="项目名称" min-width="160">
              <template #default="{ row }">
                <el-input v-if="canEdit" v-model="row.item_name" placeholder="项目名称" />
                <span v-else>{{ row.item_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="规格说明" min-width="140">
              <template #default="{ row }">
                <el-input v-if="canEdit" v-model="row.specification" placeholder="规格" />
                <span v-else>{{ row.specification || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="100">
              <template #default="{ row }">
                <el-input-number v-if="canEdit" v-model="row.quantity" :min="0" :precision="2" size="small" controls-position="right" />
                <span v-else>{{ row.quantity ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="单位" width="80">
              <template #default="{ row }">
                <el-input v-if="canEdit" v-model="row.unit" placeholder="单位" />
                <span v-else>{{ row.unit || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="验收结果" width="120">
              <template #default="{ row }">
                <el-select v-if="!isCreate" v-model="row.item_status" size="small">
                  <el-option label="待验收" value="pending" />
                  <el-option label="通过" value="accepted" />
                  <el-option label="不通过" value="rejected" />
                  <el-option label="有条件通过" value="conditional" />
                </el-select>
                <span v-else>{{ itemStatusLabel(row.item_status) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="120">
              <template #default="{ row }">
                <el-input v-if="canEdit || !isCreate" v-model="row.remark" placeholder="备注" />
                <span v-else>{{ row.remark || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" v-if="canEdit">
              <template #default="{ $index }">
                <el-button text type="danger" size="small" @click="removeItem($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 附件 -->
      <el-tab-pane label="附件" name="attachments" v-if="!isCreate">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>验收照片 / 附件</span>
              <el-upload
                :show-file-list="false"
                :http-request="handleUpload"
                accept="image/*,.pdf,.doc,.docx"
              >
                <el-button type="primary" size="small">上传附件</el-button>
              </el-upload>
            </div>
          </template>

          <el-table :data="form.attachments" border>
            <el-table-column prop="filename" label="文件名" min-width="200" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">
                {{ row.filesize ? (row.filesize / 1024).toFixed(1) + ' KB' : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="downloadFile(row)">下载</el-button>
                <el-button text type="danger" size="small" @click="deleteAtt(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 保存按钮 -->
    <div class="save-bar" v-if="canEdit">
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      <el-button @click="$router.push('/acceptances')">取消</el-button>
    </div>

    <!-- 驳回原因弹框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回验收" width="400px">
      <el-form>
        <el-form-item label="驳回原因" required>
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="statusChanging">确认驳回</el-button>
      </template>
    </el-dialog>

    <AcceptancePrint
      v-if="!isCreate"
      :visible="showPrint"
      :acceptance-id="String(route.params.id)"
      @close="showPrint = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Printer } from '@element-plus/icons-vue'
import {
  getAcceptance, createAcceptance, updateAcceptance,
  changeAcceptanceStatus, uploadAcceptanceAttachment, deleteAcceptanceAttachment
} from '@/api/acceptances'
import { getOrders, getOrder } from '@/api/orders'
import { getUsers } from '@/api/users'
import type {
  AcceptanceDetailResponse, AcceptanceItemResponse, AcceptanceAttachmentResponse,
  OrderListResponse, UserResponse
} from '@/types/api'
import type { ElTable } from 'element-plus'
import AcceptancePrint from './AcceptancePrint.vue'

const route = useRoute()
const router = useRouter()
const activeTab = ref('info')
const saving = ref(false)
const statusChanging = ref(false)
const showPrint = ref(false)
const rejectDialogVisible = ref(false)
const rejectReason = ref('')

const isCreate = computed(() => route.name === 'AcceptanceCreate')
const canEdit = computed(() => isCreate.value || form.status === 'draft' || form.status === 'rejected' || route.query.edit === '1')

const form = reactive<AcceptanceDetailResponse>({
  id: '',
  acceptance_no: '',
  order_id: '',
  order_no: '',
  customer_name: '',
  project_name: '',
  status: 'draft',
  accepted_at: undefined,
  accepted_by: '',
  our_acceptor_id: '',
  our_acceptor_name: '',
  remark: '',
  reject_reason: '',
  created_at: '',
  updated_at: '',
  items: [],
  attachments: [],
})

const orderOptions = ref<OrderListResponse[]>([])
const orderSearching = ref(false)
const userOptions = ref<UserResponse[]>([])
const selectedItems = ref<AcceptanceItemResponse[]>([])
const itemsTableRef = ref<InstanceType<typeof ElTable> | null>(null)

const selectedCount = computed(() => selectedItems.value.length)

function handleSelectionChange(rows: AcceptanceItemResponse[]) {
  selectedItems.value = rows
}

function toggleSelectAll() {
  if (!itemsTableRef.value) return
  if (selectedCount.value === form.items.length) {
    itemsTableRef.value.clearSelection()
  } else {
    itemsTableRef.value.clearSelection()
    form.items.forEach((row) => {
      itemsTableRef.value!.toggleRowSelection(row, true)
    })
  }
}

async function searchOrders(query: string) {
  if (!query) return
  orderSearching.value = true
  try {
    const data = await getOrders({ page: 1, page_size: 20, keyword: query })
    orderOptions.value = data.items
  } finally {
    orderSearching.value = false
  }
}

async function loadOrderItems(orderId: string) {
  try {
    const detail = await getOrder(orderId)
    form.customer_name = detail.customer_name || ''
    if (detail.items && detail.items.length > 0) {
      form.items = detail.items.map((item) => ({
        item_name: item.item_name || '',
        specification: [item.length, item.width, item.height].filter(Boolean).join('×') || '',
        quantity: item.quantity || null,
        unit: item.unit || '',
        order_item_id: item.id,
        item_status: 'pending',
        remark: '',
      }))
      // 默认全选
      await nextTick()
      if (itemsTableRef.value) {
        form.items.forEach((row) => {
          itemsTableRef.value!.toggleRowSelection(row, true)
        })
      }
    }
  } catch { /* ignore */ }
}

async function loadUsers() {
  try {
    const data = await getUsers({ page: 1, page_size: 100 })
    userOptions.value = data.items || data
  } catch { /* ignore */ }
}

function addItem() {
  form.items.push({
    item_name: '',
    specification: '',
    quantity: null,
    unit: '',
    item_status: 'pending',
    remark: '',
  })
}

function removeItem(index: number) {
  form.items.splice(index, 1)
}

async function handleSave() {
  if (!form.order_id) {
    ElMessage.warning('请选择关联订单')
    return
  }
  const itemsToSave = isCreate.value ? selectedItems.value : form.items
  if (isCreate.value && itemsToSave.length === 0) {
    ElMessage.warning('请至少勾选一项验收明细')
    return
  }
  saving.value = true
  try {
    const payload = {
      order_id: form.order_id,
      accepted_by: form.accepted_by || undefined,
      our_acceptor_id: form.our_acceptor_id || undefined,
      remark: form.remark || undefined,
      items: itemsToSave.map((item) => ({
        item_name: item.item_name,
        specification: item.specification || undefined,
        quantity: item.quantity || undefined,
        unit: item.unit || undefined,
        order_item_id: item.order_item_id || undefined,
      })),
    }

    if (isCreate.value) {
      const res = await createAcceptance(payload)
      ElMessage.success('创建成功')
      router.replace(`/acceptances/${res.id}`)
    } else {
      await updateAcceptance(form.id, payload)
      ElMessage.success('保存成功')
      loadDetail(form.id)
    }
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  await ElMessageBox.confirm('确定提交验收？提交后将无法编辑。', '提示')
  await changeAcceptanceStatus(form.id, { to_status: 'pending' })
  ElMessage.success('已提交验收')
  loadDetail(form.id)
}

async function handleAccept() {
  const { value } = await ElMessageBox.prompt('请输入客户签收人（可选）', '确认验收', {
    inputPlaceholder: '签收人姓名',
    confirmButtonText: '确认验收',
    cancelButtonText: '取消',
    inputValue: form.accepted_by || '',
  })
  await changeAcceptanceStatus(form.id, { to_status: 'accepted', accepted_by: value || undefined })
  ElMessage.success('已确认验收')
  loadDetail(form.id)
}

function handleReject() {
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  statusChanging.value = true
  try {
    await changeAcceptanceStatus(form.id, { to_status: 'rejected', reason: rejectReason.value })
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    loadDetail(form.id)
  } finally {
    statusChanging.value = false
  }
}

async function handleBackToDraft() {
  await ElMessageBox.confirm('确定退回草稿？退回后可重新编辑。', '提示')
  await changeAcceptanceStatus(form.id, { to_status: 'draft' })
  ElMessage.success('已退回草稿')
  loadDetail(form.id)
}

async function handleUpload(options: { file: File }) {
  try {
    await uploadAcceptanceAttachment(form.id, options.file)
    ElMessage.success('上传成功')
    loadDetail(form.id)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '上传失败')
  }
}

async function deleteAtt(att: AcceptanceAttachmentResponse) {
  await ElMessageBox.confirm('确定删除该附件？', '提示')
  await deleteAcceptanceAttachment(form.id, att.id)
  ElMessage.success('已删除')
  loadDetail(form.id)
}

function downloadFile(att: AcceptanceAttachmentResponse) {
  window.open(att.filepath, '_blank')
}

async function loadDetail(id: string) {
  const data = await getAcceptance(id)
  Object.assign(form, data)
}

const statusLabel = (s: string) => {
  const map: Record<string, string> = { draft: '草稿', pending: '待验收', accepted: '已验收', rejected: '已驳回' }
  return map[s] || s
}
const statusColor = (s: string): '' | 'success' | 'warning' | 'info' | 'danger' => {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = { draft: 'info', pending: 'warning', accepted: 'success', rejected: 'danger' }
  return map[s] || ''
}
const itemStatusLabel = (s: string) => {
  const map: Record<string, string> = { pending: '待验收', accepted: '通过', rejected: '不通过', conditional: '有条件通过' }
  return map[s] || s
}

onMounted(async () => {
  await loadUsers()
  if (!isCreate.value) {
    await loadDetail(route.params.id as string)
    if (form.order_no) {
      orderOptions.value = [{ id: form.order_id, order_no: form.order_no, customer_name: form.customer_name }]
    }
  }
})

watch(() => route.params.id, async (newId) => {
  if (newId && route.name === 'AcceptanceDetail') {
    await loadDetail(newId as string)
    if (form.order_no) {
      orderOptions.value = [{ id: form.order_id, order_no: form.order_no, customer_name: form.customer_name }]
    }
  }
})

watch(() => form.order_id, async (newOrderId) => {
  if (newOrderId && isCreate.value) {
    await loadOrderItems(newOrderId)
  }
})
</script>

<style scoped>
.page { padding: 20px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); flex: 1; }
.header-actions { display: flex; gap: 8px; }
.save-bar { margin-top: 20px; display: flex; gap: 12px; }
</style>
