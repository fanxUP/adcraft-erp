<template>
  <div class="page">
    <el-button text @click="$router.push('/quotes')" style="font-size: 16px">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <h2 style="margin: 16px 0; color: var(--ad-text)">{{ isEdit ? '编辑报价' : '新建报价' }}</h2>

    <el-card shadow="never" class="section-card">
      <el-form :model="form" label-width="100px" inline>
        <el-form-item label="客户" required>
          <el-select ref="customerSelectRef" v-model="form.customer_id" placeholder="选择或输入客户名称" filterable allow-create default-first-option :disabled="isReadonly" @visible-change="onCustomerVisible" @blur="onCustomerBlur" style="width: 260px">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.project_name" :disabled="isReadonly" style="width: 260px" />
        </el-form-item>
        <el-form-item label="部门/科室">
          <el-input v-model="form.department" :disabled="isReadonly" placeholder="如：宣传部、办公室" style="width: 260px" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-select v-model="form.contact_person" filterable allow-create default-first-option clearable autocomplete="off" :disabled="isReadonly" placeholder="选择联系人或输入" style="width: 160px" @change="handleContactChange" @clear="form.contact_phone = ''">
            <el-option v-for="c in contactOptions" :key="c.id" :label="c.name" :value="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" autocomplete="off" :disabled="isReadonly" placeholder="手机/电话" style="width: 160px" />
        </el-form-item>
        <el-form-item label="税率">
          <el-input-number v-model="form.tax_rate" :precision="2" :min="0" :max="100" :step="1" :disabled="isReadonly" style="width: 160px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
          <span style="margin-left: 6px">%</span>
        </el-form-item>
        <el-form-item label="有效期">
          <el-date-picker v-model="form.valid_until" type="date" value-format="YYYY-MM-DD" :disabled="isReadonly" style="width: 160px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" :disabled="isReadonly" style="width: 260px" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>报价明细</span>
          <div style="display: flex; gap: 8px;">
            <el-button v-if="!isReadonly" size="small" @click="addGroup">添加分项</el-button>
            <el-button v-if="!isReadonly" type="danger" size="small" @click="addItem()">添加行</el-button>
            <el-button v-if="!isReadonly" size="small" @click="downloadQuoteTemplate">📥 下载导入模板</el-button>
            <el-upload
              v-if="!isReadonly"
              :auto-upload="false"
              :show-file-list="false"
              accept=".xlsx,.xls"
              :on-change="onImportItems"
            >
              <el-button size="small" type="success" :loading="importingItems">
                <el-icon><Upload /></el-icon> 导入明细
              </el-button>
            </el-upload>
          </div>
        </div>
      </template>

      <el-table ref="tableRef" :data="displayRows" stripe border scrollbar-always-on :row-key="(row: DisplayRow) => row.key" :row-class-name="rowClassName">
        <el-table-column v-if="!isReadonly" label="排序" width="46" align="center">
          <template #default="{ row }">
            <span v-if="row.type !== 'group-total'" class="row-drag-handle" title="拖动排序" @mousedown="dragStartKey = row.key">⠿</span>
          </template>
        </el-table-column>
        <el-table-column label="项目内容" min-width="320">
          <template #default="{ row }">
            <template v-if="row.type === 'group-header'">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="group-header-drag" title="拖动整个分项" style="font-weight: 600; white-space: nowrap;" @mousedown="dragStartKey = row.key">分项名称：</span>
                <el-input v-if="!isReadonly" :model-value="row.groupName" size="small" style="flex: 1" placeholder="输入分项名称" @input="(v: string) => renameGroup(row.groupName, v)" />
                <span v-else style="font-weight: 600;">{{ row.groupName }}</span>
              </div>
            </template>
            <template v-else-if="row.type === 'group-total'">
              <span style="font-weight: 600;">分项合计：{{ row.groupName }}</span>
            </template>
            <template v-else>
              <el-input v-model="row.item.item_name" :disabled="isReadonly" size="small" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="产品/材质/工艺" min-width="280">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input
                v-model="row.item.material_process"
                :disabled="isReadonly"
                size="small"
                placeholder="点击选择产品/材质/工艺"
                @click="openProductPicker(row.item)"
                clearable
                @clear="row.item.use_area = false; row.item.quantity = 1; row.item.product_id = undefined; row.item.item_name = ''"
              />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="宽" width="170">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <div style="display: flex; align-items: center; gap: 4px;">
                <el-input-number v-model="row.item.width" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" style="width: 90px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" @change="syncAreaQuantity(row.item)" />
                <el-select v-model="row.item.width_unit" :disabled="isReadonly" size="small" placeholder="选择" style="width: 65px" @change="syncAreaQuantity(row.item)">
                  <el-option label="选择" value="" disabled />
                  <el-option label="m" value="m" />
                  <el-option label="cm" value="cm" />
                  <el-option label="mm" value="mm" />
                </el-select>
              </div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="高" width="170">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <div style="display: flex; align-items: center; gap: 4px;">
                <el-input-number v-model="row.item.height" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" style="width: 90px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
                <el-select v-model="row.item.height_unit" :disabled="isReadonly" size="small" placeholder="选择" style="width: 65px">
                  <el-option label="选择" value="" disabled />
                  <el-option label="m" value="m" />
                  <el-option label="cm" value="cm" />
                  <el-option label="mm" value="mm" />
                </el-select>
              </div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="件数" width="70">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.pieces" :precision="0" :min="1" :disabled="isReadonly" size="small" :controls="false" @change="syncAreaQuantity(row.item)" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="面积" width="130">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <div style="display: flex; align-items: center; gap: 4px;">
                <span>{{ calcArea(row.item).toFixed(2) }}</span>
                <el-switch v-model="row.item.use_area" :disabled="isReadonly" size="small" @change="(val: boolean) => onAreaToggle(row.item, val)" />
              </div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="90">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.quantity" :precision="2" :min="0.01" :disabled="isReadonly || row.item.use_area" size="small" :controls="false" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="单位" width="100">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-autocomplete
                v-model="row.item.unit"
                :disabled="isReadonly"
                size="small"
                :fetch-suggestions="(q: string, cb: Function) => queryUnits(q, cb, row.item.unit)"
                placeholder="选择/输入"
                style="width: 100%"
                :trigger-on-focus="true"
                @select="(opt) => { if (!opt.disabled) row.item.unit = opt.value }"
                @blur="addRecentUnit(row.item.unit)"
              >
                <template #default="{ item }">
                  <div :style="{ color: item.disabled ? '#c0c4cc' : '', cursor: item.disabled ? 'default' : 'pointer' }">
                    {{ item.value }}
                  </div>
                </template>
              </el-autocomplete>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="120">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.unit_price" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="工艺费" width="110">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.process_fee" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="安装费" width="110">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.installation_fee" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="设计费" width="110">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.design_fee" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="运输费" width="110">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input-number v-model="row.item.transport_fee" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="小计" width="120">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">¥ {{ calcItemSubtotal(row.item).toFixed(2) }}</template>
            <template v-else-if="row.type === 'group-total'"><strong>¥ {{ row.total.toFixed(2) }}</strong></template>
          </template>
        </el-table-column>
        <el-table-column label="样图" width="90">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <div v-if="row.item.image_url" style="display: flex; align-items: center; gap: 4px;">
                <el-image :src="row.item.image_url" :preview-src-list="[row.item.image_url]" fit="cover" style="width: 32px; height: 32px; border-radius: 4px; cursor: pointer;" />
                <el-button v-if="!isReadonly" text type="danger" size="small" @click="row.item.image_url = ''" style="padding: 0;">×</el-button>
              </div>
              <el-upload v-else-if="!isReadonly" :show-file-list="false" :http-request="(opt: any) => handleImageUpload(opt, row.item)" accept="image/*" style="display: inline;">
                <el-button text type="primary" size="small" style="padding: 0;">上传</el-button>
              </el-upload>
              <span v-else style="color: #999;">-</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="120">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input v-model="row.item.remark" :disabled="isReadonly" size="small" />
            </template>
          </template>
        </el-table-column>
        <el-table-column v-if="!isReadonly" label="操作" width="100">
          <template #default="{ row }">
            <template v-if="row.type === 'group-header'">
              <div style="display: flex; gap: 4px;">
                <el-button text type="primary" size="small" @click="addItem(row.groupName)">添加行</el-button>
                <el-button text type="danger" size="small" @click="removeGroup(row.groupName)">删除组</el-button>
              </div>
            </template>
            <template v-else-if="row.type === 'item'">
              <el-button text type="danger" size="small" @click="removeItem(row.item)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <el-row :gutter="20">
        <el-col :span="16" />
        <el-col :span="8">
          <div class="summary-item"><span>明细合计：</span><strong>¥ {{ calcQuoteSubtotal().toFixed(2) }}</strong></div>
          <div class="summary-item">
            <span>优惠金额：</span>
            <el-input-number v-model="form.discount_amount" :precision="2" :min="0" :max="calcQuoteSubtotal()" :disabled="isReadonly" size="small" style="width: 140px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
          </div>
          <div class="summary-item"><span>税额：</span><strong>¥ {{ calcTax().toFixed(2) }}</strong></div>
          <div class="summary-item total"><span>总计：</span><strong>¥ {{ calcTotal().toFixed(2) }}</strong></div>
          <div style="text-align: right; font-size: 13px; color: var(--ad-text-secondary); margin-top: 4px;">
            大写金额：{{ toChineseAmount(calcTotal()) }}
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 报价状态流程图 -->
    <QuoteWorkflow
      :current-status="quote?.status || 'draft'"
      :is-existing="isEdit"
      :saving="saving"
      :converting="converting"
      :reverting="reverting"
      @save="handleSave"
      @confirm="handleConfirm"
      @convert="handleConvert"
      @revert="handleRevertToDraft"
      @preview="previewVisible = true"
    />

    <!-- 预览弹窗 -->
    <QuotePreview :visible="previewVisible" :quote-id="quoteId" :current-items="items" @close="previewVisible = false" />

    <div v-if="quote?.status === 'confirmed'" style="margin-top: 8px; color: var(--ad-text-secondary); font-size: 13px">
      如需修改报价，请先将报价转成草稿
    </div>
  </div>
    <!-- 产品选择面板 -->
    <ProductPickerDialog v-model="productPickerVisible" :customer-id="form.customer_id" @selected="onProductPicked" @updated="onProductUpdated" />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import Sortable from 'sortablejs'
