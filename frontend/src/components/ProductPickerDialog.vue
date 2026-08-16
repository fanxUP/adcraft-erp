<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="选择产品/材质/工艺"
    width="900px"
    :close-on-click-modal="false"
    @open="onDialogOpen"
  >
    <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center;">
      <el-input
        v-model="keyword"
        placeholder="搜索产品名称 / 材质 / 工艺"
        clearable
        style="flex: 1;"
      />
      <el-button type="danger" @click="openCreate">+ 添加</el-button>
    </div>

    <el-table
      :data="products"
      v-loading="loading"
      highlight-current-row
      @row-click="onRowClick"
      max-height="420px"
    >
      <el-table-column label="产品/材质/工艺" min-width="260">
        <template #default="{ row }">
          {{ formatProductMaterialProcess(row) }}
        </template>
      </el-table-column>
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column label="全局价" width="100" align="right">
        <template #default="{ row }">
          <template v-if="row.default_price">¥{{ Number(row.default_price).toFixed(2) }}</template>
          <template v-else>-</template>
        </template>
      </el-table-column>
      <el-table-column label="协议价" width="120" align="right">
        <template #default="{ row }">
          <template v-if="agreementMap.has(row.id)">
            ¥{{ Number(agreementMap.get(row.id)!.price_value).toFixed(2) }}
          </template>
          <template v-else>
            <span style="color: var(--ad-text-secondary);">-</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click.stop="openEdit(row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      small
      background
      style="margin-top: 12px; justify-content: center;"
    />

    <!-- 新建产品对话框 -->
    <ProductCreateDialog v-model="createVisible" @created="onProductCreated" />

    <!-- 编辑产品对话框 -->
    <el-dialog
      v-model="editVisible"
      title="编辑产品"
      width="min(560px, 92vw)"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="产品">
          <el-input v-model="editForm.name" type="textarea" :rows="3" placeholder="如：标识牌" class="mp-textarea" />
        </el-form-item>
        <el-form-item label="材质">
          <el-input v-model="editForm.material_name" type="textarea" :rows="3" placeholder="如：亚克力" class="mp-textarea" />
        </el-form-item>
        <el-form-item label="工艺">
          <el-input v-model="editForm.process_name" type="textarea" :rows="3" placeholder="如：UV打印" class="mp-textarea" />
        </el-form-item>
        <el-form-item label="单位">
          <el-select v-model="editForm.unit" style="width: 100%">
            <el-option v-for="u in UNIT_OPTIONS" :key="u" :label="u" :value="u" />
          </el-select>
        </el-form-item>
        <el-form-item label="计价方式">
          <el-select v-model="editForm.pricing_method" style="width: 100%">
            <el-option
              v-for="p in PRICING_OPTIONS"
              :key="p.value"
              :label="p.label"
              :value="p.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="默认单价">
          <el-input-number v-model="editForm.default_price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最低收费">
          <el-input-number v-model="editForm.min_charge" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="danger" :loading="savingEdit" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getProducts, updateProduct } from '@/api/products'
import { formatProductMaterialProcess } from '@/utils/productMaterialProcess'
import { listCustomerAgreements, type CustomerAgreement } from '@/api/cdrQuote'
import ProductCreateDialog from './ProductCreateDialog.vue'
import type { ProductResponse } from '@/types/api'

const props = defineProps<{ modelValue: boolean; customerId?: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  selected: [product: ProductResponse]
  updated: [product: ProductResponse]
}>()

const UNIT_OPTIONS = ['项', '㎡', '米', '个', '套', '批']
const PRICING_OPTIONS = [
  { label: '按面积', value: 'area' },
  { label: '按数量', value: 'quantity' },
  { label: '按长度', value: 'length' },
  { label: '按字数', value: 'word_count' },
]
const pageSize = 15

const keyword = ref('')
const products = ref<ProductResponse[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const agreementMap = ref<Map<string, CustomerAgreement>>(new Map())

const createVisible = ref(false)
const editVisible = ref(false)
const editingProduct = ref<ProductResponse | null>(null)
const savingEdit = ref(false)
const editForm = ref({
  name: '',
  material_name: '',
  process_name: '',
  unit: '',
  pricing_method: '',
  default_price: 0,
  min_charge: 0,
  remark: '',
})

let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(keyword, () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    fetchProducts()
  }, 300)
})

watch(page, () => {
  fetchProducts()
})

