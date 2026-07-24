<template>
  <div class="page">
    <div class="page-header"><h2>高空车驾驶员</h2><el-button type="primary" @click="handleCreate">+ 新增驾驶员</el-button></div>
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="姓名/手机号搜索" clearable style="width: 200px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData">搜索</el-button>
    </div>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="driver_name" label="姓名" width="100" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="license_no" label="驾驶证号" width="140" />
      <el-table-column prop="license_type" label="驾照类型" width="80" />
      <el-table-column prop="license_expire_date" label="驾照到期" width="110">
        <template #default="{ row }"><span :style="{ color: isExpiredSoon(row.license_expire_date) ? '#f56c6c' : '' }">{{ row.license_expire_date || '-' }}</span></template>
      </el-table-column>
      <el-table-column prop="is_external" label="外协" width="60">
        <template #default="{ row }"><el-tag :type="row.is_external ? 'warning' : 'info'" size="small">{{ row.is_external ? '外协' : '内部' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">{{ row.status === 'active' ? '在职' : '停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button link :type="row.status === 'active' ? 'danger' : 'success'" size="small" @click="handleToggle(row)">{{ row.status === 'active' ? '停用' : '启用' }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" />

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑驾驶员' : '新增驾驶员'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required><el-input v-model="form.driver_name" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="驾驶证号"><el-input v-model="form.license_no" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="驾照类型"><el-input v-model="form.license_type" placeholder="A1/B2/C1等" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="驾照到期"><el-date-picker v-model="form.license_expire_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="外协司机"><el-switch v-model="form.is_external" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAerialDrivers, createAerialDriver, updateAerialDriver } from '@/api/aerial'

const loading = ref(false); const saving = ref(false); const dialogVisible = ref(false)
const list = ref<any[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20)
const keyword = ref(''); const editingId = ref<string | null>(null)

const form = reactive({ driver_name: '', phone: '', license_no: '', license_type: '', license_expire_date: '', is_external: false, remark: '' })

async function fetchData() {
  loading.value = true
  try { const res = await getAerialDrivers({ keyword: keyword.value, page: page.value, page_size: pageSize.value }); list.value = res.items || []; total.value = res.total || 0 }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { driver_name: '', phone: '', license_no: '', license_type: '', license_expire_date: '', is_external: false, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { driver_name: row.driver_name, phone: row.phone, license_no: row.license_no, license_type: row.license_type, license_expire_date: row.license_expire_date, is_external: row.is_external, remark: row.remark })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.driver_name.trim()) return ElMessage.warning('请填写姓名')
  saving.value = true
  try {
    if (editingId.value) { await updateAerialDriver(editingId.value, form); ElMessage.success('修改成功') }
    else { await createAerialDriver(form); ElMessage.success('新增成功') }
    dialogVisible.value = false; fetchData()
  } catch (e: any) { ElMessage.error(e.message) } finally { saving.value = false }
}

async function handleToggle(row: any) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  try { await ElMessageBox.confirm(`确定${newStatus === 'disabled' ? '停用' : '启用'} ${row.driver_name}？`, '确认'); await updateAerialDriver(row.id, { status: newStatus }); ElMessage.success('操作成功'); fetchData() } catch {}
}

function isExpiredSoon(d: string | null) { if (!d) return false; return new Date(d) <= new Date(Date.now() + 30 * 86400000) }

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
</style>