import QuoteWorkflow from './QuoteWorkflow.vue'
import { useRoute, useRouter } from 'vue-router'
import { onBeforeRouteLeave } from 'vue-router'
import { createQuote, getQuote, updateQuote, confirmQuote, convertQuoteToOrder, revertQuoteToDraft, importQuoteItems, downloadQuoteTemplate } from '@/api/quotes'
import { getCustomers, getCustomer } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadAttachment } from '@/api/tasks'
import type { QuoteItemResponse, QuoteDetailResponse, CustomerResponse, ContactResponse, ProductResponse } from '@/types/api'
import QuotePreview from './QuotePreview.vue'
import ProductPickerDialog from '@/components/ProductPickerDialog.vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { applyProductMaterialProcess, formatProductMaterialProcess } from '@/utils/productMaterialProcess'
import {
  calcQuoteLineArea,
  calcQuoteLineSubtotal,
  migrateLegacyQuoteDimensions,
  syncQuoteLineAreaQuantity,
} from '@/utils/quoteLineCalculation'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const converting = ref(false)
const reverting = ref(false)
const importingItems = ref(false)
const customerSelectRef = ref()
const quote = ref<QuoteDetailResponse | null>(null)
const customerOptions = ref<CustomerResponse[]>([])
const contactOptions = ref<ContactResponse[]>([])
const previewVisible = ref(false)
const productPickerVisible = ref(false)
const pendingPickerItem = ref<QuoteItemResponse | null>(null)
const quoteId = computed(() => route.params.id as string)

