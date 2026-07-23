<template>
  <div class="page-container">
    <div class="page-header">
      <h2>保险年检</h2>
      <el-button v-if="canManage" type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon> 新增证件
      </el-button>
    </div>

    <!-- 到期提醒横幅 -->
    <el-alert
      v-if="expiringCerts.length > 0"
      :title="`有 ${expiringCerts.length} 个证件即将到期或已过期`"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    >
      <template #default>
        <div v-for="cert in expiringCerts.slice(0, 5)" :key="cert.id" class="expiring-item">
          <el-tag :type="getUrgencyType(cert.urgency)" size="small" style="margin-right: 8px;">
            {{ getUrgencyLabel(cert.urgency) }}
          </el-tag>
          {{ cert.vehicle_name }} - {{ getCertTypeLabel(cert.certificate_type) }}
          <span v-if="cert.days_left !== undefined">
            ({{ cert.days_left < 0 ? `已过期 ${Math.abs(cert.days_left)} 天` : `还剩 ${cert.days_left} 天` }})
          </span>
        </div>
        <div v-if="expiringCerts.length > 5" style="margin-top: 4px; color: #909399;">
          ...还有 {{ expiringCerts.length - 5 }} 个
        </div>
      </template>
    </el-alert>

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
      <el-form-item label="证件类型">
        <el-select v-model="filters.certificate_type" placeholder="选择类型" clearable>
          <el-option label="交强险" value="compulsory_insurance" />
          <el-option label="商业险" value="commercial_insurance" />
          <el-option label="年检" value="annual_inspection" />
          <el-option label="行驶证" value="driving_license" />
          <el-option label="道路运输证" value="transport_license" />
          <el-option label="驾驶证" value="driver_license" />
          <el-option label="保养提醒" value="maintenance" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" placeholder="选择状态" clearable>
          <el-option label="有效" value="active" />
          <el-option label="已过期" value="expired" />
          <el-option label="已续期" value="renewed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 证件列表 -->
    <el-table :data="certificates" v-loading="loading" stripe>
      <el-table-column prop="vehicle_name" label="车辆" width="150">
        <template #default="{ row }">
          {{ row.plate_number }} {{ row.vehicle_name }}
        </template>
      </el-table-column>
      <el-table-column prop="certificate_type" label="证件类型" width="120">
        <template #default="{ row }">
          {{ getCertTypeLabel(row.certificate_type) }}
        </template>
      </el-table-column>
      <el-table-column prop="certificate_no" label="证件编号" width="150" />
      <el-table-column prop="expire_date" label="到期日期" width="120">
        <template #default="{ row }">
          <span :class="getExpireClass(row)">
            {{ row.expire_date ? row.expire_date.slice(0, 10) : '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.urgency" :type="getUrgencyType(row.urgency)" size="small">
            {{ getUrgencyLabel(row.urgency) }}
          </el-tag>
          <el-tag v-else :type="getStatusType(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="100" align="right">
        <template #default="{ row }">
          {{ row.amount ? `¥${row.amount.toFixed(2)}` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="reminder_days" label="提醒天数" width="90" align="center" />
      <el-table-column prop="driver_name" label="关联司机" width="100" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
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
      :title="isEdit ? '编辑证件' : '新增证件'"
      width="600px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="车辆" required>
          <el-select v-model="formData.vehicle_id" placeholder="选择车辆" filterable>
            <el-option
              v-for="v in vehicleOptions"
              :key="v.id"
              :label="`${v.plate_number} - ${v.vehicle_name}`"
              :value="v.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="证件类型" required>
          <el-select v-model="formData.certificate_type" placeholder="选择类型">
            <el-option label="交强险" value="compulsory_insurance" />
            <el-option label="商业险" value="commercial_insurance" />
            <el-option label="年检" value="annual_inspection" />
            <el-option label="行驶证" value="driving_license" />
            <el-option label="道路运输证" value="transport_license" />
            <el-option label="驾驶证" value="driver_license" />
            <el-option label="保养提醒" value="maintenance" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联司机" v-if="formData.certificate_type === 'driver_license'">
          <el-select v-model="formData.driver_id" placeholder="选择司机" filterable clearable>
            <el-option
              v-for="d in driverOptions"
              :key="d.id"
              :label="d.driver_name"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="证件编号">
          <el-input v-model="formData.certificate_no" placeholder="输入证件编号" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="formData.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="到期日期">
          <el-date-picker v-model="formData.expire_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="formData.amount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="提前提醒天数">
          <el-input-number v-model="formData.reminder_days" :min="1" :max="365" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getCertificates,
  getExpiringCertificates,
  createCertificate,
  updateCertificate,
  deleteCertificate,
  getVehicles,
  getDrivers,
  type CertificateResponse,
  type VehicleResponse,
  type VehicleDriverResponse,
} from '@/api/vehicles'

const authStore = useAuthStore()
const canManage = computed(() => authStore.hasAnyRole(['admin', 'finance']))

const loading = ref(false)
const certificates = ref<CertificateResponse[]>([])
const expiringCerts = ref<CertificateResponse[]>([])
const vehicleOptions = ref<VehicleResponse[]>([])
const driverOptions = ref<VehicleDriverResponse[]>([])

const filters = ref({
  vehicle_id: '',
  certificate_type: '',
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

const formData = ref({
  vehicle_id: '',
  driver_id: '',
  certificate_type: '',
  certificate_no: '',
  start_date: '',
  expire_date: '',
  amount: 0,
  reminder_days: 30,
  remark: '',
})

const certTypeMap: Record<string, string> = {
  compulsory_insurance: '交强险',
  commercial_insurance: '商业险',
  annual_inspection: '年检',
  driving_license: '行驶证',
  transport_license: '道路运输证',
  driver_license: '驾驶证',
  maintenance: '保养提醒',
  other: '其他',
}

function getCertTypeLabel(type: string) {
  return certTypeMap[type] || type
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    active: '有效',
    expired: '已过期',
    renewed: '已续期',
    cancelled: '已取消',
  }
  return map[status] || status
}

function getStatusType(status: string) {
  const map: Record<string, string> = {
    active: 'success',
    expired: 'danger',
    renewed: 'info',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function getUrgencyType(urgency?: string) {
  if (urgency === 'expired') return 'danger'
  if (urgency === 'urgent') return 'warning'
  if (urgency === 'warning') return 'info'
  return 'info'
}

function getUrgencyLabel(urgency?: string) {
  if (urgency === 'expired') return '已过期'
  if (urgency === 'urgent') return '即将到期'
  if (urgency === 'warning') return '即将到期'
  return ''
}

function getExpireClass(row: CertificateResponse) {
  if (row.urgency === 'expired') return 'text-danger'
  if (row.urgency === 'urgent') return 'text-warning'
  return ''
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
    }
    if (filters.value.vehicle_id) params.vehicle_id = filters.value.vehicle_id
    if (filters.value.certificate_type) params.certificate_type = filters.value.certificate_type
    if (filters.value.status) params.status = filters.value.status
    const res = await getCertificates(params)
    if (res.data) {
      certificates.value = res.data.items
      pagination.value.total = res.data.total
    }
  } catch {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

async function loadExpiring() {
  try {
    const res = await getExpiringCertificates({ days: 30 })
    if (res.data) {
      expiringCerts.value = res.data
    }
  } catch {
    // ignore
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

function resetFilters() {
  filters.value = { vehicle_id: '', certificate_type: '', status: '' }
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
    certificate_type: '',
    certificate_no: '',
    start_date: '',
    expire_date: '',
    amount: 0,
    reminder_days: 30,
    remark: '',
  }
  dialogVisible.value = true
}

function showEditDialog(row: CertificateResponse) {
  isEdit.value = true
  editingId.value = row.id
  formData.value = {
    vehicle_id: row.vehicle_id || '',
    driver_id: row.driver_id || '',
    certificate_type: row.certificate_type,
    certificate_no: row.certificate_no || '',
    start_date: row.start_date || '',
    expire_date: row.expire_date || '',
    amount: row.amount,
    reminder_days: row.reminder_days,
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.vehicle_id) {
    ElMessage.warning('请选择车辆')
    return
  }
  if (!formData.value.certificate_type) {
    ElMessage.warning('请选择证件类型')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateCertificate(editingId.value, formData.value)
      ElMessage.success('更新成功')
    } else {
      await createCertificate(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
    loadExpiring()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: CertificateResponse) {
  try {
    await ElMessageBox.confirm('确定删除该证件记录？', '确认删除', { type: 'warning' })
    await deleteCertificate(row.id)
    ElMessage.success('删除成功')
    loadData()
    loadExpiring()
  } catch {
    // cancelled
  }
}

onMounted(() => {
  loadData()
  loadExpiring()
  loadVehicles()
  loadDrivers()
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
.expiring-item {
  margin-bottom: 4px;
  font-size: 13px;
}
.text-danger {
  color: #f56c6c;
  font-weight: bold;
}
.text-warning {
  color: #e6a23c;
  font-weight: bold;
}
</style>
