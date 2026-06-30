<template>
  <div class="page">
    <div class="page-header">
      <h2>外协任务</h2>
      <el-button type="danger" @click="handleCreate">新建外协任务</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已结算" value="settled" />
      </el-select>
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无外协任务">
      <el-table-column prop="task_no" label="任务编号" width="160" />
      <el-table-column prop="vendor_name" label="外协商" width="150" />
      <el-table-column label="任务类型" width="100">
        <template #default="{ row }">{{ taskTypeLabel(row.task_type) }}</template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column prop="quantity" label="数量" width="70" />
      <el-table-column prop="unit_price" label="单价" width="100" align="right">
        <template #default="{ row }">¥{{ row.unit_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="total_amount" label="总金额" width="120" align="right">
        <template #default="{ row }">¥{{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row as OutsourceTaskResponse)">编辑</el-button>
          <el-button v-if="row.status === 'pending'" text type="primary" @click="handleUpdateStatus(row as OutsourceTaskResponse, 'in_progress')">开始</el-button>
          <el-button v-if="row.status === 'in_progress'" text type="success" @click="handleUpdateStatus(row as OutsourceTaskResponse, 'completed')">完成</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑外协任务' : '新建外协任务'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="外协商" prop="vendor_id">
          <el-select v-model="form.vendor_id" filterable clearable style="width: 100%">
            <el-option v-for="v in vendors" :key="v.id" :label="v.name" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" clearable style="width: 100%">
            <el-option label="制作" value="production" />
            <el-option label="安装" value="installation" />
            <el-option label="设计" value="design" />
            <el-option label="运输" value="transport" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="form.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
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
import {
  getOutsourceVendors, getOutsourceTasks, createOutsourceTask, updateOutsourceTask,
} from '@/api/outsource'
import { ElMessage } from 'element-plus'
import { OutsourceTaskResponse, VendorResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<OutsourceTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const vendors = ref<VendorResponse[]>([])
const form = reactive({
  vendor_id: '', task_type: 'production', description: '',
  quantity: 1, unit_price: 0, remark: '',
})
const rules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
}

function taskTypeLabel(val: string) {
  const map: Record<string, string> = { production: '制作', installation: '安装', design: '设计', transport: '运输' }
  return map[val] || val
}

function statusType(val: string) {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', settled: '' }
  return (map[val] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function statusLabel(val: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算' }
  return map[val] || val
}

async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 200 })
    vendors.value = data.items
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getOutsourceTasks({
      page: page.value, page_size: pageSize.value,
      status: statusFilter.value || undefined,
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { vendor_id: '', task_type: 'production', description: '', quantity: 1, unit_price: 0, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: OutsourceTaskResponse) {
  editingId.value = row.id
  Object.assign(form, {
    vendor_id: row.vendor_id, task_type: row.task_type, description: row.description,
    quantity: row.quantity, unit_price: row.unit_price, remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateOutsourceTask(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createOutsourceTask(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleUpdateStatus(row: OutsourceTaskResponse, status: string) {
  try {
    await updateOutsourceTask(row.id, { status })
    ElMessage.success(`已更新为：${statusLabel(status)}`)
    await fetchData()
  } catch {
    // API error handled by interceptor
  }
}

onMounted(() => { fetchData(); loadVendors() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
