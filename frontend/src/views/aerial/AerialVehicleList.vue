<template>
  <div class="page">
    <div class="page-header"><h2>高空车档案</h2><el-button type="primary" @click="handleCreate">+ 新增高空车</el-button></div>
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="车牌号/名称搜索" clearable style="width: 200px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData">搜索</el-button>
    </div>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="plate_number" label="车牌号" width="110" />
      <el-table-column prop="vehicle_name" label="车辆名称" width="140" />
      <el-table-column prop="brand_model" label="品牌型号" width="120" />
      <el-table-column prop="max_working_height" label="最大高度" width="90" />
      <el-table-column prop="platform_capacity" label="平台承重" width="90" />
      <el-table-column prop="default_personnel_name" label="默认人员" width="100" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'available' ? 'success' : row.status === 'disabled' ? 'danger' : 'warning'" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="insurance_expire_date" label="保险到期" width="110">
        <template #default="{ row }"><span :style="{ color: isExpiredSoon(row.insurance_expire_date) ? '#f56c6c' : '' }">{{ row.insurance_expire_date || '-' }}</span></template>
      </el-table-column>
      <el-table-column prop="inspection_expire_date" label="年检到期" width="110">
        <template #default="{ row }"><span :style="{ color: isExpiredSoon(row.inspection_expire_date) ? '#f56c6c' : '' }">{{ row.inspection_expire_date || '-' }}</span></template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }"><el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button></template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" />

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑高空车' : '新增高空车'" width="600px" destroy-on-close>
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
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAerialVehicles, createAerialVehicle, updateAerialVehicle } from '@/api/aerial'

const loading = ref(false); const saving = ref(false); const dialogVisible = ref(false)
const list = ref<any[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20)
const keyword = ref(''); const editingId = ref<string | null>(null)

const form = reactive({
  plate_number: '', vehicle_name: '', brand_model: '', max_working_height: '', platform_capacity: '',
  insurance_expire_date: '', inspection_expire_date: '', maintenance_due_date: '', remark: '',
})

async function fetchData() {
  loading.value = true
  try { const res = await getAerialVehicles({ keyword: keyword.value, page: page.value, page_size: pageSize.value }); list.value = res.items || []; total.value = res.total || 0 }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { plate_number: '', vehicle_name: '', brand_model: '', max_working_height: '', platform_capacity: '', insurance_expire_date: '', inspection_expire_date: '', maintenance_due_date: '', remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { plate_number: row.plate_number, vehicle_name: row.vehicle_name, brand_model: row.brand_model, max_working_height: row.max_working_height, platform_capacity: row.platform_capacity, insurance_expire_date: row.insurance_expire_date, inspection_expire_date: row.inspection_expire_date, maintenance_due_date: row.maintenance_due_date, remark: row.remark })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.plate_number.trim()) return ElMessage.warning('请填写车牌号')
  if (!form.vehicle_name.trim()) return ElMessage.warning('请填写车辆名称')
  saving.value = true
  try {
    if (editingId.value) { await updateAerialVehicle(editingId.value, form); ElMessage.success('修改成功') }
    else { await createAerialVehicle(form); ElMessage.success('新增成功') }
    dialogVisible.value = false; fetchData()
  } catch (e: any) { ElMessage.error(e.message) } finally { saving.value = false }
}

function statusLabel(s: string) { return { available: '可用', in_use: '使用中', maintenance: '维修中', disabled: '已停用', scrapped: '已报废' }[s] || s }

function isExpiredSoon(d: string | null) {
  if (!d) return false
  return new Date(d) <= new Date(Date.now() + 30 * 86400000)
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
</style>