const tableRef = ref()
let sortable: Sortable | null = null
let itemKeySeq = 0
const itemKeyMap = new WeakMap<QuoteItemResponse, string>()
function rowKeyFor(item: QuoteItemResponse): string {
  let k = itemKeyMap.get(item)
  if (!k) { k = `i-${itemKeySeq++}`; itemKeyMap.set(item, k) }
  return k
}

const form = reactive({
  customer_id: '',
  project_name: '',
  tax_rate: 0,
  discount_amount: 0,
  valid_until: '',
  remark: '',
  department: '',
  contact_person: '',
  contact_phone: '',
})

const newItem = (groupName?: string): QuoteItemResponse => ({
  id: '',
  quote_id: '',
  item_name: '',
  width: undefined,
  width_unit: '',
  height: undefined,
  height_unit: '',
  quantity: 1,
  unit: '',
  use_area: false,
  pieces: 1,
  unit_price: 0,
  process_fee: 0,
  installation_fee: 0,
  design_fee: 0,
  transport_fee: 0,
  other_fee: 0,
  subtotal_amount: 0,
  remark: '',
  image_url: '',
  sort_order: 0,
  group_name: groupName || undefined,
  material_process: '',
})

const items = ref<QuoteItemResponse[]>([newItem()])

// ===== 未保存修改检测 =====
const dirty = ref(false)
const isLoaded = ref(false)
let cleanSnapshot: string = ''

function captureCleanSnapshot() {
  cleanSnapshot = JSON.stringify({
    form: { ...form },
    items: items.value.map(i => ({ ...i, subtotal_amount: calcSubtotal(i) })),
  })
  isLoaded.value = true
  dirty.value = false
}

function hasUnsavedChanges(): boolean {
  if (!isLoaded.value) return false
  const current = JSON.stringify({
    form: { ...form },
    items: items.value.map(i => ({ ...i, subtotal_amount: calcSubtotal(i) })),
  })
  return current !== cleanSnapshot
}

// 监听表单和明细变化
watch(
  [form, items],
  () => {
    dirty.value = hasUnsavedChanges()
  },
  { deep: true }
)

// 路由离开守卫
onBeforeRouteLeave((to, from, next) => {
  if (!dirty.value) return next()
  ElMessageBox.confirm(
    '您有未保存的修改，确定要离开吗？离开后修改将丢失。',
    '未保存的修改',
    { confirmButtonText: '离开', cancelButtonText: '取消', type: 'warning' }
  ).then(() => next()).catch(() => next(false))
})

// 浏览器刷新/关闭
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  initSortable()
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  sortable?.destroy()
  sortable = null
})

const isReadonly = computed(() => {
  if (!isEdit.value || !quote.value) return false
  return ['confirmed', 'converted', 'cancelled'].includes(quote.value.status)
})

function calcArea(item: QuoteItemResponse) {
  return calcQuoteLineArea(item)
}

function onAreaToggle(row: QuoteItemResponse, val: boolean) {
  if (val) {
    // 开启面积模式：数量自动 = 面积，单位设为㎡
    row.quantity = Math.max(0.01, calcArea(row))
    row.unit = '㎡'
  } else {
    // 关闭面积模式：重置数量，清空单位
    row.quantity = 1
    row.unit = ''
  }
}

function syncAreaQuantity(item: QuoteItemResponse) {
  syncQuoteLineAreaQuantity(item)
}

function calcSubtotal(item: QuoteItemResponse) {
  return calcQuoteLineSubtotal(item)
}

function calcItemSubtotal(item: QuoteItemResponse) {
  const subtotal = calcSubtotal(item)
  item.subtotal_amount = subtotal
  return subtotal
}

function calcQuoteSubtotal() { return items.value.reduce((s, i) => s + calcSubtotal(i), 0) }
function calcTax() { return (calcQuoteSubtotal() - (form.discount_amount || 0)) * (form.tax_rate || 0) / 100 }
function calcTotal() { return calcQuoteSubtotal() - (form.discount_amount || 0) + calcTax() }

