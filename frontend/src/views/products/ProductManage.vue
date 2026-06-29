<template>
  <div class="page">
    <div class="page-header">
      <h2>产品管理</h2>
      <el-button type="danger" @click="handleCreate">新建产品</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索产品名称" clearable style="width: 300px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="name" label="产品名称" min-width="180" />
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column prop="pricing_method" label="计价方式" width="100" />
      <el-table-column label="默认单价" width="120">
        <template #default="{ row }">¥ {{ row.default_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑产品' : '新建产品'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="产品名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="form.unit" style="width: 100%">
            <el-option label="项" value="项" />
            <el-option label="㎡" value="㎡" />
            <el-option label="米" value="米" />
            <el-option label="个" value="个" />
            <el-option label="套" value="套" />
          </el-select>
        </el-form-item>
        <el-form-item label="计价方式">
          <el-select v-model="form.pricing_method" style="width: 100%">
            <el-option label="按面积" value="area" />
            <el-option label="按数量" value="quantity" />
            <el-option label="按长度" value="length" />
            <el-option label="按字数" value="word_count" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认单价">
          <el-input-number v-model="form.default_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最低收费">
          <el-input-number v-model="form.min_charge" :precision="2" :min="0" style="width: 100%" />
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
import { getProducts, createProduct, updateProduct, deleteProduct } from '@/api/products'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0, remark: '' })

async function fetchData() {
  loading.value = true
  try {
    const data = await getProducts({ page: page.value, page_size: pageSize.value, keyword: keyword.value })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, unit: row.unit, pricing_method: row.pricing_method, default_price: row.default_price, min_charge: row.min_charge, remark: row.remark })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateProduct(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除产品 "${row.name}"？`, '确认', { type: 'warning' })
  await deleteProduct(row.id)
  ElMessage.success('已删除')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
