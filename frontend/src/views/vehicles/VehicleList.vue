<template>
  <div class="page">
    <div class="page-header">
      <h2>车辆管理</h2>
      <el-button type="danger" @click="handleCreate">新增车辆</el-button>
    </div>

    <!-- 保险/年检到期提醒 -->
    <el-alert
      v-if="expiringVehicles.length"
      :title="`有 ${expiringVehicles.length} 辆车保险/年检即将到期或已过期`"
      :type="hasExpired() ? 'error' : 'warning'"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #default>
        <div v-for="v in expiringVehicles.slice(0, 5)" :key="v.vehicle_id" class="expiring-item">
          <el-tag size="small" :type="hasVehicleExpired(v) ? 'danger' : 'warning'" style="margin-right: 8px">
            {{ hasVehicleExpired(v) ? '已过期' : '将到期' }}
          </el-tag>
          {{ v.plate_number }} {{ v.vehicle_name }} — {{ getItemParts(v).join('，') }}
        </div>
        <div v-if="expiringVehicles.length > 5" style="color: #909399; margin-top: 4px">...还有 {{ expiringVehicles.length - 5 }} 辆</div>
      </template>
    </el-alert>

    <div class="search-bar">
      <el-input v-model="filters.keyword" placeholder="搜索车牌号/名称" clearable style="width: 240px" @keyup.enter="fetchData" />
      <el-select v-model="filters.vehicle_type" placeholder="车辆类型" clearable style="width: 140px; margin-left: 12px">
        <el-option v-for="t in vehicleTypes" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px; margin-left: 12px">
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="plate_number" label="车牌号" width="120" />
      <el-table-column prop="vehicle_name" label="车辆名称" min-width="140" />
      <el-table-column label="车辆类型" width="100">
        <template #default="{ row }">{{ vehicleTypeLabel(row.vehicle_type) }}</template>
      </el-table-column>
      <el-table-column prop="brand_model" label="品牌型号" width="140" />
      <el-table-column prop="default_driver_name" label="默认司机" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="保险到期" width="150">
        <template #default="{ row }">
          <span v-if="row.insurance_expire_date">
            {{ row.insurance_expire_date.slice(0, 10) }}
            <el-tag :type="getUrgency(row.insurance_expire_date).tag" size="small" style="margin-left: 4px">{{ getUrgency(row.insurance_expire_date).label }}</el-tag>
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="年检到期" width="150">
        <template #default="{ row }">
          <span v-if="row.inspection_expire_date">
            {{ row.inspection_expire_date.slice(0, 10) }}
            <el-tag :type="getUrgency(row.inspection_expire_date).tag" size="small" style="margin-left: 4px">{{ getUrgency(row.inspection_expire_date).label }}</el-tag>
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'available'" text type="warning" @click="handleDisable(row)">停用</el-button>
          <el-button v-if="row.status === 'disabled'" text type="success" @click="handleEnable(row)">启用</el-button>
          <el-button v-if="row.status !== 'scrapped'" text type="danger" @click="handleScrap(row)">报废</el-button>
          <el-popconfirm title="确定删除该车辆？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
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
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑车辆' : '新增车辆'" width="800px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="车牌号" required>
              <el-input v-model="form.plate_number" placeholder="如 京A12345" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="车辆名称" required>
              <el-input v-model="form.vehicle_name" placeholder="如 五菱宏光" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="车辆类型" required>
              <el-select v-model="form.vehicle_type" style="width: 100%">
                <el-option v-for="t in vehicleTypes" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="品牌型号">
              <el-input v-model="form.brand_model" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="颜色">
              <el-input v-model="form.color" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="购买日期">
              <el-date-picker v-model="form.purchase_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属部门">
              <el-input v-model="form.department" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="保险到期">
              <el-date-picker v-model="form.insurance_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年检到期">
              <el-date-picker v-model="form.inspection_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="下次保养">
              <el-date-picker v-model="form.maintenance_due_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="载重信息">
              <el-input v-model="form.load_capacity" placeholder="如 1.5吨" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="座位数">
              <el-input-number v-model="form.seats" :min="1" :max="50" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <!-- 其他证件：仅编辑车辆且有权限时显示（保险/年检/保养已并入上方车辆日期字段） -->
      <template v-if="editingId && canManage">
        <el-divider content-position="left">其他证件</el-divider>
        <div class="cert-section">
          <div class="cert-head">
            <span class="cert-title">行驶证 / 道路运输证 / 驾驶证 / 其他</span>
            <el-button type="primary" size="small" @click="showCertAdd">
              <el-icon><Plus /></el-icon> 新增证件
            </el-button>
          </div>
          <el-table :data="certificates" v-loading="certLoading" size="small" stripe>
            <el-table-column label="证件类型" width="110">
              <template #default="{ row }">{{ getCertTypeLabel(row.certificate_type) }}</template>
            </el-table-column>
            <el-table-column prop="certificate_no" label="证件编号" min-width="140" />
            <el-table-column label="到期日期" width="120">
              <template #default="{ row }">
                <span :class="getExpireClass(row)">{{ row.expire_date ? row.expire_date.slice(0, 10) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.urgency" :type="getUrgencyType(row.urgency)" size="small">{{ getUrgencyLabel(row.urgency) }}</el-tag>
                <el-tag v-else :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="金额" width="100" align="right">
              <template #default="{ row }">{{ row.amount ? `¥${row.amount.toFixed(2)}` : '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="showCertEdit(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="handleCertDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 证件新增/编辑对话框 -->
    <el-dialog
      v-model="certDialogVisible"
      :title="certIsEdit ? '编辑证件' : '新增证件'"
      width="600px"
      append-to-body
      :close-on-click-modal="false"
    >
      <el-form :model="certForm" label-width="100px">
        <el-form-item label="车辆" required>
          <el-select v-model="certForm.vehicle_id" disabled>
            <el-option :value="certForm.vehicle_id" :label="currentVehicleLabel" />
          </el-select>
        </el-form-item>
        <el-form-item label="证件类型" required>
          <el-select v-model="certForm.certificate_type" placeholder="选择类型">
            <el-option label="行驶证" value="driving_license" />
            <el-option label="道路运输证" value="transport_license" />
            <el-option label="驾驶证" value="driver_license" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联司机" v-if="certForm.certificate_type === 'driver_license'">
          <el-select v-model="certForm.driver_id" placeholder="选择司机" filterable clearable>
            <el-option v-for="d in driverOptions" :key="d.id" :label="d.driver_name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="证件编号">
          <el-input v-model="certForm.certificate_no" placeholder="输入证件编号" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="certForm.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="到期日期">
          <el-date-picker v-model="certForm.expire_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="certForm.amount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="提前提醒天数">
          <el-input-number v-model="certForm.reminder_days" :min="1" :max="365" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="certForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="certDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCertSubmit" :loading="certSubmitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getVehicles, createVehicle, updateVehicle,
  disableVehicle, enableVehicle, scrapVehicle, deleteVehicle,
  getCertificates, getExpiringVehicles, createCertificate, updateCertificate, deleteCertificate,
  getDrivers,
  type CertificateResponse,
  type ExpiringVehicle,
  type VehicleDriverResponse,
} from '@/api/vehicles'
import type { VehicleCreateData, VehicleUpdateData } from '@/api/vehicles'
import type { VehicleResponse } from '@/api/vehicles'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const saving = ref(false)
const list = ref<VehicleResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)