function toChineseAmount(n: number): string {
  const digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const units = ['', '拾', '佰', '仟']
  const bigUnits = ['', '万', '亿']
  if (n === 0) return '零元整'
  const negative = n < 0
  n = Math.abs(n)
  const intPart = Math.floor(n)
  const decPart = Math.round((n - intPart) * 100)
  const jiao = Math.floor(decPart / 10)
  const fen = decPart % 10
  let result = ''
  if (intPart > 0) {
    const str = String(intPart)
    const len = str.length
    let zeroFlag = false
    for (let i = 0; i < len; i++) {
      const d = parseInt(str[i])
      const pos = len - 1 - i
      const unitIdx = pos % 4
      const bigIdx = Math.floor(pos / 4)
      if (d === 0) {
        zeroFlag = true
        if (unitIdx === 0 && bigUnits[bigIdx]) { result += bigUnits[bigIdx]; zeroFlag = false }
      } else {
        if (zeroFlag) { result += '零'; zeroFlag = false }
        result += digits[d] + units[unitIdx]
        if (unitIdx === 0 && bigUnits[bigIdx]) result += bigUnits[bigIdx]
      }
    }
    result += '元'
  }
  if (jiao === 0 && fen === 0) { result += '整' }
  else {
    if (jiao > 0) result += digits[jiao] + '角'
    else if (intPart > 0) result += '零'
    if (fen > 0) result += digits[fen] + '分'
  }
  return (negative ? '负' : '') + result
}

function addItem(groupName?: string) { items.value.push(newItem(groupName)) }

// --- 分组管理 ---
function addGroup() {
  const existing = new Set(items.value.filter(i => i.group_name).map(i => i.group_name))
  let idx = 1
  while (existing.has(`分项${idx}`)) idx++
  items.value.push(newItem(`分项${idx}`))
}

function removeGroup(groupName: string) {
  items.value = items.value.filter(i => i.group_name !== groupName)
}

function removeItem(target: QuoteItemResponse) {
  const idx = items.value.indexOf(target)
  if (idx >= 0) items.value.splice(idx, 1)
}

function renameGroup(oldName: string, newName: string) {
  if (!newName || oldName === newName) return
  items.value.forEach(i => { if (i.group_name === oldName) i.group_name = newName })
}

type DisplayRow =
  | { type: 'group-header'; groupName: string; gi: number; key: string }
  | { type: 'item'; item: QuoteItemResponse; groupName: string; gi: number; key: string }
  | { type: 'group-total'; groupName: string; total: number; gi: number; key: string }

const displayRows = computed<DisplayRow[]>(() => {
  const grouped = new Map<string, QuoteItemResponse[]>()
  const ungrouped: QuoteItemResponse[] = []

  for (const item of items.value) {
    if (item.group_name) {
      if (!grouped.has(item.group_name)) grouped.set(item.group_name, [])
      grouped.get(item.group_name)!.push(item)
    } else {
      ungrouped.push(item)
    }
  }

  const rows: DisplayRow[] = []
  let gi = 0
  for (const [groupName, groupItems] of grouped) {
    rows.push({ type: 'group-header', groupName, gi, key: 'gh-' + gi })
    for (const item of groupItems) rows.push({ type: 'item', item, groupName, gi, key: rowKeyFor(item) })
    const total = groupItems.reduce((s, i) => s + calcSubtotal(i), 0)
    rows.push({ type: 'group-total', groupName, total, gi, key: 'gt-' + gi })
    gi++
  }
  for (const item of ungrouped) rows.push({ type: 'item', item, groupName: '', gi: -1, key: rowKeyFor(item) })
  return rows
})

function rowClassName({ row }: { row: DisplayRow }) {
  const cls: string[] = []
  if (row.gi >= 0) cls.push(`group-c${(row.gi % 5) + 1}`)
  if (row.type === 'group-header') cls.push('group-header-row')
  if (row.type === 'group-total') cls.push('group-total-row')
  cls.push('rk-' + row.key)
  return cls.join(' ')
}

// ── 拖拽排序（Sortablejs）──
function initSortable() {
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody')
  if (sortable) { sortable.destroy(); sortable = null }
  if (!tbody || isReadonly.value) return
  sortable = Sortable.create(tbody as HTMLElement, {
    handle: '.row-drag-handle, .group-header-drag',
    animation: 150,
    ghostClass: 'ad-drag-ghost',
    chosenClass: 'ad-drag-chosen',
    dragClass: 'ad-drag-dragging',
    onStart: handleDragStart,
    onMove: handleDragMove,
    onEnd: handleDragEnd,
  })
}

// ── 组拖拽：整组跟随卡片 + 源分项整块"选中感" ──
let groupDragCard: HTMLElement | null = null
const dragStartKey = ref<string | null>(null)

