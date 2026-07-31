<template>
  <div class="page">
    <div class="page-header">
      <h2>库存管理</h2>
      <div>
        <el-button type="primary" @click="showStockRecords = !showStockRecords">
          {{ showStockRecords ? '查看库存' : '查看记录' }}
        </el-button>
        <el-button type="danger" @click="handleCreate">新建物料</el-button>
      </div>
    </div>

    <!-- Inventory Items -->
    <template v-if="!showStockRecords">
      <div class="search-bar">
        <el-input v-model="keyword" placeholder="搜索物料名称" clearable style="width: 240px" @keyup.enter="fetchItems" />
        <el-select v-model="category" placeholder="分类" clearable style="width: 160px; margin-left: 12px">
          <el-option label="原材料" value="raw_material" />
          <el-option label="半成品" value="semi_finished" />
          <el-option label="耗材" value="consumable" />
        </el-select>
        <el-button type="primary" @click="fetchItems" style="margin-left: 12px">搜索</el-button>
      </div>

      <el-table :data="items" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无库存物料">
        <el-table-column prop="material_name" label="物料名称" min-width="160" />
        <el-table-column label="分类" width="80">
          <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column prop="spec" label="规格" width="160" />
        <el-table-column prop="quantity" label="库存数量" width="120" align="right">
          <template #default="{ row }">
            <el-tag :type="row.quantity <= row.min_quantity ? 'danger' : 'success'" size="small">
              {{ row.quantity }} {{ row.material_unit || '' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="min_quantity" label="最低库存" width="100" align="right">
          <template #default="{ row }">{{ row.min_quantity }} {{ row.material_unit || '' }}</template>
        </el-table-column>
        <el-table-column prop="unit_cost" label="单价" width="100" align="right">
          <template #default="{ row }">¥{{ row.unit_cost?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button text type="success" @click="handleStockIn(row as InventoryItemResponse)">入库</el-button>
            <el-button text type="warning" @click="handleStockOut(row as InventoryItemResponse)">出库</el-button>
            <el-button text type="primary" @click="handleEdit(row as InventoryItemResponse)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="itemPage"
        v-model:page-size="itemPageSize"
        :total="itemTotal"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @change="fetchItems"
      />
    </template>

    <!-- Stock Records -->
    <template v-else>
      <el-table :data="records" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无出入库记录">
        <el-table-column prop="item_name" label="物料" min-width="160" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.record_type === 'in' ? 'success' : 'warning'" size="small">
              {{ row.record_type === 'in' ? '入库' : '出库' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="100" align="right" />
        <el-table-column prop="unit_cost" label="单价" width="100" align="right">
          <template #default="{ row }">¥{{ row.unit_cost?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="total_cost" label="总金额" width="120" align="right">
          <template #default="{ row }">¥{{ row.total_cost?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="operated_at" label="操作时间" width="180" />
      </el-table>

      <el-pagination
        v-model:current-page="recordPage"
        v-model:page-size="recordPageSize"
        :total="recordTotal"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @change="fetchRecords"
      />
    </template>

    <!-- Create / Edit Item Dialog -->
    <el-dialog v-model="itemDialogVisible" :title="editingItemId ? '编辑物料' : '新建物料'" width="500px" :close-on-click-modal="false">
      <el-form ref="itemFormRef" :model="itemForm" :rules="itemRules" label-width="100px">
        <el-form-item label="物料名称" prop="material_name">
          <el-input v-model="itemForm.material_name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="itemForm.category" clearable style="width: 100%">
            <el-option label="原材料" value="raw_material" />
            <el-option label="半成品" value="semi_finished" />
            <el-option label="耗材" value="consumable" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="itemForm.spec" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="itemForm.material_unit" style="width: 120px" />
        </el-form-item>
        <el-form-item label="初始数量">
          <el-input-number v-model="itemForm.quantity" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最低库存">
          <el-input-number v-model="itemForm.min_quantity" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="itemForm.unit_cost" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="itemForm.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSaveItem">保存</el-button>
      </template>
    </el-dialog>

    <!-- Stock In / Out Dialog -->
    <el-dialog v-model="stockDialogVisible" :title="stockType === 'in' ? '入库' : '出库'" width="400px" :close-on-click-modal="false">
      <el-form ref="stockFormRef" :model="stockForm" :rules="stockRules" label-width="80px">
        <el-form-item label="物料">
          <span>{{ selectedItem?.material_name }}</span>
        </el-form-item>
        <el-form-item label="当前库存">
          <span>{{ selectedItem?.quantity }} {{ selectedItem?.material_unit || '' }}</span>
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="stockForm.quantity" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="stockType === 'in'" label="单价">
          <el-input-number v-model="stockForm.unit_cost" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="stockForm.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stockDialogVisible = false">取消</el-button>
        <el-button :type="stockType === 'in' ? 'success' : 'warning'" :loading="saving" @click="handleStockSave">
          确认{{ stockType === 'in' ? '入库' : '出库' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import {
  getInventoryItems, createInventoryItem, updateInventoryItem,
  getStockRecords, stockIn, stockOut,
} from '@/api/inventory'
import type { InventoryItemResponse, StockRecordResponse } from '@/types/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const showStockRecords = ref(false)

// Items
const items = ref<InventoryItemResponse[]>([])
const itemTotal = ref(0)
const itemPage = ref(1)
const itemPageSize = ref(20)
const keyword = ref('')
const category = ref('')
const itemDialogVisible = ref(false)
const editingItemId = ref<string | null>(null)
const itemForm = reactive({
  material_name: '', category: '', spec: '', material_unit: '',
  quantity: 0, min_quantity: 0, unit_cost: 0, remark: '',
})
const itemRules = { material_name: [{ required: true, message: '请输入物料名称', trigger: 'blur' }] }

// Records
const records = ref<StockRecordResponse[]>([])
const recordTotal = ref(0)
const recordPage = ref(1)
const recordPageSize = ref(20)

// Stock in/out
const stockDialogVisible = ref(false)
const stockType = ref<'in' | 'out'>('in')
const selectedItem = ref<InventoryItemResponse | null>(null)
const stockForm = reactive({ quantity: 0, unit_cost: 0, remark: '' })
const stockRules = {
  quantity: [{ required: true, type: 'number', min: 0.01, message: '请输入数量', trigger: 'blur' }],
}

function categoryLabel(val: string | null) {
  const map: Record<string, string> = { raw_material: '原材料', semi_finished: '半成品', consumable: '耗材' }
  return map[val || ''] || val || '-'
}

async function fetchItems() {
  loading.value = true
  try {
    const data = await getInventoryItems({
      page: itemPage.value, page_size: itemPageSize.value,
      keyword: keyword.value || undefined,
      category: category.value || undefined,
    })
    items.value = data.items
    itemTotal.value = data.total
  } finally {
    loading.value = false
  }
}

async function fetchRecords() {
  loading.value = true
  try {
    const data = await getStockRecords({ page: recordPage.value, page_size: recordPageSize.value })
    records.value = data.items
    recordTotal.value = data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingItemId.value = null
  Object.assign(itemForm, { material_name: '', category: '', spec: '', material_unit: '', quantity: 0, min_quantity: 0, unit_cost: 0, remark: '' })
  itemDialogVisible.value = true
}

function handleEdit(row: InventoryItemResponse) {
  editingItemId.value = row.id
  Object.assign(itemForm, {
    material_name: row.material_name, category: row.category, spec: row.spec,
    material_unit: row.material_unit, quantity: row.quantity, min_quantity: row.min_quantity,
    unit_cost: row.unit_cost, remark: row.remark,
  })
  itemDialogVisible.value = true
}

async function handleSaveItem() {
  saving.value = true
  try {
    if (editingItemId.value) {
      await updateInventoryItem(editingItemId.value, itemForm)
      ElMessage.success('更新成功')
    } else {
      await createInventoryItem(itemForm)
      ElMessage.success('创建成功')
    }
    itemDialogVisible.value = false
    await fetchItems()
  } finally {
    saving.value = false
  }
}

function handleStockIn(row: InventoryItemResponse) {
  stockType.value = 'in'
  selectedItem.value = row
  Object.assign(stockForm, { quantity: 0, unit_cost: row.unit_cost || 0, remark: '' })
  stockDialogVisible.value = true
}

function handleStockOut(row: InventoryItemResponse) {
  stockType.value = 'out'
  selectedItem.value = row
  Object.assign(stockForm, { quantity: 0, unit_cost: 0, remark: '' })
  stockDialogVisible.value = true
}

async function handleStockSave() {
  if (!selectedItem.value) return
  saving.value = true
  try {
    const payload = {
      item_id: selectedItem.value.id,
      record_type: stockType.value,
      quantity: stockForm.quantity,
      unit_cost: stockType.value === 'in' ? stockForm.unit_cost : 0,
      remark: stockForm.remark || undefined,
    }
    if (stockType.value === 'in') {
      await stockIn(payload)
    } else {
      await stockOut(payload)
    }
    ElMessage.success(stockType.value === 'in' ? '入库成功' : '出库成功')
    stockDialogVisible.value = false
    await fetchItems()
  } finally {
    saving.value = false
  }
}

onMounted(fetchItems)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
