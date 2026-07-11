<template>
  <div class="page">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- Tab 1: 产品管理 -->
      <el-tab-pane label="产品管理" name="products">
        <div class="tab-content">
          <div class="search-bar">
            <el-input v-model="prod.keyword" placeholder="搜索产品名称" clearable style="width: 300px" @keyup.enter="prod.fetchData" />
            <el-button type="primary" @click="prod.fetchData" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button type="danger" @click="prod.handleCreate">新建产品</el-button>
            </div>
          </div>

          <el-table :data="prod.list" v-loading="prod.loading" stripe style="margin-top: 16px">
            <el-table-column prop="name" label="产品名称" min-width="160" />
            <el-table-column prop="material_name" label="材质" width="120" />
            <el-table-column prop="process_name" label="工艺" width="120" />
            <el-table-column prop="unit" label="单位" width="60" />
            <el-table-column label="默认单价" width="100">
              <template #default="{ row }">¥ {{ row.default_price?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button text type="primary" @click="prod.handleEdit(row as ProductResponse)">编辑</el-button>
                <el-button text type="danger" @click="prod.handleDelete(row as ProductResponse)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="prod.page" v-model:page-size="prod.pageSize"
            :page-sizes="[10, 20, 50, 100]" :total="prod.total"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end" @change="prod.fetchData"
          />

          <el-dialog v-model="prod.dialogVisible" :title="prod.editingId ? '编辑产品' : '新建产品'" width="600px" :close-on-click-modal="false">
            <el-form :model="prod.form" ref="prod.formRef" :rules="prod.rules" label-width="100px">
              <el-form-item label="名称" prop="name"><el-input v-model="prod.form.name" /></el-form-item>
              <el-form-item label="材质">
                <el-select v-model="prod.form.material_id" clearable filterable placeholder="选择材质" style="width: 100%">
                  <el-option v-for="m in prod.materialOptions" :key="m.id" :label="m.name" :value="m.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="工艺">
                <el-select v-model="prod.form.process_id" clearable filterable placeholder="选择工艺" style="width: 100%">
                  <el-option v-for="p in prod.processOptions" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="规格尺寸">
                <div style="display: flex; gap: 8px; width: 100%; flex-wrap: wrap">
                  <el-input-number v-model="prod.form.length" :precision="3" :min="0" placeholder="长" style="width: 100px" />
                  <span style="line-height: 32px; color: var(--ad-text-secondary)">×</span>
                  <el-input-number v-model="prod.form.width" :precision="3" :min="0" placeholder="宽" style="width: 100px" />
                  <span style="line-height: 32px; color: var(--ad-text-secondary)">×</span>
                  <el-input-number v-model="prod.form.height" :precision="3" :min="0" placeholder="高" style="width: 100px" />
                  <span style="line-height: 32px; color: var(--ad-text-secondary); margin: 0 4px">面积</span>
                  <el-input-number v-model="prod.form.area" :precision="3" :min="0" style="width: 100px" />
                  <span style="line-height: 32px; color: var(--ad-text-secondary); margin: 0 4px">数量</span>
                  <el-input-number v-model="prod.form.quantity" :precision="3" :min="0" style="width: 100px" />
                </div>
              </el-form-item>
              <el-form-item label="默认单价"><el-input-number v-model="prod.form.default_price" :precision="2" :min="0" style="width: 100%" /></el-form-item>
              <el-form-item label="最低收费"><el-input-number v-model="prod.form.min_charge" :precision="2" :min="0" style="width: 100%" /></el-form-item>
              <el-form-item label="备注"><el-input v-model="prod.form.remark" type="textarea" /></el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="prod.dialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="prod.saving" @click="prod.handleSave">保存</el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 材质管理 -->
      <el-tab-pane label="材质管理" name="materials">
        <div class="tab-content">
          <div class="search-bar">
            <el-input v-model="mat.keyword" placeholder="搜索材质名称" clearable style="width: 300px" @keyup.enter="mat.fetchData" />
            <el-button type="primary" @click="mat.fetchData" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button type="danger" @click="mat.handleCreate">新建材质</el-button>
            </div>
          </div>

          <el-table :data="mat.list" v-loading="mat.loading" stripe style="margin-top: 16px">
            <el-table-column prop="name" label="材质名称" min-width="160" />
            <el-table-column prop="spec" label="规格" width="120" />
            <el-table-column prop="unit" label="单位" width="60" />
            <el-table-column label="采购价" width="100"><template #default="{ row }">¥ {{ row.purchase_price?.toFixed(2) }}</template></el-table-column>
            <el-table-column label="销售价" width="100"><template #default="{ row }">¥ {{ row.sale_price?.toFixed(2) }}</template></el-table-column>
            <el-table-column label="损耗率" width="80"><template #default="{ row }">{{ row.loss_rate ? (row.loss_rate * 100).toFixed(2) + '%' : '-' }}</template></el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button text type="primary" @click="mat.handleEdit(row as MaterialResponse)">编辑</el-button>
                <el-button text type="danger" @click="mat.handleDelete(row as MaterialResponse)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="mat.page" v-model:page-size="mat.pageSize"
            :page-sizes="[10, 20, 50, 100]" :total="mat.total"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end" @change="mat.fetchData"
          />

          <el-dialog v-model="mat.dialogVisible" :title="mat.editingId ? '编辑材质' : '新建材质'" width="500px" :close-on-click-modal="false">
            <el-form :model="mat.form" label-width="100px">
              <el-form-item label="材质名称"><el-input v-model="mat.form.name" /></el-form-item>
              <el-form-item label="规格"><el-input v-model="mat.form.spec" placeholder="如 1220×2440mm" /></el-form-item>
              <el-form-item label="单位">
                <el-select v-model="mat.form.unit" style="width: 100%">
                  <el-option label="张" value="张" /><el-option label="㎡" value="㎡" />
                  <el-option label="米" value="米" /><el-option label="个" value="个" /><el-option label="kg" value="kg" />
                </el-select>
              </el-form-item>
              <el-form-item label="采购价"><el-input-number v-model="mat.form.purchase_price" :precision="2" :min="0" style="width: 100%" /></el-form-item>
              <el-form-item label="销售价"><el-input-number v-model="mat.form.sale_price" :precision="2" :min="0" style="width: 100%" /></el-form-item>
              <el-form-item label="损耗率"><el-input-number v-model="mat.form.loss_rate" :precision="4" :min="0" :step="0.01" style="width: 100%" /></el-form-item>
              <el-form-item label="备注"><el-input v-model="mat.form.remark" type="textarea" /></el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="mat.dialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="mat.saving" @click="mat.handleSave">保存</el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 工艺管理 -->
      <el-tab-pane label="工艺管理" name="processes">
        <div class="tab-content">
          <div class="search-bar">
            <el-input v-model="proc.keyword" placeholder="搜索工艺名称" clearable style="width: 300px" @keyup.enter="proc.fetchData" />
            <el-button type="primary" @click="proc.fetchData" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button type="danger" @click="proc.handleCreate">新建工艺</el-button>
            </div>
          </div>

          <el-table :data="proc.list" v-loading="proc.loading" stripe style="margin-top: 16px">
            <el-table-column prop="name" label="工艺名称" min-width="160" />
            <el-table-column prop="charge_method" label="计费方式" width="100" />
            <el-table-column label="默认价格" width="100"><template #default="{ row }">¥ {{ row.default_price?.toFixed(2) }}</template></el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button text type="primary" @click="proc.handleEdit(row as ProcessResponse)">编辑</el-button>
                <el-button text type="danger" @click="proc.handleDelete(row as ProcessResponse)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="proc.page" v-model:page-size="proc.pageSize"
            :total="proc.total" layout="total, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end" @change="proc.fetchData"
          />

          <el-dialog v-model="proc.dialogVisible" :title="proc.editingId ? '编辑工艺' : '新建工艺'" width="500px" :close-on-click-modal="false">
            <el-form :model="proc.form" label-width="100px">
              <el-form-item label="工艺名称"><el-input v-model="proc.form.name" /></el-form-item>
              <el-form-item label="计费方式">
                <el-select v-model="proc.form.charge_method" style="width: 100%">
                  <el-option label="固定价" value="fixed" /><el-option label="按面积" value="area" /><el-option label="按数量" value="quantity" />
                </el-select>
              </el-form-item>
              <el-form-item label="默认价格"><el-input-number v-model="proc.form.default_price" :precision="2" :min="0" style="width: 100%" /></el-form-item>
              <el-form-item label="备注"><el-input v-model="proc.form.remark" type="textarea" /></el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="proc.dialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="proc.saving" @click="proc.handleSave">保存</el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>

      <!-- Tab 4: 供应商管理 -->
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
              <template #default="{ row }"><el-tag size="small">{{ supplyTypeLabel(row.supply_type) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button text type="primary" @click="sup.handleEdit(row as SupplierResponse)">编辑</el-button>
                <el-button text type="danger" @click="sup.handleDelete(row as SupplierResponse)">删除</el-button>
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
import { ref, reactive, onMounted } from 'vue'
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

