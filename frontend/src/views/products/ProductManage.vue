<template>
  <div class="pricing-center">
    <!-- 产品/材质/工艺定价（全局库） -->
    <div class="right-panel">
      <div class="page-header">
        <h2>产品/材质/工艺定价</h2>
        <div>
          <el-button @click="importDialogVisible = true">导入</el-button>
          <el-button type="danger" @click="handleCreate">新建定价</el-button>
        </div>
      </div>
      <div class="search-bar">
        <el-input v-model="keyword" placeholder="搜索产品、材质或工艺" clearable style="width: 300px" @keyup.enter="fetchProducts" />
        <el-button type="primary" @click="fetchProducts" style="margin-left: 12px">搜索</el-button>
      </div>

      <el-table :data="productList" v-loading="productLoading" stripe style="margin-top: 16px">
        <el-table-column label="产品/材质/工艺" min-width="220">
          <template #default="{ row }">{{ [row.name, row.material_name, row.process_name].filter(Boolean).join(' / ') }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column label="计价方式" width="100">
          <template #default="{ row }">{{ pricingLabel(row.pricing_method) }}</template>
        </el-table-column>
        <el-table-column label="默认单价" width="120">
          <template #default="{ row }">¥ {{ row.default_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleEdit(row as ProductResponse)">编辑</el-button>
            <el-button text type="danger" @click="handleDelete(row as ProductResponse)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="prodPage"
        v-model:page-size="prodPageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="prodTotal"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @change="fetchProducts"
      />

      <!-- ── Product Create/Edit Dialog ── -->
      <el-dialog v-model="dialogVisible" :title="editingId ? '编辑产品/材质/工艺组合' : '新建'" width="min(760px, 92vw)" :close-on-click-modal="false">
        <el-form :model="form" label-width="100px">
          <div class="combination-fields">
            <el-form-item label="产品">
              <el-input v-model="form.name" placeholder="如：标识牌" />
            </el-form-item>
            <el-form-item label="材质">
              <el-input v-model="form.material_name" placeholder="如：亚克力" />
            </el-form-item>
            <el-form-item label="工艺">
              <el-input v-model="form.process_name" placeholder="如：UV打印" />
            </el-form-item>
          </div>
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

      <!-- ── Import Dialog ── -->
      <el-dialog v-model="importDialogVisible" title="导入产品/材质/工艺组合" width="520px" :close-on-click-modal="false">
        <div style="margin-bottom: 16px; font-size: 13px; color: var(--ad-text-secondary)">
          <p>支持 .xlsx / .xls 格式，请确保 Excel 包含以下列（<span style="color: #f56c6c">*</span>为必填）：</p>
          <el-table :data="templateColumns" border size="small" style="margin: 12px 0">
            <el-table-column prop="name" label="列名" width="120" />
            <el-table-column prop="desc" label="说明" />
            <el-table-column label="必填" width="60">
              <template #default="{ row: r }"><span v-if="r.required" style="color: #f56c6c">*</span></template>
            </el-table-column>
          </el-table>
        </div>
        <el-upload :auto-upload="false" :limit="1" :on-change="handleFileChange" :on-exceed="() => ElMessage.warning('只能上传一个文件')">
          <template #trigger><el-button type="primary">选择文件</el-button></template>
        </el-upload>
        <div v-if="importResult" style="margin-top: 16px">
          <el-alert :title="'导入完成：成功 ' + importResult.succeeded + ' 条，失败 ' + importResult.failed + ' 条'" :type="importResult.failed > 0 ? 'warning' : 'success'" show-icon />
        </div>
        <template #footer>
          <el-button @click="importDialogVisible = false">关闭</el-button>
          <el-button type="danger" :loading="importing" :disabled="!importFile" @click="handleImport">开始导入</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  getProducts, createProduct, updateProduct, deleteProduct, importProducts,
} from '@/api/products'
import type { ProductResponse, ImportResponse } from '@/types/api'
import { getErrorMessage } from '@/utils/error'

// ── Global Product Library ───────────────────────────────────
const keyword = ref('')
const productLoading = ref(false)
const productList = ref<ProductResponse[]>([])
const prodTotal = ref(0)
const prodPage = ref(1)
const prodPageSize = ref(20)

function pricingLabel(m: string) {
  const map: Record<string, string> = { area: '按面积', quantity: '按数量', length: '按长度', word_count: '按字数' }
  return map[m] || m
}

async function fetchProducts() {
  productLoading.value = true
  try {
    const data = await getProducts({ page: prodPage.value, page_size: prodPageSize.value, keyword: keyword.value })
    productList.value = data.items
    prodTotal.value = data.total
  } finally { productLoading.value = false }
}

// ── Product CRUD ──
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const form = reactive({
  name: '', material_name: '', process_name: '',
  unit: '项', pricing_method: 'quantity',
  default_price: 0, min_charge: 0, remark: '',
})

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', material_name: '', process_name: '', unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0, remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: ProductResponse) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, material_name: row.material_name || '', process_name: row.process_name || '',
    unit: row.unit, pricing_method: row.pricing_method,
    default_price: row.default_price, min_charge: row.min_charge, remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleSave() {
  const filled = [form.name.trim(), form.material_name.trim(), form.process_name.trim()].filter(Boolean)
  if (filled.length === 0) { ElMessage.warning('请至少填写产品、材质、工艺中的一项'); return }
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
    fetchProducts()
  } finally { saving.value = false }
}

async function handleDelete(row: ProductResponse) {
  const label = [row.name, row.material_name, row.process_name].filter(Boolean).join(' / ')
  await ElMessageBox.confirm('确认删除产品/材质/工艺组合 "' + label + '"？', '确认', { type: 'warning' })
  await deleteProduct(row.id)
  ElMessage.success('已删除')
  fetchProducts()
}

// ── Import ──
const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)
const importResult = ref<ImportResponse | null>(null)
const templateColumns = [
  { name: '产品', desc: '产品名称', required: true },
  { name: '材质', desc: '材质名称', required: false },
  { name: '工艺', desc: '工艺名称', required: false },
  { name: '单位', desc: '项 / ㎡ / 米 / 个 / 套', required: false },
  { name: '计价方式', desc: 'area / quantity / length / word_count', required: false },
  { name: '默认价格', desc: '默认单价（数字）', required: false },
  { name: '最低收费', desc: '最低收费金额（数字）', required: false },
  { name: '备注', desc: '备注信息', required: false },
]

function handleFileChange(uploadFile: UploadFile) {
  importFile.value = uploadFile.raw || null
  importResult.value = null
}

async function handleImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const data = await importProducts(importFile.value)
    importResult.value = data
    ElMessage.success('导入完成：成功 ' + data.succeeded + ' 条，失败 ' + data.failed + ' 条')
    fetchProducts()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导入失败'))
  } finally { importing.value = false }
}

// ── Init ──
onMounted(() => {
  fetchProducts()
})
</script>

<style scoped>
.pricing-center {
  display: flex;
  gap: 0;
}
.right-panel {
  flex: 1;
  padding: 20px 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.page-header h2 {
  margin: 0;
  color: var(--ad-text);
  font-size: 18px;
}
.search-bar {
  display: flex;
  align-items: center;
}
.combination-fields {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.combination-fields :deep(.el-form-item) { display: block; }
.combination-fields :deep(.el-form-item__label) { justify-content: flex-start; }
.combination-fields :deep(.el-form-item__content) { margin-left: 0 !important; }
@media (max-width: 720px) {
  .combination-fields { grid-template-columns: 1fr; }
}
</style>