function handleDragStart(evt: Sortable.SortableEvent) {
  // start 事件不带可靠的 item/oldIndex，行 key 已在 handle 的 @mousedown 里捕获
  const key = dragStartKey.value
  const dragged = key ? displayRows.value.find(r => r.key === key) : undefined
  if (!dragged || dragged.type !== 'group-header') return

  const rows = displayRows.value
  const headerIdx = rows.indexOf(dragged)
  const block = blockOf(rows, headerIdx)
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody')

  // 隐藏原生拖拽快照（浏览器默认只跟随表头一行），改由下方整组卡片跟随
  const de = (evt as { originalEvent?: DragEvent }).originalEvent
  const blank = document.createElement('canvas')
  blank.width = blank.height = 0
  de?.dataTransfer?.setDragImage(blank, 0, 0)

  // 源分项整块"选中感"：高亮 + 轻微降透明
  document.body.classList.add('ad-group-drag')
  for (const r of block) tbody?.querySelector('.rk-' + r.key)?.classList.add('ad-drag-lifted')

  // 整组概要卡片（跟随光标）
  const card = document.createElement('div')
  card.className = 'ad-drag-card'
  card.style.setProperty('--ad-g', `var(--ad-group-${((dragged.gi % 5) + 1)})`)
  const header = block.find(r => r.type === 'group-header')
  const items = block.filter(r => r.type === 'item')
  const total = block.find(r => r.type === 'group-total')?.total ?? 0
  const nameEl = document.createElement('div')
  nameEl.className = 'ad-drag-card__name'
  nameEl.textContent = `分项：${header?.groupName ?? ''}`
  const metaEl = document.createElement('div')
  metaEl.className = 'ad-drag-card__meta'
  metaEl.textContent = `${items.length} 条明细 · 合计 ¥${total.toFixed(2)}`
  card.append(nameEl, metaEl)
  document.body.appendChild(card)
  groupDragCard = card
  positionDragCard(de?.clientX ?? 0, de?.clientY ?? 0)
}

function positionDragCard(clientX: number, clientY: number) {
  if (!groupDragCard) return
  groupDragCard.style.transform = `translate(${clientX + 14}px, ${clientY + 14}px)`
}

function handleDragMove(_evt: Sortable.MoveEvent, originalEvent: Event) {
  const e = originalEvent as MouseEvent | TouchEvent
  const x = 'clientX' in e ? e.clientX : 0
  const y = 'clientY' in e ? e.clientY : 0
  positionDragCard(x, y)
}

function cleanupGroupDrag() {
  dragStartKey.value = null
  document.body.classList.remove('ad-group-drag')
  if (groupDragCard) { groupDragCard.remove(); groupDragCard = null }
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody')
  const lifted = tbody?.querySelectorAll('.ad-drag-lifted')
  lifted?.forEach((el: Element) => el.classList.remove('ad-drag-lifted'))
}

function handleDragEnd(evt: Sortable.SortableEvent) {
  cleanupGroupDrag()
  const oldIndex = evt.oldIndex
  if (oldIndex == null || evt.newIndex == null || oldIndex === evt.newIndex) return
  const rows = displayRows.value
  const dragged = rows[oldIndex]
  if (!dragged || dragged.type === 'group-total') return

  const isGroup = dragged.type === 'group-header'
  const blockRows = isGroup ? blockOf(rows, oldIndex) : [dragged]
  const rest = rows.filter(r => !blockRows.includes(r))

  // 落点 = 拖拽行在 DOM 中的下一个兄弟行（天然代表视觉落点，不受分组结构影响）
  const succ = evt.item.nextElementSibling as HTMLElement | null
  let insertAt = rest.length
  let afterHeader = false
  if (succ) {
    const sk = rkKeyOf(succ)
    const si = rest.findIndex(r => r.key === sk)
    if (si >= 0) {
      // 表头拖回自己块内（落到自己的条目/合计之间）→ 无操作
      if (isGroup && blockRows.some(r => r.key === sk)) return
      insertAt = si
      afterHeader = rest[si].type === 'group-header'
    }
  }
  // 条目落到分项表头正下方 → 成为该分项第一条；其余情况插在落点之前
  const finalRows = (!isGroup && afterHeader)
    ? [...rest.slice(0, insertAt + 1), dragged, ...rest.slice(insertAt + 1)]
    : [...rest.slice(0, insertAt), ...blockRows, ...rest.slice(insertAt)]

  rebuildItemsFromRows(finalRows)
}

function rkKeyOf(tr: HTMLElement): string {
  const cls = String(tr.className || '')
  return cls.split(/\s+/).find(c => c.startsWith('rk-'))?.slice(3) || ''
}

function blockOf(rows: DisplayRow[], headerIdx: number): DisplayRow[] {
  const h = rows[headerIdx]
  const end = rows.findIndex((r, i) => i > headerIdx && r.type === 'group-total' && r.groupName === h.groupName)
  return rows.slice(headerIdx, end >= 0 ? end + 1 : rows.length)
}

function rebuildItemsFromRows(rows: DisplayRow[]) {
  const next: QuoteItemResponse[] = []
  let curGroup: string | undefined
  for (const r of rows) {
    if (r.type === 'group-header') curGroup = r.groupName
    else if (r.type === 'group-total') curGroup = undefined
    else if (r.type === 'item') {
      r.item.group_name = curGroup
      next.push(r.item)
    }
  }
  const old = items.value
  const same = old.length === next.length && old.every((it, i) => it === next[i])
  if (!same) items.value = next
}

// 明细结构变化后重建 sortable（el-table 可能重建 tbody）
watch([displayRows, isReadonly], () => { nextTick(() => initSortable()) })