function onTabChange(tab: string) { activeTab.value = tab }

function supplyTypeLabel(val: string | null) {
  const map: Record<string, string> = { material: '材料', processing: '加工', installation: '安装', transport: '运输', other: '其他' }
  return map[val || ''] || val || '-'
}

// ── Products ──
function useProductTab() {
  const loading = ref(false)
  const saving = ref(false)
  const list = ref<ProductResponse[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<string | null>(null)
  const formRef = ref<FormInstance>()
  const materialOptions = ref<{ id: string; name: string }[]>([])
  const processOptions = ref<{ id: string; name: string }[]>([])

  const form = reactive({
    name: '', material_id: '', process_id: '',
    unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0,
    length: undefined as number | undefined, width: undefined as number | undefined,
    height: undefined as number | undefined, area: undefined as number | undefined,
    quantity: undefined as number | undefined, remark: '',
  })
  const rules = { name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }] }

  async function loadOptions() {
    try {
      const [matData, procData] = await Promise.all([
        getMaterials({ page: 1, page_size: 100 }),
        getProcesses({ page: 1, page_size: 100 }),
      ])
      materialOptions.value = matData.items.map((m: MaterialResponse) => ({ id: m.id, name: m.name }))
      processOptions.value = procData.items.map((p: ProcessResponse) => ({ id: p.id, name: p.name }))
    } catch { /* ignore */ }
  }

  async function fetchData() {
    loading.value = true
    try {
      const data = await getProducts({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined })
      list.value = data.items
      total.value = data.total
    } finally { loading.value = false }
  }

  function handleCreate() {
    editingId.value = null
    Object.assign(form, { name: '', material_id: '', process_id: '', unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0, length: undefined, width: undefined, height: undefined, area: undefined, quantity: undefined, remark: '' })
    dialogVisible.value = true
  }

  function handleEdit(row: ProductResponse) {
    editingId.value = row.id
    Object.assign(form, {
      name: row.name, material_id: row.material_id || '', process_id: row.process_id || '',
      length: row.length ?? undefined, width: row.width ?? undefined, height: row.height ?? undefined,
      area: row.area ?? undefined, quantity: row.quantity ?? undefined,
      unit: row.unit, pricing_method: row.pricing_method,
      default_price: row.default_price, min_charge: row.min_charge, remark: row.remark || '',
    })
    dialogVisible.value = true
  }

  async function handleSave() {
    saving.value = true
    try {
      const payload = {
        name: form.name, unit: form.unit, pricing_method: form.pricing_method,
        default_price: form.default_price, min_charge: form.min_charge, remark: form.remark,
        material_id: form.material_id || undefined, process_id: form.process_id || undefined,
        length: form.length ?? undefined, width: form.width ?? undefined,
        height: form.height ?? undefined, area: form.area ?? undefined, quantity: form.quantity ?? undefined,
      }
      if (editingId.value) {
        await updateProduct(editingId.value, payload)
        ElMessage.success('更新成功')
      } else {
        await createProduct(payload)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchData()
    } finally { saving.value = false }
  }

  async function handleDelete(row: ProductResponse) {
    try {
      await ElMessageBox.confirm(`确认删除产品 "${row.name}"？`, '确认', { type: 'warning' })
      await deleteProduct(row.id)
      ElMessage.success('已删除')
      fetchData()
    } catch { /* ignore */ }
  }

  return { loading, saving, list, total, page, pageSize, keyword, dialogVisible, editingId, formRef, form, rules, materialOptions, processOptions, loadOptions, fetchData, handleCreate, handleEdit, handleSave, handleDelete }
}

