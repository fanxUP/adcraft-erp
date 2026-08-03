<template>
  <div class="page">
    <div class="page-header"><h2>高空车档案</h2><el-button type="primary" @click="handleCreate">+ 新增高空车</el-button></div>
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="车牌号/名称搜索" clearable style="width: 200px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData">搜索</el-button>
    </div>
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
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="plate_number" label="车牌号" width="110" />
      <el-table-column prop="vehicle_name" label="车辆名称" width="140" />
      <el-table-column prop="brand_model" label="品牌型号" width="120" />
      <el-table-column prop="max_working_height" label="最大高度" width="90" />
      <el-table-column prop="platform_capacity" label="平台承重" width="90" />
      <el-table-column prop="default_personnel_name" label="默认人员" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'available' ? 'success' : row.status === 'disabled' ? 'danger' : 'warning'" size="small">{{ statusLabel(row.status) }}</el-tag>
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
          <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除该车辆？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" />

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑高空车' : '新增高空车'" width="600px" destroy-on-close :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="车牌号" required><el-input v-model="form.plate_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="车辆名称" required><el-input v-model="form.vehicle_name" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="品牌型号"><el-input v-model="form.brand_model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="最大作业高度"><el-input v-model="form.max_working_height" placeholder="如：20米" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="平台承重"><el-input v-model="form.platform_capacity" placeholder="如：200kg" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="保险到期"><el-date-picker v-model="form.insurance_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="年检到期"><el-date-picker v-model="form.inspection_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="下次保养"><el-date-picker v-model="form.maintenance_due_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="默认人员">
          <el-select v-model="form.default_personnel_id" clearable placeholder="选择默认人员" style="width: 100%">
            <el-option v-for="d in personnelOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
        <template v-if="editingId">
          <el-divider content-position="left">附件</el-divider>
          <div class="att-upload-row">
            <el-select v-model="attCategory" style="width: 120px">
              <el-option v-for="(label, val) in VEH_ATT_LABELS" :key="val" :label="label" :value="val" />
            </el-select>
            <el-upload :http-request="handleUploadAttachment" :show-file-list="false" :disabled="attUploading">
              <el-button type="primary" plain size="small" :loading="attUploading">上传附件</el-button>
            </el-upload>
          </div>
          <div v-if="attachments.length" class="att-list">
            <el-tag v-for="att in attachments" :key="att.id" :type="VEH_ATT_TAGS[att.attachment_type] || 'info'" closable @close="handleDeleteAttachment(att.id)">
              <a :href="att.file_url" target="_blank" class="att-link">{{ VEH_ATT_LABELS[att.attachment_type] || att.attachment_type }}·{{ att.file_name }}</a>
            </el-tag>
          </div>
          <div v-else style="color: #909399; font-size: 13px">暂无附件</div>
        </template>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import {
  getAerialVehicles,
  createAerialVehicle,
  updateAerialVehicle,
  deleteAerialVehicle,
  getAerialPersonnel,
  getAerialVehicleAttachments,
  createAerialVehicleAttachment,
  deleteAerialVehicleAttachment,
  getAerialExpiringVehicles,
  checkAerialExpiryNotifications,
  type AerialPersonnel,
  type AerialVehicle,
  type AerialVehicleAttachment,
  type AerialExpiringVehicle,
} from '@/api/aerial'
import { VEHICLE_ATTACHMENT_TYPE_LABELS, VEHICLE_ATTACHMENT_TYPE_TAGS } from '@/config/attachment'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false); const saving = ref(false); const dialogVisible = ref(false)
const list = ref<AerialVehicle[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20)
const keyword = ref(''); const editingId = ref<string | null>(null)
const personnelOptions = ref<AerialPersonnel[]>([])

// 附件
const attachments = ref<AerialVehicleAttachment[]>([])
const attCategory = ref('other')
const attUploading = ref(false)
const VEH_ATT_LABELS = VEHICLE_ATTACHMENT_TYPE_LABELS
const VEH_ATT_TAGS = VEHICLE_ATTACHMENT_TYPE_TAGS

// 保险/年检到期提醒
const expiringVehicles = ref<AerialExpiringVehicle[]>([])

function getUrgency(d: string): { tag: 'success' | 'warning' | 'danger'; label: string } {
  const days = Math.floor((new Date(d).getTime() - Date.now()) / 86400000)
  if (days < 0) return { tag: 'danger', label: '已过期' }
  if (days <= 7) return { tag: 'danger', label: '紧急' }
  if (days <= 30) return { tag: 'warning', label: '将到期' }
  return { tag: 'success', label: '正常' }
}

