<template>
  <div class="page">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="产品管理" name="products">
        <div class="tab-content">
          <div class="search-bar">
            <el-input v-model="prod.keyword" placeholder="搜索产品名称" clearable style="width: 300px" @keyup.enter="prod.fetchData" />
            <el-button type="primary" @click="prod.fetchData" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button @click="prod.importDialogVisible = true">导入</el-button>
              <el-button type="danger" @click="prod.handleCreate">新建产品</el-button>
            </div>
          </div>

          <el-table :data="prod.list" v-loading="prod.loading" stripe style="margin-top: 16px">
            <el-table-column prop="name" label="产品名称" min-width="180" />
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column label="计价方式" width="100">
              <template #default="{ row }">{{ pricingLabel(row.pricing_method) }}</template>
            </el-table-column>
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
                <el-button text type="primary" @click="prod.handleEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="prod.handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="prod.page" v-model:page-size="prod.pageSize"
            :page-sizes="[10, 20, 50, 100]" :total="prod.total"
            layout="total, sizes, prev, pager, next"
            style="margin-top: 16px; justify-content: flex-end" @change="prod.fetchData"
          />

          <el-dialog v-model="prod.dialogVisible" :title="prod.editingId ? '编辑产品' : '新建产品'" width="500px" :close-on-click-modal="false">
            <el-form :model="prod.form" label-width="100px">
              <el-form-item label="产品名称"><el-input v-model="prod.form.name" /></el-form-item>
              <el-form-item label="单位">
                <el-select v-model="prod.form.unit" style="width: 100%">
                  <el-option label="项" value="项" /><el-option label="㎡" value="㎡" />
                  <el-option label="米" value="米" /><el-option label="个" value="个" /><el-option label="套" value="套" />
                </el-select>
              </el-form-item>
              <el-form-item label="计价方式">
                <el-select v-model="prod.form.pricing_method" style="width: 100%">
                  <el-option label="按面积" value="area" /><el-option label="按数量" value="quantity" />
                  <el-option label="按长度" value="length" /><el-option label="按字数" value="word_count" />
                </el-select>
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

          <el-dialog v-model="prod.importDialogVisible" title="导入产品" width="520px" :close-on-click-modal="false">
            <div style="margin-bottom: 16px; font-size: 13px; color: var(--ad-text-secondary)">
              <p>支持 .xlsx / .xls 格式（<span style="color: #f56c6c">*</span>为必填）：</p>
              <el-table :data="prod.templateColumns" border size="small" style="margin: 12px 0">
                <el-table-column prop="name" label="列名" width="120" />
                <el-table-column prop="desc" label="说明" />
                <el-table-column label="必填" width="60">
                  <template #default="{ row }"><span v-if="row.required" style="color: #f56c6c">*</span></template>
                </el-table-column>
              </el-table>
              <el-table :data="prod.sampleData" border size="small" style="margin: 8px 0">
                <el-table-column prop="col1" label="产品名称" /><el-table-column prop="col2" label="单位" />
                <el-table-column prop="col3" label="计价方式" /><el-table-column prop="col4" label="默认价格" />
              </el-table>
            </div>
            <el-upload ref="prod.uploadRef" accept=".xlsx,.xls" :auto-upload="false" :limit="1" :on-change="prod.handleFileChange" :on-exceed="() => ElMessage.warning('只能上传一个文件')">
              <template #trigger><el-button type="primary">选择文件</el-button></template>
              <template #tip><div class="el-upload__tip">仅支持 .xlsx / .xls 文件</div></template>
            </el-upload>
            <div v-if="prod.importResult" style="margin-top: 16px">
              <el-alert :title="`导入完成：成功 ${prod.importResult.succeeded} 条，失败 ${prod.importResult.failed} 条`" :type="prod.importResult.failed > 0 ? 'warning' : 'success'" show-icon />
              <el-table v-if="prod.importResult.errors?.length" :data="prod.importResult.errors" border size="small" style="margin-top: 8px" max-height="200px">
                <el-table-column prop="row" label="行号" width="60" /><el-table-column prop="message" label="错误信息" />
              </el-table>
            </div>
            <template #footer>
              <el-button @click="prod.importDialogVisible = false">关闭</el-button>
              <el-button type="danger" :loading="prod.importing" :disabled="!prod.importFile" @click="prod.handleImport">开始导入</el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>

      <el-tab-pane label="材质管理" name="materials">
        <div class="tab-content">
          <div class="search-bar">
            <el-input v-model="mat.keyword" placeholder="搜索材质名称" clearable style="width: 300px" @keyup.enter="mat.fetchData" />
            <el-button type="primary" @click="mat.fetchData" style="margin-left: 12px">搜索</el-button>
            <div style="margin-left: auto">
              <el-button @click="mat.importDialogVisible = true">导入</el-button>
              <el-button type="danger" @click="mat.handleCreate">新建材质</el-button>
            </div>
          </div>

          <el-table :data="mat.list" v-loading="mat.loading" stripe style="margin-top: 16px">
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
                <el-button text type="primary" @click="mat.handleEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="mat.handleDelete(row)">删除</el-button>
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
            </el-form>
            <template #footer>
              <el-button @click="mat.dialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="mat.saving" @click="mat.handleSave">保存</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="mat.importDialogVisible" title="导入材质" width="520px" :close-on-click-modal="false">
            <div style="margin-bottom: 16px; font-size: 13px; color: var(--ad-text-secondary)">
              <p>支持 .xlsx / .xls 格式（<span style="color: #f56c6c">*</span>为必填）：</p>
              <el-table :data="mat.templateColumns" border size="small" style="margin: 12px 0">
                <el-table-column prop="name" label="列名" width="120" />
                <el-table-column prop="desc" label="说明" />
                <el-table-column label="必填" width="60">
                  <template #default="{ row }"><span v-if="row.required" style="color: #f56c6c">*</span></template>
                </el-table-column>
              </el-table>
              <el-table :data="mat.sampleData" border size="small" style="margin: 8px 0">
                <el-table-column prop="col1" label="材质名称" /><el-table-column prop="col2" label="规格" />
                <el-table-column prop="col3" label="单位" /><el-table-column prop="col4" label="采购价" /><el-table-column prop="col5" label="销售价" />
              </el-table>
            </div>
            <el-upload ref="mat.uploadRef" accept=".xlsx,.xls" :auto-upload="false" :limit="1" :on-change="mat.handleFileChange" :on-exceed="() => ElMessage.warning('只能上传一个文件')">
              <template #trigger><el-button type="primary">选择文件</el-button></template>
              <template #tip><div class="el-upload__tip">仅支持 .xlsx / .xls 文件</div></template>
            </el-upload>
            <div v-if="mat.importResult" style="margin-top: 16px">
              <el-alert :title="`导入完成：成功 ${mat.importResult.succeeded} 条，失败 ${mat.importResult.failed} 条`" :type="mat.importResult.failed > 0 ? 'warning' : 'success'" show-icon />
              <el-table v-if="mat.importResult.errors?.length" :data="mat.importResult.errors" border size="small" style="margin-top: 8px" max-height="200px">
                <el-table-column prop="row" label="行号" width="60" /><el-table-column prop="message" label="错误信息" />
              </el-table>
            </div>
            <template #footer>
              <el-button @click="mat.importDialogVisible = false">关闭</el-button>
              <el-button type="danger" :loading="mat.importing" :disabled="!mat.importFile" @click="mat.handleImport">开始导入</el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>

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
            <el-table-column label="默认价格" width="120">
              <template #default="{ row }">¥ {{ row.default_price?.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button text type="primary" @click="proc.handleEdit(row)">编辑</el-button>
                <el-button text type="danger" @click="proc.handleDelete(row)">删除</el-button>
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
            </el-form>
            <template #footer>
              <el-button @click="proc.dialogVisible = false">取消</el-button>
              <el-button type="danger" :loading="proc.saving" @click="proc.handleSave">保存</el-button>
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
                  <el-option label="材料" value="material" />
                  <el-option label="加工" value="processing" />
                  <el-option label="安装" value="installation" />
                  <el-option label="运输" value="transport" />
                  <el-option label="其他" value="other" />
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
import type { UploadFile } from 'element-plus'
import { getProducts, createProduct, updateProduct, deleteProduct, importProducts } from '@/api/products'
import { getMaterials, createMaterial, updateMaterial, deleteMaterial, importMaterials } from '@/api/products'
import { getProcesses, createProcess, updateProcess, deleteProcess } from '@/api/products'
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier } from '@/api/suppliers'
import type { ProductResponse, MaterialResponse, ProcessResponse, SupplierResponse, ImportResponse } from '@/types/api'
import { getErrorMessage } from '@/utils/error'