const prod = useProductTab()

// ── Materials ──
function useMaterialTab() {
  const loading = ref(false)
  const saving = ref(false)
  const list = ref<MaterialResponse[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<string | null>(null)
  const form = reactive({ name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0, remark: '' })

  async function fetchData() {
    loading.value = true
    try {
      const data = await getMaterials({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined })
      list.value = data.items
      total.value = data.total
    } finally { loading.value = false }
  }

  function handleCreate() {
    editingId.value = null
    Object.assign(form, { name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0, remark: '' })
    dialogVisible.value = true
  }

  function handleEdit(row: MaterialResponse) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, spec: row.spec || '', unit: row.unit, purchase_price: row.purchase_price, sale_price: row.sale_price, loss_rate: row.loss_rate, remark: row.remark || '' })
    dialogVisible.value = true
  }

  async function handleSave() {
    saving.value = true
    try {
      const payload = { name: form.name, spec: form.spec || undefined, unit: form.unit, purchase_price: form.purchase_price, sale_price: form.sale_price, loss_rate: form.loss_rate, remark: form.remark }
      if (editingId.value) {
        await updateMaterial(editingId.value, payload)
        ElMessage.success('更新成功')
      } else {
        await createMaterial(payload)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchData()
    } finally { saving.value = false }
  }

  async function handleDelete(row: MaterialResponse) {
    try {
      await ElMessageBox.confirm(`确认删除材质 "${row.name}"？`, '确认', { type: 'warning' })
      await deleteMaterial(row.id)
      ElMessage.success('已删除')
      fetchData()
    } catch { /* ignore */ }
  }

  return { loading, saving, list, total, page, pageSize, keyword, dialogVisible, editingId, form, fetchData, handleCreate, handleEdit, handleSave, handleDelete }
}