function hasVehicleExpired(v: AerialExpiringVehicle) {
  return v.insurance_urgency === 'expired' || v.inspection_urgency === 'expired'
}

function hasExpired() {
  return expiringVehicles.value.some(hasVehicleExpired)
}

function getItemParts(v: AerialExpiringVehicle): string[] {
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

const form = reactive({
  plate_number: '', vehicle_name: '', brand_model: '', max_working_height: '', platform_capacity: '',
  insurance_expire_date: '', inspection_expire_date: '', maintenance_due_date: '', default_personnel_id: '', remark: '',
})

async function fetchData() {
  loading.value = true
  try { const res = await getAerialVehicles({ keyword: keyword.value, page: page.value, page_size: pageSize.value }); list.value = res.items || []; total.value = res.total || 0 }
  catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  attachments.value = []
  Object.assign(form, { plate_number: '', vehicle_name: '', brand_model: '', max_working_height: '', platform_capacity: '', insurance_expire_date: '', inspection_expire_date: '', maintenance_due_date: '', default_personnel_id: '', remark: '' })
  dialogVisible.value = true
}

async function handleEdit(row: AerialVehicle) {
  editingId.value = row.id
  attachments.value = []
  Object.assign(form, { plate_number: row.plate_number, vehicle_name: row.vehicle_name, brand_model: row.brand_model, max_working_height: row.max_working_height, platform_capacity: row.platform_capacity, insurance_expire_date: row.insurance_expire_date, inspection_expire_date: row.inspection_expire_date, maintenance_due_date: row.maintenance_due_date, default_personnel_id: row.default_personnel_id || '', remark: row.remark })
  dialogVisible.value = true
  try { attachments.value = (await getAerialVehicleAttachments(row.id)) || [] } catch (e: unknown) { ElMessage.error(getErrorMessage(e)) }
}

async function handleSave() {
  if (!form.plate_number.trim()) return ElMessage.warning('请填写车牌号')
  if (!form.vehicle_name.trim()) return ElMessage.warning('请填写车辆名称')
  saving.value = true
  try {
    if (editingId.value) { await updateAerialVehicle(editingId.value, form); ElMessage.success('修改成功') }
    else { await createAerialVehicle(form); ElMessage.success('新增成功') }
    dialogVisible.value = false; fetchData()
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { saving.value = false }
}

async function handleDelete(row: AerialVehicle) {
  try { await deleteAerialVehicle(row.id); ElMessage.success('删除成功'); fetchData() } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) }
}

// ── 附件上传/删除 ──────────────────────────────────────────────────────────

async function handleUploadAttachment(options: UploadRequestOptions) {
  if (!editingId.value) return
  attUploading.value = true
  try {
    await createAerialVehicleAttachment(editingId.value, options.file, attCategory.value)
    ElMessage.success('上传成功')
    attachments.value = (await getAerialVehicleAttachments(editingId.value)) || []
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { attUploading.value = false }
}

async function handleDeleteAttachment(aid: string) {
  try { await ElMessageBox.confirm('确定删除该附件？', '确认') } catch { return }
  try {
    await deleteAerialVehicleAttachment(aid)
    ElMessage.success('删除成功')
    if (editingId.value) attachments.value = (await getAerialVehicleAttachments(editingId.value)) || []
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) }
}

function statusLabel(s: string) { return { available: '可用', in_use: '使用中', maintenance: '维修中', disabled: '已停用', scrapped: '已报废' }[s] || s }

// ── 到期提醒加载 / 每日节流通知检查 ──────────────────────────────────────────

async function loadExpiring() {
  try { expiringVehicles.value = (await getAerialExpiringVehicles(30)) || [] }
  catch { /* 横幅加载失败不打扰 */ }
}

async function checkExpiryThrottled() {
  const KEY = 'aerial_expiry_check'
  const last = Number(localStorage.getItem(KEY) || 0)
  if (Date.now() - last < 24 * 3600 * 1000) return
  try {
    const r = await checkAerialExpiryNotifications(30)
    if (r.created > 0) ElMessage.success(`已生成 ${r.created} 条到期提醒`)
    localStorage.setItem(KEY, String(Date.now()))
  } catch { /* 失败静默，下次访问重试 */ }
}

onMounted(async () => {
  fetchData()
  try { const d = await getAerialPersonnel({ page_size: 100 }); personnelOptions.value = d.items || [] } catch {}
  loadExpiring()
  checkExpiryThrottled()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.att-upload-row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.att-list { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.att-link { text-decoration: none; }
.expiring-item { display: flex; align-items: center; margin: 2px 0; }
</style>
