<template>
  <div class="page">
    <div class="page-header">
      <h2>用车申请</h2>
      <el-button type="danger" @click="handleCreate">新建申请</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="filters.keyword" placeholder="搜索原因/目的地" clearable style="width: 220px" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px; margin-left: 12px">
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="requester_name" label="申请人" width="100" />
      <el-table-column prop="reason" label="用车原因" min-width="160" />
      <el-table-column prop="destination" label="目的地" width="160" />
      <el-table-column label="出发时间" width="160">
        <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
      </el-table-column>
      <el-table-column label="预计返回" width="160">
        <template #default="{ row }">{{ formatTime(row.expected_return_time) }}</template>
      </el-table-column>
      <el-table-column prop="customer_name" label="关联客户" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleView(row)">查看</el-button>
          <el-button v-if="row.status === 'draft' || row.status === 'rejected'" text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'draft' || row.status === 'rejected'" text type="success" @click="handleSubmit(row)">提交</el-button>
          <el-button v-if="row.status === 'pending'" text type="success" @click="handleApprove(row)">通过</el-button>
          <el-button v-if="row.status === 'pending'" text type="warning" @click="handleReject(row)">驳回</el-button>
          <el-button v-if="!['cancelled', 'completed', 'dispatched'].includes(row.status)" text type="danger" @click="handleCancel(row)">取消</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="650px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="用车原因" required>
          <el-input v-model="form.reason" placeholder="如：安装送货、客户测量、采购材料" />
        </el-form-item>
        <el-form-item label="目的地">
          <el-input v-model="form.destination" placeholder="到达地点" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="出发时间">
              <el-date-picker v-model="form.start_time" type="datetime" placeholder="选择出发时间" style="width: 100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预计返回">
              <el-date-picker v-model="form.expected_return_time" type="datetime" placeholder="选择返回时间" style="width: 100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="需要司机">
              <el-switch v-model="form.need_driver" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="需要装货">
              <el-switch v-model="form.need_cargo" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预计里程">
              <el-input-number v-model="form.estimated_distance_km" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="form.need_cargo" label="货物说明">
          <el-input v-model="form.cargo_description" type="textarea" :rows="2" placeholder="描述需要装载的货物" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存草稿</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="用车申请详情" width="600px">
      <el-descriptions :column="2" border v-if="detail">
        <el-descriptions-item label="申请人">{{ detail.requester_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="用车原因" :span="2">{{ detail.reason }}</el-descriptions-item>
        <el-descriptions-item label="目的地">{{ detail.destination || '-' }}</el-descriptions-item>
        <el-descriptions-item label="出发时间">{{ formatTime(detail.start_time) }}</el-descriptions-item>
        <el-descriptions-item label="预计返回">{{ formatTime(detail.expected_return_time) }}</el-descriptions-item>
        <el-descriptions-item label="需要司机">{{ detail.need_driver ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="需要装货">{{ detail.need_cargo ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.need_cargo" label="货物说明" :span="2">{{ detail.cargo_description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="预计里程">{{ detail.estimated_distance_km ? detail.estimated_distance_km + ' km' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="关联客户">{{ detail.customer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.approver_name" label="审批人">{{ detail.approver_name }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.approved_at" label="审批时间">{{ formatTime(detail.approved_at) }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.reject_reason" label="驳回原因" :span="2">
          <el-text type="danger">{{ detail.reject_reason }}</el-text>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 驳回原因对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回原因" width="400px" :close-on-click-modal="false">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="rejecting">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getVehicleUseRequests,
  getVehicleUseRequest,
  createVehicleUseRequest,
  updateVehicleUseRequest,
  submitVehicleUseRequest,
  approveVehicleUseRequest,
  rejectVehicleUseRequest,
  cancelVehicleUseRequest,
  type VehicleUseRequestResponse,
  type VehicleUseRequestCreateData,
} from '@/api/vehicleUseRequests'

const list = ref<VehicleUseRequestResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const saving = ref(false)

const filters = reactive({
  keyword: '',
  status: '',
})

const statusOptions = [
  { value: 'draft', label: '草稿' },
  { value: 'pending', label: '待审批' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
  { value: 'dispatched', label: '已派车' },
  { value: 'cancelled', label: '已取消' },
  { value: 'completed', label: '已完成' },
]

const statusMap: Record<string, string> = {
  draft: '草稿',
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
  dispatched: '已派车',
  cancelled: '已取消',
  completed: '已完成',
}

const statusTagMap: Record<string, string> = {
  draft: 'info',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  dispatched: '',
  cancelled: 'info',
  completed: 'success',
}

function statusLabel(status: string) { return statusMap[status] || status }
function statusTagType(status: string) { return statusTagMap[status] || 'info' }
function formatTime(t: string | null) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 16)
}

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const dialogTitle = ref('新建用车申请')

const defaultForm = (): VehicleUseRequestCreateData => ({
  reason: '',
  destination: null,
  start_time: null,
  expected_return_time: null,
  need_driver: true,
  need_cargo: false,
  cargo_description: null,
  estimated_distance_km: null,
  remark: null,
})

const form = reactive<VehicleUseRequestCreateData>(defaultForm())

const detailVisible = ref(false)
const detail = ref<VehicleUseRequestResponse | null>(null)

const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejectingId = ref<string | null>(null)
const rejecting = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const res = await getVehicleUseRequests({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingId.value = null
  dialogTitle.value = '新建用车申请'
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function handleEdit(row: VehicleUseRequestResponse) {
  editingId.value = row.id
  dialogTitle.value = '编辑用车申请'
  Object.assign(form, {
    reason: row.reason,
    destination: row.destination,
    start_time: row.start_time,
    expected_return_time: row.expected_return_time,
    need_driver: row.need_driver,
    need_cargo: row.need_cargo,
    cargo_description: row.cargo_description,
    estimated_distance_km: row.estimated_distance_km,
    remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleView(row: VehicleUseRequestResponse) {
  try {
    const res = await getVehicleUseRequest(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    ElMessage.error('获取详情失败')
  }
}

async function handleSave() {
  if (!form.reason) {
    ElMessage.warning('请填写用车原因')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateVehicleUseRequest(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createVehicleUseRequest(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
  }
}

async function handleSubmit(row: VehicleUseRequestResponse) {
  try {
    await ElMessageBox.confirm('确认提交此用车申请？', '提交确认')
    await submitVehicleUseRequest(row.id)
    ElMessage.success('已提交审批')
    fetchData()
  } catch {}
}

async function handleApprove(row: VehicleUseRequestResponse) {
  try {
    await ElMessageBox.confirm('确认通过此用车申请？', '审批确认')
    await approveVehicleUseRequest(row.id)
    ElMessage.success('已通过')
    fetchData()
  } catch {}
}

function handleReject(row: VehicleUseRequestResponse) {
  rejectingId.value = row.id
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectReason.value) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  rejecting.value = true
  try {
    await rejectVehicleUseRequest(rejectingId.value!, rejectReason.value)
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    rejecting.value = false
  }
}

async function handleCancel(row: VehicleUseRequestResponse) {
  try {
    await ElMessageBox.confirm('确认取消此用车申请？', '取消确认')
    await cancelVehicleUseRequest(row.id)
    ElMessage.success('已取消')
    fetchData()
  } catch {}
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; }
.search-bar { display: flex; align-items: center; }
</style>
