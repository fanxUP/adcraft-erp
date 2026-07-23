<template>
  <div class="page">
    <div class="page-header">
      <h2>派车管理</h2>
      <el-button type="danger" @click="handleCreate">新建派车</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="filters.keyword" placeholder="搜索单号/目的地" clearable style="width: 220px" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px; margin-left: 12px">
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="dispatch_no" label="派车单号" width="140" />
      <el-table-column prop="request_no" label="申请单号" width="140" />
      <el-table-column prop="vehicle_name" label="车辆" width="120" />
      <el-table-column prop="plate_number" label="车牌号" width="110" />
      <el-table-column prop="driver_name" label="司机" width="90" />
      <el-table-column prop="destination" label="目的地" min-width="150" />
      <el-table-column label="计划出发" width="160">
        <template #default="{ row }">{{ formatTime(row.planned_start_time) }}</template>
      </el-table-column>
      <el-table-column label="计划返回" width="160">
        <template #default="{ row }">{{ formatTime(row.planned_return_time) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleView(row)">查看</el-button>
          <el-button v-if="row.status === 'assigned'" text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'assigned'" text type="danger" @click="handleCancel(row)">取消派车</el-button>
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
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="用车申请">
          <el-select v-model="form.request_id" placeholder="选择已审批的用车申请（可选）" clearable filterable style="width: 100%" @change="onRequestChange">
            <el-option v-for="r in approvedRequests" :key="r.id" :label="`${r.request_no} - ${r.reason} (${r.destination || '无目的地'})`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车辆" required>
              <el-select v-model="form.vehicle_id" placeholder="选择车辆" filterable style="width: 100%">
                <el-option v-for="v in availableVehicles" :key="v.id" :label="`${v.vehicle_name} (${v.plate_number})`" :value="v.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="司机">
              <el-select v-model="form.driver_id" placeholder="选择司机" clearable filterable style="width: 100%">
                <el-option v-for="d in availableDrivers" :key="d.id" :label="`${d.driver_name}${d.phone ? ' (' + d.phone + ')' : ''}`" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="随车人员">
          <el-input v-model="form.companions" placeholder="随车人员姓名，多人用逗号分隔" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="出发地点">
              <el-input v-model="form.start_location" placeholder="出发地点" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目的地">
              <el-input v-model="form.destination" placeholder="到达地点" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="计划出发">
              <el-date-picker v-model="form.planned_start_time" type="datetime" placeholder="选择出发时间" style="width: 100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划返回">
              <el-date-picker v-model="form.planned_return_time" type="datetime" placeholder="选择返回时间" style="width: 100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="装载物料">
          <el-input v-model="form.cargo_description" type="textarea" :rows="2" placeholder="描述需要装载的物料" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">确认派车</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="派车单详情" width="650px">
      <el-descriptions :column="2" border v-if="detail">
        <el-descriptions-item label="派车单号">{{ detail.dispatch_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(detail.status)" size="small">{{ statusLabel(detail.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请单号">{{ detail.request_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="车辆">{{ detail.vehicle_name }} ({{ detail.plate_number }})</el-descriptions-item>
        <el-descriptions-item label="司机">{{ detail.driver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="随车人员" :span="2">{{ detail.companions || '-' }}</el-descriptions-item>
        <el-descriptions-item label="出发地点">{{ detail.start_location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="目的地">{{ detail.destination || '-' }}</el-descriptions-item>
        <el-descriptions-item label="计划出发">{{ formatTime(detail.planned_start_time) }}</el-descriptions-item>
        <el-descriptions-item label="计划返回">{{ formatTime(detail.planned_return_time) }}</el-descriptions-item>
        <el-descriptions-item label="实际出发">{{ formatTime(detail.actual_start_time) }}</el-descriptions-item>
        <el-descriptions-item label="实际返回">{{ formatTime(detail.actual_return_time) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getVehicleDispatches,
  getVehicleDispatch,
  createVehicleDispatch,
  updateVehicleDispatch,
  cancelVehicleDispatch,
  getAvailableVehicles,
  getAvailableDrivers,
  type VehicleDispatchResponse,
  type VehicleDispatchCreateData,
} from '@/api/vehicleDispatches'
import { getVehicleUseRequests, type VehicleUseRequestResponse } from '@/api/vehicleUseRequests'

const list = ref<VehicleDispatchResponse[]>([])
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
  { value: 'assigned', label: '待出车' },
  { value: 'started', label: '已出车' },
  { value: 'arrived', label: '已到达' },
  { value: 'completed', label: '已完成' },
  { value: 'returned', label: '已收车' },
  { value: 'cancelled', label: '已取消' },
  { value: 'abnormal', label: '异常' },
]

const statusMap: Record<string, string> = {
  assigned: '待出车',
  started: '已出车',
  arrived: '已到达',
  completed: '已完成',
  returned: '已收车',
  cancelled: '已取消',
  abnormal: '异常',
}

const statusTagMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
  assigned: 'warning',
  started: 'info',
  arrived: 'success',
  completed: 'success',
  returned: 'info',
  cancelled: 'info',
  abnormal: 'danger',
}

function statusLabel(status: string) { return statusMap[status] || status }
function statusTagType(status: string): 'success' | 'warning' | 'info' | 'danger' { return statusTagMap[status] || 'info' }
function formatTime(t: string | null) { return t ? t.replace('T', ' ').slice(0, 16) : '-' }

// Dialog state
const dialogVisible = ref(false)
const dialogTitle = ref('新建派车')
const editingId = ref<string | null>(null)
const form = reactive<VehicleDispatchCreateData>({
  request_id: '',
  vehicle_id: '',
  driver_id: '',
  companions: '',
  start_location: '',
  destination: '',
  planned_start_time: '',
  planned_return_time: '',
  cargo_description: '',
  remark: '',
})

const detailVisible = ref(false)
const detail = ref<VehicleDispatchResponse | null>(null)

const approvedRequests = ref<VehicleUseRequestResponse[]>([])
const availableVehicles = ref<{ id: string; vehicle_name: string; plate_number: string }[]>([])
const availableDrivers = ref<{ id: string; driver_name: string; phone: string }[]>([])

async function fetchDropdownData() {
  try {
    const reqRes = await getVehicleUseRequests({ status: 'approved', page_size: 100 })
    approvedRequests.value = reqRes.data?.items || []
    const vehRes = await getAvailableVehicles()
    availableVehicles.value = (vehRes as { data: { id: string; vehicle_name: string; plate_number: string }[] }).data || []
    const drvRes = await getAvailableDrivers()
    availableDrivers.value = (drvRes as { data: { id: string; driver_name: string; phone: string }[] }).data || []
  } catch {}
}

function onRequestChange(requestId: string) {
  if (requestId) {
    const req = approvedRequests.value.find(r => r.id === requestId)
    if (req) {
      form.destination = req.destination || ''
      form.planned_start_time = req.start_time || ''
      form.planned_return_time = req.expected_return_time || ''
    }
  }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getVehicleDispatches({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
    })
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch {
    ElMessage.error('获取派车列表失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    request_id: '',
    vehicle_id: '',
    driver_id: '',
    companions: '',
    start_location: '',
    destination: '',
    planned_start_time: '',
    planned_return_time: '',
    cargo_description: '',
    remark: '',
  })
  editingId.value = null
}

function handleCreate() {
  resetForm()
  dialogTitle.value = '新建派车'
  dialogVisible.value = true
  fetchDropdownData()
}

function handleEdit(row: VehicleDispatchResponse) {
  editingId.value = row.id
  dialogTitle.value = '编辑派车'
  Object.assign(form, {
    request_id: row.request_id || '',
    vehicle_id: row.vehicle_id,
    driver_id: row.driver_id || '',
    companions: row.companions || '',
    start_location: row.start_location || '',
    destination: row.destination || '',
    planned_start_time: row.planned_start_time || '',
    planned_return_time: row.planned_return_time || '',
    remark: row.remark || '',
  })
  dialogVisible.value = true
  fetchDropdownData()
}

async function handleView(row: VehicleDispatchResponse) {
  try {
    const res = await getVehicleDispatch(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    ElMessage.error('获取详情失败')
  }
}

async function handleSave() {
  if (!form.vehicle_id) {
    ElMessage.warning('请选择车辆')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateVehicleDispatch(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createVehicleDispatch(form)
      ElMessage.success('派车成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
  }
}

async function handleCancel(row: VehicleDispatchResponse) {
  try {
    await ElMessageBox.confirm('确认取消此派车？取消后车辆将恢复可用状态。', '取消确认')
    await cancelVehicleDispatch(row.id)
    ElMessage.success('已取消派车')
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