// 单位相关
const defaultUnits = ['㎡', 'm', '个', '套', '块', '件', '批', '次', '组', '台']
const RECENT_UNITS_KEY = 'quoteEditor_recentUnits'
const recentUnits = ref<string[]>(JSON.parse(localStorage.getItem(RECENT_UNITS_KEY) || '[]'))
const allUnits = computed(() => [
  ...recentUnits.value.map(u => ({ value: u })),
  ...defaultUnits.map(u => ({ value: u })),
])

function addRecentUnit(unit: string) {
  if (!unit || defaultUnits.includes(unit)) return
  recentUnits.value = [unit, ...recentUnits.value.filter(u => u !== unit)].slice(0, 3)
  localStorage.setItem(RECENT_UNITS_KEY, JSON.stringify(recentUnits.value))
}

function queryUnits(queryString: string, cb: (results: { value: string; disabled?: boolean }[]) => void, currentValue?: string) {
  const list = allUnits.value
  const filtered = (queryString && queryString !== currentValue)
    ? list.filter(u => u.value.toLowerCase().includes(queryString.toLowerCase()))
    : list
  // 在第一行添加灰色"选择"提示
  cb([{ value: '选择', disabled: true }, ...filtered])
}

async function loadCustomers() {
  const data = await getCustomers({ page_size: 100 })
  customerOptions.value = data.items
}

// 联系人下拉：加载所选客户的已存联系人（客户管理里添加的）
async function loadCustomerContacts(customerId: string) {
  if (!customerId || !isExistingCustomer(customerId)) {
    contactOptions.value = []
    return
  }
  try {
    const customer = await getCustomer(customerId)
    contactOptions.value = customer.contacts || []
  } catch {
    contactOptions.value = []
  }
}

function handleContactChange(name: string) {
  const c = contactOptions.value.find(c => c.name === name)
  if (c?.phone) form.contact_phone = c.phone
}

watch(() => form.customer_id, (val) => {
  if (!val) {
    contactOptions.value = []
    return
  }
  void loadCustomerContacts(String(val))
})


function openProductPicker(item: QuoteItemResponse) {
  if (!form.customer_id) {
    ElMessage.warning('请先选择客户')
    return
  }
  pendingPickerItem.value = item
  productPickerVisible.value = true
}

function onProductPicked(product: ProductResponse) {
  const item = pendingPickerItem.value
  if (!item) return
  onProductSelect(item, { value: formatProductMaterialProcess(product), product })
  pendingPickerItem.value = null
}

function onProductUpdated(product: ProductResponse) {
  const item = pendingPickerItem.value
  if (!item || !item.product_id || item.product_id !== product.id) return
  // 产品主数据在选产品弹窗里被编辑后，同步到当前行；只更新产品继承字段，不改数量/面积开关
  Object.assign(item, applyProductMaterialProcess(item, product))
}

function onProductSelect(item: QuoteItemResponse, opt: { value: string; product?: ProductResponse }) {
  if (!opt.product) {
    item.product_id = undefined
    item.use_area = false
    item.quantity = 1
    return
  }
  Object.assign(item, applyProductMaterialProcess(item, opt.product))
  item.material_process = opt.value
  item.item_name = opt.product.name
  if (opt.product.pricing_method === 'area') {
    if (!item.use_area) {
      item.use_area = true
      syncAreaQuantity(item)
    }
  } else {
    item.use_area = false
    item.quantity = 1
  }
}

function onCustomerVisible(visible: boolean) {
  if (visible) loadCustomers()
}

function onCustomerBlur() {
  // Element Plus clears allow-create value on blur if not explicitly selected.
  // Read the input text directly from the DOM to recover it — must be synchronous
  // so the value is restored before save/click handlers fire.
  if (!form.customer_id) {
    const input = customerSelectRef.value?.$el?.querySelector('input') as HTMLInputElement | null
    const typed = input?.value?.trim()
    if (typed) form.customer_id = typed
  }
}

async function fetchQuote() {
  quote.value = await getQuote(route.params.id as string)
  Object.assign(form, {
    customer_id: quote.value.customer_id || quote.value.customer_name || '',
    project_name: quote.value.project_name,
    tax_rate: quote.value.tax_rate,
    discount_amount: quote.value.discount_amount,
    valid_until: quote.value.valid_until || '',
    remark: quote.value.remark || '',
    department: quote.value.department || '',
    contact_person: quote.value.contact_person || '',
    contact_phone: quote.value.contact_phone || '',
  })
  items.value = quote.value.items?.length
    ? quote.value.items.map(i => migrateLegacyQuoteDimensions({ ...i }))
    : [newItem()]
  captureCleanSnapshot()
}

function isExistingCustomer(value: string): boolean {
  return customerOptions.value.some(c => c.id === value)
}

function buildCustomerPayload(): Record<string, string> {
  if (form.customer_id && isExistingCustomer(form.customer_id)) {
    return { customer_id: form.customer_id }
  }
  if (form.customer_id) {
    return { customer_name: form.customer_id }
  }
  return {}
}

async function handleImageUpload(opt: { file: File }, item: QuoteItemResponse) {
  try {
    const res = await uploadAttachment('quote_item', item.id || route.params.id as string, opt.file, 'image')
    item.image_url = `/uploads/${res.file_path}`
    ElMessage.success('上传成功')
  } catch {
    ElMessage.error('上传失败')
  }
}

