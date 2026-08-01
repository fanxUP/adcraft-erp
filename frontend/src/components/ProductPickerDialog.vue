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
      width="420px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form :model="editForm" label-width="80px">
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
import ProductCreateDialog from './ProductCreateDialog.vue'
import type { ProductResponse } from '@/types/api'

const props = defineProps<{ modelValue: boolean; customerId?: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  selected: [product: ProductResponse]
}>()

const UNIT_OPTIONS = ['项', '㎡', '米', '个', '套']
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

const createVisible = ref(false)
const editVisible = ref(false)
const editingProduct = ref<ProductResponse | null>(null)
const savingEdit = ref(false)
const editForm = ref({
  unit: '',
  pricing_method: '',
  default_price: 0,
  min_charge: 0,
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
}

function onRowClick(row: ProductResponse) {
  emit('selected', row)
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
    unit: product.unit ?? '',
    pricing_method: product.pricing_method ?? '',
    default_price: product.default_price ?? 0,
    min_charge: product.min_charge ?? 0,
  }
  editVisible.value = true
}

async function saveEdit() {
  if (!editingProduct.value) return
  savingEdit.value = true
  try {
    await updateProduct(editingProduct.value.id, { ...editForm.value })
    ElMessage.success('产品已更新')
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
