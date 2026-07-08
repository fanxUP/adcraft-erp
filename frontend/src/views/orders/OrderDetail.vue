<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="order" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">订单 {{ order.order_no }}</h2>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="info">
          <el-card shadow="never" class="info-card">
            <el-descriptions :column="2">
              <el-descriptions-item label="订单编号">{{ order.order_no }}</el-descriptions-item>
              <el-descriptions-item label="项目名称">{{ order.project_name }}</el-descriptions-item>
             <el-descriptions-item label="状态">
                <el-tag :type="statusColor(order.status)">{{ statusLabel(order.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="联系人">{{ order.contact_person || '-' }}</el-descriptions-item>
              <el-descriptions-item label="联系电话">{{ order.contact_phone || '-' }}</el-descriptions-item>
              <el-descriptions-item label="总金额">¥ {{ order.total_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="已收金额">¥ {{ order.paid_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="未收金额">¥ {{ order.unpaid_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="安装地址">{{ order.installation_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="备注">{{ order.remark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="info-card" style="margin-top: 16px">
            <template #header>
              <div class="card-header">
                <span>成本与利润</span>
                <div>
                  <el-button size="small" @click="handleAutoCost" :loading="autoCostLoading">自动核算</el-button>
                  <el-button size="small" type="danger" @click="$router.push(`/project-costs/${order.id}`)">登记成本</el-button>
                </div>
              </div>
            </template>
            <el-descriptions :column="3">
              <el-descriptions-item label="订单金额">¥ {{ order.total_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="成本金额">¥ {{ order.cost_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="毛利">
                <el-tag :type="(order.gross_profit || 0) >= 0 ? 'success' : 'danger'" size="small">
                  ¥ {{ order.gross_profit?.toFixed(2) }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 订单状态流程图按钮 -->
          <OrderWorkflow
            :current-status="order.status"
            :changing="changing"
            @change="handleChangeStatus"
          />
        </el-tab-pane>

        <el-tab-pane label="订单明细" name="items">
          <el-card shadow="never" class="info-card">
            <el-table :data="displayRows" stripe border size="small" :row-class-name="rowClassName">
              <el-table-column label="序号" width="55">
                <template #default="{ row, $index }">
                  <template v-if="row.type === 'item'">{{ itemIndex(row, $index) }}</template>
                </template>
              </el-table-column>
              <el-table-column label="项目内容" min-width="150">
                <template #default="{ row }">
                  <template v-if="row.type === 'group-header'">
                    <span style="font-weight: 600;">分项：{{ row.groupName }}</span>
                  </template>
                  <template v-else-if="row.type === 'group-total'">
                    <span style="font-weight: 600; float: right;">分项合计</span>
                  </template>
                  <template v-else>{{ row.item.item_name }}</template>
                </template>
              </el-table-column>
              <el-table-column label="材质工艺" min-width="120">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.material_process || '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="规格" min-width="140">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">
                    <template v-if="row.item.specification">
                      {{ row.item.specification }}
                    </template>
                    <template v-else-if="row.item.length || row.item.width || row.item.height">
                      {{ row.item.length ?? '' }}{{ row.item.length_unit || 'm' }}
                      <template v-if="row.item.width"> x {{ row.item.width }}{{ row.item.width_unit || 'm' }}</template>
                      <template v-if="row.item.height"> x {{ row.item.height }}{{ row.item.height_unit || 'm' }}</template>
                    </template>
                    <span v-else>-</span>
                  </template>
                </template>
              </el-table-column>
              <el-table-column label="面积" width="80">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.area != null ? row.item.area.toFixed(2) : '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="数量" width="70">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.quantity }}</template>
                </template>
              </el-table-column>
              <el-table-column label="单位" width="60">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.unit || '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="单价" width="90">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">¥ {{ row.item.unit_price?.toFixed(2) }}</template>
                </template>
              </el-table-column>
              <el-table-column label="工艺费" width="90">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.process_fee ? '¥ ' + row.item.process_fee.toFixed(2) : '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="安装费" width="90">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.installation_fee ? '¥ ' + row.item.installation_fee.toFixed(2) : '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="设计费" width="90">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.design_fee ? '¥ ' + row.item.design_fee.toFixed(2) : '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="运输费" width="90">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.transport_fee ? '¥ ' + row.item.transport_fee.toFixed(2) : '-' }}</template>
                </template>
              </el-table-column>
              <el-table-column label="小计" width="110">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">¥ {{ row.item.subtotal_amount?.toFixed(2) }}</template>
                  <template v-else-if="row.type === 'group-total'"><strong>¥ {{ row.total.toFixed(2) }}</strong></template>
                </template>
              </el-table-column>
              <el-table-column label="样图" width="80">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">
                    <el-image v-if="row.item.image_url" :src="row.item.image_url" :preview-src-list="[row.item.image_url]" fit="cover" style="width: 32px; height: 32px; border-radius: 4px; cursor: pointer;" />
                    <span v-else style="color: #999;">-</span>
                  </template>
                </template>
              </el-table-column>
              <el-table-column label="备注" min-width="120">
                <template #default="{ row }">
                  <template v-if="row.type === 'item'">{{ row.item.remark || '-' }}</template>
                </template>
              </el-table-column>
            </el-table>

            <!-- 明细合计 -->
            <div v-if="order.items?.length" style="margin-top: 12px; padding-top: 12px; border-top: 2px solid var(--ad-primary, #409eff); text-align: right;">
              <div style="font-size: 16px; font-weight: 600; color: var(--ad-text); margin-bottom: 6px;">
                明细合计：¥ {{ itemsTotal.toFixed(2) }}
              </div>
              <div style="font-size: 13px; color: var(--ad-text-secondary);">
                大写金额：{{ toChineseAmount(itemsTotal) }}
              </div>
            </div>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="状态日志" name="logs">
          <el-card shadow="never" class="info-card">
            <el-timeline>
              <el-timeline-item
                v-for="log in order.status_logs"
                :key="log.id"
                :timestamp="log.operated_at?.slice(0, 19).replace('T', ' ')"
                placement="top"
              >
                <div>
                  <el-tag v-if="log.from_status" size="small">{{ statusLabel(log.from_status) }}</el-tag>
                  <span v-else style="color: var(--ad-text-secondary)">-</span>
                  <span style="margin: 0 8px">→</span>
                  <el-tag :type="statusColor(log.to_status)" size="small">{{ statusLabel(log.to_status) }}</el-tag>
                  <span v-if="log.reason" style="margin-left: 8px; color: var(--ad-text-secondary)">{{ log.reason }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="任务" name="tasks">
          <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
            <template #header>
              <div class="card-header">
                <span>设计任务</span>
                <el-button size="small" type="danger" @click="showDesignDialog = true">创建</el-button>
              </div>
            </template>
            <el-table :data="designTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="design_no" label="编号" width="180" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="designStatusColor(row.status)" size="small">{{ designStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="$router.push(`/design-tasks/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
            <template #header>
              <div class="card-header">
                <span>制作任务</span>
                <el-button size="small" type="danger" @click="showProdDialog = true">创建</el-button>
              </div>
            </template>
            <el-table :data="productionTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="production_no" label="编号" width="180" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="prodStatusColor(row.status)" size="small">{{ prodStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="$router.push(`/production-tasks/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">
                <span>安装任务</span>
                <el-button size="small" type="danger" @click="showInstDialog = true">创建</el-button>
              </div>
            </template>
            <el-table :data="installationTasks" stripe size="small" v-loading="tasksLoading">
              <el-table-column prop="installation_no" label="编号" width="180" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="instStatusColor(row.status)" size="small">{{ instStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="$router.push(`/installation-tasks/${row.id}`)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="showDesignDialog" title="创建设计任务" width="450px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="项目名称">
          <el-input v-model="taskForm.project_name" :placeholder="order?.project_name" />
        </el-form-item>
        <el-form-item label="设计师">
          <el-input v-model="taskForm.assigned_to" placeholder="可选" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="taskForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDesignDialog = false">取消</el-button>
        <el-button type="danger" @click="handleCreateDesign">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showProdDialog" title="创建制作任务" width="450px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="项目名称">
          <el-input v-model="taskForm.project_name" :placeholder="order?.project_name" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="taskForm.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="taskForm.assigned_to" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProdDialog = false">取消</el-button>
        <el-button type="danger" @click="handleCreateProduction">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showInstDialog" title="创建安装任务" width="450px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="项目名称">
          <el-input v-model="taskForm.project_name" :placeholder="order?.project_name" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="taskForm.assigned_to" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInstDialog = false">取消</el-button>
        <el-button type="danger" @click="handleCreateInstallation">创建</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import OrderWorkflow from './OrderWorkflow.vue'
import { useRoute } from 'vue-router'
import { getOrder, changeOrderStatus, autoCalculateCost } from '@/api/orders'
import { getDesignTasks, getProductionTasks, getInstallationTasks, createDesignTask, createProductionTask, createInstallationTask } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { DesignTaskResponse, ProductionTaskResponse, InstallationTaskResponse, OrderDetailResponse, OrderItemResponse } from '@/types/api'

const route = useRoute()
const loading = ref(false)
const changing = ref(false)
const tasksLoading = ref(false)
const order = ref<OrderDetailResponse | null>(null)
const activeTab = ref('info')
// 状态管理由 OrderWorkflow 组件接管

const designTasks = ref<DesignTaskResponse[]>([])
const productionTasks = ref<ProductionTaskResponse[]>([])
const installationTasks = ref<InstallationTaskResponse[]>([])
const showDesignDialog = ref(false)
const showProdDialog = ref(false)
const showInstDialog = ref(false)
const autoCostLoading = ref(false)
const taskForm = reactive({ project_name: '', assigned_to: '' as string | null, description: '', quantity: 1 })

const itemsTotal = computed(() => (order.value?.items || []).reduce((s, i) => s + (i.subtotal_amount || 0), 0))

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
        if (unitIdx === 0 && bigUnits[bigIdx]) {
          result += bigUnits[bigIdx]
          zeroFlag = false
        }
      } else {
        if (zeroFlag) { result += '零'; zeroFlag = false }
        result += digits[d] + units[unitIdx]
        if (unitIdx === 0 && bigUnits[bigIdx]) result += bigUnits[bigIdx]
      }
    }
    result += '元'
  }

  if (jiao === 0 && fen === 0) {
    result += '整'
  } else {
    if (jiao > 0) result += digits[jiao] + '角'
    else if (intPart > 0) result += '零'
    if (fen > 0) result += digits[fen] + '分'
  }

  return (negative ? '负' : '') + result
}

type DisplayRow =
  | { type: 'group-header'; groupName: string }
  | { type: 'item'; item: OrderItemResponse; groupName: string }
  | { type: 'group-total'; groupName: string; total: number }

const displayRows = computed<DisplayRow[]>(() => {
  const items = order.value?.items || []
  const grouped = new Map<string, OrderItemResponse[]>()
  const ungrouped: OrderItemResponse[] = []

  for (const item of items) {
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
    const total = groupItems.reduce((s, i) => s + (i.subtotal_amount || 0), 0)
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

function itemIndex(row: DisplayRow, displayIdx: number): number {
  let count = 0
  for (let i = 0; i <= displayIdx; i++) {
    if (displayRows.value[i].type === 'item') count++
  }
  return count
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function designStatusLabel(s: string) { const m: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已确认' }; return m[s] || s }
function designStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', designing: '', pending_review: 'warning', revision: 'danger', confirmed: 'success' }; return (m[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined }
function prodStatusLabel(s: string) { const m: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成' }; return m[s] || s }
function prodStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success' }; return (m[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined }
function instStatusLabel(s: string) { const m: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成' }; return m[s] || s }
function instStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success' }; return (m[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined }

async function fetchOrder() {
  loading.value = true
  try {
    order.value = await getOrder(route.params.id as string)
  } finally { loading.value = false }
}

async function fetchTasks() {
  tasksLoading.value = true
  try {
    const [d, p, i] = await Promise.all([
      getDesignTasks({ order_id: route.params.id as string, page_size: 100 }),
      getProductionTasks({ order_id: route.params.id as string, page_size: 100 }),
      getInstallationTasks({ order_id: route.params.id as string, page_size: 100 }),
    ])
    designTasks.value = d.items; productionTasks.value = p.items; installationTasks.value = i.items
  } finally { tasksLoading.value = false }
}

async function handleCreateDesign() {
  if (!order.value) return
  await createDesignTask({ order_id: route.params.id as string, customer_id: order.value.customer_id, project_name: taskForm.project_name || order.value.project_name, assigned_to: taskForm.assigned_to || undefined, description: taskForm.description })
  ElMessage.success('已创建设计任务')
  showDesignDialog.value = false; taskForm.project_name = ''; taskForm.assigned_to = ''; taskForm.description = ''
  fetchTasks()
}
async function handleCreateProduction() {
  if (!order.value) return
  await createProductionTask({ order_id: route.params.id as string, customer_id: order.value.customer_id, project_name: taskForm.project_name || order.value.project_name, assigned_to: taskForm.assigned_to || undefined, quantity: taskForm.quantity })
  ElMessage.success('已创建制作任务')
  showProdDialog.value = false; taskForm.project_name = ''; taskForm.assigned_to = ''; taskForm.quantity = 1
  fetchTasks()
}
async function handleCreateInstallation() {
  if (!order.value) return
  await createInstallationTask({ order_id: route.params.id as string, customer_id: order.value.customer_id, project_name: taskForm.project_name || order.value.project_name, assigned_to: taskForm.assigned_to || undefined, address: order.value.installation_address || '' })
  ElMessage.success('已创建安装任务')
  showInstDialog.value = false; taskForm.project_name = ''; taskForm.assigned_to = ''
  fetchTasks()
}

async function handleChangeStatus(to_status: string) {
  const labels: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  const label = labels[to_status] || to_status
  const msg = to_status === 'cancelled'
    ? '确定取消此订单？此操作不可撤销。'
    : `确定将订单状态变更为「${label}」？`
  await ElMessageBox.confirm(msg, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  changing.value = true
  try {
    order.value = await changeOrderStatus(route.params.id as string, {
      to_status,
      reason: undefined,
    })
    ElMessage.success(`状态已变更为「${label}」`)
  } finally { changing.value = false }
}

async function handleAutoCost() {
  await ElMessageBox.confirm('将覆盖现有成本数据，确定继续？', '自动核算', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  autoCostLoading.value = true
  try {
    order.value = await autoCalculateCost(route.params.id as string)
    ElMessage.success('自动核算完成')
  } finally { autoCostLoading.value = false }
}

onMounted(() => { fetchOrder(); fetchTasks() })
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
:deep(.group-header-row) { background: var(--ad-bg-secondary, #f5f7fa) !important; }
:deep(.group-header-row td) { border-bottom: 2px solid var(--ad-primary, #409eff) !important; }
:deep(.group-total-row) { background: var(--ad-bg-secondary, #fafafa) !important; }
:deep(.group-total-row td) { border-top: 1px solid var(--ad-border, #dcdfe6) !important; font-weight: 600; }
</style>