async function onImportItems(uploadFile: unknown) {
  const file = (uploadFile as { raw?: File }).raw || uploadFile as File
  if (!file) return
  importingItems.value = true
  try {
    let targetId = quoteId.value
    if (!isEdit.value) {
      // 新建模式：先保存报价获取 ID
      if (!form.customer_id && !form.project_name) {
        ElMessage.warning('请先填写客户和项目名称')
        importingItems.value = false
        return
      }
      targetId = await saveNewAndGetId()
    }
    await importQuoteItems(targetId, file)
    if (!isEdit.value) {
      await router.replace(`/quotes/${targetId}/edit`)
    }
    await fetchQuote()
    dirty.value = false
    captureCleanSnapshot()
    ElMessage.success('导入成功')
  } catch { /* handled by interceptor */ } finally {
    importingItems.value = false
  }
}

async function doCreateNewQuote(): Promise<QuoteDetailResponse> {
  items.value.forEach(item => calcItemSubtotal(item))
  const cleanItems = items.value.map((item, idx) => ({
    ...(item.id ? { id: item.id } : {}),
    item_name: item.item_name || '待填写',
    product_id: item.product_id || undefined,
    width: item.width || undefined,
    width_unit: item.width_unit || undefined,
    height: item.height || undefined,
    height_unit: item.height_unit || undefined,
    quantity: item.quantity || 1,
    unit: item.unit || null,
    use_area: item.use_area || false,
    pieces: item.pieces || 1,
    unit_price: item.unit_price || 0,
    process_fee: item.process_fee || 0,
    installation_fee: item.installation_fee || 0,
    design_fee: item.design_fee || 0,
    transport_fee: item.transport_fee || 0,
    other_fee: item.other_fee || 0,
    remark: item.remark || undefined,
    image_url: item.image_url || undefined,
    sort_order: idx,
    group_name: item.group_name || null,
    material_process: item.material_process || undefined,
  }))
  const payload: Record<string, unknown> = {
    ...form,
    ...buildCustomerPayload(),
    items: cleanItems,
  }
  if (!payload.valid_until) delete payload.valid_until
  if (!payload.remark) delete payload.remark
  if (!payload.contact_person) delete payload.contact_person
  if (!payload.contact_phone) delete payload.contact_phone
  if (!isExistingCustomer(form.customer_id)) delete payload.customer_id
  return createQuote(payload)
}

async function saveNewAndGetId(): Promise<string> {
  const result = await doCreateNewQuote()
  return result.id
}

async function handleSave() {
  saving.value = true
  try {
    // 更新所有 items 的小计
    items.value.forEach(item => calcItemSubtotal(item))

    if (isEdit.value) {
      // Prepare items for update - only send editable fields
      const cleanItems = items.value.map((item, idx) => ({
        ...(item.id ? { id: item.id } : {}),
        item_name: item.item_name,
        product_id: item.product_id || undefined,
        width: item.width || undefined,
        width_unit: item.width_unit || undefined,
        height: item.height || undefined,
        height_unit: item.height_unit || undefined,
        quantity: item.quantity,
        unit: item.unit || undefined,
        use_area: item.use_area || false,
        pieces: item.pieces || 1,
        unit_price: item.unit_price || 0,
        process_fee: item.process_fee || 0,
        installation_fee: item.installation_fee || 0,
        design_fee: item.design_fee || 0,
        transport_fee: item.transport_fee || 0,
        other_fee: item.other_fee || 0,
        remark: item.remark || undefined,
        image_url: item.image_url || undefined,
        sort_order: idx,
        group_name: item.group_name || undefined,
        material_process: item.material_process || undefined,
      }))
      await updateQuote(route.params.id as string, {
        ...buildCustomerPayload(),
        project_name: form.project_name,
        tax_rate: form.tax_rate,
        discount_amount: form.discount_amount,
        valid_until: form.valid_until || undefined,
        remark: form.remark,
        department: form.department || undefined,
        contact_person: form.contact_person || undefined,
        contact_phone: form.contact_phone || undefined,
        items: cleanItems,
      })
      ElMessage.success('保存成功')
      dirty.value = false
      captureCleanSnapshot()
    } else {
      const result = await doCreateNewQuote()
      ElMessage.success('创建成功')
      dirty.value = false
      captureCleanSnapshot()
      await router.replace(`/quotes/${result.id}/edit`)
    }
  } finally { saving.value = false }
}

