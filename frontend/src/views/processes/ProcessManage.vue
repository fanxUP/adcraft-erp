<template>
  <div class="page">
    <div class="page-header">
      <h2>工艺管理</h2>
      <el-button type="danger" @click="handleCreate">新建工艺</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索工艺名称" clearable style="width: 300px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="name" label="工艺名称" min-width="160" />
      <el-table-column prop="charge_method" label="计费方式" width="100" />
      <el-table-column label="默认价格" width="120">
        <template #default="{ row }">¥ {{ row.default_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row as ProcessResponse)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row as ProcessResponse)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑工艺' : '新建工艺'" width="500px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="工艺名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="计费方式">
          <el-select v-model="form.charge_method" style="width: 100%">
            <el-option label="固定价" value="fixed" />
            <el-option label="按面积" value="area" />
            <el-option label="按数量" value="quantity" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认价格">
          <el-input-number v-model="form.default_price" :precision="2" :min="0" style="width: 100%" />
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
import { getProcesses, createProcess, updateProcess, deleteProcess } from '@/api/products'
import type { ProcessResponse } from '@/types/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const list = ref<ProcessResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', charge_method: 'fixed', default_price: 0 })

async function fetchData() {
  loading.value = true
  try {
    const data = await getProcesses({ page: page.value, page_size: pageSize.value, keyword: keyword.value })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', charge_method: 'fixed', default_price: 0 })
  dialogVisible.value = true
}

function handleEdit(row: ProcessResponse) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, charge_method: row.charge_method, default_price: row.default_price })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateProcess(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createProcess(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleDelete(row: ProcessResponse) {
  try {
    await ElMessageBox.confirm(`确认删除工艺 "${row.name}"？`, '确认', { type: 'warning' })
    await deleteProcess(row.id)
    ElMessage.success('已删除')
    fetchData()
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