async function fetchProducts() {
  loading.value = true
  try {
    const res = await getProducts({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
    })
    products.value = res.items ?? []
    total.value = res.total ?? 0
  } catch {
    ElMessage.error('加载产品列表失败')
  } finally {
    loading.value = false
  }
}

function onDialogOpen() {
  keyword.value = ''
  page.value = 1
  fetchProducts()
  if (props.customerId) {
    loadAgreements()
  }
}

async function loadAgreements() {
  try {
    const list = await listCustomerAgreements(props.customerId!)
    const map = new Map<string, CustomerAgreement>()
    for (const a of list) {
      if (a.product_id && !map.has(a.product_id)) {
        map.set(a.product_id, a)
      }
    }
    agreementMap.value = map
  } catch {
    agreementMap.value = new Map()
  }
}

function onRowClick(row: ProductResponse) {
  const agreement = agreementMap.value.get(row.id)
  const merged = agreement
    ? { ...row, default_price: Number(agreement.price_value) || row.default_price, min_charge: Number(agreement.minimum_charge) || row.min_charge, pricing_method: agreement.pricing_method || row.pricing_method }
    : row
  emit('selected', merged)
  emit('update:modelValue', false)
}

function openCreate() {
  createVisible.value = true
}

function onProductCreated(product: ProductResponse) {
  createVisible.value = false
  emit('selected', product)
  emit('update:modelValue', false)
}

function openEdit(product: ProductResponse) {
  editingProduct.value = product
  editForm.value = {
    name: product.name ?? '',
    material_name: product.material_name ?? '',
    process_name: product.process_name ?? '',
    unit: product.unit ?? '',
    pricing_method: product.pricing_method ?? '',
    default_price: product.default_price ?? 0,
    min_charge: product.min_charge ?? 0,
    remark: product.remark ?? '',
  }
  editVisible.value = true
}

async function saveEdit() {
  if (!editingProduct.value) return
  const filled = [editForm.value.name.trim(), editForm.value.material_name.trim(), editForm.value.process_name.trim()].filter(Boolean)
  if (filled.length === 0) {
    ElMessage.warning('请至少填写产品、材质、工艺中的一项')
    return
  }
  savingEdit.value = true
  try {
    await updateProduct(editingProduct.value.id, { ...editForm.value })
    ElMessage.success('产品已更新')
    emit('updated', { ...editingProduct.value, ...editForm.value })
    editVisible.value = false
    editingProduct.value = null
    await fetchProducts()
  } catch {
    ElMessage.error('更新失败')
  } finally {
    savingEdit.value = false
  }
}
</script>

<style scoped>
/* 产品/材质/工艺文本域：滚动条常驻输入框，未满3行灰轨+上下箭头，可滚动时深色滑块浮现。
   根因：Chrome 121+ 设置标准 scrollbar-width/scrollbar-color 会走标准渲染路径，
   macOS 上为 overlay 自动隐藏且压制 ::-webkit-scrollbar，故仅用 webkit 伪元素；
   Firefox 不支持 webkit 伪元素，@supports not 单独给标准属性。 */
:deep(.mp-textarea .el-textarea__inner) {
  overflow-y: scroll;
}
:deep(.mp-textarea .el-textarea__inner::-webkit-scrollbar) {
  width: 12px;
  background: var(--ad-darker);
}
:deep(.mp-textarea .el-textarea__inner::-webkit-scrollbar-track) {
  background: #d8d8d8;
  border-radius: 4px;
}
:deep(.mp-textarea .el-textarea__inner::-webkit-scrollbar-thumb) {
  background-color: var(--ad-text-secondary);
  border: 2px solid #d8d8d8;
  border-radius: 4px;
}
:deep(.mp-textarea .el-textarea__inner::-webkit-scrollbar-button) {
  display: block;
  height: 16px;
  background-color: var(--ad-border);
  background-repeat: no-repeat;
  background-position: center;
}
:deep(.mp-textarea .el-textarea__inner::-webkit-scrollbar-button:vertical:decrement) {
  background-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12'%3E%3Cpath d='M6 2 L11 8 L1 8 Z' fill='%23909999'/%3E%3C/svg%3E");
}
:deep(.mp-textarea .el-textarea__inner::-webkit-scrollbar-button:vertical:increment) {
  background-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12'%3E%3Cpath d='M1 3 L11 3 L6 10 Z' fill='%23909999'/%3E%3C/svg%3E");
}
@supports not selector(::-webkit-scrollbar) {
  :deep(.mp-textarea .el-textarea__inner) {
    scrollbar-width: thin;
    scrollbar-color: #909399 #d8d8d8;
  }
}
</style>

