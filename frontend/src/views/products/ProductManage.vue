<template>
  <div class="pricing-center">
    <!-- Left: Customer Tree -->
    <div class="left-panel">
      <div class="tree-header">
        <el-input v-model="treeFilter" placeholder="搜索客户..." size="small" clearable />
      </div>
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="{ children: 'children', label: 'label' }"
        node-key="id"
        :filter-node-method="filterTreeNode"
        highlight-current
        :expand-on-click-node="true"
        :default-expanded-keys="expandedKeys"
        @node-click="onNodeClick"
      >
        <template #default="{ data }">
          <span class="tree-node">
            <el-icon v-if="data.type === 'all'" :size="16"><Folder /></el-icon>
            <el-icon v-else-if="data.type === 'type'" :size="16"><FolderOpened /></el-icon>
            <el-icon v-else-if="data.type === 'level'" :size="16"><Collection /></el-icon>
            <el-icon v-else :size="16"><User /></el-icon>
            <span class="tree-label" :title="data.label">{{ data.label }}</span>
            <el-tag v-if="data.count != null" size="small" type="info">{{ data.count }}</el-tag>
          </span>
        </template>
      </el-tree>
    </div>

    <!-- Right: Content -->
    <div class="right-panel">
      <!-- View 1: Global Product Library -->
      <div v-if="viewMode === 'global'" class="view-global">
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

            <el-table :data="productList" v-loading="productLoading" stripe style="margin-top: 16px" @selection-change="onProductSelectionChange">
              <el-table-column type="selection" width="50" />
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
            /></div>

      <!-- View 2: Batch Pricing (customer type/level selected) -->
      <div v-else-if="viewMode === 'batch'" class="view-batch">
        <div class="page-header">
          <h2>批量调价 — {{ selectedNode?.label }}</h2>
        </div>

        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header><span>调价设置</span></template>
          <el-form :model="batchForm" label-width="100px" inline>
            <el-form-item label="选择产品">
              <el-select v-model="batchForm.product_ids" multiple filterable placeholder="全部产品（留空=所有产品）" style="width: 360px">
                <el-option v-for="p in allProducts" :key="p.id" :label="formatProductLabel(p)" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="协议价格">
              <el-input-number v-model="batchForm.price_value" :min="0" :precision="2" style="width: 160px" />
            </el-form-item>
            <el-form-item label="折扣率">
              <el-input-number v-model="batchForm.discount_rate" :min="0" :max="1" :step="0.05" :precision="2" style="width: 120px" />
            </el-form-item>
            <el-form-item label="生效日期">
              <el-input v-model="batchForm.effective_from" placeholder="YYYY-MM-DD" style="width: 150px" />
            </el-form-item>
            <el-form-item>
              <el-checkbox v-model="batchForm.overwrite">覆盖已有价格</el-checkbox>
            </el-form-item>
          </el-form>
          <el-button type="danger" :loading="batchSubmitting" @click="handleBatchApply">应用到 {{ selectedNode?.count || 0 }} 个客户</el-button>
          <span v-if="batchResult" style="margin-left: 12px; color: var(--ad-text-secondary)">
            创建 {{ batchResult.created }}，更新 {{ batchResult.updated }}，跳过 {{ batchResult.skipped }}
          </span>
        </el-card>

        <el-card shadow="never">
          <template #header><span>受影响客户</span></template>
          <el-table :data="batchCustomers" v-loading="batchCustomersLoading" stripe max-height="400">
            <el-table-column prop="name" label="客户名称" min-width="160" />
            <el-table-column prop="customer_type" label="类型" width="100" />
            <el-table-column prop="level" label="等级" width="80" />
          </el-table>
        </el-card>
      </div>

      <!-- View 3: Customer Pricing Table -->
      <div v-else-if="viewMode === 'customer'" class="view-customer">
        <div class="page-header">
          <h2>{{ selectedCustomer?.name }} — 产品定价</h2>
          <div>
            <el-tag style="margin-right: 8px">{{ selectedCustomer?.customer_type }}</el-tag>
            <el-tag type="success">{{ selectedCustomer?.level || '未分级' }}</el-tag>
            <el-button type="primary" @click="openAddPricingDialog" style="margin-left: 12px">新建定价</el-button>
          </div>
        </div>

        <div class="search-bar" style="margin-bottom: 12px">
          <el-button @click="handleInitCustomerPricing">一键初始化（复制全局标准价）</el-button>
          <el-button type="danger" :disabled="selectedAgreements.length === 0" @click="handleBatchDeleteAgreements">删除选中 ({{ selectedAgreements.length }})</el-button>
        </div>

        <el-table :data="customerAgreements" v-loading="agreementLoading" stripe @selection-change="onAgreementSelectionChange">
          <el-table-column type="selection" width="50" />
          <el-table-column label="产品/材质/工艺" min-width="220">
            <template #default="{ row }">{{ [getProductName(row.product_id), getProductField(row.product_id, 'material_name'), getProductField(row.product_id, 'process_name')].filter(Boolean).join(' / ') }}</template>
          </el-table-column>
          <el-table-column label="标准价" width="120">
            <template #default="{ row }">¥ {{ productDefaultPrice(row.product_id)?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="客户协议价" width="130">
            <template #default="{ row }">¥ {{ Number(row.price_value).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="折扣" width="90">
            <template #default="{ row }">{{ (Number(row.discount_rate) * 100).toFixed(0) }}%</template>
          </el-table-column>
          <el-table-column label="最低收费" width="110">
            <template #default="{ row }">¥ {{ Number(row.minimum_charge).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="有效期" width="160">
            <template #default="{ row }">{{ row.effective_from }} ~ {{ row.effective_to || '长期' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="openEditAgreementDialog(row)">编辑</el-button>
              <el-button text type="danger" @click="handleDeleteAgreement(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

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
            <el-option label="批" value="批" />
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

            <!-- ── Add Pricing Dialog ── -->
    <el-dialog v-model="addPricingDialogVisible" title="新建客户定价" width="650px" :close-on-click-modal="false">
      <el-form :model="agreementForm" label-width="100px">
        <!-- 编辑模式：显示已选产品（只读） -->
        <template v-if="editingAgreementId">
          <el-form-item label="产品">
            <el-input :model-value="getProductName(agreementForm.product_id)" readonly />
          </el-form-item>
        </template>
        <!-- 新建模式：产品创建字段 -->
        <template v-else>
          <div class="combination-fields">
            <el-form-item label="产品">
              <el-input v-model="agreementForm.name" placeholder="如：标识牌" />
            </el-form-item>
            <el-form-item label="材质">
              <el-input v-model="agreementForm.material_name" placeholder="如：亚克力" />
            </el-form-item>
            <el-form-item label="工艺">
              <el-input v-model="agreementForm.process_name" placeholder="如：UV打印" />
            </el-form-item>
          </div>
          <el-form-item label="单位">
            <el-select v-model="agreementForm.unit" style="width: 100%">
              <el-option label="项" value="项" />
              <el-option label="㎡" value="㎡" />
              <el-option label="米" value="米" />
              <el-option label="个" value="个" />
              <el-option label="套" value="套" />
              <el-option label="批" value="批" />
            </el-select>
          </el-form-item>
          <el-form-item label="计价方式">
            <el-select v-model="agreementForm.pricing_method" style="width: 100%">
              <el-option label="按面积" value="area" />
              <el-option label="按数量" value="quantity" />
              <el-option label="按长度" value="length" />
              <el-option label="按字数" value="word_count" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="协议价" required>
          <el-input-number v-model="agreementForm.price_value" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="折扣率">
          <el-input-number v-model="agreementForm.discount_rate" :min="0" :max="1" :step="0.05" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="最低收费">
          <el-input-number v-model="agreementForm.minimum_charge" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="生效日期" required>
          <el-input v-model="agreementForm.effective_from" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="失效日期">
          <el-input v-model="agreementForm.effective_to" placeholder="YYYY-MM-DD，留空=长期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addPricingDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="agreementSubmitting" @click="handleSaveAgreement">保存</el-button>
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
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { Folder, FolderOpened, Collection, User } from '@element-plus/icons-vue'
import {
  getProducts, createProduct, updateProduct, deleteProduct, importProducts,
} from '@/api/products'
import { getCustomerTree } from '@/api/customers'
import {
  listCustomerAgreements, createCustomerAgreement,
  updateCustomerAgreement, deleteCustomerAgreement,
  batchCustomerAgreements,
  type CustomerAgreement, type BatchAgreementInput,
} from '@/api/cdrQuote'
import type { ProductResponse, ImportResponse, CustomerTreeNode } from '@/types/api'
import { getErrorMessage } from '@/utils/error'

