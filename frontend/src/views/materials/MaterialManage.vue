<template>
  <div class="page">
    <div class="page-header">
      <h2>材质管理</h2>
      <el-button type="danger" @click="handleCreate">新建材质</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索材质名称" clearable style="width: 300px" @keyup.enter="fetchData" />
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="name" label="材质名称" min-width="160" />
      <el-table-column prop="spec" label="规格" width="120" />
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column label="采购价" width="120">
        <template #default="{ row }">¥ {{ row.purchase_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="销售价" width="120">
        <template #default="{ row }">¥ {{ row.sale_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑材质' : '新建材质'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="材质名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.spec" placeholder="如 1220×2440mm" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="form.unit" style="width: 100%">
            <el-option label="张" value="张" />
            <el-option label="㎡" value="㎡" />
            <el-option label="米" value="米" />
            <el-option label="个" value="个" />
            <el-option label="kg" value="kg" />
          </el-select>
        </el-form-item>
        <el-form-item label="采购价">
          <el-input-number v-model="form.purchase_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销售价">
          <el-input-number v-model="form.sale_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="损耗率">
          <el-input-number v-model="form.loss_rate" :precision="4" :min="0" :step="0.01" style="width: 100%" />
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
import { getMaterials, createMaterial, updateMaterial, deleteMaterial } from '@/api/products'
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
const form = reactive({ name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0 })

async function fetchData() {
  loading.value = true
  try {
    const data = await getMaterials({ page: page.value, page_size: pageSize.value, keyword: keyword.value })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0 })
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, spec: row.spec, unit: row.unit, purchase_price: row.purchase_price, sale_price: row.sale_price, loss_rate: row.loss_rate })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateMaterial(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createMaterial(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除材质 "${row.name}"？`, '确认', { type: 'warning' })
  await deleteMaterial(row.id)
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
