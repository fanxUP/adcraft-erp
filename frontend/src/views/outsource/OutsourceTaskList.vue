<template>
  <div class="page">
    <div class="page-header">
      <h2>外协任务</h2>
      <div style="display: flex; gap: 8px;">
        <el-button v-if="canDeleteTask" @click="$router.push('/outsource/tasks/recycle')" type="warning">回收站</el-button>
      </div>
    </div>
    <div class="page-create">
      <el-button v-if="canCreateTask" @click="handleCreate" type="danger">新建外协任务</el-button>
    </div>

    <div class="task-tabs">
      <el-tabs v-model="activeTaskType" @tab-change="handleTaskTypeChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="设计任务" name="design" />
        <el-tab-pane label="制作任务" name="production" />
        <el-tab-pane label="安装任务" name="installation" />
      </el-tabs>
    </div>

    <div class="search-bar">
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 140px">
        <el-option label="待处理" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已完成" value="completed" />
        <el-option label="已结算" value="settled" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button @click="handleSearch" style="margin-left: 12px" type="primary">搜索</el-button>
    </div>

    <el-collapse v-model="expandedGroupKeys" class="task-groups" v-loading="loading" @change="handleGroupChange">
      <el-collapse-item v-for="group in groups" :key="group.group_key" :name="group.group_key">
        <template #title>
          <div class="group-header">
            <div class="group-heading">
              <el-tag size="small" effect="plain">{{ groupTypeLabel(group) }}</el-tag>
              <el-button
                v-if="group.source_task_no && group.source_task_exists !== false"
                link
                type="primary"
                class="source-task-link"
                @click.stop="openSourceTask(group)"
              >
                {{ group.source_task_no }}
              </el-button>
              <span v-else class="group-label">{{ group.group_label }}</span>
              <div
                v-if="group.related_project_name || (canViewOutsourceCost && group.related_project_amount !== null && group.related_project_amount !== undefined)"
                class="group-project"
              >
                <span
                  v-if="group.related_project_name"
                  class="group-project-name"
                  :title="group.related_project_name"
                >
                  项目：{{ group.related_project_name }}
                </span>
                <span v-if="canViewOutsourceCost && group.related_project_amount !== null && group.related_project_amount !== undefined" class="group-project-amount">
                  项目金额：¥{{ formatMoney(group.related_project_amount) }}
                </span>
              </div>
              <el-tag v-if="group.consistency_warning" type="warning" size="small">需核对</el-tag>
            </div>
            <div class="group-summary">
              <span>外协 {{ group.task_count }} 条</span>
              <template v-if="canViewOutsourceCost">
                <span>计划 ¥{{ formatMoney(group.planned_amount) }}</span>
                <span class="paid">已付 ¥{{ formatMoney(group.paid_amount) }}</span>
                <span class="unpaid">未付 ¥{{ formatMoney(group.unpaid_amount) }}</span>
              </template>
            </div>
          </div>
        </template>

        <div class="group-meta">
          <span v-if="group.related_doc_no">单据：{{ group.related_doc_no }}</span>
          <span v-if="group.source_task_status">来源状态：{{ internalStatusLabel(group.source_task_status) }}</span>
          <span>状态分布：{{ groupStatusSummary(group) }}</span>
          <span v-if="canViewOutsourceCost">已识别成本：¥{{ formatMoney(group.recognized_cost) }}</span>
          <span v-if="group.status_counts.cancelled">已取消 {{ group.status_counts.cancelled }} 条不计成本</span>
        </div>
        <el-alert
          v-if="group.consistency_warning"
          :title="group.consistency_warning"
          type="warning"
          :closable="false"
          show-icon
          class="group-warning"
        />
        <el-alert
          v-if="group.tasksError"
          :title="group.tasksError"
          type="error"
          :closable="false"
          show-icon
          class="group-warning"
        />

        <el-table :data="group.tasks" v-loading="group.tasksLoading" stripe empty-text="暂无符合筛选条件的明细">
          <el-table-column prop="task_no" label="外协任务编号" width="180" />
          <el-table-column prop="vendor_name" label="外协商" width="140" />
          <el-table-column label="项目" width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.related_project_name">{{ row.related_project_name }}</span>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column label="订单明细" min-width="170" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.order_item_name">{{ row.order_item_name }}</span>
              <span v-else-if="row.related_doc_type === 'order'" style="color: var(--ad-text-secondary)">整单外协</span>
              <span v-else style="color: var(--ad-text-secondary)">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
          <el-table-column label="数量" width="90" align="right">
            <template #default="{ row }">{{ row.quantity }}</template>
          </el-table-column>
          <el-table-column v-if="canViewOutsourceCost" label="单价" width="100" align="right">
            <template #default="{ row }">¥{{ formatMoney(row.unit_price) }}</template>
          </el-table-column>
          <el-table-column v-if="canViewOutsourceCost" prop="total_amount" label="总金额" width="120" align="right">
            <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
          </el-table-column>
          <el-table-column v-if="canViewOutsourceCost" label="已付" width="100" align="right">
            <template #default="{ row }">
              <span style="color: var(--el-color-success)">¥{{ formatMoney(row.paid_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column v-if="canViewOutsourceCost" label="未付" width="100" align="right">
            <template #default="{ row }">
              <span v-if="row.unpaid_amount > 0" style="color: var(--el-color-danger)">¥{{ formatMoney(row.unpaid_amount) }}</span>
              <span v-else style="color: var(--el-color-success)">已结清</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="200" fixed="right">
            <template #default="{ row }">
              <el-button v-if="canUpdateTask" text type="primary" @click="handleEdit(row as OutsourceTaskResponse)">编辑</el-button>
              <el-button v-if="canChangeTaskStatus && row.status === 'pending'" text type="primary" @click="handleUpdateStatus(row as OutsourceTaskResponse, 'in_progress')">开始</el-button>
              <el-button v-if="canChangeTaskStatus && row.status === 'in_progress'" text type="success" @click="handleUpdateStatus(row as OutsourceTaskResponse, 'completed')">完成</el-button>
              <el-button v-if="canCreatePayment && row.unpaid_amount > 0 && row.status !== 'cancelled' && row.status !== 'settled'" text type="warning" @click="handlePay(row as OutsourceTaskResponse)">付款</el-button>
              <el-button v-if="canChangeTaskStatus && row.status === 'completed'" text type="warning" @click="handleRevert(row as OutsourceTaskResponse)">退回</el-button>
              <el-button v-if="canChangeTaskStatus && !['completed', 'settled', 'cancelled'].includes(row.status)" text type="danger" @click="handleCancel(row as OutsourceTaskResponse)">取消</el-button>
              <el-button v-if="canDeleteTask" text type="danger" @click="handleDelete(row as OutsourceTaskResponse)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="group.tasksTotal > 0"
          v-model:current-page="group.tasksPage"
          v-model:page-size="group.tasksPageSize"
          :page-sizes="[10, 20, 50]"
          :total="group.tasksTotal"
          layout="total, sizes, prev, pager, next"
          class="group-pagination"
          @change="loadGroupTasks(group, true)"
        />
      </el-collapse-item>
    </el-collapse>
    <el-empty v-if="!loading && groups.length === 0" description="暂无外协任务" />

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="handleGroupPageChange"
    />

    <!-- 新建/编辑任务对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑外协任务' : '新建外协任务'" width="550px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="外协商" prop="vendor_id">
          <el-select v-model="form.vendor_id" filterable clearable style="width: 100%">
            <el-option v-for="v in vendors" :key="v.id" :label="v.name" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联任务" prop="related_doc_id">
          <el-select v-model="form.related_doc_id" filterable clearable placeholder="请选择关联的报价单或订单" style="width: 100%" @change="onRelatedDocChange">
            <el-option-group label="报价单">
              <el-option v-for="q in quotes" :key="'q_' + q.id" :label="q.label" :value="q.id" />
            </el-option-group>
            <el-option-group label="订单">
              <el-option v-for="o in orders" :key="'o_' + o.id" :label="o.label" :value="o.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.related_doc_type === 'order' && form.related_doc_id" label="订单明细">
          <el-select v-model="form.order_item_id" filterable clearable placeholder="留空表示整单外协" style="width: 100%">
            <el-option v-for="item in orderItems" :key="item.id" :label="item.label" :value="item.id" :disabled="item.disabled" />
          </el-select>
          <div class="form-tip">订单明细外协会参与明细数量和外协成本核对；历史整单外协可继续保留。</div>
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" clearable style="width: 100%">
            <el-option label="制作" value="production" />
            <el-option label="安装" value="installation" />
            <el-option label="设计" value="design" />
            <el-option label="运输" value="transport" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="canViewOutsourceCost" label="单价" prop="unit_price">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" @click="handleSave" type="primary">保存</el-button>
      </template>
    </el-dialog>

    <!-- 付款对话框 -->
    <el-dialog v-model="payDialogVisible" title="外协付款" width="500px" :close-on-click-modal="false">
      <div v-if="payTask" class="pay-summary">
        <div class="pay-summary-row">
          <span class="label">外协商：</span>
          <span class="value">{{ payTask.vendor_name }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">任务编号：</span>
          <span class="value">{{ payTask.task_no }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">项目名称：</span>
          <span class="value">{{ payTask.related_project_name || '-' }}</span>
        </div>
        <div class="pay-divider"></div>
        <div class="pay-summary-row">
          <span class="label">总金额：</span>
          <span class="value total">¥{{ payTask.total_amount?.toFixed(2) }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">已付金额：</span>
          <span class="value paid">¥{{ payTask.paid_amount?.toFixed(2) }}</span>
        </div>
        <div class="pay-summary-row">
          <span class="label">待付金额：</span>
          <span class="value unpaid">¥{{ payTask.unpaid_amount?.toFixed(2) }}</span>
        </div>
        <div class="pay-divider"></div>
      </div>
      <el-form ref="payFormRef" :model="payForm" :rules="payRules" label-width="100px">
        <el-form-item label="付款金额" prop="amount">
          <el-input-number v-model="payForm.amount" :min="0.01" :max="payTask?.unpaid_amount || 0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="付款方式" prop="payment_method">
          <el-select v-model="payForm.payment_method" clearable style="width: 100%">
            <el-option label="银行转账" value="bank_transfer" />
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="现金" value="cash" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款公司">
          <el-input v-model="payForm.payee_company_name" placeholder="收款公司名称（可选）" />
        </el-form-item>
        <el-form-item label="付款日期">
          <el-date-picker v-model="payForm.paid_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="payForm.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payDialogVisible = false">取消</el-button>
        <el-button :loading="paySaving" @click="handlePaySubmit" type="primary">确认付款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getOutsourceVendors, getOutsourceTaskGroups, getOutsourceTaskGroupTasks, getOutsourceTaskPaymentSummary,
  createOutsourceTask, updateOutsourceTask, createOutsourcePayment,
  cancelOutsourceTask, revertOutsourceTask, deleteOutsourceTask,
  getQuotesForDropdown, getOrdersForDropdown, getOutsourceOrderItems,
} from '@/api/outsource'
import type { OutsourceTaskPaymentSummary } from '@/api/outsource'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { OutsourceTaskGroupResponse, OutsourceTaskResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
interface TaskGroup extends OutsourceTaskGroupResponse {
  tasks: OutsourceTaskResponse[]
  tasksPage: number
  tasksPageSize: number
  tasksTotal: number
  tasksLoading: boolean
  tasksLoaded: boolean
  tasksError: string
}

const groups = ref<TaskGroup[]>([])
const expandedGroupKeys = ref<string[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
type TaskTab = 'all' | 'design' | 'production' | 'installation'
const activeTaskType = ref<TaskTab>('all')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const vendors = ref<{id: string; name: string}[]>([])
const quotes = ref<{id: string; label: string; project_name: string}[]>([])
const orders = ref<{id: string; label: string; project_name: string}[]>([])

const form = reactive({
  vendor_id: '', related_doc_id: '', related_doc_type: '', task_type: 'production',
  order_item_id: '', description: '', quantity: 1, unit_price: 0, remark: '',
})
const rules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  related_doc_id: [{ required: true, message: '请选择关联任务', trigger: 'change' }],
}

// 付款对话框
const payDialogVisible = ref(false)
const paySaving = ref(false)
type PaymentTarget = Omit<OutsourceTaskPaymentSummary, 'payments'>
const payTask = ref<PaymentTarget | null>(null)
const payForm = reactive({
  amount: 0, payment_method: 'bank_transfer', payee_company_name: '', paid_at: '', remark: '',
})
const payRules = {
  amount: [{ required: true, message: '请输入付款金额', trigger: 'blur' }],
}

// 页面操作按显式权限控制，后端仍是最终授权边界。
const authStore = useAuthStore()
const canCreateTask = computed(() => authStore.hasPermission('outsource_task:create'))
const canUpdateTask = computed(() => authStore.hasPermission('outsource_task:update'))
const canChangeTaskStatus = computed(() => (
  authStore.hasPermission('outsource_task:update')
  && authStore.hasPermission('outsource_task:change_status')
))
const canDeleteTask = computed(() => authStore.hasPermission('outsource_task:delete'))
const canCreatePayment = computed(() => authStore.hasPermission('outsource_payment:create'))
const canViewOutsourceCost = computed(() => authStore.hasPermission('finance:view_cost'))
const route = useRoute()
const router = useRouter()

interface OrderItemOption {
  id: string
  label: string
  item_name: string
  quantity: number
  unit?: string | null
  group_name?: string | null
  sort_order: number
  disabled?: boolean
}

const orderItems = ref<OrderItemOption[]>([])

function statusType(val: string) {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', settled: '', cancelled: 'danger' }
  return (map[val] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function statusLabel(val: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消' }
  return map[val] || val
}

function internalStatusLabel(val: string) {
  const map: Record<string, string> = {
    pending: '待处理', assigned: '已分配', in_progress: '进行中', completed: '已完成', cancelled: '已取消',
  }
  return map[val] || val
}

function formatMoney(value: number | null | undefined) {
  return Number(value || 0).toFixed(2)
}

function groupTypeLabel(group: OutsourceTaskGroupResponse) {
  const taskLabels: Record<string, string> = { design: '设计任务', production: '制作任务', installation: '安装任务' }
  if (group.group_kind === 'source_task') return taskLabels[group.source_task_type || ''] || '内部任务'
  if (group.group_kind === 'related_document') return group.related_doc_type === 'quote' ? '报价单' : '订单'
  if (group.group_kind === 'unresolved_source') return '异常来源'
  if (group.group_kind === 'unresolved_document') return '异常单据'
  return '未关联'
}

function groupStatusSummary(group: OutsourceTaskGroupResponse) {
  const labels: Record<string, string> = {
    pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消', other: '其他',
  }
  const counts = group.status_counts || {}
  const summary = Object.entries(labels)
    .filter(([key]) => Number(counts[key] || 0) > 0)
    .map(([key, label]) => `${label} ${counts[key]}`)
  return summary.join(' / ') || '无'
}

function createTaskGroup(group: OutsourceTaskGroupResponse): TaskGroup {
  return {
    ...group,
    tasks: [],
    tasksPage: 1,
    tasksPageSize: 20,
    tasksTotal: 0,
    tasksLoading: false,
    tasksLoaded: false,
    tasksError: '',
  }
}

function groupQueryParams() {
  const contextualTaskType = typeof route.query.task_type === 'string' ? route.query.task_type : ''
  const keepSourceScope = contextualTaskType !== '' && contextualTaskType === activeTaskType.value
  return {
    status: statusFilter.value || undefined,
    task_type: activeTaskType.value === 'all' ? undefined : activeTaskType.value,
    order_id: typeof route.query.order_id === 'string' ? route.query.order_id : undefined,
    order_item_id: typeof route.query.order_item_id === 'string' ? route.query.order_item_id : undefined,
    source_task_type: keepSourceScope && typeof route.query.source_task_type === 'string' ? route.query.source_task_type : undefined,
    source_task_id: keepSourceScope && typeof route.query.source_task_id === 'string' ? route.query.source_task_id : undefined,
  }
}

function contextualSourceGroupKey() {
  const contextualTaskType = typeof route.query.task_type === 'string' ? route.query.task_type : ''
  const sourceTaskType = typeof route.query.source_task_type === 'string' ? route.query.source_task_type : ''
  const sourceTaskId = typeof route.query.source_task_id === 'string' ? route.query.source_task_id : ''
  if (
    contextualTaskType !== activeTaskType.value
    || !['design', 'production', 'installation'].includes(sourceTaskType)
    || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(sourceTaskId)
  ) return ''
  return `source:${sourceTaskType}:${sourceTaskId.toLowerCase()}`
}

async function loadQuotes() {
  try { quotes.value = await getQuotesForDropdown() } catch { /* ignore */ }
}
async function loadOrders() {
  try { orders.value = await getOrdersForDropdown() } catch { /* ignore */ }
}
async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 100 })
    vendors.value = data.items
  } catch { /* ignore */ }
}

async function loadOrderItems(orderId: string, preserveItemId = '', preserveItemName = '') {
  if (!orderId) {
    orderItems.value = []
    return
  }
  try {
    const activeItems = await getOutsourceOrderItems(orderId)
    if (preserveItemId && !activeItems.some(item => item.id === preserveItemId)) {
      orderItems.value = [
        {
          id: preserveItemId,
          label: `${preserveItemName || '历史订单明细'}（已作废，仅可保留）`,
          item_name: preserveItemName || '历史订单明细',
          quantity: 0,
          unit: null,
          group_name: null,
          sort_order: -1,
          disabled: true,
        },
        ...activeItems,
      ]
    } else {
      orderItems.value = activeItems
    }
    if (form.order_item_id && !orderItems.value.some(item => item.id === form.order_item_id)) {
      form.order_item_id = ''
    }
  } catch {
    orderItems.value = []
  }
}

async function fetchData(options: { preserveExpanded?: boolean } = {}) {
  loading.value = true
  const previousExpanded = options.preserveExpanded ? [...expandedGroupKeys.value] : []
  try {
    const data = await getOutsourceTaskGroups({
      page: page.value, page_size: pageSize.value,
      ...groupQueryParams(),
    })
    groups.value = data.items.map(createTaskGroup)
    total.value = data.total
    const availableKeys = new Set(groups.value.map(group => group.group_key))
    const contextualGroupKey = options.preserveExpanded ? '' : contextualSourceGroupKey()
    expandedGroupKeys.value = contextualGroupKey && availableKeys.has(contextualGroupKey)
      ? [contextualGroupKey]
      : previousExpanded.filter(groupKey => availableKeys.has(groupKey))
    if (contextualGroupKey && expandedGroupKeys.value.includes(contextualGroupKey)) {
      const contextualGroup = groups.value.find(group => group.group_key === contextualGroupKey)
      if (contextualGroup) await loadGroupTasks(contextualGroup)
    }
  } finally {
    loading.value = false
  }
}

async function loadGroupTasks(group: TaskGroup, force = false) {
  if (group.tasksLoading || (group.tasksLoaded && !force)) return
  group.tasksLoading = true
  group.tasksError = ''
  try {
    let data = await getOutsourceTaskGroupTasks(group.group_key, {
      ...groupQueryParams(),
      page: group.tasksPage,
      page_size: group.tasksPageSize,
    })
    // If a row was removed from the last child page, move back to the first
    // page instead of showing an empty page while the group still has rows.
    if (data.items.length === 0 && data.total > 0 && group.tasksPage > 1) {
      group.tasksPage = 1
      data = await getOutsourceTaskGroupTasks(group.group_key, {
        ...groupQueryParams(),
        page: group.tasksPage,
        page_size: group.tasksPageSize,
      })
    }
    group.tasks = data.items
    group.tasksTotal = data.total
    group.tasksLoaded = true
  } catch (error) {
    group.tasksError = error instanceof Error ? error.message : '明细加载失败'
  } finally {
    group.tasksLoading = false
  }
}

function handleGroupChange(value: string | string[]) {
  const keys = Array.isArray(value) ? value : [value]
  void Promise.all(
    keys.map(groupKey => {
      const group = groups.value.find(item => item.group_key === groupKey)
      return group ? loadGroupTasks(group) : Promise.resolve()
    }),
  )
}

function handleSearch() {
  page.value = 1
  expandedGroupKeys.value = []
  void fetchData()
}

function handleTaskTypeChange() {
  page.value = 1
  expandedGroupKeys.value = []
  void fetchData()
}

function handleGroupPageChange() {
  expandedGroupKeys.value = []
  void fetchData()
}

async function refreshData() {
  const previousExpanded = [...expandedGroupKeys.value]
  await fetchData({ preserveExpanded: true })
  await Promise.all(
    groups.value
      .filter(group => previousExpanded.includes(group.group_key))
      .map(group => loadGroupTasks(group, true)),
  )
}

function openSourceTask(group: OutsourceTaskGroupResponse) {
  if (!group.source_task_id) return
  const pathMap: Record<string, string> = {
    design: '/design-tasks',
    production: '/production-tasks',
    installation: '/installation-tasks',
  }
  const path = pathMap[group.source_task_type || '']
  if (path) void router.push(`${path}/${group.source_task_id}`)
}

function onRelatedDocChange(val: string) {
  form.order_item_id = ''
  if (!val) {
    form.related_doc_type = ''
    orderItems.value = []
    return
  }
  const foundQuote = quotes.value.find(q => q.id === val)
  form.related_doc_type = foundQuote ? 'quote' : 'order'
  if (form.related_doc_type === 'order') void loadOrderItems(val)
  else orderItems.value = []
}

function handleCreate() {
  editingId.value = null
  const routeOrderId = typeof route.query.order_id === 'string' ? route.query.order_id : ''
  Object.assign(form, {
    vendor_id: '',
    related_doc_id: routeOrderId,
    related_doc_type: routeOrderId ? 'order' : '',
    order_item_id: typeof route.query.order_item_id === 'string' ? route.query.order_item_id : '',
    task_type: activeTaskType.value === 'all' ? 'production' : activeTaskType.value,
    description: '',
    quantity: 1,
    unit_price: 0,
    remark: '',
  })
  if (routeOrderId) void loadOrderItems(routeOrderId)
  else orderItems.value = []
  dialogVisible.value = true
}

function handleEdit(row: OutsourceTaskResponse) {
  editingId.value = row.id
  Object.assign(form, {
    vendor_id: row.vendor_id, related_doc_id: row.related_doc_id || '', related_doc_type: row.related_doc_type || '',
    order_item_id: row.order_item_id || '',
    task_type: row.task_type, description: row.description,
    quantity: row.quantity, unit_price: row.unit_price, remark: row.remark,
  })
  if (form.related_doc_type === 'order' && form.related_doc_id) {
    void loadOrderItems(form.related_doc_id, row.order_item_id || '', row.order_item_name || '')
  }
  else orderItems.value = []
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form }
    if (!canViewOutsourceCost.value) delete (payload as { unit_price?: number }).unit_price
    if (editingId.value) {
      await updateOutsourceTask(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createOutsourceTask(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await refreshData()
  } finally {
    saving.value = false
  }
}

async function handleUpdateStatus(row: OutsourceTaskResponse, status: string) {
  try {
    await updateOutsourceTask(row.id, { status })
    ElMessage.success(`已更新为：${statusLabel(status)}`)
    await refreshData()
  } catch { /* ignore */ }
}

async function handlePay(row: OutsourceTaskResponse) {
  // 先刷新最新的付款摘要
  try {
    const summary = await getOutsourceTaskPaymentSummary(row.id)
    payTask.value = summary
    payForm.amount = summary.unpaid_amount > 0 ? summary.unpaid_amount : 0
    payForm.payment_method = 'bank_transfer'
    payForm.paid_at = ''
    payForm.remark = ''
    payForm.payee_company_name = ''
    payDialogVisible.value = true
  } catch {
    // fallback: use row data
    payTask.value = {
      task_id: row.id,
      task_no: row.task_no,
      vendor_id: row.vendor_id,
      vendor_name: row.vendor_name || null,
      related_project_name: row.related_project_name || null,
      total_amount: row.total_amount,
      paid_amount: row.paid_amount,
      unpaid_amount: row.unpaid_amount,
    }
    payForm.amount = row.unpaid_amount > 0 ? row.unpaid_amount : 0
    payForm.payment_method = 'bank_transfer'
    payForm.paid_at = ''
    payForm.remark = ''
    payForm.payee_company_name = ''
    payDialogVisible.value = true
  }
}

async function handlePaySubmit() {
  if (!payTask.value) return
  paySaving.value = true
  try {
    await createOutsourcePayment({
      vendor_id: payTask.value.vendor_id,
      task_id: payTask.value.task_id,
      amount: payForm.amount,
      payment_method: payForm.payment_method || undefined,
      payee_company_name: payForm.payee_company_name || undefined,
      paid_at: payForm.paid_at || undefined,
      remark: payForm.remark || undefined,
    })
    ElMessage.success('付款成功')
    payDialogVisible.value = false
    await refreshData()
  } finally {
    paySaving.value = false
  }
}

async function handleCancel(row: OutsourceTaskResponse) {
  try {
    await ElMessageBox.confirm(`确认取消外协任务「${row.task_no}」？`, '确认', {
      confirmButtonText: '确认取消', cancelButtonText: '取消', type: 'warning',
    })
    await cancelOutsourceTask(row.id)
    ElMessage.success('外协任务已取消')
    await refreshData()
  } catch { /* ignore */ }
}

async function handleRevert(row: OutsourceTaskResponse) {
  try {
    await ElMessageBox.confirm(`确认退回外协任务「${row.task_no}」为进行中？`, '确认', {
      confirmButtonText: '确认退回', cancelButtonText: '取消', type: 'warning',
    })
    await revertOutsourceTask(row.id)
    ElMessage.success('外协任务已退回为进行中')
    await refreshData()
  } catch { /* ignore */ }
}

async function handleDelete(row: OutsourceTaskResponse) {
  // 拉取关联付款摘要，用于删除确认提示
  let summary: OutsourceTaskPaymentSummary | null = null
  try {
    summary = await getOutsourceTaskPaymentSummary(row.id)
  } catch { /* 摘要拿不到不阻塞删除 */ }

  const payments = summary?.payments ?? []
  let msg: string
  if (payments.length) {
    const total = payments.reduce((s, p) => s + p.amount, 0)
    const detail = payments.slice(0, 5).map(p => `${p.payment_no} ¥${p.amount.toFixed(2)}`).join('、')
    msg = `外协任务「${row.task_no}」关联 ${payments.length} 条付款记录，合计 ¥${total.toFixed(2)}` +
      (detail ? `（${detail}）` : '') +
      `。删除任务将一并删除这些付款记录，付款记录删除后不可恢复。确认删除？`
  } else {
    msg = `确认删除外协任务「${row.task_no}」？该任务无关联付款记录。删除后任务可在回收站恢复。`
  }

  try {
    await ElMessageBox.confirm(msg, '确认删除', {
      confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteOutsourceTask(row.id)
    ElMessage.success(payments.length ? `已删除任务及 ${payments.length} 条关联付款记录` : '外协任务已删除')
    await refreshData()
  } catch { /* ignore */ }
}

onMounted(() => {
  const requestedTaskType = route.query.task_type
  if (requestedTaskType === 'design' || requestedTaskType === 'production' || requestedTaskType === 'installation') {
    activeTaskType.value = requestedTaskType
  }
  fetchData(); loadVendors(); loadQuotes(); loadOrders()
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.task-tabs { margin-top: 8px; }
.search-bar { display: flex; align-items: center; flex-wrap: wrap; }
.form-tip { color: var(--ad-text-secondary); font-size: 12px; line-height: 1.5; }

.task-groups { margin-top: 16px; border-bottom: none; }
.task-groups :deep(.el-collapse-item__header) { min-height: 64px; height: auto; padding: 10px 16px; line-height: 1.4; }
.task-groups :deep(.el-collapse-item__wrap) { border-bottom: 1px solid var(--el-border-color-light); }
.group-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; width: 100%; min-width: 0; }
.group-heading { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1 1 auto; flex-wrap: wrap; }
.group-label { color: var(--ad-text); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-task-link { padding: 0; font-weight: 600; }
.group-project { display: flex; align-items: center; gap: 10px; min-width: 0; color: var(--ad-text-secondary); font-size: 13px; }
.group-project-name { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.group-project-amount { color: var(--ad-text); font-weight: 600; white-space: nowrap; }
.group-summary { display: flex; align-items: center; gap: 14px; flex-shrink: 0; color: var(--ad-text-secondary); font-size: 13px; white-space: nowrap; }
.group-summary .paid { color: var(--el-color-success); }
.group-summary .unpaid { color: var(--el-color-danger); }
.group-meta { display: flex; flex-wrap: wrap; gap: 8px 18px; padding: 0 0 10px; color: var(--ad-text-secondary); font-size: 12px; }
.group-warning { margin-bottom: 10px; }
.group-pagination { margin: 12px 0 4px; justify-content: flex-end; }

@media (max-width: 900px) {
  .group-header { align-items: flex-start; flex-direction: column; gap: 6px; }
  .group-summary { flex-wrap: wrap; white-space: normal; gap: 6px 12px; }
}

.pay-summary {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.pay-summary-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 14px;
}
.pay-summary-row .label { color: var(--el-text-color-secondary); }
.pay-summary-row .value { font-weight: 500; }
.pay-summary-row .value.total { font-weight: 600; color: var(--el-color-primary); }
.pay-summary-row .value.paid { color: var(--el-color-success); }
.pay-summary-row .value.unpaid { color: var(--el-color-danger); font-weight: 600; }
.pay-divider {
  height: 1px;
  background: var(--el-border-color-light);
  margin: 8px 0;
}
</style>
