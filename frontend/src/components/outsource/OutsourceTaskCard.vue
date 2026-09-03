<template>
  <el-card shadow="never" class="info-card" style="margin-top: 16px">
    <template #header>
      <div class="card-header">
        <div>
          <span>外协情况</span>
          <el-tag v-if="hasOutsource" type="warning" size="small" style="margin-left: 8px">已外协</el-tag>
        </div>
        <el-button text type="primary" size="small" @click="goToOutsourceList()">外协任务管理</el-button>
      </div>
    </template>

    <el-alert
      v-if="summary && summary.order_level_task_count > 0"
      type="warning"
      :closable="false"
      show-icon
      class="order-level-alert"
    >
      <template #title>
        当前订单仍有 {{ summary.order_level_task_count }} 条整单外协任务，计划成本 ¥{{ moneyText(summary.order_level_planned_amount) }}。
      </template>
      <div>
        整单外协不会自动拆分到下方明细；新发送的外协会绑定到明确的订单项目明细，便于数量、成本和付款核对。
        <el-button text type="primary" size="small" @click="goToOutsourceList()">查看整单外协</el-button>
      </div>
    </el-alert>

    <div class="section-heading">
      <div>
        <span class="section-title">订单项目明细外协分配</span>
        <span v-if="summary" class="section-caption">订单 {{ summary.order_no }} · 当前{{ taskTypeLabel }}任务</span>
      </div>
      <el-button text type="primary" size="small" :loading="loading" @click="fetchOutsource">刷新</el-button>
    </div>

    <el-table
      :data="summary?.items || []"
      v-loading="loading"
      stripe
      size="small"
      empty-text="该订单暂无可分配的项目明细"
      class="item-table"
    >
      <el-table-column label="项目明细" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="item-name">{{ row.item_name }}</div>
          <div v-if="row.group_name" class="item-group">{{ row.group_name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="订单数量" width="105" align="right">
        <template #default="{ row }">{{ quantityText(row.quantity) }} {{ row.unit || '' }}</template>
      </el-table-column>
      <el-table-column label="已分配" width="105" align="right">
        <template #default="{ row }">{{ quantityText(row.allocated_quantity) }} {{ row.unit || '' }}</template>
      </el-table-column>
      <el-table-column label="剩余" width="105" align="right">
        <template #default="{ row }">
          <span :class="{ 'remaining-warning': row.remaining_quantity <= 0 }">
            {{ quantityText(row.remaining_quantity) }} {{ row.unit || '' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="计划成本" width="115" align="right">
        <template #default="{ row }">¥{{ moneyText(row.planned_amount) }}</template>
      </el-table-column>
      <el-table-column label="外协状态" width="105">
        <template #default="{ row }">
          <el-tag :type="itemStatusType(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="175" fixed="right">
        <template #default="{ row }">
          <el-tooltip v-if="!row.can_send" :content="row.block_reason || '当前明细不可发送外协'" placement="top">
            <span>
              <el-button text type="info" size="small" disabled>不可发送</el-button>
            </span>
          </el-tooltip>
          <el-button v-else text type="danger" size="small" @click="openItemDialog(row)">
            {{ row.active_task_count > 0 ? '追加外协' : '发送外协' }}
          </el-button>
          <el-button text type="primary" size="small" @click="goToOutsourceList(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="cost-note">
      明细外协计划成本 ¥{{ moneyText(itemPlannedAmount) }}，已确认成本 ¥{{ moneyText(itemRecognizedCost) }}。
      订单销售金额与外协成本分别核算，不会相互覆盖。
    </div>

    <div class="section-heading task-heading">
      <div>
        <span class="section-title">当前任务已发送外协任务</span>
        <span class="section-caption">仅展示当前{{ taskTypeLabel }}任务发出的外协记录</span>
      </div>
      <span v-if="outsourceTasks.length" class="task-count">{{ outsourceTasks.length }} 条</span>
    </div>

    <el-table :data="outsourceTasks" v-loading="loading" stripe size="small" empty-text="当前任务尚未发送外协">
      <el-table-column prop="task_no" label="外协编号" width="150" />
      <el-table-column label="订单明细" min-width="170" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.order_item_name">{{ row.order_item_name }}</span>
          <span v-else class="muted-text">整单外协（历史）</span>
        </template>
      </el-table-column>
      <el-table-column prop="vendor_name" label="外协商" width="135" show-overflow-tooltip />
      <el-table-column label="数量" width="90" align="right">
        <template #default="{ row }">{{ quantityText(row.quantity) }}</template>
      </el-table-column>
      <el-table-column label="外协成本" width="110" align="right">
        <template #default="{ row }">¥{{ moneyText(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column label="未付" width="105" align="right">
        <template #default="{ row }">
          <span v-if="Number(row.unpaid_amount) > 0" class="unpaid-text">¥{{ moneyText(row.unpaid_amount) }}</span>
          <span v-else class="paid-text">已结清</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="goToOutsourceList(row.order_item_id ? findSummaryItem(row.order_item_id) : undefined)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="发送订单明细外协" width="560px" :close-on-click-modal="false" append-to-body>
      <el-alert
        v-if="selectedItem"
        type="info"
        :closable="false"
        show-icon
        class="dialog-context"
      >
        <template #title>{{ selectedItem.item_name }} · {{ isAppend ? '追加外协' : '首次外协' }}</template>
        <div>
          订单数量 {{ quantityText(selectedItem.quantity) }} {{ selectedItem.unit || '' }}，
          已分配 {{ quantityText(selectedItem.allocated_quantity) }} {{ selectedItem.unit || '' }}，
          当前剩余 {{ quantityText(selectedItem.remaining_quantity) }} {{ selectedItem.unit || '' }}。
        </div>
      </el-alert>

      <el-alert
        v-if="selectedItem?.requires_reason"
        type="warning"
        :closable="false"
        show-icon
        class="dialog-warning"
        title="该明细已分配完订单数量；如需继续外协，数量将作为追加数量，必须填写原因。"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-width="105px">
        <el-form-item label="外协商" prop="vendor_id">
          <el-select v-model="form.vendor_id" filterable clearable placeholder="选择外协商" style="width: 100%">
            <el-option v-for="vendor in vendors" :key="vendor.id" :label="vendor.name" :value="vendor.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="外协数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="0.001" :precision="3" :step="1" controls-position="right" style="width: 100%" />
          <div class="form-tip">默认发送当前明细剩余数量；超过剩余数量时按追加外协处理。</div>
        </el-form-item>
        <el-form-item label="外协成本单价" prop="unit_price">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" :step="0.01" controls-position="right" style="width: 100%" />
          <div class="form-tip">此处为供应商成本单价，不是订单销售单价。</div>
        </el-form-item>
        <el-form-item label="预计完成">
          <el-date-picker v-model="form.expected_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="isAppend ? '追加原因/备注' : '备注'" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" :placeholder="isAppend ? '追加数量超过剩余数量时必须填写原因' : '填写外协说明（可选）'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSubmit">确认发送</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  getOutsourceOrderItemsSummary,
  getOutsourceTasks,
  getOutsourceVendors,
  sendOutsourceOrderItem,
} from '@/api/outsource'
import type {
  OutsourceOrderItemSummary,
  OutsourceOrderItemSummaryResponse,
  OutsourceTaskResponse,
  VendorResponse,
} from '@/types/api'

const props = defineProps<{
  taskType: 'design' | 'production' | 'installation'
  taskId: string
  orderId: string
  projectName: string
}>()

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const summary = ref<OutsourceOrderItemSummaryResponse | null>(null)
const outsourceTasks = ref<OutsourceTaskResponse[]>([])
const vendors = ref<VendorResponse[]>([])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const selectedItem = ref<OutsourceOrderItemSummary | null>(null)
const form = reactive({
  vendor_id: '',
  description: '',
  quantity: 1,
  unit_price: 0,
  expected_at: '',
  remark: '',
})

const taskTypeLabel = computed(() => ({
  design: '设计',
  production: '制作',
  installation: '安装',
}[props.taskType]))
const isAppend = computed(() => Boolean(selectedItem.value?.active_task_count))
const hasOutsource = computed(() => outsourceTasks.value.length > 0 || Boolean(summary.value?.items.some(item => item.active_task_count > 0)))
const itemPlannedAmount = computed(() => summary.value?.items.reduce((total, item) => total + item.planned_amount, 0) || 0)
const itemRecognizedCost = computed(() => summary.value?.items.reduce((total, item) => total + item.recognized_cost, 0) || 0)

const rules: FormRules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
  quantity: [{
    validator: (_rule, value, callback) => {
      const quantity = Number(value)
      if (!Number.isFinite(quantity) || quantity <= 0) {
        callback(new Error('外协数量必须大于 0'))
        return
      }
      if (selectedItem.value && quantity > selectedItem.value.remaining_quantity && !form.remark.trim()) {
        callback(new Error('数量超过剩余数量时必须填写追加原因'))
        return
      }
      callback()
    },
    trigger: ['change', 'blur'],
  }],
}

function quantityText(value: number | null | undefined) {
  const amount = Number(value || 0)
  return amount.toLocaleString('zh-CN', { maximumFractionDigits: 3 })
}

function moneyText(value: number | null | undefined) {
  return Number(value || 0).toFixed(2)
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    settled: '已结算',
    cancelled: '已取消',
  }
  return map[status] || status
}

function statusType(status: string) {
  const map: Record<string, string> = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
    settled: '',
    cancelled: 'danger',
  }
  return (map[status] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function itemStatusType(status: string) {
  const map: Record<string, string> = {
    未外协: 'info',
    部分外协: 'warning',
    待处理: 'warning',
    进行中: 'primary',
    已完成: 'success',
    已作废: 'danger',
  }
  return (map[status] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function findSummaryItem(itemId: string) {
  return summary.value?.items.find(item => item.id === itemId)
}

function goToOutsourceList(item?: OutsourceOrderItemSummary) {
  const query: Record<string, string> = {
    order_id: props.orderId,
    task_type: props.taskType,
    source_task_type: props.taskType,
    source_task_id: props.taskId,
  }
  if (item) query.order_item_id = item.id
  void router.push({ path: '/outsource/tasks', query })
}

async function fetchOutsource() {
  loading.value = true
  try {
    const [summaryResult, taskResult] = await Promise.allSettled([
      getOutsourceOrderItemsSummary(props.orderId, {
        task_type: props.taskType,
        source_task_type: props.taskType,
        source_task_id: props.taskId,
      }),
      getOutsourceTasks({
        page: 1,
        page_size: 50,
        order_id: props.orderId,
        source_task_id: props.taskId,
        source_task_type: props.taskType,
        task_type: props.taskType,
      }),
    ])
    if (summaryResult.status === 'fulfilled') summary.value = summaryResult.value
    if (taskResult.status === 'fulfilled') outsourceTasks.value = taskResult.value.items
  } finally {
    loading.value = false
  }
}

async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 100 })
    vendors.value = data.items
  } catch {
    // The shared card remains readable if the vendor directory is temporarily unavailable.
  }
}