const filters = reactive({
  keyword: '',
  vehicle_type: '',
  status: '',
})

const form = reactive({
  plate_number: '',
  vehicle_name: '',
  vehicle_type: 'van',
  brand_model: '',
  color: '',
  purchase_date: '',
  insurance_expire_date: '',
  inspection_expire_date: '',
  maintenance_due_date: '',
  department: '',
  load_capacity: '',
  seats: 2,
  remark: '',
})

const vehicleTypes = [
  { label: '面包车', value: 'van' },
  { label: '货车', value: 'truck' },
  { label: '皮卡', value: 'pickup' },
  { label: '轿车', value: 'sedan' },
  { label: '电动车', value: 'electric' },
  { label: '三轮车', value: 'tricycle' },
  { label: '外租车辆', value: 'rented' },
  { label: '其他', value: 'other' },
]

const statusOptions = [
  { label: '可用', value: 'available' },
  { label: '已派车', value: 'assigned' },
  { label: '出车中', value: 'in_use' },
  { label: '维修中', value: 'maintenance' },
  { label: '停用', value: 'disabled' },
  { label: '报废', value: 'scrapped' },
  { label: '外租', value: 'rented' },
]

const statusMap: Record<string, string> = {
  available: '可用', assigned: '已派车', in_use: '出车中',
  maintenance: '维修中', disabled: '停用', scrapped: '报废', rented: '外租',
}

const typeMap: Record<string, string> = {
  van: '面包车', truck: '货车', pickup: '皮卡', sedan: '轿车',
  electric: '电动车', tricycle: '三轮车', rented: '外租车辆', other: '其他',
}

function statusLabel(s: string) { return statusMap[s] || s }
function vehicleTypeLabel(t: string) { return typeMap[t] || t }
function statusTagType(s: string) {
  const m: Record<string, string> = {
    available: 'success', assigned: 'warning', in_use: '',
    maintenance: 'warning', disabled: 'info', scrapped: 'danger', rented: 'info',
  }
  return m[s] || ''
}

