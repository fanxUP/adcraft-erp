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
          <el-input v-model="form.contact_person" :disabled="isReadonly" placeholder="联系人姓名" style="width: 160px" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" :disabled="isReadonly" placeholder="手机/电话" style="width: 160px" />
        </el-form-item>
        <el-form-item label="税率">
          <el-input-number v-model="form.tax_rate" :precision="4" :min="0" :step="0.01" :disabled="isReadonly" style="width: 160px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
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
            <el-upload
              v-if="!isReadonly && isEdit"
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

      <el-table :data="displayRows" stripe border :row-class-name="rowClassName">
        <el-table-column label="项目内容" min-width="160">
          <template #default="{ row }">
            <template v-if="row.type === 'group-header'">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-weight: 600; white-space: nowrap;">分项：</span>
                <el-input v-if="!isReadonly" :model-value="row.groupName" size="small" style="flex: 1" placeholder="输入分项名称" @input="(v: string) => renameGroup(row.groupName, v)" />
                <span v-else style="font-weight: 600;">{{ row.groupName }}</span>
              </div>
            </template>
            <template v-else-if="row.type === 'group-total'">
              <span style="font-weight: 600; float: right;">分项合计</span>
            </template>
            <template v-else>
              <el-input v-model="row.item.item_name" :disabled="isReadonly" size="small" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="材质工艺" min-width="140">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <el-input v-model="row.item.material_process" :disabled="isReadonly" size="small" placeholder="材质/工艺" />
            </template>
          </template>
        </el-table-column>
        <el-table-column label="长" width="170">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <div style="display: flex; align-items: center; gap: 4px;">
                <el-input-number v-model="row.item.length" :precision="2" :min="0" :disabled="isReadonly" size="small" :controls="false" style="width: 90px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" @change="syncAreaQuantity(row.item)" />
                <el-select v-model="row.item.length_unit" :disabled="isReadonly" size="small" placeholder="选择" style="width: 65px" @change="syncAreaQuantity(row.item)">
                  <el-option label="选择" value="" disabled />
                  <el-option label="m" value="m" />
                  <el-option label="cm" value="cm" />
                  <el-option label="mm" value="mm" />
                </el-select>
              </div>
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
            <el-input-number v-model="form.discount_amount" :precision="2" :min="0" :disabled="isReadonly" size="small" style="width: 140px" @click="(e: MouseEvent) => (e.target as HTMLInputElement).select()" />
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
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import QuoteWorkflow from './QuoteWorkflow.vue'
import { useRoute, useRouter } from 'vue-router'
import { onBeforeRouteLeave } from 'vue-router'
import { createQuote, getQuote, updateQuote, confirmQuote, convertQuoteToOrder, revertQuoteToDraft, importQuoteItems } from '@/api/quotes'
import { getCustomers } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadAttachment } from '@/api/tasks'
import type { QuoteItemResponse, QuoteDetailResponse, CustomerResponse } from '@/types/api'
import QuotePreview from './QuotePreview.vue'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const converting = ref(false)
const reverting = ref(false)
const importingItems = ref(false)
const customerSelectRef = ref()
const quote = ref<QuoteDetailResponse | null>(null)
const customerOptions = ref<CustomerResponse[]>([])
const previewVisible = ref(false)
const quoteId = computed(() => route.params.id as string)

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
  length: undefined,
  length_unit: '',
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
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

const isReadonly = computed(() => {
  if (!isEdit.value || !quote.value) return false
  return quote.value.status === 'converted' || quote.value.status === 'cancelled'
})

function convertToMeters(value: number, unit: string): number {
  switch (unit) {
    case 'cm': return value / 100
    case 'mm': return value / 1000
    default: return value // m
  }
}

function calcArea(item: QuoteItemResponse) {
  const length = convertToMeters(item.length || 0, item.length_unit || 'm')
  const width = convertToMeters(item.width || 0, item.width_unit || 'm')
  const raw = length * width * (item.pieces || 1)
  return Math.round(raw * 100) / 100
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
  // 当长/宽变化时，如果处于面积模式，自动更新数量
  if (item.use_area) {
    item.quantity = Math.max(0.01, calcArea(item))
  }
}

function calcSubtotal(item: QuoteItemResponse) {
  const base = item.use_area
    ? calcArea(item)  // 面积 = 长 × 宽
    : (item.quantity || 0)
  return base * (item.unit_price || 0)
    + (item.process_fee || 0)
    + (item.installation_fee || 0)
    + (item.design_fee || 0)
    + (item.transport_fee || 0)
    + (item.other_fee || 0)
}

function calcItemSubtotal(item: QuoteItemResponse) {
  const subtotal = calcSubtotal(item)
  item.subtotal_amount = subtotal
  return subtotal
}

