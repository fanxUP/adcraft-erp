<template>
  <div class="page">
    <div class="page-header">
      <h2>材质工艺</h2>
      <div>
        <el-button v-if="activeTab === 'materials'" @click="importDialogVisible = true">导入</el-button>
        <el-button type="danger" @click="handleCreate">
          新建{{ activeTab === 'materials' ? '材质' : '工艺' }}
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="材质管理" name="materials" />
      <el-tab-pane label="工艺管理" name="processes" />
    </el-tabs>

    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        :placeholder="activeTab === 'materials' ? '搜索材质名称' : '搜索工艺名称'"
        clearable style="width: 300px"
        @keyup.enter="fetchData"
      />
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <!-- 材质表格 -->
    <el-table v-if="activeTab === 'materials'" :data="materialList" v-loading="loading" stripe style="margin-top: 16px">
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

    <!-- 工艺表格 -->
    <el-table v-else :data="processList" v-loading="loading" stripe style="margin-top: 16px">
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
      v-model:current-page="currentPage"
      v-model:page-size="currentPageSize"
      :page-sizes="activeTab === 'materials' ? [10, 20, 50, 100] : []"
      :total="total"
      :layout="activeTab === 'materials' ? 'total, sizes, prev, pager, next' : 'total, prev, pager, next'"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" :close-on-click-modal="false">
      <!-- 材质表单 -->
      <el-form v-if="activeTab === 'materials'" :model="materialForm" label-width="100px">
        <el-form-item label="材质名称">
          <el-input v-model="materialForm.name" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="materialForm.spec" placeholder="如 1220×2440mm" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="materialForm.unit" style="width: 100%">
            <el-option label="张" value="张" />
            <el-option label="㎡" value="㎡" />
            <el-option label="米" value="米" />
            <el-option label="个" value="个" />
            <el-option label="kg" value="kg" />
          </el-select>
        </el-form-item>
        <el-form-item label="采购价">
          <el-input-number v-model="materialForm.purchase_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="销售价">
          <el-input-number v-model="materialForm.sale_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="损耗率">
          <el-input-number v-model="materialForm.loss_rate" :precision="4" :min="0" :step="0.01" style="width: 100%" />
        </el-form-item>
      </el-form>
      <!-- 工艺表单 -->
      <el-form v-else :model="processForm" label-width="100px">
        <el-form-item label="工艺名称">
          <el-input v-model="processForm.name" />
        </el-form-item>
        <el-form-item label="计费方式">
          <el-select v-model="processForm.charge_method" style="width: 100%">
            <el-option label="固定价" value="fixed" />
            <el-option label="按面积" value="area" />
            <el-option label="按数量" value="quantity" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认价格">
          <el-input-number v-model="processForm.default_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框（仅材质） -->
    <el-dialog v-model="importDialogVisible" title="导入材质" width="520px" :close-on-click-modal="false">
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
import { ref, reactive, computed, onMounted } from 'vue'
import {
  getMaterials, createMaterial, updateMaterial, deleteMaterial, importMaterials,
  getProcesses, createProcess, updateProcess, deleteProcess
} from '@/api/products'
import type { MaterialResponse, ProcessResponse, ImportResponse } from '@/types/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { getErrorMessage } from '@/utils/error'

// ---- Tab ----
const activeTab = ref<'materials' | 'processes'>('materials')

// ---- Shared UI ----
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)

// ---- 材质状态 ----
const materialList = ref<MaterialResponse[]>([])
const materialTotal = ref(0)
const materialPage = ref(1)
const materialPageSize = ref(20)
const materialKeyword = ref('')
const materialEditingId = ref<string | null>(null)
const materialForm = reactive({ name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0 })

// ---- 工艺状态 ----
const processList = ref<ProcessResponse[]>([])
const processTotal = ref(0)
const processPage = ref(1)
const processPageSize = ref(20)
const processKeyword = ref('')
const processEditingId = ref<string | null>(null)
const processForm = reactive({ name: '', charge_method: 'fixed', default_price: 0 })

// ---- 导入状态 ----
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

// ---- 计算属性桥接 ----
const total = computed(() =>
  activeTab.value === 'materials' ? materialTotal.value : processTotal.value
)

const searchKeyword = computed({
  get: () => activeTab.value === 'materials' ? materialKeyword.value : processKeyword.value,
  set: (v) => { (activeTab.value === 'materials' ? materialKeyword : processKeyword).value = v }
})
const currentPage = computed({
  get: () => activeTab.value === 'materials' ? materialPage.value : processPage.value,
  set: (v) => { (activeTab.value === 'materials' ? materialPage : processPage).value = v }
})
const currentPageSize = computed({
  get: () => activeTab.value === 'materials' ? materialPageSize.value : processPageSize.value,
  set: (v) => { (activeTab.value === 'materials' ? materialPageSize : processPageSize).value = v }
})

const dialogTitle = computed(() => {
  const prefix = activeTab.value === 'materials' ? '材质' : '工艺'
  const id = activeTab.value === 'materials' ? materialEditingId.value : processEditingId.value
  return id ? `编辑${prefix}` : `新建${prefix}`
})

// ---- 数据获取 ----
async function fetchMaterials() {
  loading.value = true
  try {
    const data = await getMaterials({ page: materialPage.value, page_size: materialPageSize.value, keyword: materialKeyword.value })
    materialList.value = data.items
    materialTotal.value = data.total
  } finally { loading.value = false }
}

async function fetchProcesses() {
  loading.value = true
  try {
    const data = await getProcesses({ page: processPage.value, page_size: processPageSize.value, keyword: processKeyword.value })
    processList.value = data.items
    processTotal.value = data.total
  } finally { loading.value = false }
}

function fetchData() {
  if (activeTab.value === 'materials') { fetchMaterials() } else { fetchProcesses() }
}

function onTabChange() {
  fetchData()
}

// ---- CRUD ----
function handleCreate() {
  if (activeTab.value === 'materials') {
    materialEditingId.value = null
    Object.assign(materialForm, { name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0 })
  } else {
    processEditingId.value = null
    Object.assign(processForm, { name: '', charge_method: 'fixed', default_price: 0 })
  }
  dialogVisible.value = true
}

function handleEdit(row: MaterialResponse | ProcessResponse) {
  if (activeTab.value === 'materials') {
    const m = row as MaterialResponse
    materialEditingId.value = m.id
    Object.assign(materialForm, { name: m.name, spec: m.spec, unit: m.unit, purchase_price: m.purchase_price, sale_price: m.sale_price, loss_rate: m.loss_rate })
  } else {
    const p = row as ProcessResponse
    processEditingId.value = p.id
    Object.assign(processForm, { name: p.name, charge_method: p.charge_method, default_price: p.default_price })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (activeTab.value === 'materials') {
      if (materialEditingId.value) {
        await updateMaterial(materialEditingId.value, materialForm)
      } else {
        await createMaterial(materialForm)
      }
    } else {
      if (processEditingId.value) {
        await updateProcess(processEditingId.value, processForm)
      } else {
        await createProcess(processForm)
      }
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleDelete(row: MaterialResponse | ProcessResponse) {
  try {
    const label = activeTab.value === 'materials' ? '材质' : '工艺'
    await ElMessageBox.confirm(`确认删除${label} "${row.name}"？`, '确认', { type: 'warning' })
    if (activeTab.value === 'materials') {
      await deleteMaterial(row.id)
    } else {
      await deleteProcess(row.id)
    }
    ElMessage.success('已删除')
    fetchData()
  } catch {
    // User cancelled
  }
}

// ---- 导入 ----
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