// ── 保险/年检（车辆日期字段）+ 其他证件 ──────────────────────────────────
const authStore = useAuthStore()
const canManage = computed(() => authStore.hasAnyRole(['admin', 'finance']))

const certificates = ref<CertificateResponse[]>([])
const certLoading = ref(false)
const expiringVehicles = ref<ExpiringVehicle[]>([])
const driverOptions = ref<VehicleDriverResponse[]>([])

// 保险/年检/保养已并入车辆日期字段；其余证件类型
const REMAINING_CERT_TYPES = ['driving_license', 'transport_license', 'driver_license', 'other']
const currentVehicleLabel = ref('')

const certDialogVisible = ref(false)
const certIsEdit = ref(false)
const certEditingId = ref('')
const certSubmitting = ref(false)
const certForm = reactive({
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
  compulsory_insurance: '交强险', commercial_insurance: '商业险', annual_inspection: '年检',
  driving_license: '行驶证', transport_license: '道路运输证', driver_license: '驾驶证',
  maintenance: '保养提醒', other: '其他',
}
function getCertTypeLabel(type: string) { return certTypeMap[type] || type }

function getStatusLabel(status: string) {
  const map: Record<string, string> = { active: '有效', expired: '已过期', renewed: '已续期', cancelled: '已取消' }
  return map[status] || status
}
function getStatusType(status: string) {
  const map: Record<string, string> = { active: 'success', expired: 'danger', renewed: 'info', cancelled: 'info' }
  return map[status] || 'info'
}
function getUrgencyType(urgency?: string) {
  if (urgency === 'expired') return 'danger'
  if (urgency === 'urgent' || urgency === 'warning') return 'warning'
  return 'info'
}
function getUrgencyLabel(urgency?: string) {
  if (urgency === 'expired') return '已过期'
  if (urgency === 'urgent' || urgency === 'warning') return '即将到期'
  return ''
}
function getExpireClass(row: CertificateResponse) {
  if (row.urgency === 'expired') return 'text-danger'
  if (row.urgency === 'urgent') return 'text-warning'
  return ''
}

// ── 保险/年检到期提醒（仿高空车） ─────────────────────────────────────────
function getUrgency(d: string): { tag: 'success' | 'warning' | 'danger'; label: string } {
  const days = Math.floor((new Date(d).getTime() - Date.now()) / 86400000)
  if (days < 0) return { tag: 'danger', label: '已过期' }
  if (days <= 7) return { tag: 'danger', label: '紧急' }
  if (days <= 30) return { tag: 'warning', label: '将到期' }
  return { tag: 'success', label: '正常' }
}

function hasVehicleExpired(v: ExpiringVehicle) {
  return v.insurance_urgency === 'expired' || v.inspection_urgency === 'expired'
}

function hasExpired() {
  return expiringVehicles.value.some(hasVehicleExpired)
}

function getItemParts(v: ExpiringVehicle): string[] {
  const parts: string[] = []
  for (const [field, label] of [['insurance', '保险'], ['inspection', '年检']] as const) {
    const daysLeft = v[`${field}_days_left`] ?? null
    const urgency = v[`${field}_urgency`]
    if (urgency && daysLeft !== null) {
      parts.push(`${label}${daysLeft < 0 ? `已过期 ${-daysLeft} 天` : `还剩 ${daysLeft} 天`}`)
    }
  }
  return parts
}

async function loadCertificates(vehicleId: string) {
  certLoading.value = true
  try {
    const res = await getCertificates({ page: 1, page_size: 100, vehicle_id: vehicleId })
    certificates.value = (res?.items ?? []).filter(c => REMAINING_CERT_TYPES.includes(c.certificate_type))
  } catch {
    certificates.value = []
  } finally {
    certLoading.value = false
  }
}

async function loadExpiring() {
  try { expiringVehicles.value = (await getExpiringVehicles(30)) ?? [] } catch { expiringVehicles.value = [] }
}

async function loadDrivers() {
  try {
    const res = await getDrivers({ page: 1, page_size: 100 })
    driverOptions.value = res?.items ?? []
  } catch {
    driverOptions.value = []
  }
}

function resetCertForm() {
  Object.assign(certForm, {
    vehicle_id: editingId.value || '', driver_id: '', certificate_type: '',
    certificate_no: '', start_date: '', expire_date: '', amount: 0, reminder_days: 30, remark: '',
  })
}

function showCertAdd() {
  certIsEdit.value = false
  certEditingId.value = ''
  resetCertForm()
  certDialogVisible.value = true
}

function showCertEdit(row: CertificateResponse) {
  certIsEdit.value = true
  certEditingId.value = row.id
  Object.assign(certForm, {
    vehicle_id: row.vehicle_id || editingId.value,
    driver_id: row.driver_id || '',
    certificate_type: row.certificate_type,
    certificate_no: row.certificate_no || '',
    start_date: row.start_date || '',
    expire_date: row.expire_date || '',
    amount: row.amount,
    reminder_days: row.reminder_days,
    remark: row.remark || '',
  })
  certDialogVisible.value = true
}

async function handleCertSubmit() {
  if (!certForm.vehicle_id) { ElMessage.warning('请选择车辆'); return }
  if (!certForm.certificate_type) { ElMessage.warning('请选择证件类型'); return }
  certSubmitting.value = true
  try {
    if (certIsEdit.value) {
      await updateCertificate(certEditingId.value, certForm)
      ElMessage.success('更新成功')
    } else {
      await createCertificate(certForm)
      ElMessage.success('创建成功')
    }
    certDialogVisible.value = false
    if (editingId.value) await loadCertificates(editingId.value)
    loadExpiring()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '操作失败'))
  } finally {
    certSubmitting.value = false
  }
}