// ── Tree Data ────────────────────────────────────────────────
interface TreeNode {
  id: string
  label: string
  type: 'all' | 'type' | 'level' | 'customer'
  count?: number
  children?: TreeNode[]
  customer_type?: string
  level?: string
  customer_id?: string
  customer_name?: string
}

const treeRef = ref()
const treeFilter = ref('')
const expandedKeys = ref<string[]>([])
const treeData = ref<TreeNode[]>([])
const selectedNode = ref<TreeNode | null>(null)
const viewMode = ref<'global' | 'batch' | 'customer'>('global')
const selectedCustomer = ref<{ id: string; name: string; customer_type: string; level: string } | null>(null)

function filterTreeNode(value: string, data: TreeNode): boolean {
  return data.label.toLowerCase().includes(value.toLowerCase())
}

watch(treeFilter, (v) => {
  treeRef.value?.filter(v)
})

function buildTree(raw: CustomerTreeNode[]): TreeNode[] {
  const rootId = 'node-all'
  const totalCount = raw.reduce((s, t) => s + t.count, 0)
  const children: TreeNode[] = raw.map((t, ti) => ({
    id: `type-${ti}`,
    label: t.customer_type,
    type: 'type' as const,
    count: t.count,
    customer_type: t.customer_type,
    children: t.levels.map((l, li) => ({
      id: `level-${ti}-${li}`,
      label: l.level,
      type: 'level' as const,
      count: l.count,
      customer_type: t.customer_type,
      level: l.level,
      children: l.customers.map((c) => ({
        id: `cust-${c.id}`,
        label: c.name,
        type: 'customer' as const,
        customer_id: c.id,
        customer_name: c.name,
        customer_type: t.customer_type,
        level: l.level,
      })),
    })),
  }))
  return [{ id: rootId, label: '全部客户', type: 'all', count: totalCount, children }]
}

