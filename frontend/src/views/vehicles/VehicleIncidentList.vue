<template>
  <div class="page-container">
    <div class="page-header">
      <h2>违章事故</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon> 新增异常
      </el-button>
    </div>

    <!-- 待处理提醒 -->
    <el-alert
      v-if="pendingCount > 0"
      :title="`有 ${pendingCount} 条异常记录待处理`"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    />

    <!-- 筛选条件 -->
    <el-form :inline="true" class="filter-form">
      <el-form-item label="车辆">
        <el-select v-model="filters.vehicle_id" placeholder="选择车辆" clearable filterable>
          <el-option
            v-for="v in vehicleOptions"
            :key="v.id"
            :label="`${v.plate_number} - ${v.vehicle_name}`"
            :value="v.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="事件类型">
        <el-select v-model="filters.incident_type" placeholder="选择类型" clearable>
          <el-option label="违章" value="traffic_violation" />
          <el-option label="事故" value="accident" />
          <el-option label="剐蹭" value="scratch" />
          <el-option label="车辆损坏" value="vehicle_damage" />
          <el-option label="客户投诉" value="customer_complaint" />
          <el-option label="交通处罚" value="traffic_penalty" />
          <el-option label="现场异常" value="site_issue" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" placeholder="选择状态" clearable>
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已处理" value="resolved" />
          <el-option label="已关闭" value="closed" />
          <el-option label="有争议" value="disputed" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 异常列表 -->
    <el-table :data="incidents" v-loading="loading" stripe>
      <el-table-column prop="vehicle_name" label="车辆" width="150">
        <template #default="{ row }">
          {{ row.plate_number }} {{ row.vehicle_name }}
        </template>
      </el-table-column>
      <el-table-column prop="incident_type" label="事件类型" width="110">
        <template #default="{ row }">
          <el-tag :type="getIncidentTypeTag(row.incident_type)" size="small">
            {{ getIncidentTypeLabel(row.incident_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="incident_time" label="发生时间" width="120">
        <template #default="{ row }">
          {{ row.incident_time ? row.incident_time.slice(0, 10) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="location" label="地点" width="150" show-overflow-tooltip />
      <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
      <el-table-column prop="driver_name" label="司机" width="100" />
      <el-table-column prop="fine_amount" label="罚款" width="100" align="right">
        <template #default="{ row }">
          {{ row.fine_amount > 0 ? `¥${row.fine_amount.toFixed(2)}` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="repair_amount" label="维修费" width="100" align="right">
        <template #default="{ row }">
          {{ row.repair_amount > 0 ? `¥${row.repair_amount.toFixed(2)}` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="responsible_user_name" label="责任人" width="100" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDetail(row)">详情</el-button>
          <el-button v-if="canManage && row.status !== 'closed'" type="success" link size="small" @click="showResolveDialog(row)">处理</el-button>
          <el-button v-if="canManage" type="primary" link size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-button v-if="canManage" type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="loadData"
      @size-change="handleSizeChange"
      style="margin-top: 16px; justify-content: flex-end;"
    />

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑异常' : '新增异常'"
      width="650px"
    >
      <el-form :model="formData" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车辆" required>
              <el-select v-model="formData.vehicle_id" placeholder="选择车辆" filterable style="width: 100%;">
                <el-option
                  v-for="v in vehicleOptions"
                  :key="v.id"
                  :label="`${v.plate_number} - ${v.vehicle_name}`"
                  :value="v.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="事件类型" required>
              <el-select v-model="formData.incident_type" placeholder="选择类型" style="width: 100%;">
                <el-option label="违章" value="traffic_violation" />
                <el-option label="事故" value="accident" />
                <el-option label="剐蹭" value="scratch" />
                <el-option label="车辆损坏" value="vehicle_damage" />
                <el-option label="客户投诉" value="customer_complaint" />
                <el-option label="交通处罚" value="traffic_penalty" />
                <el-option label="现场异常" value="site_issue" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="司机">
              <el-select v-model="formData.driver_id" placeholder="选择司机" filterable clearable style="width: 100%;">
                <el-option
                  v-for="d in driverOptions"
                  :key="d.id"
                  :label="d.driver_name"
                  :value="d.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发生时间">
              <el-date-picker v-model="formData.incident_time" type="datetime" placeholder="选择时间" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="发生地点">
          <el-input v-model="formData.location" placeholder="输入发生地点" />
        </el-form-item>
        <el-form-item label="事件描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="详细描述事件经过" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="罚款金额">
              <el-input-number v-model="formData.fine_amount" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="扣分">
              <el-input-number v-model="formData.points_deducted" :min="0" :max="12" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="维修金额">
              <el-input-number v-model="formData.repair_amount" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="责任人">
          <el-select v-model="formData.responsible_user_id" placeholder="选择责任人" filterable clearable style="width: 100%;">
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="u.real_name"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 处理对话框 -->
    <el-dialog
      v-model="resolveDialogVisible"
      title="处理异常"
      width="500px"
    >
      <el-form :model="resolveForm" label-width="80px">
        <el-form-item label="处理状态">
          <el-radio-group v-model="resolveForm.status">
            <el-radio value="resolved">已处理</el-radio>
            <el-radio value="closed">已关闭</el-radio>
            <el-radio value="disputed">有争议</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理结果" required>
          <el-input v-model="resolveForm.resolution" type="textarea" :rows="4" placeholder="填写处理结果" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleResolve" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="异常详情"
      width="600px"
    >
      <el-descriptions :column="2" border v-if="currentDetail">
        <el-descriptions-item label="车辆" :span="2">{{ currentDetail.plate_number }} {{ currentDetail.vehicle_name }}</el-descriptions-item>
        <el-descriptions-item label="事件类型">
          <el-tag :type="getIncidentTypeTag(currentDetail.incident_type)" size="small">
            {{ getIncidentTypeLabel(currentDetail.incident_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentDetail.status)" size="small">
            {{ getStatusLabel(currentDetail.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="司机">{{ currentDetail.driver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="派车单">{{ currentDetail.dispatch_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发生时间">{{ currentDetail.incident_time || '-' }}</el-descriptions-item>
        <el-descriptions-item label="地点">{{ currentDetail.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ currentDetail.description || '-' }}</el-descriptions-item>
        <el-descriptions-item label="罚款金额">¥{{ currentDetail.fine_amount.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="扣分">{{ currentDetail.points_deducted }} 分</el-descriptions-item>
        <el-descriptions-item label="维修金额">¥{{ currentDetail.repair_amount.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ currentDetail.responsible_user_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处理结果" :span="2" v-if="currentDetail.resolution">{{ currentDetail.resolution }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentDetail.remark || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentDetail.created_at }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ currentDetail.updated_at }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getIncidents,
  createIncident,
  updateIncident,
  resolveIncident,
  deleteIncident,
  getVehicles,
  getDrivers,
  type IncidentResponse,
  type VehicleResponse,
  type VehicleDriverResponse,
} from '@/api/vehicles'
import { getUsers } from '@/api/users'

const authStore = useAuthStore()
const canManage = computed(() => authStore.hasAnyRole(['admin', 'finance', 'production']))

const loading = ref(false)
const incidents = ref<IncidentResponse[]>([])
const pendingCount = ref(0)
const vehicleOptions = ref<VehicleResponse[]>([])
const driverOptions = ref<VehicleDriverResponse[]>([])
const userOptions = ref<{ id: string; real_name: string }[]>([])

const filters = ref({
  vehicle_id: '',
  incident_type: '',
  status: '',
})

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0,
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const submitting = ref(false)

const resolveDialogVisible = ref(false)
const resolvingId = ref('')
const resolveForm = ref({
  status: 'resolved',
  resolution: '',
})

const detailDialogVisible = ref(false)
const currentDetail = ref<IncidentResponse | null>(null)

const formData = ref({
  vehicle_id: '',
  driver_id: '',
  dispatch_id: '',
  related_order_id: '',
  related_install_task_id: '',
  incident_type: '',
  incident_time: '',
  location: '',
  description: '',
  fine_amount: 0,
  points_deducted: 0,
  repair_amount: 0,
  responsible_user_id: '',
  evidence_url: '',
  remark: '',
})

const incidentTypeMap: Record<string, string> = {
  traffic_violation: '违章',
  accident: '事故',
  scratch: '剐蹭',
  vehicle_damage: '车辆损坏',
  customer_complaint: '客户投诉',
  traffic_penalty: '交通处罚',
  site_issue: '现场异常',
  other: '其他',
}

function getIncidentTypeLabel(type: string) {
  return incidentTypeMap[type] || type
}

function getIncidentTypeTag(type: string) {
  const map: Record<string, string> = {
    traffic_violation: 'warning',
    accident: 'danger',
    scratch: '',
    vehicle_damage: 'warning',
    customer_complaint: 'info',
    traffic_penalty: 'warning',
    site_issue: 'info',
    other: 'info',
  }
  return map[type] || 'info'
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已处理',
    closed: '已关闭',
    disputed: '有争议',
  }
  return map[status] || status
}

function getStatusType(status: string) {
  const map: Record<string, string> = {
    pending: 'warning',
    processing: 'info',
    resolved: 'success',
    closed: 'info',
    disputed: 'danger',
  }
  return map[status] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    }
    if (filters.value.vehicle_id) params.vehicle_id = filters.value.vehicle_id
    if (filters.value.incident_type) params.incident_type = filters.value.incident_type
    if (filters.value.status) params.status = filters.value.status
    const res = await getIncidents(params)
    if (res.data) {
      incidents.value = res.data.items
      pagination.value.total = res.data.total
      pendingCount.value = res.data.items.filter((i: IncidentResponse) => i.status === 'pending').length
    }
  } catch {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

async function loadVehicles() {
  try {
    const res = await getVehicles({ page: 1, page_size: 100 })
    if (res.data) {
      vehicleOptions.value = res.data.items
    }
  } catch {
    // ignore
  }
}

async function loadDrivers() {
  try {
    const res = await getDrivers({ page: 1, page_size: 100 })
    if (res.data) {
      driverOptions.value = res.data.items
    }
  } catch {
    // ignore
  }
}

async function loadUsers() {
  try {
    const res = await getUsers({ page: 1, page_size: 200 })
    if (res.data) {
      userOptions.value = res.data.items || res.data
    }
  } catch {
    // ignore
  }
}

function resetFilters() {
  filters.value = { vehicle_id: '', incident_type: '', status: '' }
  pagination.value.page = 1
  loadData()
}

function handleSizeChange() {
  pagination.value.page = 1
  loadData()
}

function showAddDialog() {
  isEdit.value = false
  editingId.value = ''
  formData.value = {
    vehicle_id: '',
    driver_id: '',
    dispatch_id: '',
    related_order_id: '',
    related_install_task_id: '',
    incident_type: '',
    incident_time: '',
    location: '',
    description: '',
    fine_amount: 0,
    points_deducted: 0,
    repair_amount: 0,
    responsible_user_id: '',
    evidence_url: '',
    remark: '',
  }
  dialogVisible.value = true
}

function showEditDialog(row: IncidentResponse) {
  isEdit.value = true
  editingId.value = row.id
  formData.value = {
    vehicle_id: row.vehicle_id || '',
    driver_id: row.driver_id || '',
    dispatch_id: row.dispatch_id || '',
    related_order_id: row.related_order_id || '',
    related_install_task_id: row.related_install_task_id || '',
    incident_type: row.incident_type,
    incident_time: row.incident_time || '',
    location: row.location || '',
    description: row.description || '',
    fine_amount: row.fine_amount,
    points_deducted: row.points_deducted,
    repair_amount: row.repair_amount,
    responsible_user_id: row.responsible_user_id || '',
    evidence_url: row.evidence_url || '',
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

function showResolveDialog(row: IncidentResponse) {
  resolvingId.value = row.id
  resolveForm.value = {
    status: 'resolved',
    resolution: row.resolution || '',
  }
  resolveDialogVisible.value = true
}

function showDetail(row: IncidentResponse) {
  currentDetail.value = row
  detailDialogVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.vehicle_id) {
    ElMessage.warning('请选择车辆')
    return
  }
  if (!formData.value.incident_type) {
    ElMessage.warning('请选择事件类型')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateIncident(editingId.value, formData.value)
      ElMessage.success('更新成功')
    } else {
      await createIncident(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleResolve() {
  if (!resolveForm.value.resolution) {
    ElMessage.warning('请填写处理结果')
    return
  }
  submitting.value = true
  try {
    await resolveIncident(resolvingId.value, resolveForm.value)
    ElMessage.success('处理成功')
    resolveDialogVisible.value = false
    loadData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: IncidentResponse) {
  try {
    await ElMessageBox.confirm('确定删除该异常记录？', '确认删除', { type: 'warning' })
    await deleteIncident(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // cancelled
  }
}

onMounted(() => {
  loadData()
  loadVehicles()
  loadDrivers()
  loadUsers()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.filter-form {
  margin-bottom: 16px;
}
</style>
