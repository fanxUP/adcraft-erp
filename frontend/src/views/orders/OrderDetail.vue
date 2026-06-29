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
                  <el-button size="small" type="danger" @click="showCostDialog = true">录入成本</el-button>
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

          <el-card shadow="never" class="info-card" style="margin-top: 16px">
            <template #header>
              <div class="card-header">
                <span>变更状态</span>
              </div>
            </template>
            <el-form :model="statusForm" inline>
              <el-form-item label="目标状态">
                <el-select v-model="statusForm.to_status" style="width: 160px">
                  <el-option label="已确认" value="confirmed" />
                  <el-option label="进行中" value="in_progress" />
                  <el-option label="已完成" value="completed" />
                  <el-option label="已取消" value="cancelled" />
                </el-select>
              </el-form-item>
              <el-form-item label="原因">
                <el-input v-model="statusForm.reason" style="width: 200px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="changing" @click="handleChangeStatus">变更</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="订单明细" name="items">
          <el-card shadow="never" class="info-card">
            <el-table :data="order.items" stripe size="small">
              <el-table-column prop="item_name" label="项目" min-width="180" />
              <el-table-column label="长(m)" width="90">
                <template #default="{ row }">{{ row.length ?? '-' }}</template>
              </el-table-column>
              <el-table-column label="宽(m)" width="90">
                <template #default="{ row }">{{ row.width ?? '-' }}</template>
              </el-table-column>
              <el-table-column label="数量" width="80">
                <template #default="{ row }">{{ row.quantity }}</template>
              </el-table-column>
              <el-table-column label="单价" width="120">
                <template #default="{ row }">¥ {{ row.unit_price?.toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="小计" width="120">
                <template #default="{ row }">¥ {{ row.subtotal_amount?.toFixed(2) }}</template>
              </el-table-column>
            </el-table>
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

    <el-dialog v-model="showCostDialog" title="录入成本" width="400px">
      <el-form label-width="80px">
        <el-form-item label="订单金额">
          <span>¥ {{ order?.total_amount?.toFixed(2) }}</span>
        </el-form-item>
        <el-form-item label="成本金额">
          <el-input-number v-model="costAmount" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCostDialog = false">取消</el-button>
        <el-button type="danger" :loading="savingCost" @click="handleSaveCost">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getOrder, changeOrderStatus, setOrderCost, autoCalculateCost } from '@/api/orders'
import { getDesignTasks, getProductionTasks, getInstallationTasks, createDesignTask, createProductionTask, createInstallationTask } from '@/api/tasks'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const changing = ref(false)
const tasksLoading = ref(false)
const order = ref<any>(null)
const activeTab = ref('info')
const statusForm = reactive({ to_status: '', reason: '' })

const designTasks = ref<any[]>([])
const productionTasks = ref<any[]>([])
const installationTasks = ref<any[]>([])
const showDesignDialog = ref(false)
const showProdDialog = ref(false)
const showInstDialog = ref(false)
const showCostDialog = ref(false)
const costAmount = ref(0)
const savingCost = ref(false)
const autoCostLoading = ref(false)
const taskForm = reactive({ project_name: '', assigned_to: '' as string | null, description: '', quantity: 1 })

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return map[s] || 'info'
}

function designStatusLabel(s: string) { const m: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已确认' }; return m[s] || s }
function designStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', designing: '', pending_review: 'warning', revision: 'danger', confirmed: 'success' }; return m[s] || 'info' }
function prodStatusLabel(s: string) { const m: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成' }; return m[s] || s }
function prodStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success' }; return m[s] || 'info' }
function instStatusLabel(s: string) { const m: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成' }; return m[s] || s }
function instStatusColor(s: string) { const m: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success' }; return m[s] || 'info' }

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
      getDesignTasks({ order_id: route.params.id, page_size: 100 }),
      getProductionTasks({ order_id: route.params.id, page_size: 100 }),
      getInstallationTasks({ order_id: route.params.id, page_size: 100 }),
    ])
    designTasks.value = d.items; productionTasks.value = p.items; installationTasks.value = i.items
  } finally { tasksLoading.value = false }
}

async function handleCreateDesign() {
  await createDesignTask({ order_id: route.params.id, customer_id: order.value.customer_id, project_name: taskForm.project_name || order.value.project_name, assigned_to: taskForm.assigned_to || undefined, description: taskForm.description })
  ElMessage.success('已创建设计任务')
  showDesignDialog.value = false; taskForm.project_name = ''; taskForm.assigned_to = ''; taskForm.description = ''
  fetchTasks()
}
async function handleCreateProduction() {
  await createProductionTask({ order_id: route.params.id, customer_id: order.value.customer_id, project_name: taskForm.project_name || order.value.project_name, assigned_to: taskForm.assigned_to || undefined, quantity: taskForm.quantity })
  ElMessage.success('已创建制作任务')
  showProdDialog.value = false; taskForm.project_name = ''; taskForm.assigned_to = ''; taskForm.quantity = 1
  fetchTasks()
}
async function handleCreateInstallation() {
  await createInstallationTask({ order_id: route.params.id, customer_id: order.value.customer_id, project_name: taskForm.project_name || order.value.project_name, assigned_to: taskForm.assigned_to || undefined, address: order.value.installation_address || '' })
  ElMessage.success('已创建安装任务')
  showInstDialog.value = false; taskForm.project_name = ''; taskForm.assigned_to = ''
  fetchTasks()
}

async function handleSaveCost() {
  savingCost.value = true
  try {
    order.value = await setOrderCost(route.params.id as string, costAmount.value)
    ElMessage.success('成本已保存')
    showCostDialog.value = false
  } finally { savingCost.value = false }
}

async function handleAutoCost() {
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
</style>
