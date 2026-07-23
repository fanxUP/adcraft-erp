<template>
  <div class="page-container">
    <div class="page-header">
      <h2>出车/收车台账</h2>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索派车单号/目的地"
        clearable
        style="width: 200px"
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="searchStatus" placeholder="派车状态" clearable style="width: 120px" @change="handleSearch">
        <el-option label="待出车" value="assigned" />
        <el-option label="已出车" value="started" />
        <el-option label="已到达" value="arrived" />
        <el-option label="已完成" value="completed" />
        <el-option label="已收车" value="returned" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
    </div>

    <!-- 派车单列表 -->
    <el-table :data="dispatchList" stripe border style="width: 100%">
      <el-table-column prop="dispatch_no" label="派车单号" width="140" />
      <el-table-column prop="vehicle_name" label="车辆" width="120" />
      <el-table-column prop="plate_number" label="车牌号" width="110" />
      <el-table-column prop="driver_name" label="司机" width="100" />
      <el-table-column prop="destination" label="目的地" min-width="150" />
      <el-table-column prop="planned_start_time" label="计划出发" width="160">
        <template #default="{ row }">
          {{ row.planned_start_time ? formatTime(row.planned_start_time) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="actual_start_time" label="实际出发" width="160">
        <template #default="{ row }">
          {{ row.actual_start_time ? formatTime(row.actual_start_time) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="actual_return_time" label="收车时间" width="160">
        <template #default="{ row }">
          {{ row.actual_return_time ? formatTime(row.actual_return_time) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="start_mileage" label="出车里程" width="100">
        <template #default="{ row }">
          {{ row.start_mileage ? `${row.start_mileage} km` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="end_mileage" label="收车里程" width="100">
        <template #default="{ row }">
          {{ row.end_mileage ? `${row.end_mileage} km` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="actual_distance_km" label="实际公里" width="100">
        <template #default="{ row }">
          {{ row.actual_distance_km ? `${row.actual_distance_km} km` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleViewTrip(row)">查看</el-button>
          <el-button v-if="row.status === 'assigned'" size="small" type="success" @click="handleStartTrip(row)">出车</el-button>
          <el-button v-if="row.status === 'started'" size="small" type="warning" @click="handleArriveTrip(row)">到达</el-button>
          <el-button v-if="row.status === 'arrived'" size="small" type="primary" @click="handleFinishTrip(row)">完工</el-button>
          <el-button v-if="['completed', 'arrived', 'started'].includes(row.status)" size="small" type="danger" @click="handleReturnTrip(row)">收车</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 出车对话框 -->
    <el-dialog v-model="startDialogVisible" title="出车确认" width="500px">
      <el-form :model="startForm" label-width="100px">
        <el-form-item label="派车单号">
          <el-input :model-value="currentDispatch?.dispatch_no" disabled />
        </el-form-item>
        <el-form-item label="车辆">
          <el-input :model-value="`${currentDispatch?.vehicle_name} (${currentDispatch?.plate_number})`" disabled />
        </el-form-item>
        <el-form-item label="出车时间">
          <el-date-picker v-model="startForm.start_time" type="datetime" placeholder="选择出车时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="出车里程(km)">
          <el-input-number v-model="startForm.start_mileage" :min="0" :precision="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="出车备注">
          <el-input v-model="startForm.start_remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitStart">确认出车</el-button>
      </template>
    </el-dialog>

    <!-- 到达对话框 -->
    <el-dialog v-model="arriveDialogVisible" title="到达现场" width="400px">
      <el-form :model="arriveForm" label-width="80px">
        <el-form-item label="到达备注">
          <el-input v-model="arriveForm.arrive_remark" type="textarea" :rows="3" placeholder="到达现场情况" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="arriveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitArrive">确认到达</el-button>
      </template>
    </el-dialog>

    <!-- 收车对话框 -->
    <el-dialog v-model="returnDialogVisible" title="收车回执" width="500px">
      <el-form :model="returnForm" label-width="100px">
        <el-form-item label="派车单号">
          <el-input :model-value="currentDispatch?.dispatch_no" disabled />
        </el-form-item>
        <el-form-item label="出车里程">
          <el-input :model-value="currentDispatch?.start_mileage ? `${currentDispatch.start_mileage} km` : '-'" disabled />
        </el-form-item>
        <el-form-item label="收车时间">
          <el-date-picker v-model="returnForm.return_time" type="datetime" placeholder="选择收车时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="收车里程(km)">
          <el-input-number v-model="returnForm.end_mileage" :min="0" :precision="1" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="returnForm.end_mileage && currentDispatch?.start_mileage" label="实际公里">
          <el-input :model-value="`${(returnForm.end_mileage - currentDispatch.start_mileage).toFixed(1)} km`" disabled />
        </el-form-item>
        <el-form-item label="车辆异常">
          <el-switch v-model="returnForm.abnormal_flag" />
        </el-form-item>
        <el-form-item v-if="returnForm.abnormal_flag" label="异常说明">
          <el-input v-model="returnForm.abnormal_description" type="textarea" :rows="2" placeholder="请描述车辆异常情况" />
        </el-form-item>
        <el-form-item label="收车备注">
          <el-input v-model="returnForm.return_remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="returnDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitReturn">确认收车</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="台账详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="派车单号">{{ detailData?.dispatch_no }}</el-descriptions-item>
        <el-descriptions-item label="台账编号">{{ detailData?.trip_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="车辆">{{ detailData?.vehicle_name }} ({{ detailData?.plate_number }})</el-descriptions-item>
        <el-descriptions-item label="司机">{{ detailData?.driver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="出车时间">{{ detailData?.start_time ? formatTime(detailData.start_time) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="收车时间">{{ detailData?.return_time ? formatTime(detailData.return_time) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="出车里程">{{ detailData?.start_mileage ? `${detailData.start_mileage} km` : '-' }}</el-descriptions-item>
        <el-descriptions-item label="收车里程">{{ detailData?.end_mileage ? `${detailData.end_mileage} km` : '-' }}</el-descriptions-item>
        <el-descriptions-item label="实际公里">{{ detailData?.distance_km ? `${detailData.distance_km} km` : '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(detailData?.status)">{{ statusLabel(detailData?.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="异常" :span="2">
          <el-tag v-if="detailData?.abnormal_flag" type="danger">有异常</el-tag>
          <el-tag v-else type="success">正常</el-tag>
          <span v-if="detailData?.abnormal_description" style="margin-left: 8px">{{ detailData.abnormal_description }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="出车备注" :span="2">{{ detailData?.start_remark || '-' }}</el-descriptions-item>
        <el-descriptions-item label="收车备注" :span="2">{{ detailData?.return_remark || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { get, post } from '@/api'

// Types
interface DispatchItem {
  id: string
  dispatch_no: string
  vehicle_id: string
  vehicle_name: string
  plate_number: string
  driver_id: string
  driver_name: string
  destination: string
  planned_start_time: string | null
  actual_start_time: string | null
  actual_return_time: string | null
  start_mileage: number | null
  end_mileage: number | null
  actual_distance_km: number | null
  status: string
  abnormal_flag: boolean
  abnormal_description: string | null
}

interface TripRecord {
  id: string
  trip_no: string
  dispatch_no: string
  vehicle_name: string
  plate_number: string
  driver_name: string
  start_time: string | null
  return_time: string | null
  start_mileage: number | null
  end_mileage: number | null
  distance_km: number | null
  abnormal_flag: boolean
  abnormal_description: string | null
  start_remark: string | null
  return_remark: string | null
  status: string
}

// State
const dispatchList = ref<DispatchItem[]>([])
const searchKeyword = ref('')
const searchStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const submitting = ref(false)

// Dialog states
const startDialogVisible = ref(false)
const arriveDialogVisible = ref(false)
const returnDialogVisible = ref(false)
const detailDialogVisible = ref(false)

const currentDispatch = ref<DispatchItem | null>(null)
const detailData = ref<TripRecord | null>(null)

const startForm = ref({
  start_time: '',
  start_mileage: null as number | null,
  start_remark: '',
})

const arriveForm = ref({
  arrive_remark: '',
})

const returnForm = ref({
  return_time: '',
  end_mileage: null as number | null,
  return_remark: '',
  abnormal_flag: false,
  abnormal_description: '',
})

// Load dispatches
async function loadDispatches() {
  try {
    const params = new URLSearchParams({
      page: String(currentPage.value),
      page_size: String(pageSize.value),
    })
    if (searchKeyword.value) params.append('keyword', searchKeyword.value)
    if (searchStatus.value) params.append('status', searchStatus.value)

    const res = await get(`/vehicle-dispatches/?${params}`)
    dispatchList.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载数据失败')
  }
}

function handleSearch() {
  currentPage.value = 1
  loadDispatches()
}

function handleSizeChange() {
  currentPage.value = 1
  loadDispatches()
}

function handlePageChange() {
  loadDispatches()
}

// Status helpers
function statusLabel(status: string | undefined): string {
  const map: Record<string, string> = {
    assigned: '待出车',
    started: '已出车',
    arrived: '已到达',
    completed: '已完成',
    returned: '已收车',
    cancelled: '已取消',
    abnormal: '异常',
  }
  return map[status || ''] || status || ''
}

function statusTagType(status: string | undefined): 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    assigned: 'info',
    started: 'warning',
    arrived: 'warning',
    completed: 'success',
    returned: 'success',
    cancelled: 'info',
    abnormal: 'danger',
  }
  return map[status || ''] || 'info'
}

function formatTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// Actions
function handleStartTrip(row: DispatchItem) {
  currentDispatch.value = row
  startForm.value = { start_time: '', start_mileage: null, start_remark: '' }
  startDialogVisible.value = true
}

function handleArriveTrip(row: DispatchItem) {
  currentDispatch.value = row
  arriveForm.value = { arrive_remark: '' }
  arriveDialogVisible.value = true
}

function handleFinishTrip(row: DispatchItem) {
  ElMessageBox.confirm('确认该派车任务已完工？', '完工确认').then(async () => {
    try {
      await post(`/vehicle-dispatches/${row.id}/finish`)
      ElMessage.success('已完工')
      loadDispatches()
    } catch {
      ElMessage.error('操作失败')
    }
  }).catch(() => {})
}

function handleReturnTrip(row: DispatchItem) {
  currentDispatch.value = row
  returnForm.value = { return_time: '', end_mileage: null, return_remark: '', abnormal_flag: false, abnormal_description: '' }
  returnDialogVisible.value = true
}

async function handleViewTrip(row: DispatchItem) {
  try {
    const res = await get(`/vehicle-dispatches/${row.id}`)
    detailData.value = res.data
    detailDialogVisible.value = true
  } catch {
    ElMessage.error('获取详情失败')
  }
}

// Submit actions
async function submitStart() {
  if (!currentDispatch.value) return
  submitting.value = true
  try {
    await post(`/vehicle-dispatches/${currentDispatch.value.id}/start`, startForm.value)
    ElMessage.success('出车成功')
    startDialogVisible.value = false
    loadDispatches()
  } catch {
    ElMessage.error('出车失败')
  } finally {
    submitting.value = false
  }
}

async function submitArrive() {
  if (!currentDispatch.value) return
  submitting.value = true
  try {
    await post(`/vehicle-dispatches/${currentDispatch.value.id}/arrive`, arriveForm.value)
    ElMessage.success('已标记到达')
    arriveDialogVisible.value = false
    loadDispatches()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function submitReturn() {
  if (!currentDispatch.value) return
  submitting.value = true
  try {
    await post(`/vehicle-dispatches/${currentDispatch.value.id}/return`, returnForm.value)
    ElMessage.success('收车成功')
    returnDialogVisible.value = false
    loadDispatches()
  } catch {
    ElMessage.error('收车失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadDispatches()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