const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'products')

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
  const form = reactive({ name: '', unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0, remark: '' })
  const importDialogVisible = ref(false)
  const importing = ref(false)
  const importFile = ref<File | null>(null)
  const importResult = ref<ImportResponse | null>(null)
  const uploadRef = ref()
  const templateColumns = [
    { name: '产品名称', desc: '产品/服务名称', required: true },
    { name: '单位', desc: '项 / ㎡ / 米 / 个 / 套', required: false },
    { name: '计价方式', desc: 'area / quantity / length / word_count', required: false },
    { name: '默认价格', desc: '默认单价（数字）', required: false },
    { name: '最低收费', desc: '最低收费金额（数字）', required: false },
    { name: '备注', desc: '备注信息', required: false },
  ]
  const sampleData = [{ col1: '灯箱制作', col2: '㎡', col3: 'area', col4: '350.00' }]

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
  function handleEdit(row: ProductResponse) {
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
  async function handleDelete(row: ProductResponse) {
    try {
      await ElMessageBox.confirm(`确认删除产品 "${row.name}"？`, '确认', { type: 'warning' })
      await deleteProduct(row.id)
      ElMessage.success('已删除')
      fetchData()
    } catch { /* ignore */ }
  }
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
      ElMessage.success(`导入完成：成功 ${data.succeeded} 条${data.failed > 0 ? `，失败 ${data.failed} 条` : ''}`)
      fetchData()
    } catch (e: unknown) {
      ElMessage.error(getErrorMessage(e, '导入失败'))
    } finally { importing.value = false }
  }
  return { loading, saving, list, total, page, pageSize, keyword, dialogVisible, editingId, form, importDialogVisible, importing, importFile, importResult, uploadRef, templateColumns, sampleData, fetchData, handleCreate, handleEdit, handleSave, handleDelete, handleFileChange, handleImport }
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
  const form = reactive({ name: '', spec: '', unit: '张', purchase_price: 0, sale_price: 0, loss_rate: 0 })
  const importDialogVisible = ref(false)
  const importing = ref(false)
  const importFile = ref<File | null>(null)
  const importResult = ref<ImportResponse | null>(null)
  const uploadRef = ref()
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
    try {
      await ElMessageBox.confirm(`确认删除材质 "${row.name}"？`, '确认', { type: 'warning' })
      await deleteMaterial(row.id)
      ElMessage.success('已删除')
      fetchData()
    } catch { /* ignore */ }
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
    } finally { importing.value = false }
  }
  return { loading, saving, list, total, page, pageSize, keyword, dialogVisible, editingId, form, importDialogVisible, importing, importFile, importResult, uploadRef, templateColumns, sampleData, fetchData, handleCreate, handleEdit, handleSave, handleDelete, handleFileChange, handleImport }
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
  const form = reactive({ name: '', charge_method: 'fixed', default_price: 0 })

  async function fetchData() {
    loading.value = true
    try {
      const data = await getProcesses({ page: page.value, page_size: pageSize.value, keyword: keyword.value })
      list.value = data.items
      total.value = data.total
    } finally { loading.value = false }
  }
  function handleCreate() {
    editingId.value = null
    Object.assign(form, { name: '', charge_method: 'fixed', default_price: 0 })
    dialogVisible.value = true
  }
  function handleEdit(row: ProcessResponse) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, charge_method: row.charge_method, default_price: row.default_price })
    dialogVisible.value = true
  }
  async function handleSave() {
    saving.value = true
    try {
      if (editingId.value) {
        await updateProcess(editingId.value, form)
        ElMessage.success('更新成功')
      } else {
        await createProcess(form)
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
  prod.fetchData()
})
</script>

<style scoped>
.page { padding: 0; }
.tab-content { margin-top: 16px; }
.search-bar { display: flex; align-items: center; margin-bottom: 16px; }
</style>