function expandTreeNode(node: TreeNode) {
  if (!node.children) return
  const store = (treeRef.value as { store?: { nodesMap?: Record<string, { expand(): void }> } } | undefined)?.store
  if (!store) return
  for (const child of node.children) {
    const n = store.nodesMap?.[child.id]
    if (n) n.expand()
    if (child.children?.length) {
      expandTreeNode(child)
    }
  }
}

function onNodeClick(data: TreeNode) {
  selectedNode.value = data
  if (data.type === 'all') {
    viewMode.value = 'global'
    selectedCustomer.value = null
  } else if (data.type === 'type' || data.type === 'level') {
    viewMode.value = 'batch'
    selectedCustomer.value = null
    loadBatchCustomers()
    // 点击二级菜单时展开所有子级
    if (data.type === 'type') {
      nextTick(() => {
        expandTreeNode(data)
      })
    }
  } else if (data.type === 'customer') {
    viewMode.value = 'customer'
    selectedCustomer.value = {
      id: data.customer_id!,
      name: data.customer_name!,
      customer_type: data.customer_type || '',
      level: data.level || '',
    }
    loadCustomerAgreements()
  }
}

// ── Global Product Library ───────────────────────────────────
const keyword = ref('')
const productLoading = ref(false)
const selectedProducts = ref<ProductResponse[]>([])
function onProductSelectionChange(rows: ProductResponse[]) { selectedProducts.value = rows }
const productList = ref<ProductResponse[]>([])
const prodTotal = ref(0)
const prodPage = ref(1)
const prodPageSize = ref(20)
const allProducts = ref<ProductResponse[]>([])

function pricingLabel(m: string) {
  const map: Record<string, string> = { area: '按面积', quantity: '按数量', length: '按长度', word_count: '按字数' }
  return map[m] || m
}

function formatProductLabel(p: ProductResponse): string {
  return [p.name, p.material_name, p.process_name, p.unit ? `(${p.unit})` : ''].filter(Boolean).join(' / ')
}

async function fetchProducts() {
  productLoading.value = true
  try {
    const data = await getProducts({ page: prodPage.value, page_size: prodPageSize.value, keyword: keyword.value })
    productList.value = data.items
    prodTotal.value = data.total
  } finally { productLoading.value = false }
}

async function loadAllProducts() {
  try {
    const data = await getProducts({ page: 1, page_size: 100 })
    allProducts.value = data.items
  } catch { /* ignore */ }
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
    loadAllProducts()
  } finally { saving.value = false }
}

async function handleDelete(row: ProductResponse) {
  const label = [row.name, row.material_name, row.process_name].filter(Boolean).join(' / ')
  await ElMessageBox.confirm('确认删除产品/材质/工艺组合 "' + label + '"？', '确认', { type: 'warning' })
  await deleteProduct(row.id)
  ElMessage.success('已删除')
  fetchProducts()
  loadAllProducts()
}

