<template>
  <div class="page">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="产品管理" name="products">
        <div class="tab-content">
          <div class="search-bar">
            <el-select v-model="itemType" placeholder="全部类型" clearable style="width: 140px" @change="fetchAll">
              <el-option label="产品" value="product" />
              <el-option label="材质" value="material" />
              <el-option label="工艺" value="process" />
            </el-select>
            <el-input v-model="keyword" placeholder="搜索名称" clearable style="width: 240px; margin-left: 12px" @keyup.enter="fetchAll" />
            <el-button type="primary" @click="fetchAll" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button type="danger" @click="handleCreate">新建</el-button>
            </div>
          </div>

          <el-table :data="unifiedList" v-loading="loading" stripe style="margin-top: 16px">
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row._type === 'product' ? 'primary' : row._type === 'material' ? 'success' : 'warning'" size="small">
                  {{ row._type === 'product' ? '产品' : row._type === 'material' ? '材质' : '工艺' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column label="规格/单位" width="120">
              <template #default="{ row }">
                <span v-if="row._type === 'material'">{{ row.spec || '-' }}</span>
                <span v-else>{{ row.unit || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="单价" width="120">
              <template #default="{ row }">
                <span v-if="row._type === 'material'">¥ {{ row.sale_price?.toFixed(2) }}</span>
                <span v-else>¥ {{ row.default_price?.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="计价方式" width="100" v-if="showPricingColumn">
              <template #default="{ row }">{{ pricingLabel(row.pricing_method) }}</template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="page" v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]" :total="total"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end" @change="fetchAll"
          />

          <el-dialog v-model="dialogVisible" :title="editingId ? '编辑' : '新建'" width="600px" :close-on-click-modal="false">
            <el-form :model="form" ref="formRef" :rules="rules" label-width="100px">
              <el-form-item label="类型" prop="_type">
                <el-select v-model="form._type" :disabled="!!editingId" style="width: 100%">
                  <el-option label="产品" value="product" />
                  <el-option label="材质" value="material" />
                  <el-option label="工艺" value="process" />
                </el-select>
              </el-form-item>
              <el-form-item label="名称" prop="name">
                <el-input v-model="form.name" />
              </el-form-item>

              <!-- 产品专用字段 -->
              <template v-if="form._type === 'product'">
                <el-form-item label="材质">
                  <el-select v-model="form.material_id" clearable filterable placeholder="选择材质" style="width: 100%">
                    <el-option v-for="m in materialOptions" :key="m.id" :label="m.name" :value="m.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="工艺">
                  <el-select v-model="form.process_id" clearable filterable placeholder="选择工艺" style="width: 100%">
                    <el-option v-for="p in processOptions" :key="p.id" :label="p.name" :value="p.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="规格尺寸">
                  <div style="display: flex; gap: 8px; width: 100%; flex-wrap: wrap">
                    <el-input-number v-model="form.length" :precision="3" :min="0" placeholder="长" style="width: 100px" />
                    <span style="line-height: 32px; color: var(--ad-text-secondary)">×</span>
                    <el-input-number v-model="form.width" :precision="3" :min="0" placeholder="宽" style="width: 100px" />
                    <span style="line-height: 32px; color: var(--ad-text-secondary)">×</span>
                    <el-input-number v-model="form.height" :precision="3" :min="0" placeholder="高" style="width: 100px" />
                    <span style="line-height: 32px; color: var(--ad-text-secondary); margin: 0 4px">面积</span>
                    <el-input-number v-model="form.area" :precision="3" :min="0" placeholder="面积" style="width: 100px" />
                    <span style="line-height: 32px; color: var(--ad-text-secondary); margin: 0 4px">数量</span>
                    <el-input-number v-model="form.quantity" :precision="3" :min="0" placeholder="数量" style="width: 100px" />
                  </div>
                </el-form-item>
                <el-form-item label="默认单价">
                  <el-input-number v-model="form.default_price" :precision="2" :min="0" style="width: 100%" />
                </el-form-item>
                <el-form-item label="最低收费">
                  <el-input-number v-model="form.min_charge" :precision="2" :min="0" style="width: 100%" />
                </el-form-item>
              </template>

              <!-- 材质专用字段 -->
              <template v-if="form._type === 'material'">
                <el-form-item label="规格">
                  <el-input v-model="form.spec" placeholder="如 1220×2440mm" />
                </el-form-item>
                <el-form-item label="单位">
                  <el-select v-model="form.unit" style="width: 100%">
                    <el-option label="张" value="张" /><el-option label="㎡" value="㎡" />
                    <el-option label="米" value="米" /><el-option label="个" value="个" /><el-option label="kg" value="kg" />
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
              </template>

              <!-- 工艺专用字段 -->
              <template v-if="form._type === 'process'">
                <el-form-item label="计费方式">
                  <el-select v-model="form.charge_method" style="width: 100%">
                    <el-option label="固定价" value="fixed" /><el-option label="按面积" value="area" /><el-option label="按数量" value="quantity" />
                  </el-select>
                </el-form-item>
                <el-form-item label="默认价格">
                  <el-input-number v-model="form.default_price" :precision="2" :min="0" style="width: 100%" />
                </el-form-item>
              </template>

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
      </el-tab-pane>

      <el-tab-pane label="供应商管理" name="suppliers">
        <div class="tab-content">
          <div class="search-bar">
            <el-input v-model="sup.keyword" placeholder="搜索供应商名称" clearable style="width: 300px" @keyup.enter="sup.fetchData" />
            <el-button type="primary" @click="sup.fetchData" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button type="danger" @click="sup.handleCreate">新建供应商</el-button>
            </div>
          </div>

          <el-table :data="sup.list" v-loading="sup.loading" stripe style="margin-top: 16px">
            <el-table-column prop="supplier_no" label="编号" width="150" />
            <el-table-column prop="name" label="供应商名称" min-width="160" />
            <el-table-column prop="contact_person" label="联系人" width="120" />
            <el-table-column prop="phone" label="电话" width="140" />
            <el-table-column label="供应类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ supplyTypeLabel(row.supply_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button text type="primary" @click="sup.handleEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="sup.handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="sup.page" v-model:page-size="sup.pageSize"
            :page-sizes="[10, 20, 50, 100]" :total="sup.total"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end" @change="sup.fetchData"
          />

          <el-dialog v-model="sup.dialogVisible" :title="sup.editingId ? '编辑供应商' : '新建供应商'" width="550px" :close-on-click-modal="false">
            <el-form ref="sup.formRef" :model="sup.form" :rules="sup.rules" label-width="100px">
              <el-form-item label="名称" prop="name"><el-input v-model="sup.form.name" /></el-form-item>
              <el-form-item label="联系人"><el-input v-model="sup.form.contact_person" /></el-form-item>
              <el-form-item label="电话"><el-input v-model="sup.form.phone" /></el-form-item>
              <el-form-item label="地址"><el-input v-model="sup.form.address" /></el-form-item>
              <el-form-item label="供应类型">
                <el-select v-model="sup.form.supply_type" clearable style="width: 100%">
                  <el-option label="材料" value="material" /><el-option label="加工" value="processing" />
                  <el-option label="安装" value="installation" /><el-option label="运输" value="transport" /><el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-form-item label="银行账号"><el-input v-model="sup.form.bank_account" /></el-form-item>
              <el-form-item label="备注"><el-input v-model="sup.form.remark" type="textarea" /></el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="sup.dialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="sup.saving" @click="sup.handleSave">保存</el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { getProducts, createProduct, updateProduct, deleteProduct } from '@/api/products'
import { getMaterials, createMaterial, updateMaterial, deleteMaterial } from '@/api/products'
import { getProcesses, createProcess, updateProcess, deleteProcess } from '@/api/products'
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier } from '@/api/suppliers'
import type { ProductResponse, MaterialResponse, ProcessResponse, SupplierResponse } from '@/types/api'

const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'products')

type UnifiedItem = (ProductResponse | MaterialResponse | ProcessResponse) & { _type: 'product' | 'material' | 'process' }

const loading = ref(false)
const saving = ref(false)
const list = ref<UnifiedItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const itemType = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const editingType = ref<'product' | 'material' | 'process' | null>(null)
const formRef = ref<FormInstance>()

const materialOptions = ref<{ id: string; name: string }[]>([])
const processOptions = ref<{ id: string; name: string }[]>([])

async function loadMaterialProcessOptions() {
  try {
    const [matData, procData] = await Promise.all([
      getMaterials({ page: 1, page_size: 100 }),
      getProcesses({ page: 1, page_size: 100 }),
    ])
    materialOptions.value = matData.items.map((m: MaterialResponse) => ({ id: m.id, name: m.name }))
    processOptions.value = procData.items.map((p: ProcessResponse) => ({ id: p.id, name: p.name }))
  } catch { /* ignore */ }
}

const form = reactive({
  _type: 'product' as 'product' | 'material' | 'process',
  name: '',
  // Product
  material_id: '',
  process_id: '',
  unit: '项',
  pricing_method: 'quantity',
  default_price: 0,
  min_charge: 0,
  length: undefined as number | undefined,
  width: undefined as number | undefined,
  height: undefined as number | undefined,
  area: undefined as number | undefined,
  quantity: undefined as number | undefined,
  // Material
  spec: '',
  purchase_price: 0,
  sale_price: 0,
  loss_rate: 0,
  // Process
  charge_method: 'fixed',
  // Common
  remark: '',
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  _type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

const showPricingColumn = computed(() => {
  return list.value.some(r => r._type === 'product')
})

function onTabChange(tab: string) {
  activeTab.value = tab
}

function pricingLabel(m: string) {
  const map: Record<string, string> = { area: '按面积', quantity: '按数量', length: '按长度', word_count: '按字数' }
  return map[m] || m
}

function supplyTypeLabel(val: string | null) {
  const map: Record<string, string> = { material: '材料', processing: '加工', installation: '安装', transport: '运输', other: '其他' }
  return map[val || ''] || val || '-'
}

async function fetchAll() {
  loading.value = true
  try {
    const kw = keyword.value || undefined
    const p = page.value
    const ps = pageSize.value
    type FetchResult = { items: UnifiedItem[]; total: number; type: 'product' | 'material' | 'process' }
    const promises: Promise<FetchResult>[] = []

    if (!itemType.value || itemType.value === 'product') {
      promises.push(getProducts({ page: p, page_size: ps, keyword: kw }).then(r => ({ items: r.items.map(i => ({ ...i, _type: 'product' as const })), total: r.total, type: 'product' as const })))
    }
    if (!itemType.value || itemType.value === 'material') {
      promises.push(getMaterials({ page: p, page_size: ps, keyword: kw }).then(r => ({ items: r.items.map(i => ({ ...i, _type: 'material' as const })), total: r.total, type: 'material' as const })))
    }
    if (!itemType.value || itemType.value === 'process') {
      promises.push(getProcesses({ page: p, page_size: ps, keyword: kw }).then(r => ({ items: r.items.map(i => ({ ...i, _type: 'process' as const })), total: r.total, type: 'process' as const })))
    }

    const results = await Promise.all(promises)
    const all: UnifiedItem[] = []
    let maxTotal = 0

    for (const r of results) {
      all.push(...r.items)
      maxTotal = Math.max(maxTotal, r.total)
    }

    // Sort by created_at desc then name
    all.sort((a, b) => ((b.created_at || '').localeCompare(a.created_at || '')) || a.name.localeCompare(b.name))

    list.value = all
    total.value = maxTotal
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingId.value = null
  editingType.value = null
  Object.assign(form, {
    _type: 'product', name: '',
    material_id: '', process_id: '', unit: '项', pricing_method: 'quantity',
    default_price: 0, min_charge: 0, length: undefined, width: undefined,
    height: undefined, area: undefined, quantity: undefined,
    spec: '', purchase_price: 0, sale_price: 0, loss_rate: 0,
    charge_method: 'fixed', remark: '',
  })
  dialogVisible.value = true
}

function handleEdit(row: UnifiedItem) {
  editingId.value = row.id
  editingType.value = row._type
  form._type = row._type
  form.name = row.name
  form.remark = 'remark' in row ? (row as Record<string, unknown>).remark as string || '' : ''

  if (row._type === 'product') {
    const p = row as ProductResponse
    form.material_id = p.material_id || ''
    form.process_id = p.process_id || ''
    form.length = p.length ?? undefined
    form.width = p.width ?? undefined
    form.height = p.height ?? undefined
    form.area = p.area ?? undefined
    form.quantity = p.quantity ?? undefined
    form.unit = p.unit
    form.pricing_method = p.pricing_method
    form.default_price = p.default_price
    form.min_charge = p.min_charge
  } else if (row._type === 'material') {
    const m = row as MaterialResponse
    form.spec = m.spec || ''
    form.unit = m.unit
    form.purchase_price = m.purchase_price
    form.sale_price = m.sale_price
    form.loss_rate = m.loss_rate
  } else if (row._type === 'process') {
    const pr = row as ProcessResponse
    form.charge_method = pr.charge_method
    form.default_price = pr.default_price
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name) {
    ElMessage.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    const t = form._type
    if (t === 'product') {
      const payload: Record<string, unknown> = {
        name: form.name,
        unit: form.unit,
        pricing_method: form.pricing_method,
        default_price: form.default_price,
        min_charge: form.min_charge,
        remark: form.remark,
        material_id: form.material_id || undefined,
        process_id: form.process_id || undefined,
        length: form.length ?? undefined,
        width: form.width ?? undefined,
        height: form.height ?? undefined,
        area: form.area ?? undefined,
        quantity: form.quantity ?? undefined,
      }
      if (editingId.value) {
        await updateProduct(editingId.value, payload)
      } else {
        await createProduct(payload)
      }
    } else if (t === 'material') {
      const payload = { name: form.name, spec: form.spec || undefined, unit: form.unit, purchase_price: form.purchase_price, sale_price: form.sale_price, loss_rate: form.loss_rate, remark: form.remark }
      if (editingId.value) {
        await updateMaterial(editingId.value, payload)
      } else {
        await createMaterial(payload)
      }
    } else if (t === 'process') {
      const payload = { name: form.name, charge_method: form.charge_method, default_price: form.default_price, remark: form.remark }
      if (editingId.value) {
        await updateProcess(editingId.value, payload)
      } else {
        await createProcess(payload)
      }
    }
    ElMessage.success(editingId.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    fetchAll()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: UnifiedItem) {
  const typeLabel = row._type === 'product' ? '产品' : row._type === 'material' ? '材质' : '工艺'
  try {
    await ElMessageBox.confirm(`确认删除${typeLabel} "${row.name}"？`, '确认', { type: 'warning' })
    if (row._type === 'product') await deleteProduct(row.id)
    else if (row._type === 'material') await deleteMaterial(row.id)
    else if (row._type === 'process') await deleteProcess(row.id)
    ElMessage.success('已删除')
    fetchAll()
  } catch { /* ignore */ }
}

// ── Suppliers (same as before) ──
function useSupplierTab() {
  const loading = ref(false)
  const saving = ref(false)
  const list = ref<SupplierResponse[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<string | null>(null)
  const formRef = ref()
  const form = reactive({ name: '', contact_person: '', phone: '', address: '', supply_type: '', bank_account: '', remark: '' })
  const rules = { name: [{ required: true, message: '请输入供应商名称', trigger: 'blur' }] }

  async function fetchData() {
    loading.value = true
    try {
      const data = await getSuppliers({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined })
      list.value = data.items
      total.value = data.total
    } finally { loading.value = false }
  }
  function handleCreate() {
    editingId.value = null
    Object.assign(form, { name: '', contact_person: '', phone: '', address: '', supply_type: '', bank_account: '', remark: '' })
    dialogVisible.value = true
  }
  function handleEdit(row: SupplierResponse) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, contact_person: row.contact_person, phone: row.phone, address: row.address, supply_type: row.supply_type, bank_account: row.bank_account, remark: row.remark })
    dialogVisible.value = true
  }
  async function handleSave() {
    saving.value = true
    try {
      if (editingId.value) {
        await updateSupplier(editingId.value, form)
        ElMessage.success('更新成功')
      } else {
        await createSupplier(form)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchData()
    } finally { saving.value = false }
  }
  async function handleDelete(row: SupplierResponse) {
    try {
      await ElMessageBox.confirm(`确认删除供应商 "${row.name}"？`, '确认', { type: 'warning' })
      await deleteSupplier(row.id)
      ElMessage.success('已删除')
      fetchData()
    } catch { /* ignore */ }
  }
  return { loading, saving, list, total, page, pageSize, keyword, dialogVisible, editingId, formRef, form, rules, fetchData, handleCreate, handleEdit, handleSave, handleDelete }
}

const sup = useSupplierTab()

onMounted(() => {
  fetchAll()
  loadMaterialProcessOptions()
})
</script>

<style scoped>
.page { padding: 0; }
.tab-content { margin-top: 16px; }
.search-bar { display: flex; align-items: center; margin-bottom: 16px; }
</style>