function calcQuoteSubtotal() { return items.value.reduce((s, i) => s + calcSubtotal(i), 0) }
function calcTax() { return (calcQuoteSubtotal() - (form.discount_amount || 0)) * (form.tax_rate || 0) }
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
  | { type: 'group-header'; groupName: string }
  | { type: 'item'; item: QuoteItemResponse; groupName: string }
  | { type: 'group-total'; groupName: string; total: number }

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
  for (const [groupName, groupItems] of grouped) {
    rows.push({ type: 'group-header', groupName })
    for (const item of groupItems) rows.push({ type: 'item', item, groupName })
    const total = groupItems.reduce((s, i) => s + calcSubtotal(i), 0)
    rows.push({ type: 'group-total', groupName, total })
  }
  for (const item of ungrouped) rows.push({ type: 'item', item, groupName: '' })
  return rows
})

function rowClassName({ row }: { row: DisplayRow }) {
  if (row.type === 'group-header') return 'group-header-row'
  if (row.type === 'group-total') return 'group-total-row'
  return ''
}

// 单位相关
const defaultUnits = ['㎡', 'm', '个', '套', '块', '件', '批', '次', '组', '台']
const recentUnits = ref<string[]>([])
const allUnits = computed(() => [
  ...recentUnits.value.map(u => ({ value: u })),
  ...defaultUnits.map(u => ({ value: u })),
])

function addRecentUnit(unit: string) {
  if (!unit || defaultUnits.includes(unit)) return
  recentUnits.value = [unit, ...recentUnits.value.filter(u => u !== unit)].slice(0, 3)
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
  items.value = quote.value.items?.length ? quote.value.items.map(i => ({ ...i })) : [newItem()]
  captureCleanSnapshot()
}

function isExistingCustomer(value: string): boolean {
  return customerOptions.value.some(c => c.id === value)
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
    const detail = await importQuoteItems(quoteId.value, file)
    if (detail?.items) {
      const existing = items.value
      // Append imported items preserving existing ones
      const imported = detail.items.map((i: QuoteItemResponse) => ({
        ...i,
        _groupTotal: false,
        _groupName: i.group_name || undefined,
      }))
      // Refresh items from response to get proper IDs
      items.value = [...existing.filter((i: QuoteItemResponse) => i.item_name), ...imported]
    }
    ElMessage.success(`导入成功`)
  } catch { /* handled by interceptor */ } finally {
    importingItems.value = false
  }
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
        material_id: item.material_id || undefined,
        process_id: item.process_id || undefined,
        length: item.length || undefined,
        length_unit: item.length_unit || undefined,
        width: item.width || undefined,
        width_unit: item.width_unit || undefined,
        height: item.height || undefined,
        height_unit: item.height_unit || undefined,
        quantity: item.quantity,
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
      await updateQuote(route.params.id as string, {
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
      const cleanItems = items.value.map((item, idx) => ({
        ...(item.id ? { id: item.id } : {}),
        item_name: item.item_name,
        product_id: item.product_id || undefined,
        material_id: item.material_id || undefined,
        process_id: item.process_id || undefined,
        length: item.length || undefined,
        length_unit: item.length_unit || undefined,
        width: item.width || undefined,
        width_unit: item.width_unit || undefined,
        height: item.height || undefined,
        height_unit: item.height_unit || undefined,
        quantity: item.quantity,
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
      const payload: Record<string, unknown> = { ...form, items: cleanItems }
      // Clean empty optional fields that Pydantic would reject
      if (!payload.valid_until) delete payload.valid_until
      if (!payload.remark) delete payload.remark
      if (!payload.contact_person) delete payload.contact_person
      if (!payload.contact_phone) delete payload.contact_phone
      // discount_amount is not a field on QuoteCreate — remove it
      delete payload.discount_amount
      if (form.customer_id && !isExistingCustomer(form.customer_id)) {
        // Typed a new customer name — send as customer_name
        payload.customer_name = form.customer_id
        delete payload.customer_id
      } else if (!form.customer_id) {
        // No customer selected — remove empty field
        delete payload.customer_id
      }
      // else: existing customer UUID stays as customer_id
      const result = await createQuote(payload)
      ElMessage.success('创建成功')
      dirty.value = false
      captureCleanSnapshot()
      const quoteId = result.id
      await router.replace(`/quotes/${quoteId}/edit`)
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
  fetchQuote()
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
    router.push(`/orders/${order.order_id || order.id}`)
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
:deep(.group-header-row) { background: var(--ad-bg-secondary, #f5f7fa) !important; }
:deep(.group-header-row td) { border-bottom: 2px solid var(--ad-primary, #409eff) !important; }
:deep(.group-total-row) { background: var(--ad-bg-secondary, #fafafa) !important; }
:deep(.group-total-row td) { border-top: 1px solid var(--ad-border, #dcdfe6) !important; font-weight: 600; }
</style>