function openItemDialog(item: OutsourceOrderItemSummary) {
  selectedItem.value = item
  Object.assign(form, {
    vendor_id: '',
    description: `${props.projectName || '订单项目'} - ${item.item_name}`,
    quantity: item.remaining_quantity > 0 ? Number(item.remaining_quantity.toFixed(3)) : 1,
    unit_price: 0,
    expected_at: '',
    remark: '',
  })
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

async function handleSubmit() {
  if (!selectedItem.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await sendOutsourceOrderItem(props.orderId, selectedItem.value.id, {
      vendor_id: form.vendor_id,
      task_type: props.taskType,
      source_task_type: props.taskType,
      source_task_id: props.taskId,
      quantity: form.quantity,
      unit_price: form.unit_price,
      description: form.description || undefined,
      expected_at: form.expected_at || undefined,
      remark: form.remark || undefined,
    })
    ElMessage.success(isAppend.value ? '已追加订单明细外协' : '已发送订单明细外协')
    dialogVisible.value = false
    await fetchOutsource()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void fetchOutsource()
  void loadVendors()
})
</script>

<style scoped>
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.section-heading { display: flex; justify-content: space-between; align-items: center; margin: 18px 0 10px; }
.task-heading { margin-top: 24px; }
.section-title { font-weight: 600; color: var(--ad-text); }
.section-caption { margin-left: 10px; color: var(--ad-text-secondary); font-size: 12px; }
.item-table { margin-top: 4px; }
.item-name { font-weight: 500; color: var(--ad-text); }
.item-group { margin-top: 3px; color: var(--ad-text-secondary); font-size: 12px; }
.remaining-warning { color: var(--el-color-warning); font-weight: 600; }
.cost-note { margin-top: 10px; color: var(--ad-text-secondary); font-size: 12px; line-height: 1.6; }
.task-count { color: var(--ad-text-secondary); font-size: 12px; }
.muted-text { color: var(--ad-text-secondary); }
.unpaid-text { color: var(--el-color-danger); }
.paid-text { color: var(--el-color-success); }
.order-level-alert { margin-bottom: 4px; }
.dialog-context { margin-bottom: 14px; }
.dialog-warning { margin-bottom: 14px; }
.form-tip { color: var(--ad-text-secondary); font-size: 12px; line-height: 1.5; }

@media (max-width: 768px) {
  .section-heading { align-items: flex-start; }
  .section-caption { display: block; margin: 4px 0 0; }
}
</style>
