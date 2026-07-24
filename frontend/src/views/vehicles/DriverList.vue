<template>
  <div class="page">
    <div class="page-header">
      <h2>司机管理</h2>
      <el-button type="danger" @click="handleCreate">新增司机</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索司机姓名/手机号" clearable style="width: 260px" @keyup.enter="fetchData" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px; margin-left: 12px">
        <el-option label="启用" value="active" />
        <el-option label="停用" value="disabled" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="driver_name" label="司机姓名" width="120" />
      <el-table-column label="是否员工" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_external ? 'info' : 'success'" size="small">{{ row.is_external ? '外协' : '员工' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="license_type" label="驾驶证类型" width="110" />
      <el-table-column label="驾驶证到期" width="120">
        <template #default="{ row }">
          <span :class="{ 'text-danger': isExpiredSoon(row.license_expire_date) }">
            {{ row.license_expire_date ? row.license_expire_date.slice(0, 10) : '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'active'" text type="warning" @click="handleDisable(row)">停用</el-button>
          <el-button v-if="row.status === 'disabled'" text type="success" @click="handleEnable(row)">启用</el-button>
          <el-popconfirm title="确定删除该司机？" @confirm="handleDelete(row)">
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
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑司机' : '新增司机'" width="500px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="司机姓名" required>
          <el-input v-model="form.driver_name" />
        </el-form-item>
        <el-form-item label="绑定员工">
          <el-input v-model="form.employee_id" placeholder="员工ID（可选）" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="驾驶证号">
          <el-input v-model="form.license_no" />
        </el-form-item>
        <el-form-item label="驾驶证类型">
          <el-select v-model="form.license_type" style="width: 100%">
            <el-option label="A1" value="A1" />
            <el-option label="A2" value="A2" />
            <el-option label="B1" value="B1" />
            <el-option label="B2" value="B2" />
            <el-option label="C1" value="C1" />
            <el-option label="C2" value="C2" />
          </el-select>
        </el-form-item>
        <el-form-item label="驾驶证到期">
          <el-date-picker v-model="form.license_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="外协司机">
          <el-switch v-model="form.is_external" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDrivers, createDriver, updateDriver, disableDriver, enableDriver, deleteDriver } from '@/api/vehicles'
import type { VehicleDriverResponse } from '@/api/vehicles'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const saving = ref(false)
const list = ref<VehicleDriverResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const statusFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)

const form = reactive({
  driver_name: '',
  employee_id: '',
  phone: '',
  license_no: '',
  license_type: 'C1',
  license_expire_date: '',
  is_external: false,
  remark: '',
})

function isExpiredSoon(dateStr?: string) {
  if (!dateStr) return false
  const d = new Date(dateStr)
  const now = new Date()
  const diff = (d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  return diff < 30
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getDrivers({
      page: page.value, page_size: pageSize.value,
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
    })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { driver_name: '', employee_id: '', phone: '', license_no: '', license_type: 'C1', license_expire_date: '', is_external: false, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: VehicleDriverResponse) {
  editingId.value = row.id
  Object.assign(form, {
    driver_name: row.driver_name,
    employee_id: row.employee_id || '',
    phone: row.phone || '',
    license_no: row.license_no || '',
    license_type: row.license_type || 'C1',
    license_expire_date: row.license_expire_date || '',
    is_external: row.is_external,
    remark: row.remark || '',
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.driver_name) {
    ElMessage.warning('请填写司机姓名')
    return
  }
  saving.value = true
  try {
    const payload = { ...form } as Record<string, unknown>
    Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = undefined })
    if (editingId.value) {
      await updateDriver(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createDriver(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally { saving.value = false }
}

async function handleDisable(row: VehicleDriverResponse) {
  await ElMessageBox.confirm(`确认停用司机 "${row.driver_name}"？`, '确认停用', { type: 'warning' })
  await disableDriver(row.id)
  ElMessage.success('已停用')
  fetchData()
}

async function handleEnable(row: VehicleDriverResponse) {
  await enableDriver(row.id)
  ElMessage.success('已启用')
  fetchData()
}

async function handleDelete(row: VehicleDriverResponse) {
  try { await deleteDriver(row.id); ElMessage.success('删除成功'); fetchData() } catch (e: any) { ElMessage.error(getErrorMessage(e)) }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
.text-danger { color: #f56c6c; font-weight: bold; }
</style>
