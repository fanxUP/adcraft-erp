<template>
  <div class="page">
    <el-button text @click="goBack" style="font-size: 16px">
      <el-icon><ArrowLeft /></el-icon> 返回订单
    </el-button>

    <div class="page-title-row">
      <div>
        <h2 style="margin: 16px 0 4px; color: var(--ad-text)">编辑订单 {{ order?.order_no || '' }}</h2>
        <div v-if="order" class="title-meta">
          <span>订单编号：{{ order.order_no }}</span>
          <el-tag :type="statusColor(order.status)" size="small">{{ statusLabel(order.status) }}</el-tag>
          <span v-if="order.source_quote_id">来源报价已锁定，只读引用</span>
        </div>
      </div>
      <div class="title-actions">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!canEdit" @click="handleSave">
          保存订单
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="itemEditability && !canEdit"
      type="warning"
      :closable="false"
      style="margin-bottom: 16px"
      title="当前订单不可编辑"
    >
      <template #default>
        <span v-for="(reason, index) in itemEditability.lock_reasons" :key="reason.code">
          <span v-if="index">；</span>{{ reason.message }}
        </span>
      </template>
    </el-alert>
    <el-alert
      v-else-if="itemEditability?.requires_confirmation"
      type="info"
      :closable="false"
      style="margin-bottom: 16px"
      title="订单保存会一次性预检并展示影响目录"
    >
      当前识别到 {{ itemEditability.association_count }} 条关联记录。保存时会列出关联模块，确认后再整批提交；已发生的付款、库存、验收、结算和合同事实不会被覆盖。
    </el-alert>

    <div v-loading="loading">
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header"><span>订单基本信息</span><el-tag type="info" size="small">订单号/状态/来源只读</el-tag></div>
      </template>
      <el-form :model="form" label-width="100px" inline>
        <el-form-item label="客户" required>
          <el-select
            ref="customerSelectRef"
            v-model="form.customer_id"
            placeholder="选择或输入客户名称"
            filterable
            allow-create
            default-first-option
            :disabled="!canEdit"
            style="width: 260px"
            @visible-change="onCustomerVisible"
            @blur="onCustomerBlur"
          >
            <el-option v-for="customer in customerOptions" :key="customer.id" :label="customer.name" :value="customer.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.project_name" :disabled="!canEdit" style="width: 260px" />
        </el-form-item>
        <el-form-item label="部门/科室">
          <el-input v-model="form.department" :disabled="!canEdit" placeholder="如：宣传部、办公室" style="width: 260px" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-select
            v-model="form.contact_person"
            filterable
            allow-create
            default-first-option
            clearable
            :disabled="!canEdit"
            placeholder="选择联系人或输入"
            style="width: 180px"
            @change="handleContactChange"
            @clear="form.contact_phone = ''"
          >
            <el-option v-for="contact in contactOptions" :key="contact.id" :label="contact.name" :value="contact.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" :disabled="!canEdit" placeholder="手机/电话" style="width: 180px" />
        </el-form-item>
        <el-form-item label="交付日期">
          <el-date-picker v-model="form.delivery_deadline" type="date" value-format="YYYY-MM-DD" :disabled="!canEdit" style="width: 180px" />
        </el-form-item>
        <el-form-item label="安装地址">
          <el-input v-model="form.installation_address" :disabled="!canEdit" placeholder="请输入安装地址" style="width: 360px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" :disabled="!canEdit" placeholder="订单备注" style="width: 360px" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>订单明细</span>
          <div class="toolbar">
            <el-button v-if="canEdit" size="small" type="danger" @click="addGroup">添加分项</el-button>
            <el-button v-if="canEdit" size="small" type="danger" @click="addItem()">添加行</el-button>
          </div>
        </div>
      </template>

      <el-table
        ref="tableRef"
        :data="displayRows"
        stripe
        border
        scrollbar-always-on
        :row-key="(row: DisplayRow) => row.key"
        :row-class-name="rowClassName"
        :row-style="rowStyle"
      >
        <el-table-column v-if="canEdit" label="排序" width="46" align="center">
          <template #default="{ row }">
            <span
              v-if="row.type === 'group-header'"
              class="row-drag-handle"
              title="拖动整个分项"
              @mousedown="dragStartKey = row.key"
              @touchstart.passive="dragStartKey = row.key"
            >⠿</span>
            <span
              v-else-if="row.type === 'item'"
              class="row-drag-handle"
              title="拖动排序"
              @mousedown="dragStartKey = row.key"
              @touchstart.passive="dragStartKey = row.key"
            >
              <el-icon><Rank /></el-icon>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="项目内容" min-width="300">
          <template #default="{ row }">
            <template v-if="row.type === 'group-header'">
              <div class="group-header-content">
                <span class="group-header-drag" title="拖动整个分项">分项名称：</span>
                <el-input
                  v-if="canEdit"
                  :model-value="row.groupName"
                  size="small"
                  placeholder="输入分项名称"
                  @focus="selectInput"
                  @input="(value: string) => renameGroup(row.groupId, value)"
                />
                <span v-else>{{ row.groupName || '未命名分项' }}</span>
              </div>
            </template>
            <template v-else-if="row.type === 'group-total'">
              <span class="group-total-label">分项合计：{{ row.groupName || '未命名分项' }}</span>
            </template>
            <el-input v-else v-model="row.item.item_name" :disabled="!canEdit" size="small" placeholder="项目内容" />
          </template>
        </el-table-column>
        <el-table-column label="产品/材质/工艺" min-width="260">
          <template #default="{ row }">
            <el-input
              v-if="row.type === 'item'"
              v-model="row.item.material_process"
              :disabled="!canEdit"
              size="small"
              placeholder="点击选择产品/材质/工艺"
              clearable
              @click="openProductPicker(row.item)"
              @clear="clearProduct(row.item)"
            />
          </template>
        </el-table-column>
        <el-table-column label="宽" width="168">
          <template #default="{ row }">
            <div v-if="row.type === 'item'" class="dimension-cell">
              <el-input-number v-model="row.item.width" :precision="2" :min="0" :disabled="!canEdit" size="small" :controls="false" @change="syncAreaQuantity(row.item)" />
              <el-select v-model="row.item.width_unit" :disabled="!canEdit" size="small" style="width: 64px" @change="syncAreaQuantity(row.item)">
                <el-option label="m" value="m" /><el-option label="cm" value="cm" /><el-option label="mm" value="mm" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="高" width="168">
          <template #default="{ row }">
            <div v-if="row.type === 'item'" class="dimension-cell">
              <el-input-number v-model="row.item.height" :precision="2" :min="0" :disabled="!canEdit" size="small" :controls="false" @change="syncAreaQuantity(row.item)" />
              <el-select v-model="row.item.height_unit" :disabled="!canEdit" size="small" style="width: 64px" @change="syncAreaQuantity(row.item)">
                <el-option label="m" value="m" /><el-option label="cm" value="cm" /><el-option label="mm" value="mm" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="件数" width="76">
          <template #default="{ row }">
            <el-input-number v-if="row.type === 'item'" v-model="row.item.pieces" :precision="0" :min="1" :disabled="!canEdit" size="small" :controls="false" @change="syncAreaQuantity(row.item)" />
          </template>
        </el-table-column>
        <el-table-column label="面积" width="132">
          <template #default="{ row }">
            <div v-if="row.type === 'item'" class="area-cell">
              <span>{{ calcArea(row.item).toFixed(2) }}</span>
              <el-switch v-model="row.item.use_area" :disabled="!canEdit" size="small" @change="(value: boolean) => onAreaToggle(row.item, value)" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="92">
          <template #default="{ row }">
            <el-input-number v-if="row.type === 'item'" v-model="row.item.quantity" :precision="2" :min="0.01" :disabled="!canEdit || row.item.use_area" size="small" :controls="false" />
          </template>
        </el-table-column>
        <el-table-column label="单位" width="104">
          <template #default="{ row }">
            <el-autocomplete
              v-if="row.type === 'item'"
              v-model="row.item.unit"
              :disabled="!canEdit"
              size="small"
              :fetch-suggestions="(query: string, callback: Function) => queryUnits(query, callback, row.item.unit)"
              placeholder="选择/输入"
              :trigger-on-focus="true"
              @select="(option: { value: string; disabled?: boolean }) => { if (!option.disabled) row.item.unit = option.value }"
              @blur="addRecentUnit(row.item.unit || '')"
            />
          </template>
        </el-table-column>
        <el-table-column label="单价" width="120">
          <template #default="{ row }">
            <el-input-number v-if="row.type === 'item'" v-model="row.item.unit_price" :precision="2" :min="0" :disabled="!canEdit" size="small" :controls="false" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="124">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">¥ {{ calcItemSubtotal(row.item).toFixed(2) }}</template>
            <template v-else-if="row.type === 'group-total'"><strong>¥ {{ row.total.toFixed(2) }}</strong></template>
          </template>
        </el-table-column>
        <el-table-column label="样图" width="90">
          <template #default="{ row }">
            <template v-if="row.type === 'item'">
              <div v-if="row.item.image_url" class="image-cell">
                <el-image :src="row.item.image_url" :preview-src-list="[row.item.image_url]" fit="cover" class="item-image" />
                <el-button v-if="canEdit" text type="danger" size="small" @click="row.item.image_url = ''">×</el-button>
              </div>
              <el-upload v-else-if="canEdit" :show-file-list="false" :http-request="(option: any) => handleImageUpload(option, row.item)" accept="image/*">
                <el-button text type="primary" size="small">上传</el-button>
              </el-upload>
              <span v-else class="muted">-</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="140">
          <template #default="{ row }">
            <el-input v-if="row.type === 'item'" v-model="row.item.remark" :disabled="!canEdit" size="small" />
          </template>
        </el-table-column>
        <el-table-column v-if="canEdit" label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="row.type === 'group-header'">
              <div class="row-actions">
                <el-button text type="primary" size="small" @click="addItem(row.groupId, row.groupName)">添加行</el-button>
                <el-button text type="danger" size="small" @click="removeGroup(row.groupId)">删除组</el-button>
              </div>
            </template>
            <el-button v-else-if="row.type === 'item'" text type="danger" size="small" @click="removeItem(row.item)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="section-card summary-card">
      <el-row :gutter="20">
        <el-col :span="14">
          <el-alert type="info" :closable="false" title="保存前请填写变更原因">
            明细删除会以作废方式留痕；保存后的订单头、明细、分组和关联刷新结果属于同一变更批次。
          </el-alert>
          <el-input
            v-model="reason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            :disabled="!canEdit"
            placeholder="例如：客户确认调整门头尺寸和运输费用"
            style="margin-top: 12px"
          />
        </el-col>
        <el-col :span="10">
          <div class="summary-item"><span>明细合计：</span><strong>¥ {{ localTotal.toFixed(2) }}</strong></div>
          <div class="summary-item"><span>已收金额：</span><strong>¥ {{ (order?.paid_amount || 0).toFixed(2) }}</strong></div>
          <div class="summary-item"><span>未收金额：</span><strong>¥ {{ localUnpaid.toFixed(2) }}</strong></div>
          <div class="summary-item"><span>成本金额：</span><strong>¥ {{ (order?.cost_amount || 0).toFixed(2) }}</strong></div>
          <div class="summary-item total"><span>订单总计：</span><strong>¥ {{ localTotal.toFixed(2) }}</strong></div>
          <div class="amount-words">大写金额：{{ toChineseAmount(localTotal) }}</div>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog
      v-model="impactDialogVisible"
      title="确认修改并刷新关联数据"
      width="1080px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template v-if="preview">
        <el-alert :type="preview.requires_high_risk_ack ? 'warning' : 'info'" :closable="false" style="margin-bottom: 14px">
          <template #title>{{ mutationDecisionLabel(preview.decision) }}</template>
          本次保存将一次性应用 {{ preview.diff.added }} 条新增、{{ preview.diff.updated }} 条修改、{{ preview.diff.deleted }} 条作废，以及 {{ preview.diff.header_changed }} 个订单头字段变更。已发生事实只保留并核对差额。
        </el-alert>

        <el-descriptions :column="3" border size="small" style="margin-bottom: 14px">
          <el-descriptions-item label="订单总额">¥{{ preview.before.total_amount.toFixed(2) }} → ¥{{ preview.after.total_amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="已收金额">¥{{ preview.after.paid_amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="未收金额">¥{{ preview.after.unpaid_amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="成本">¥{{ preview.after.cost_amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="毛利">¥{{ preview.after.gross_profit.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="金额差额"><span :class="preview.delta >= 0 ? 'amount-up' : 'amount-down'">¥{{ preview.delta.toFixed(2) }}</span></el-descriptions-item>
        </el-descriptions>

        <div v-if="preview.header_diff.length" class="impact-section-title">订单头字段变更</div>
        <el-table v-if="preview.header_diff.length" :data="preview.header_diff" border size="small" style="margin-bottom: 12px">
          <el-table-column prop="field" label="字段" width="160" />
          <el-table-column label="变更前" min-width="230"><template #default="{ row }">{{ displayValue(row.before) }}</template></el-table-column>
          <el-table-column label="变更后" min-width="230"><template #default="{ row }">{{ displayValue(row.after) }}</template></el-table-column>
        </el-table>

        <div v-if="preview.item_diffs.length" class="impact-section-title">明细差异</div>
        <el-table v-if="preview.item_diffs.length" :data="preview.item_diffs" border stripe size="small" max-height="230" style="margin-bottom: 12px">
          <el-table-column label="操作" width="75"><template #default="{ row }">{{ mutationOperationLabel(row.operation) }}</template></el-table-column>
          <el-table-column prop="item_name" label="项目内容" min-width="180" />
          <el-table-column label="变更字段" min-width="240"><template #default="{ row }">{{ row.changed_fields.join('、') || '-' }}</template></el-table-column>
          <el-table-column label="变更后小计" width="130"><template #default="{ row }">{{ amountFromDiff(row.after) }}</template></el-table-column>
        </el-table>

        <div class="impact-section-title">关联目录（{{ preview.association_catalog.length }} 条）</div>
        <el-table v-if="preview.association_catalog.length" :data="preview.association_catalog" border stripe size="small" max-height="300">
          <el-table-column prop="label" label="关联模块" width="130" />
          <el-table-column label="记录编号" min-width="150"><template #default="{ row }">{{ row.record_no || row.record_id }}</template></el-table-column>
          <el-table-column label="关联方式" width="95"><template #default="{ row }">{{ relationTypeLabel(row.relation_type) }}</template></el-table-column>
          <el-table-column label="状态" width="105"><template #default="{ row }">{{ relationStatusLabel(row.status) }}</template></el-table-column>
          <el-table-column label="处理动作" min-width="190"><template #default="{ row }">{{ relationActionLabel(row.action) }}</template></el-table-column>
          <el-table-column label="风险" width="70"><template #default="{ row }"><el-tag :type="riskTagType(row.risk)" size="small">{{ riskLabel(row.risk) }}</el-tag></template></el-table-column>
          <el-table-column label="说明" min-width="250"><template #default="{ row }">{{ row.note || '-' }}</template></el-table-column>
        </el-table>
        <el-empty v-else description="本次没有可识别的关联记录" :image-size="60" />

        <el-checkbox v-if="preview.requires_high_risk_ack" v-model="highRiskAcknowledged" style="margin-top: 14px">
          我已阅读上述高风险关联项，确认提交本次订单修改，并接受系统生成的差异/待复核项。
        </el-checkbox>
      </template>
      <template #footer>
        <el-button @click="cancelImpactConfirmation">返回修改</el-button>
        <el-button type="primary" :loading="saving" :disabled="Boolean(preview?.requires_high_risk_ack && !highRiskAcknowledged)" @click="confirmImpactAndApply">
          确认修改并刷新关联数据
        </el-button>
      </template>
    </el-dialog>

    </div>
    <ProductPickerDialog v-model="productPickerVisible" :customer-id="form.customer_id" @selected="onProductPicked" @updated="onProductUpdated" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeMount, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import Sortable from 'sortablejs'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCustomers, getCustomer } from '@/api/customers'
import { getOrder, getOrderItemEditability, previewOrderEdit, saveOrderEdit } from '@/api/orders'
import { uploadAttachment } from '@/api/tasks'
import ProductPickerDialog from '@/components/ProductPickerDialog.vue'
import { applyProductMaterialProcess, formatProductMaterialProcess } from '@/utils/productMaterialProcess'
import { createQuoteGroupDragVisual, type QuoteGroupDragVisual } from '@/utils/quoteGroupDragVisual'
import { createQuoteGroupColorRegistry } from '@/utils/quoteGroupColors'
import { calcQuoteLineArea, calcQuoteLineSubtotal, migrateLegacyQuoteDimensions, syncQuoteLineAreaQuantity } from '@/utils/quoteLineCalculation'
import { applyQuoteDisplayOrder, buildQuoteDisplayRows, getQuoteDropSuccessorKey, getQuoteGroupBlock, isDuplicateQuoteGroupName, reorderQuoteDisplayRows, type QuoteEmptyGroup, type QuoteDisplayRow } from '@/utils/quoteItemOrdering'
import { buildOrderBatchItemDiff, buildOrderGroupPayload, serializeOrderItemDraft, type OrderEditorEmptyGroup } from '@/utils/orderEditorDraft'
import type { ContactResponse, CustomerResponse, OrderDetailResponse, OrderEditImpactResponse, OrderItemEditabilityResponse, OrderItemResponse, ProductResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()
const orderId = computed(() => route.params.id as string)
const order = ref<OrderDetailResponse | null>(null)
const itemEditability = ref<OrderItemEditabilityResponse | null>(null)
const loading = ref(false)
const saving = ref(false)
const customerOptions = ref<CustomerResponse[]>([])
const contactOptions = ref<ContactResponse[]>([])
const customerSelectRef = ref()
const tableRef = ref()
const items = ref<OrderItemResponse[]>([])
const originalItems = ref<OrderItemResponse[]>([])
const emptyGroups = ref<OrderEditorEmptyGroup[]>([])
const reason = ref('')
const dirty = ref(false)
const isLoaded = ref(false)
const impactDialogVisible = ref(false)
const highRiskAcknowledged = ref(false)
const preview = ref<OrderEditImpactResponse | null>(null)
const pendingPayload = ref<ReturnType<typeof buildPayload> | null>(null)
const productPickerVisible = ref(false)
const pendingPickerItem = ref<OrderItemResponse | null>(null)
const groupColors = createQuoteGroupColorRegistry()
const dragStartKey = ref<string | null>(null)
let sortable: Sortable | null = null
let dragDropSuccessorKey: string | null = null
let groupDragVisual: QuoteGroupDragVisual | null = null
let groupDragSourceKeys = new Set<string>()
let itemKeySeq = 0
const itemKeyMap = new WeakMap<OrderItemResponse, string>()
let cleanSnapshot = ''

const form = reactive({
  customer_id: '',
  project_name: '',
  department: '',
  contact_person: '',
  contact_phone: '',
  delivery_deadline: '',
  installation_address: '',
  remark: '',
})

const canEdit = computed(() => itemEditability.value?.can_edit_items === true)
const localTotal = computed(() => items.value.reduce((sum, item) => sum + calcQuoteLineSubtotal(item), 0))
const localUnpaid = computed(() => Math.max(0, localTotal.value - (order.value?.paid_amount || 0)))

type DisplayRow = QuoteDisplayRow<OrderItemResponse>

function rowKeyFor(item: OrderItemResponse): string {
  let key = itemKeyMap.get(item)
  if (!key) {
    key = `order-item-${itemKeySeq++}`
    itemKeyMap.set(item, key)
  }
  return key
}

function newItem(groupId?: string, groupName?: string): OrderItemResponse {
  return {
    id: '',
    item_name: '',
    product_id: undefined,
    material_id: undefined,
    process_id: undefined,
    length: undefined,
    length_unit: 'm',
    width: undefined,
    width_unit: 'm',
    height: undefined,
    height_unit: 'm',
    quantity: 1,
    unit: '',
    use_area: false,
    quantity_mode: 'piece',
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
    sort_order: items.value.length,
    group_id: groupId,
    group_name: groupName,
    material_process: '',
  }
}

function snapshotValue() {
  return JSON.stringify({
    form: { ...form },
    reason: reason.value,
    items: items.value.map(item => ({ ...serializeOrderItemDraft(item), subtotal_amount: calcQuoteLineSubtotal(item) })),
    emptyGroups: emptyGroups.value,
  })
}

function captureCleanSnapshot() {
  cleanSnapshot = snapshotValue()
  isLoaded.value = true
  dirty.value = false
}

function hasUnsavedChanges() {
  return isLoaded.value && snapshotValue() !== cleanSnapshot
}

watch([form, items, emptyGroups, reason], () => { dirty.value = hasUnsavedChanges() }, { deep: true })

onBeforeRouteLeave((_to, _from, next) => {
  if (!dirty.value) return next()
  ElMessageBox.confirm('您有未保存的修改，确定要离开吗？离开后修改将丢失。', '未保存的修改', {
    confirmButtonText: '离开', cancelButtonText: '取消', type: 'warning',
  }).then(() => next()).catch(() => next(false))
})

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onBeforeMount(() => window.addEventListener('beforeunload', handleBeforeUnload))
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  sortable?.destroy()
  sortable = null
  document.removeEventListener('dragover', handleDragPointer, true)
  document.removeEventListener('touchmove', handleDragPointer, true)
  groupDragVisual?.dispose()
  groupDragVisual = null
})

function displayRowsFor(itemsToDisplay = items.value): DisplayRow[] {
  return buildQuoteDisplayRows(itemsToDisplay, rowKeyFor, calcQuoteLineSubtotal, groupColors.colorFor, emptyGroups.value as QuoteEmptyGroup[])
}

const displayRows = computed(() => displayRowsFor())
const sortableStructure = computed(() => displayRows.value.map(row => row.key).join('|'))

function rowClassName({ row, rowIndex }: { row: DisplayRow; rowIndex: number }) {
  const classes: string[] = [`rk-${row.key}`]
  if (row.colorIndex > 0) classes.push('quote-group-row')
  if (row.type === 'group-header') classes.push('group-header-row')
  if (row.type === 'group-header' && rowIndex > 0) classes.push('group-card-gap')
  if (row.type === 'group-total') classes.push('group-total-row')
  return classes.join(' ')
}

function rowStyle({ row }: { row: DisplayRow }) {
  return row.colorIndex > 0 ? { '--ad-g': `var(--ad-group-${row.colorIndex})` } : undefined
}

function initSortable() {
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody') as HTMLElement | null
  if (sortable) sortable.destroy()
  sortable = null
  if (!tbody || !canEdit.value) return
  sortable = Sortable.create(tbody, {
    handle: '.row-drag-handle, .group-header-drag',
    animation: 150,
    ghostClass: 'ad-drag-ghost',
    chosenClass: 'ad-drag-chosen',
    dragClass: 'ad-drag-dragging',
    fallbackClass: 'ad-drag-fallback',
    setData(dataTransfer, draggedElement) {
      dataTransfer.setData('Text', draggedElement.textContent ?? '')
      if (!dragStartKey.value?.startsWith('gh-')) return
      const blank = document.createElement('canvas')
      blank.width = blank.height = 0
      dataTransfer.setDragImage(blank, 0, 0)
    },
    onStart: handleDragStart,
    onMove: handleDragMove,
    onEnd: handleDragEnd,
  })
}

function handleDragStart(evt: Sortable.SortableEvent) {
  const key = dragStartKey.value || rowKeyFromElement(evt.item) || displayRows.value[evt.oldIndex ?? 0]?.key
  const dragged = key ? displayRows.value.find(row => row.key === key) : undefined
  if (!dragged || dragged.type === 'group-total') return

  dragStartKey.value = key
  dragDropSuccessorKey = key
  document.addEventListener('dragover', handleDragPointer, true)
  document.addEventListener('touchmove', handleDragPointer, { capture: true, passive: true })
  if (dragged.type !== 'group-header') return

  const rows = displayRows.value
  const headerIndex = rows.indexOf(dragged)
  const block = getQuoteGroupBlock(rows, headerIndex)
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody') as HTMLElement | null
  groupDragSourceKeys = new Set(block.map(row => row.key))
  const originalEvent = (evt as { originalEvent?: MouseEvent | TouchEvent }).originalEvent
  const point = dragPoint(originalEvent)
  groupDragVisual = createQuoteGroupDragVisual({
    colorIndex: dragged.colorIndex,
    sourceElements: block
      .map(row => tbody?.querySelector(`.rk-${row.key}`) as HTMLElement | null)
      .filter((element): element is HTMLElement => Boolean(element)),
    rows: block.map((row, index) => {
      if (row.type === 'group-header') return { type: row.type, label: `⠿ 分项名称：${row.groupName}` }
      if (row.type === 'group-total') return { type: row.type, label: `分项合计：¥ ${row.total.toFixed(2)}` }
      return {
        type: row.type,
        label: `${index}. ${row.item.item_name?.trim() || '未填写项目内容'}`,
        amount: `¥ ${calcItemSubtotal(row.item).toFixed(2)}`,
      }
    }),
    clientX: point.x,
    clientY: point.y,
  })
}

function handleDragPointer(event: Event) {
  const draggedKey = dragStartKey.value
  if (!draggedKey) return
  const point = dragPoint(event)
  groupDragVisual?.move(point.x, point.y)
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody') as HTMLElement | null
  if (!tbody || point.y >= tbody.getBoundingClientRect().bottom) {
    dragDropSuccessorKey = null
    showGroupDropIndicator(null)
    return
  }
  const target = document.elementFromPoint(point.x, point.y)?.closest('tr') as HTMLElement | null
  if (!target || !tbody.contains(target)) return
  const targetKey = rowKeyFromElement(target)
  if (!targetKey) return
  const rect = target.getBoundingClientRect()
  dragDropSuccessorKey = getQuoteDropSuccessorKey(displayRows.value, draggedKey, targetKey, point.y >= rect.top + rect.height / 2)
  showGroupDropIndicator(dragDropSuccessorKey)
}

function handleDragMove(_evt: Sortable.MoveEvent, originalEvent: Event) {
  handleDragPointer(originalEvent)
  return false
}

function showGroupDropIndicator(successorKey: string | null) {
  if (!groupDragSourceKeys.size || (successorKey && groupDragSourceKeys.has(successorKey))) {
    groupDragVisual?.showBoundary(null)
    return
  }
  const tbody = tableRef.value?.$el?.querySelector('.el-table__body-wrapper tbody') as HTMLElement | null
  if (!tbody) return
  if (successorKey) {
    groupDragVisual?.showBoundary(tbody.querySelector(`.rk-${successorKey}`), 'before')
    return
  }
  const lastTarget = [...displayRows.value].reverse().find(row => !groupDragSourceKeys.has(row.key))
  if (lastTarget) groupDragVisual?.showBoundary(tbody.querySelector(`.rk-${lastTarget.key}`), 'after')
}

function cleanupDrag() {
  document.removeEventListener('dragover', handleDragPointer, true)
  document.removeEventListener('touchmove', handleDragPointer, true)
  dragStartKey.value = null
  groupDragVisual?.dispose()
  groupDragVisual = null
  groupDragSourceKeys.clear()
  dragDropSuccessorKey = null
}

function handleDragEnd(evt: Sortable.SortableEvent) {
  const draggedKey = dragStartKey.value || (evt.oldIndex == null ? '' : displayRows.value[evt.oldIndex]?.key)
  const successorKey = dragDropSuccessorKey
  cleanupDrag()
  if (!draggedKey) return

  const rows = displayRows.value
  const nextRows = reorderQuoteDisplayRows(rows, draggedKey, successorKey)
  if (nextRows === rows) return

  const draggedRow = rows.find(row => row.key === draggedKey)
  const nextItems = applyQuoteDisplayOrder(nextRows)
  if (draggedRow?.type === 'item') {
    const previousGroupNames = new Map<string, string>()
    for (const row of rows) if (row.type === 'group-header') previousGroupNames.set(row.groupId, row.groupName)

    const nextGroupIds = new Set(nextItems.map(item => item.group_id).filter((value): value is string => Boolean(value)))
    for (const [groupId, groupName] of previousGroupNames) {
      const hadDetail = rows.some(row => row.type === 'item' && row.groupId === groupId)
      if (hadDetail && !nextGroupIds.has(groupId) && !emptyGroups.value.some(group => group.groupId === groupId)) {
        emptyGroups.value.push({ groupId, groupName })
      }
    }
    if (nextGroupIds.size) emptyGroups.value = emptyGroups.value.filter(group => !nextGroupIds.has(group.groupId))
  }
  nextItems.forEach((item, index) => { item.sort_order = index })
  items.value = nextItems
}

function rowKeyFromElement(element: HTMLElement): string {
  return String(element.className || '').split(/\s+/).find(value => value.startsWith('rk-'))?.slice(3) || ''
}

function dragPoint(event?: Event): { x: number; y: number } {
  if (!event) return { x: 0, y: 0 }
  const point = event as MouseEvent | TouchEvent
  const touch = 'touches' in point ? (point.touches[0] ?? point.changedTouches[0]) : undefined
  return {
    x: touch?.clientX ?? ('clientX' in point ? point.clientX : 0),
    y: touch?.clientY ?? ('clientY' in point ? point.clientY : 0),
  }
}

watch([sortableStructure, canEdit], () => nextTick(initSortable))

function selectInput(event: FocusEvent) { (event.target as HTMLInputElement).select() }

function addItem(groupId?: string, groupName?: string) {
  if (groupId) emptyGroups.value = emptyGroups.value.filter(group => group.groupId !== groupId)
  const item = newItem(groupId, groupName)
  item.sort_order = items.value.length
  items.value.push(item)
}

function addGroup() {
  const used = new Set([
    ...items.value.map(item => item.group_name).filter((name): name is string => Boolean(name)),
    ...emptyGroups.value.map(group => group.groupName).filter((name): name is string => Boolean(name)),
  ])
  let index = 1
  while (used.has(`分项${index}`)) index++
  const groupId = `order-group-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
  emptyGroups.value.push({ groupId, groupName: `分项${index}` })
}

function removeGroup(groupId: string) {
  const groupItems = items.value.filter(item => item.group_id === groupId)
  if (groupItems.length) {
    ElMessageBox.confirm(`删除分项后，其中 ${groupItems.length} 条明细会在保存时作废，是否继续？`, '删除分项', {
      confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning',
    }).then(() => {
      items.value = items.value.filter(item => item.group_id !== groupId)
      emptyGroups.value = emptyGroups.value.filter(group => group.groupId !== groupId)
    }).catch(() => undefined)
    return
  }
  emptyGroups.value = emptyGroups.value.filter(group => group.groupId !== groupId)
}

function removeItem(item: OrderItemResponse) {
  const index = items.value.indexOf(item)
  if (index < 0) return
  const groupId = item.group_id || ''
  const groupName = item.group_name || ''
  items.value.splice(index, 1)
  if (groupId && !items.value.some(current => current.group_id === groupId) && !emptyGroups.value.some(group => group.groupId === groupId)) {
    emptyGroups.value.push({ groupId, groupName })
  }
}

function renameGroup(groupId: string, name: string) {
  const newName = name.trim()
  if (isDuplicateQuoteGroupName(items.value, groupId, newName) || emptyGroups.value.some(group => group.groupId !== groupId && group.groupName === newName)) {
    ElMessage.warning('分项名称不能重复，否则两组明细会合并')
    return
  }
  items.value.forEach(item => { if (item.group_id === groupId) item.group_name = newName || undefined })
  const empty = emptyGroups.value.find(group => group.groupId === groupId)
  if (empty) empty.groupName = newName
}

function calcArea(item: OrderItemResponse) { return calcQuoteLineArea(item) }
function calcItemSubtotal(item: OrderItemResponse) {
  const value = calcQuoteLineSubtotal(item)
  item.subtotal_amount = value
  return value
}
function syncAreaQuantity(item: OrderItemResponse) { syncQuoteLineAreaQuantity(item) }
function onAreaToggle(item: OrderItemResponse, enabled: boolean) {
  item.use_area = enabled
  if (enabled) {
    syncAreaQuantity(item)
  } else {
    item.quantity = 1
    item.unit = ''
  }
}

const defaultUnits = ['㎡', 'm', '个', '套', '块', '件', '批', '次', '组', '台']
const recentUnits = ref<string[]>([])
const allUnits = computed(() => [...recentUnits.value.map(value => ({ value })), ...defaultUnits.map(value => ({ value }))])
function queryUnits(query: string, callback: (result: Array<{ value: string; disabled?: boolean }>) => void, current?: string) {
  const filtered = query && query !== current ? allUnits.value.filter(unit => unit.value.toLowerCase().includes(query.toLowerCase())) : allUnits.value
  callback([{ value: '选择', disabled: true }, ...filtered])
}
function addRecentUnit(unit: string) {
  if (!unit || defaultUnits.includes(unit)) return
  recentUnits.value = [unit, ...recentUnits.value.filter(value => value !== unit)].slice(0, 3)
}

function isExistingCustomer(value: string) { return customerOptions.value.some(customer => customer.id === value) }
async function loadCustomers() { customerOptions.value = (await getCustomers({ page_size: 100 })).items }
async function loadCustomerContacts(customerId: string) {
  if (!customerId || !isExistingCustomer(customerId)) { contactOptions.value = []; return }
  try { contactOptions.value = (await getCustomer(customerId)).contacts || [] } catch { contactOptions.value = [] }
}
function handleContactChange(name: string) {
  const contact = contactOptions.value.find(option => option.name === name)
  if (contact?.phone) form.contact_phone = contact.phone
}
function onCustomerVisible(visible: boolean) { if (visible) void loadCustomers() }
function onCustomerBlur() {
  if (form.customer_id) return
  const typed = customerSelectRef.value?.$el?.querySelector('input')?.value?.trim()
  if (typed) form.customer_id = typed
}
watch(() => form.customer_id, value => { if (value) void loadCustomerContacts(String(value)) })

function openProductPicker(item: OrderItemResponse) {
  if (!canEdit.value) return
  if (!form.customer_id) { ElMessage.warning('请先选择客户'); return }
  pendingPickerItem.value = item
  productPickerVisible.value = true
}
function clearProduct(item: OrderItemResponse) {
  item.product_id = undefined
  item.material_id = undefined
  item.process_id = undefined
  item.material_process = ''
  item.use_area = false
  item.quantity = 1
  item.unit = ''
}
function onProductPicked(product: ProductResponse) {
  if (!pendingPickerItem.value) return
  const item = pendingPickerItem.value
  Object.assign(item, applyProductMaterialProcess(item, product))
  item.material_process = formatProductMaterialProcess(product)
  if (product.pricing_method === 'area') { item.use_area = true; syncAreaQuantity(item) } else { item.use_area = false; item.quantity = 1 }
  pendingPickerItem.value = null
}
function onProductUpdated(product: ProductResponse) {
  if (!pendingPickerItem.value || pendingPickerItem.value.product_id !== product.id) return
  Object.assign(pendingPickerItem.value, applyProductMaterialProcess(pendingPickerItem.value, product))
}

function buildHeaderPayload() {
  const header: Record<string, string | null> = {
    project_name: form.project_name.trim(),
    department: form.department.trim() || null,
    contact_person: form.contact_person.trim() || null,
    contact_phone: form.contact_phone.trim() || null,
    delivery_deadline: form.delivery_deadline || null,
    installation_address: form.installation_address.trim() || null,
    remark: form.remark.trim() || null,
  }
  if (isExistingCustomer(form.customer_id)) header.customer_id = form.customer_id
  else if (form.customer_id.trim()) header.customer_name = form.customer_id.trim()
  return header
}

function buildPayload() {
  if (!order.value?.updated_at) throw new Error('订单版本信息缺失，请刷新页面后重试')
  const serializedItems = items.value.map((item, index) => serializeOrderItemDraft(item, index))
  return {
    reason: reason.value.trim(),
    expected_updated_at: order.value.updated_at,
    header: buildHeaderPayload(),
    items: serializedItems,
    groups: buildOrderGroupPayload(items.value, emptyGroups.value),
  }
}

async function handleSave() {
  if (!canEdit.value) return
  if (!form.customer_id.trim()) { ElMessage.warning('请先选择或填写客户'); return }
  if (!form.project_name.trim()) { ElMessage.warning('请填写项目名称'); return }
  if (!items.value.length) { ElMessage.warning('订单至少需要保留一条明细'); return }
  if (items.value.some(item => !item.item_name.trim())) { ElMessage.warning('请填写所有明细的项目内容'); return }
  if (!reason.value.trim()) { ElMessage.warning('请填写订单变更原因'); return }
  const diff = buildOrderBatchItemDiff(originalItems.value, items.value)
  const groups = buildOrderGroupPayload(items.value, emptyGroups.value)
  const hasGroupChange = JSON.stringify(groups) !== JSON.stringify(buildOrderGroupPayload(originalItems.value, [])) || emptyGroups.value.length > 0
  if (!diff.added.length && !diff.updated.length && !diff.deleted.length && !hasGroupChange && !hasHeaderChanges()) {
    ElMessage.info('没有检测到需要保存的修改')
    return
  }
  saving.value = true
  try {
    const payload = buildPayload()
    const impact = await previewOrderEdit(orderId.value, payload)
    preview.value = impact
    if (!impact.can_apply) {
      ElMessage.warning(impact.lock_reasons.map(item => item.message).join('；') || '当前订单不可修改')
      return
    }
    pendingPayload.value = payload
    if (impact.requires_confirmation) {
      highRiskAcknowledged.value = false
      impactDialogVisible.value = true
      return
    }
    await applyOrderEdit(impact, payload)
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '订单保存失败，请刷新后重试')
  } finally {
    saving.value = false
  }
}

function hasHeaderChanges() {
  if (!order.value) return false
  const header = buildHeaderPayload()
  return Object.entries(header).some(([field, value]) => {
    if (field === 'customer_id') return value !== (order.value?.customer_id || null)
    if (field === 'customer_name') return value !== (order.value?.customer_name || null)
    if (field === 'delivery_deadline') return value !== (order.value?.delivery_deadline ? order.value.delivery_deadline.slice(0, 10) : null)
    return value !== ((order.value as Record<string, unknown>)[field] || null)
  })
}

async function applyOrderEdit(impact: OrderEditImpactResponse, payload: ReturnType<typeof buildPayload>) {
  const result = await saveOrderEdit(orderId.value, {
    ...payload,
    preview_id: impact.preview_id,
    plan_hash: impact.plan_hash,
    preview_expires_at: impact.preview_expires_at,
    confirm_high_risk: highRiskAcknowledged.value,
  })
  order.value = result
  items.value = (result.items || []).map(item => migrateLegacyQuoteDimensions({ ...item }))
  originalItems.value = items.value.map(item => ({ ...item }))
  rebuildEmptyGroups(result)
  captureCleanSnapshot()
  impactDialogVisible.value = false
  preview.value = null
  pendingPayload.value = null
  highRiskAcknowledged.value = false
  await fetchItemEditability()
  ElMessage.success(result.change_batch?.status === 'PENDING_ADJUSTMENT' ? '订单已保存，部分关联事实已进入待复核' : '订单保存成功')
}

async function confirmImpactAndApply() {
  if (!preview.value || !pendingPayload.value) { ElMessage.warning('预检信息已失效，请重新保存'); return }
  saving.value = true
  try { await applyOrderEdit(preview.value, pendingPayload.value) } catch (error: unknown) { ElMessage.error(error instanceof Error ? error.message : '订单保存失败，请刷新后重试') } finally { saving.value = false }
}
function cancelImpactConfirmation() {
  impactDialogVisible.value = false
  preview.value = null
  pendingPayload.value = null
  highRiskAcknowledged.value = false
}

async function handleImageUpload(option: { file: File }, item: OrderItemResponse) {
  try {
    const result = await uploadAttachment('order_item', item.id || orderId.value, option.file, 'image')
    item.image_url = `/uploads/${result.file_path}`
    ElMessage.success('上传成功')
  } catch { ElMessage.error('上传失败') }
}

async function fetchItemEditability() { try { itemEditability.value = await getOrderItemEditability(orderId.value) } catch { itemEditability.value = null } }
function rebuildEmptyGroups(data: OrderDetailResponse) {
  groupColors.reset()
  const activeGroupIds = new Set((data.items || []).map(item => item.group_id).filter((value): value is string => Boolean(value)))
  emptyGroups.value = (data.groups || []).filter(group => !activeGroupIds.has(group.group_id)).map(group => ({ groupId: group.group_id, groupName: group.group_name || '' }))
}
async function fetchOrder() {
  loading.value = true
  try {
    const data = await getOrder(orderId.value)
    if (!data) throw new Error('订单不存在')
    order.value = data
    Object.assign(form, {
      customer_id: data.customer_id || data.customer_name || '',
      project_name: data.project_name || '',
      department: data.department || '',
      contact_person: data.contact_person || '',
      contact_phone: data.contact_phone || '',
      delivery_deadline: data.delivery_deadline ? data.delivery_deadline.slice(0, 10) : '',
      installation_address: data.installation_address || '',
      remark: data.remark || '',
    })
    items.value = (data.items?.length ? data.items : [newItem()]).map(item => migrateLegacyQuoteDimensions({ ...item }))
    originalItems.value = items.value.map(item => ({ ...item }))
    rebuildEmptyGroups(data)
    await fetchItemEditability()
    captureCleanSnapshot()
  } finally { loading.value = false }
}

function goBack() { router.push(`/orders/${orderId.value}`) }

function statusLabel(status: string) {
  const labels: Record<string, string> = { pending_confirm: '待确认', confirmed: '已确认', designing: '设计中', in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消' }
  return labels[status] || status
}
function statusColor(status: string) {
  const colors: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = { pending_confirm: 'warning', confirmed: 'info', completed: 'success', cancelled: 'danger' }
  return colors[status] || 'info'
}
function mutationDecisionLabel(decision: string) {
  const labels: Record<string, string> = { DIRECT_APPLY: '本次变更可直接应用', CONFIRM_AND_REFRESH: '确认后刷新可安全更新的关联项', APPROVAL_AND_ADJUSTMENT: '确认后修改，并保留事实生成差异/待调整项', BLOCK: '本次变更被阻断' }
  return labels[decision] || decision
}
function mutationOperationLabel(operation: string) { return operation === 'add' ? '新增' : operation === 'update' ? '修改' : '作废' }
function displayValue(value: unknown) { return value === null || value === undefined || value === '' ? '-' : String(value) }
function amountFromDiff(value: Record<string, unknown> | null | undefined) { return value?.subtotal_amount == null ? '-' : `¥${Number(value.subtotal_amount).toFixed(2)}` }
function relationTypeLabel(type: string) { return ({ document: '订单级', item: '明细级', snapshot: '快照', source: '来源引用' } as Record<string, string>)[type] || type }
function relationStatusLabel(status?: string | null) { return ({ draft: '草稿', pending: '待处理', confirmed: '已确认', accepted: '已验收', completed: '已完成', settled: '已结算', active: '有效', cancelled: '已取消', in_progress: '进行中', rejected: '已驳回', approved: '已审批' } as Record<string, string>)[status || ''] || status || '-' }
function relationActionLabel(action: string) { return ({ refresh_plan: '自动刷新执行计划', refresh_draft: '自动刷新草稿快照', refresh_plan_or_review: '刷新计划或标记复核', preserve_fact_and_reconcile: '保留事实并重新核对', preserve_fact_and_adjust: '保留事实并生成差异调整', preserve_fact_and_review: '保留事实并待复核', review_required: '必须人工复核' } as Record<string, string>)[action] || action }
function riskLabel(risk: string) { return risk === 'high' ? '高' : risk === 'medium' ? '中' : '低' }
function riskTagType(risk: string) { return (risk === 'high' ? 'danger' : risk === 'medium' ? 'warning' : 'success') as 'success' | 'warning' | 'danger' }

function toChineseAmount(value: number): string {
  const digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const units = ['', '拾', '佰', '仟']
  const bigUnits = ['', '万', '亿']
  if (value === 0) return '零元整'
  const negative = value < 0
  value = Math.abs(value)
  const integer = Math.floor(value)
  const cents = Math.round((value - integer) * 100)
  const jiao = Math.floor(cents / 10)
  const fen = cents % 10
  let result = ''
  if (integer > 0) {
    const text = String(integer)
    let zero = false
    for (let index = 0; index < text.length; index++) {
      const digit = Number(text[index])
      const position = text.length - 1 - index
      const unitIndex = position % 4
      const bigIndex = Math.floor(position / 4)
      if (digit === 0) {
        zero = true
        if (unitIndex === 0 && bigUnits[bigIndex]) { result += bigUnits[bigIndex]; zero = false }
      } else {
        if (zero) { result += '零'; zero = false }
        result += digits[digit] + units[unitIndex]
        if (unitIndex === 0 && bigUnits[bigIndex]) result += bigUnits[bigIndex]
      }
    }
    result += '元'
  }
  if (!jiao && !fen) result += '整'
  else { if (jiao) result += digits[jiao] + '角'; else if (integer) result += '零'; if (fen) result += digits[fen] + '分' }
  return (negative ? '负' : '') + result
}

onMounted(async () => {
  const stored = localStorage.getItem('quoteEditor_recentUnits')
  if (stored) { try { recentUnits.value = JSON.parse(stored) } catch { recentUnits.value = [] } }
  await loadCustomers()
  await fetchOrder()
})
</script>

<style scoped>
.page { padding: 0; }
.page-title-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.title-actions { display: flex; gap: 8px; margin-top: 16px; }
.title-meta { display: flex; align-items: center; gap: 12px; color: var(--ad-text-secondary); font-size: 13px; }
.section-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.toolbar, .row-actions, .group-header-content, .dimension-cell, .area-cell, .image-cell { display: flex; align-items: center; gap: 6px; }
.dimension-cell :deep(.el-input-number) { width: 92px; }
.group-header-content .group-header-drag { flex: 0 0 auto; font-weight: 600; cursor: grab; user-select: none; }
.group-header-content :deep(.el-input) { flex: 1; }
.group-total-label { font-weight: 600; }
.summary-card { margin-top: 16px; }
.summary-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.summary-item.total { border-top: 1px solid var(--ad-border); padding-top: 10px; margin-top: 10px; font-size: 18px; color: var(--el-color-danger); }
.amount-words { text-align: right; color: var(--ad-text-secondary); font-size: 13px; margin-top: 4px; }
.impact-section-title { font-weight: 600; color: var(--ad-text); margin: 12px 0 8px; }
.amount-up { color: var(--el-color-success); }
.amount-down { color: var(--el-color-danger); }
.row-drag-handle { cursor: grab; color: var(--ad-text-secondary); display: inline-flex; user-select: none; }
.row-drag-handle:hover, .group-header-drag:hover { color: var(--ad-primary, var(--el-color-primary)); }
.item-image { width: 32px; height: 32px; border-radius: 4px; cursor: pointer; }
.muted { color: var(--ad-text-secondary); }
:deep(.quote-group-row td) { background: rgba(var(--ad-g), 0.07) !important; }
:deep(.quote-group-row td:first-child) { box-shadow: inset 3px 0 0 rgba(var(--ad-g), 0.65); }
:deep(.group-card-gap td) { border-top: 8px solid var(--ad-card) !important; }
:deep(.group-header-row td:not(:first-child)) { box-shadow: inset 0 2px 0 rgba(var(--ad-g), 0.65); }
:deep(.group-header-row td:first-child) { box-shadow: inset 3px 0 0 rgba(var(--ad-g), 0.65), inset 0 2px 0 rgba(var(--ad-g), 0.65); }
:deep(.group-total-row td:not(:first-child)) { box-shadow: inset 0 -2px 0 rgba(var(--ad-g), 0.65); font-weight: 600; }
:deep(.group-total-row td:first-child) { box-shadow: inset 3px 0 0 rgba(var(--ad-g), 0.65), inset 0 -2px 0 rgba(var(--ad-g), 0.65); font-weight: 600; }
:deep(.el-table .el-input-number) { width: 100%; }
:deep(.ad-drag-ghost) { opacity: 0.4; }
:deep(.el-table.el-table--scrollable-x .el-scrollbar__view) { padding-bottom: 12px; }
:deep(.el-table.el-table--scrollable-x .el-table__body-wrapper) { margin-bottom: 8px; }
</style>