async function handleCertDelete(row: CertificateResponse) {
  try {
    await ElMessageBox.confirm('确定删除该证件记录？', '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteCertificate(row.id)
    ElMessage.success('删除成功')
    if (editingId.value) await loadCertificates(editingId.value)
    loadExpiring()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '删除失败'))
  }
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getVehicles({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword || undefined,
      vehicle_type: filters.vehicle_type || undefined,
      status: filters.status || undefined,
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingId.value = null
  certificates.value = []
  currentVehicleLabel.value = ''
  Object.assign(form, {
    plate_number: '', vehicle_name: '', vehicle_type: 'van',
    brand_model: '', color: '', purchase_date: '',
    insurance_expire_date: '', inspection_expire_date: '', maintenance_due_date: '',
    department: '', load_capacity: '', seats: 2, remark: '',
  })
  dialogVisible.value = true
}

function handleEdit(row: VehicleResponse) {
  editingId.value = row.id
  currentVehicleLabel.value = `${row.plate_number} - ${row.vehicle_name}`
  Object.assign(form, {
    plate_number: row.plate_number,
    vehicle_name: row.vehicle_name,
    vehicle_type: row.vehicle_type,
    brand_model: row.brand_model || '',
    color: row.color || '',
    purchase_date: row.purchase_date || '',
    insurance_expire_date: row.insurance_expire_date || '',
    inspection_expire_date: row.inspection_expire_date || '',
    maintenance_due_date: row.maintenance_due_date || '',
    department: row.department || '',
    load_capacity: row.load_capacity || '',
    seats: row.seats || 2,
    remark: row.remark || '',
  })
  dialogVisible.value = true
  loadCertificates(row.id)
}

async function handleSave() {
  if (!form.plate_number || !form.vehicle_name || !form.vehicle_type) {
    ElMessage.warning('请填写必填字段')
    return
  }
  saving.value = true
  try {
    const payload = { ...form } as Record<string, unknown>
    // 清除空字符串
    Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = undefined })
    if (editingId.value) {
      await updateVehicle(editingId.value, payload as VehicleUpdateData)
      ElMessage.success('更新成功')
    } else {
      await createVehicle(payload as unknown as VehicleCreateData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleDisable(row: VehicleResponse) {
  await ElMessageBox.confirm(`确认停用车辆 "${row.plate_number}"？停用后无法派车。`, '确认停用', { type: 'warning' })
  await disableVehicle(row.id)
  ElMessage.success('已停用')
  fetchData()
}

async function handleEnable(row: VehicleResponse) {
  await enableVehicle(row.id)
  ElMessage.success('已启用')
  fetchData()
}

async function handleScrap(row: VehicleResponse) {
  await ElMessageBox.confirm(`确认报废车辆 "${row.plate_number}"？报废后不可恢复。`, '确认报废', { type: 'error' })
  await scrapVehicle(row.id)
  ElMessage.success('已报废')
  fetchData()
}

async function handleDelete(row: VehicleResponse) {
  try { await deleteVehicle(row.id); ElMessage.success('删除成功'); fetchData() } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) }
}

onMounted(() => {
  fetchData()
  loadExpiring()
  loadDrivers()
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
.cert-section { margin-bottom: 8px; }
.cert-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.cert-title { font-size: 13px; color: #909399; }
.expiring-item { margin-bottom: 4px; font-size: 13px; }
.text-danger { color: #f56c6c; font-weight: bold; }
.text-warning { color: #e6a23c; font-weight: bold; }
</style>
