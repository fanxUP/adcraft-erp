<template>
  <div class="page">
    <div class="page-header">
      <h2>材质管理</h2>
      <div>
        <el-button @click="importDialogVisible = true">导入</el-button>
        <el-button type="danger" @click="handleCreate">新建材质</el-button>
      </div>
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
          <el-button text type="primary" @click="handleEdit(row as MaterialResponse)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row as MaterialResponse)">删除</el-button>
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

    <el-dialog v-model="importDialogVisible" title="导入材质" width="520px">
      <div style="margin-bottom: 16px; font-size: 13px; color: var(--ad-text-secondary)">
        <p>支持 .xlsx / .xls 格式，请确保 Excel 包含以下列（<span style="color: #f56c6c">*</span>为必填）：</p>
        <el-table :data="templateColumns" border size="small" style="margin: 12px 0">
          <el-table-column prop="name" label="列名" width="120" />
          <el-table-column prop="desc" label="说明" />
          <el-table-column label="必填" width="60">
            <template #default="{ row }"><span v-if="row.required" style="color: #f56c6c">*</span></template>
          </el-table-column>
        </el-table>
        <el-table :data="sampleData" border size="small" style="margin: 8px 0">
          <el-table-column prop="col1" label="材质名称" />
          <el-table-column prop="col2" label="规格" />
          <el-table-column prop="col3" label="单位" />
          <el-table-column prop="col4" label="采购价" />
          <el-table-column prop="col5" label="销售价" />
        </el-table>
      </div>
      <el-upload ref="uploadRef" accept=".xlsx,.xls" :auto-upload="false" :limit="1" :on-change="handleFileChange" :on-exceed="() => ElMessage.warning('只能上传一个文件')">
        <template #trigger><el-button type="primary">选择文件</el-button></template>
        <template #tip><div class="el-upload__tip">仅支持 .xlsx / .xls 文件</div></template>
      </el-upload>
      <div v-if="importResult" style="margin-top: 16px">
        <el-alert :title="`导入完成：成功 ${importResult.succeeded} 条，失败 ${importResult.failed} 条`" :type="importResult.failed > 0 ? 'warning' : 'success'" show-icon />
        <el-table v-if="importResult.errors?.length" :data="importResult.errors" border size="small" style="margin-top: 8px" max-height="200px">
          <el-table-column prop="row" label="行号" width="60" />
          <el-table-column prop="message" label="错误信息" />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="danger" :loading="importing" :disabled="!importFile" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getMaterials, createMaterial, updateMaterial, deleteMaterial, importMaterials } from '@/api/products'
import type { MaterialResponse, ImportResponse } from '@/types/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const saving = ref(false)
const list = ref<MaterialResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0 })

// Import
const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)
const importResult = ref<ImportResponse | null>(null)
const templateColumns = [
  { name: '材质名称', desc: '材质/材料名称', required: true },
  { name: '规格', desc: '如 1220×2440mm', required: false },
  { name: '单位', desc: '张 / ㎡ / 米 / 个 / kg', required: false },
  { name: '采购价', desc: '采购单价（数字）', required: false },
  { name: '销售价', desc: '销售单价（数字）', required: false },
  { name: '损耗率', desc: '如 0.05 表示 5%', required: false },
  { name: '安全库存', desc: '安全库存数量（数字）', required: false },
  { name: '备注', desc: '备注信息', required: false },
]
const sampleData = [{ col1: 'PVC板', col2: '1220×2440mm', col3: '张', col4: '85.00', col5: '120.00' }]

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

function handleEdit(row: MaterialResponse) {
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

async function handleDelete(row: MaterialResponse) {
  await ElMessageBox.confirm(`确认删除材质 "${row.name}"？`, '确认', { type: 'warning' })
  await deleteMaterial(row.id)
  ElMessage.success('已删除')
  fetchData()
}

function handleFileChange(uploadFile: UploadFile) {
  importFile.value = uploadFile.raw || null
  importResult.value = null
}

async function handleImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const data = await importMaterials(importFile.value)
    importResult.value = data
    ElMessage.success(`导入完成：成功 ${data.succeeded} 条${data.failed > 0 ? `，失败 ${data.failed} 条` : ''}`)
    fetchData()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导入失败'))
  } finally {
    importing.value = false
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