const mat = useMaterialTab()

// ── Processes ──
function useProcessTab() {
  const loading = ref(false)
  const saving = ref(false)
  const list = ref<ProcessResponse[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const keyword = ref('')
  const dialogVisible = ref(false)
  const editingId = ref<string | null>(null)
  const form = reactive({ name: '', charge_method: 'fixed', default_price: 0, remark: '' })

  async function fetchData() {
    loading.value = true
    try {
      const data = await getProcesses({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined })
      list.value = data.items
      total.value = data.total
    } finally { loading.value = false }
  }

  function handleCreate() {
    editingId.value = null
    Object.assign(form, { name: '', charge_method: 'fixed', default_price: 0, remark: '' })
    dialogVisible.value = true
  }

  function handleEdit(row: ProcessResponse) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, charge_method: row.charge_method, default_price: row.default_price, remark: row.remark || '' })
    dialogVisible.value = true
  }

  async function handleSave() {
    saving.value = true
    try {
      const payload = { name: form.name, charge_method: form.charge_method, default_price: form.default_price, remark: form.remark }
      if (editingId.value) {
        await updateProcess(editingId.value, payload)
        ElMessage.success('更新成功')
      } else {
        await createProcess(payload)
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
    } catch { /* ignore */ }
  }

  return { loading, saving, list, total, page, pageSize, keyword, dialogVisible, editingId, form, fetchData, handleCreate, handleEdit, handleSave, handleDelete }
}

const proc = useProcessTab()

// ── Suppliers ──
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
      if (editingId.value) { await updateSupplier(editingId.value, form) }
      else { await createSupplier(form) }
      ElMessage.success(editingId.value ? '更新成功' : '创建成功')
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
  prod.fetchData()
  prod.loadOptions()
})
</script>

<style scoped>
.page { padding: 0; }
.tab-content { margin-top: 16px; }
.search-bar { display: flex; align-items: center; margin-bottom: 16px; }
</style>