// ── Batch Pricing ──
const batchSubmitting = ref(false)
const batchResult = ref<{ created: number; updated: number; skipped: number } | null>(null)
interface BatchCustomer { name?: string; customer_type?: string; level?: number | string }
const batchCustomers = ref<BatchCustomer[]>([])
const batchCustomersLoading = ref(false)
const batchForm = reactive({
  product_ids: [] as string[],
  price_value: 0,
  discount_rate: 1,
  effective_from: '',
  effective_to: '',
  overwrite: true,
})

async function loadBatchCustomers() {
  batchCustomersLoading.value = true
  batchResult.value = null
  try {
    // Use the existing customers API to load matching customers
    const api = await import('@/api')
    const response = await api.default.get<{ items: BatchCustomer[] }>('/customers/', {
      params: {
        page: 1,
        page_size: 100,
        customer_type: selectedNode.value?.customer_type || undefined,
      },
    })
    let customers = response.items || []
    if (selectedNode.value?.level) {
      customers = customers.filter((c: BatchCustomer) => c.level === selectedNode.value?.level)
    }
    batchCustomers.value = customers
  } catch { /* ignore */ }
  finally { batchCustomersLoading.value = false }
}

async function handleBatchApply() {
  batchSubmitting.value = true
  try {
    const payload: BatchAgreementInput = {
      customer_type: selectedNode.value?.customer_type,
      level: selectedNode.value?.level,
      product_ids: batchForm.product_ids.length > 0 ? batchForm.product_ids : undefined,
      price_value: batchForm.price_value,
      discount_rate: batchForm.discount_rate,
      effective_from: batchForm.effective_from,
      effective_to: batchForm.effective_to || undefined,
      overwrite: batchForm.overwrite,
    }
    batchResult.value = await batchCustomerAgreements(payload)
    ElMessage.success('批量调价完成')
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '批量调价失败'))
  } finally { batchSubmitting.value = false }
}

// ── Customer Agreements ──
const agreementLoading = ref(false)
const customerAgreements = ref<CustomerAgreement[]>([])
const addPricingDialogVisible = ref(false)
const agreementSubmitting = ref(false)
const selectedAgreements = ref<CustomerAgreement[]>([])
function onAgreementSelectionChange(rows: CustomerAgreement[]) { selectedAgreements.value = rows }
const editingAgreementId = ref<string | null>(null)
const agreementForm = reactive({
  name: '', material_name: '', process_name: '',
  unit: '项', pricing_method: 'quantity',
  product_id: '', price_value: 0, discount_rate: 1, minimum_charge: 0,
  effective_from: new Date().toISOString().slice(0, 10), effective_to: '',
})

function getProductName(pid: string): string {
  const p = allProducts.value.find(x => x.id === pid)
  return p?.name || pid.slice(0, 8)
}

function getProductField(pid: string, field: string): unknown {
  const p = allProducts.value.find(x => x.id === pid)
  return p ? (p as Record<string, unknown>)[field] : null
}
function productDefaultPrice(pid: string): number | null {
  const p = allProducts.value.find(x => x.id === pid)
  return typeof p?.default_price === 'number' ? p.default_price : null
}

async function loadCustomerAgreements() {
  if (!selectedCustomer.value?.id) return
  agreementLoading.value = true
  try {
    customerAgreements.value = await listCustomerAgreements(selectedCustomer.value.id)
  } finally { agreementLoading.value = false }
}

function openAddPricingDialog() {
  editingAgreementId.value = null
  Object.assign(agreementForm, {
    name: '', material_name: '', process_name: '',
    unit: '项', pricing_method: 'quantity',
    product_id: '', price_value: 0, discount_rate: 1, minimum_charge: 0,
    effective_from: new Date().toISOString().slice(0, 10), effective_to: '',
  })
  addPricingDialogVisible.value = true
}

function openEditAgreementDialog(row: CustomerAgreement) {
  editingAgreementId.value = row.id
  const prod = allProducts.value.find(p => p.id === row.product_id)
  Object.assign(agreementForm, {
    name: prod?.name || '', material_name: prod?.material_name || '', process_name: prod?.process_name || '',
    unit: prod?.unit || '项', pricing_method: prod?.pricing_method || 'quantity',
    product_id: row.product_id || '',
    price_value: Number(row.price_value),
    discount_rate: Number(row.discount_rate),
    minimum_charge: Number(row.minimum_charge),
    effective_from: row.effective_from,
    effective_to: row.effective_to || '',
  })
  addPricingDialogVisible.value = true
}