async function handleConfirm() {
  await ElMessageBox.confirm('确认后报价将锁定，确定确认此报价？', '确认报价', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await confirmQuote(route.params.id as string)
  ElMessage.success('报价已确认')
  dirty.value = false
  await fetchQuote()
  await aiStore.notifyBusinessMutation()
}

async function handleConvert() {
  await ElMessageBox.confirm('确认将此报价转为订单？此操作不可撤销。', '转订单', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  converting.value = true
  try {
    const order = await convertQuoteToOrder(route.params.id as string)
    ElMessage.success('已转为订单')
    // 转单后同一条单据已变为订单，旧报价上下文刷新流程引导会报"报价单不存在"，
    // 这里不刷新，跳转到订单页后页面上下文会自动更新为订单再触发引导
    await router.push(`/orders/${order.id}`)
  } finally { converting.value = false }
}

async function handleRevertToDraft() {
  await ElMessageBox.confirm('确认将此报价撤回为草稿？撤回后可编辑修改。', '转草稿', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  reverting.value = true
  try {
    quote.value = await revertQuoteToDraft(route.params.id as string)
    ElMessage.success('已撤回为草稿')
    await aiStore.notifyBusinessMutation()
  } finally { reverting.value = false }
}

onMounted(async () => {
  await loadCustomers()
  if (route.params.id) {
    await fetchQuote()
  } else {
    // 新建报价：初始空白状态作为干净快照
    captureCleanSnapshot()
  }
})

watch(() => route.params.id, async (newId) => {
  if (newId) {
    await fetchQuote()
  }
})
</script>

<style scoped>
.page { padding: 0; }
.section-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.summary-item { margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.summary-item.total { font-size: 18px; color: #e63946; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--ad-border); }
/* 分项色块追踪：整块（分项表头→分项合计）统一同色浅底，覆盖斑马纹；5 色按分组序号循环 */
:deep(.group-c1 td),
:deep(.group-c2 td),
:deep(.group-c3 td),
:deep(.group-c4 td),
:deep(.group-c5 td) {
  background: rgba(var(--ad-g), 0.08) !important;
}
/* 每组绑定 --ad-g */
:deep(.group-c1) { --ad-g: var(--ad-group-1); }
:deep(.group-c2) { --ad-g: var(--ad-group-2); }
:deep(.group-c3) { --ad-g: var(--ad-group-3); }
:deep(.group-c4) { --ad-g: var(--ad-group-4); }
:deep(.group-c5) { --ad-g: var(--ad-group-5); }
/* 左侧连续色条：贯穿表头→明细→合计整块 */
:deep(.group-c1 td:first-child),
:deep(.group-c2 td:first-child),
:deep(.group-c3 td:first-child),
:deep(.group-c4 td:first-child),
:deep(.group-c5 td:first-child) {
  box-shadow: inset 3px 0 0 rgba(var(--ad-g), 0.85);
}
/* 分项表头：顶部同色边 = 色块上缘 */
:deep(.group-header-row td:not(:first-child)) { box-shadow: inset 0 2px 0 rgba(var(--ad-g), 0.85); }
:deep(.group-header-row td:first-child) { box-shadow: inset 3px 0 0 rgba(var(--ad-g), 0.85), inset 0 2px 0 rgba(var(--ad-g), 0.85); }
/* 分项合计：底部同色边 = 色块下缘；合计行加粗 */
:deep(.group-total-row td:not(:first-child)) { box-shadow: inset 0 -2px 0 rgba(var(--ad-g), 0.85); font-weight: 600; }
:deep(.group-total-row td:first-child) { box-shadow: inset 3px 0 0 rgba(var(--ad-g), 0.85), inset 0 -2px 0 rgba(var(--ad-g), 0.85); font-weight: 600; }

/* 修复 el-input-number 默认宽度(120px)超出窄列的问题 */
:deep(.el-table .el-input-number) { width: 100%; }

/* 出现横向滚动时，滚动条始终可见，且与最后一行、表格底部边框保持间距 */
:deep(.el-table.el-table--scrollable-x .el-scrollbar__view) { padding-bottom: 12px; }
:deep(.el-table.el-table--scrollable-x .el-table__body-wrapper) { margin-bottom: 8px; }

/* 拖拽排序（Sortablejs）反馈 */
.row-drag-handle { cursor: grab; color: var(--ad-text-secondary, #909399); display: inline-flex; align-items: center; user-select: none; font-size: 15px; line-height: 1; }
.row-drag-handle:hover { color: var(--ad-primary, #409eff); }
:deep(.ad-drag-dragging) { cursor: grabbing; }
:deep(.ad-drag-ghost) { opacity: 0.4; }
:deep(.ad-drag-ghost td) { background: rgba(148, 163, 184, 0.15) !important; }
:deep(.ad-drag-chosen td) { background: rgba(var(--ad-g, 148, 163, 184), 0.25) !important; }
</style>

<style>
/* 组拖拽（整组跟随）：源分项整块"选中感"——高亮 + 轻微降透明 */
body.ad-group-drag tr.ad-drag-lifted td { background: rgba(var(--ad-g, 64, 158, 255), 0.22) !important; }
body.ad-group-drag tr.ad-drag-lifted { opacity: 0.72 !important; }

/* 组拖拽：整组概要卡片跟随光标（Notion 式），挂在 body 上，须全局样式 */
.ad-drag-card {
  position: fixed; left: 0; top: 0; z-index: 9999; pointer-events: none;
  min-width: 200px; max-width: 340px; padding: 8px 14px 8px 12px;
  background: #fff; border-radius: 8px;
  border: 1px solid rgba(var(--ad-g), 0.4); border-left: 4px solid rgba(var(--ad-g), 0.95);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.18);
  font-size: 13px; line-height: 1.6; color: #1f2329; will-change: transform;
}
.ad-drag-card__name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ad-drag-card__meta { color: #909399; font-size: 12px; }

/* 分项名称标签可直接拖起整组（输入框仍可正常编辑） */
.group-header-drag { cursor: grab; user-select: none; }
.group-header-drag:hover { color: var(--ad-primary, #409eff); }
</style>