async function handleSaveAgreement() {
  if (!selectedCustomer.value?.id) return
  agreementSubmitting.value = true
  try {
    if (editingAgreementId.value) {
      // 编辑模式：仅更新协议价
      await updateCustomerAgreement(editingAgreementId.value, {
        customer_id: selectedCustomer.value.id,
        product_id: agreementForm.product_id,
        pricing_method: agreementForm.pricing_method,
        price_value: agreementForm.price_value,
        discount_rate: agreementForm.discount_rate,
        minimum_charge: agreementForm.minimum_charge,
        effective_from: agreementForm.effective_from,
        effective_to: agreementForm.effective_to || undefined,
      })
      ElMessage.success('定价已更新')
    } else {
      // 新建模式：先创建产品，再创建客户协议
      const filled = [agreementForm.name.trim(), agreementForm.material_name.trim(), agreementForm.process_name.trim()].filter(Boolean)
      if (filled.length === 0) { ElMessage.warning('请至少填写产品、材质、工艺中的一项'); return }
      const product = await createProduct({
        name: agreementForm.name,
        material_name: agreementForm.material_name,
        process_name: agreementForm.process_name,
        unit: agreementForm.unit,
        pricing_method: agreementForm.pricing_method,
        default_price: agreementForm.price_value,
        min_charge: agreementForm.minimum_charge,
      })
      await createCustomerAgreement({
        customer_id: selectedCustomer.value.id,
        product_id: product.id,
        pricing_method: agreementForm.pricing_method,
        price_value: agreementForm.price_value,
        discount_rate: agreementForm.discount_rate,
        minimum_charge: agreementForm.minimum_charge,
        effective_from: agreementForm.effective_from,
        effective_to: agreementForm.effective_to || undefined,
      })
      ElMessage.success('定价已创建')
    }
    addPricingDialogVisible.value = false
    loadCustomerAgreements()
    loadAllProducts()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally { agreementSubmitting.value = false }
}

async function handleDeleteAgreement(id: string) {
  await ElMessageBox.confirm('确认删除该定价？', '确认', { type: 'warning' })
  await deleteCustomerAgreement(id)
  ElMessage.success('已删除')
  loadCustomerAgreements()
}

async function handleBatchDeleteAgreements() {
  if (selectedAgreements.value.length === 0) { ElMessage.warning('请先选择要删除的定价'); return }
  await ElMessageBox.confirm('确认删除选中的 ' + selectedAgreements.value.length + ' 条定价记录？', '确认', { type: 'warning' })
  let deleted = 0
  for (const row of selectedAgreements.value) {
    try { await deleteCustomerAgreement(row.id); deleted++ } catch { /* skip */ }
  }
  ElMessage.success('已删除 ' + deleted + ' 条')
  loadCustomerAgreements()
}

async function handleInitCustomerPricing() {
  if (!selectedCustomer.value?.id) return
  try {
    const data = await batchCustomerAgreements({
      customer_ids: [selectedCustomer.value.id],
      price_value: 0,
      discount_rate: 1,
      overwrite: false,
    })
    ElMessage.success('初始化完成：创建 ' + data.created + ' 条')
    loadCustomerAgreements()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '初始化失败'))
  }
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
  { name: '单位', desc: '项 / ㎡ / 米 / 个 / 套 / 批', required: false },
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
    loadAllProducts()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导入失败'))
  } finally { importing.value = false }
}

// ── Init ──
async function loadTree() {
  try {
    const raw = await getCustomerTree()
    treeData.value = buildTree(raw)
    // 默认展开所有二级菜单（客户类型）
    const typeIds: string[] = []
    if (treeData.value.length > 0 && treeData.value[0].children) {
      for (const typeNode of treeData.value[0].children) {
        typeIds.push(typeNode.id)
      }
    }
    expandedKeys.value = typeIds
  } catch { /* ignore */ }
}

onMounted(() => {
  loadTree()
  fetchProducts()
  loadAllProducts()
})
</script>

<style scoped>
.pricing-center {
  display: flex;
  gap: 0;
  height: calc(100vh - 120px);
  min-height: 600px;
}
.left-panel {
  width: 320px;
  min-width: 220px;
  border-right: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
  overflow-y: auto;
  padding: 12px;
}
.tree-header {
  margin-bottom: 8px;
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
}
.tree-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.right-panel {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.view-global,
.view-batch,
.view-customer {
  max-width: 1400px;
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
@media (max-width: 900px) {
  .pricing-center { flex-direction: column; height: auto; }
  .left-panel { width: 100%; max-height: 300px; border-right: none; border-bottom: 1px solid var(--el-border-color-light); }
  .right-panel { padding: 12px; }
}
@media (max-width: 720px) {
  .combination-fields { grid-template-columns: 1fr; }
}
</style>
