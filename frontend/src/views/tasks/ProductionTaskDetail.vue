<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">制作任务 {{ task.production_no }}</h2>

      <el-card shadow="never" class="info-card">
        <el-descriptions :column="2">
          <el-descriptions-item label="任务编号">{{ task.production_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ task.project_name }}</el-descriptions-item>
          <el-descriptions-item label="订单明细">{{ task.item_names?.join('、') || task.item_name || (task.order_item_id ? '明细未命名' : '整单任务') }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag data-ai-targets="task-status-completed task-status-in_progress task-status-qc_check task-status-queued task-status-rework" :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="任务进度">
            <el-progress :percentage="progressPct(task.progress_pct)" :stroke-width="8" style="width: 220px" />
          </el-descriptions-item>
          <el-descriptions-item label="计划时间">
            <span v-if="task.planned_start_at || task.planned_end_at">
              {{ formatDateTimeFull(task.planned_start_at) || '-' }} 至 {{ formatDateTimeFull(task.planned_end_at) || '-' }}
            </span>
            <span v-else>-</span>
            <el-tag v-if="task.is_overdue" type="danger" size="small" style="margin-left: 8px">逾期{{ task.overdue_days ? ` ${task.overdue_days} 天` : '' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="尺寸">长{{ task.length }}m × 宽{{ task.width }}m × 高{{ task.height }}m</el-descriptions-item>
          <el-descriptions-item label="数量">{{ task.quantity }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <TaskOrderItemLinkCard
        :task-type="'production'"
        :task-id="task.id"
        :order-id="task.order_id"
        :current-item-id="task.order_item_id"
        :current-item-name="task.item_name"
        :current-item-ids="task.order_item_ids"
        :current-item-names="task.item_names"
        :steps="prodSteps"
        :current-status="task.status"
        :workflow="PROD_WORKFLOW"
        :changing="changing"
        @linked="fetchTask"
        @change="handleWorkflowChange"
      />
      <TaskDependenciesCard
        :task-type="'production'"
        :task-id="task.id"
        :order-id="task.order_id"
        :is-blocked="task.is_blocked"
        :blocked-reason="task.blocked_reason"
        style="margin-top: 16px"
      />
      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>任务分配</span></template>
        <div data-ai-targets="task-assignee" style="display: flex; align-items: center; gap: 12px;">
          <el-select v-model="assignTarget" placeholder="选择员工" clearable filterable style="width: 300px">
            <el-option v-for="emp in employeeOptions" :key="emp.id" :label="emp.name + (emp.employee_no ? '(' + emp.employee_no + ')' : '')" :value="emp.user_id || emp.id" :disabled="!emp.user_id" />
          </el-select>
          <el-button :loading="assigning" @click="handleAssign">派发</el-button>
          <span v-if="task?.assigned_to_name" style="color: var(--ad-text-secondary); font-size: 13px;">当前：{{ task.assigned_to_name }}</span>
        </div>
      </el-card>
      <OutsourceTaskCard
        :task-type="'production'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
      />

      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button :loading="deleting" @click="handleDelete" type="danger">删除此任务</el-button>
        <span style="color: var(--ad-text-secondary); margin-left: 12px; font-size: 12px;">删除后订单将回退到设计中状态，下游任务将被清除</span>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>质检与返工</span></template>
        <el-form :model="editForm" label-width="120px">
          <el-form-item label="负责人" data-ai-target="task-assignee">
            <el-select
              v-model="editForm.assigned_to"
              placeholder="选择制作负责人"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="user in userOptions"
                :key="user.id"
                :label="user.real_name || user.username"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="质检结果">
            <el-select v-model="editForm.qc_result" style="width: 200px">
              <el-option label="合格" value="pass" />
              <el-option label="不合格" value="fail" />
            </el-select>
          </el-form-item>
          <el-form-item label="返工原因" v-if="editForm.qc_result === 'fail'">
            <el-input v-model="editForm.rework_reason" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="任务进度">
            <el-input-number v-model="editForm.progress_pct" :min="0" :max="100" :step="5" />
            <span class="progress-suffix">%</span>
          </el-form-item>
          <el-form-item label="计划开始时间">
            <el-date-picker v-model="editForm.planned_start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择计划开始时间" style="width: 100%" />
          </el-form-item>
          <el-form-item label="计划结束时间">
            <el-date-picker v-model="editForm.planned_end_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择计划结束时间" style="width: 100%" />
          </el-form-item>
          <el-form-item>
            <el-button :loading="updating" @click="handleUpdate" type="primary">保存</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span>附件</span>
            <el-upload
              :http-request="handleUpload"
              :show-file-list="false"
              accept="image/*"
            >
              <el-button size="small">上传文件</el-button>
            </el-upload>
          </div>
        </template>
        <el-table :data="task.attachments" stripe size="small">
          <el-table-column prop="filename" label="文件名" min-width="200" />
          <el-table-column prop="category" label="类别" width="100" />
          <el-table-column label="大小" width="100">
            <template #default="{ row }">{{ row.file_size ? (row.file_size / 1024).toFixed(1) + 'KB' : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button text type="danger" size="small" @click="handleDeleteAttachment(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive,  onMounted } from 'vue'
import { formatDateTimeFull } from '@/utils/datetime'
import { useRoute, useRouter } from 'vue-router'
import TaskDependenciesCard from '@/components/tasks/TaskDependenciesCard.vue'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { getProductionTask, updateProductionTask, changeProductionTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { getUsers } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { ProductionTaskResponse, UserResponse } from '@/types/api'
import { getEmployees } from '@/api/employees'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteProductionTask } from '@/api/tasks'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const deleting = ref(false)
const task = ref<ProductionTaskResponse | null>(null)
const userOptions = ref<UserResponse[]>([])
const employeeOptions = ref<{ id: string; name: string; employee_no?: string; user_id?: string | null }[]>([])
const assignTarget = ref('')
const assigning = ref(false)
const editForm = reactive({
  assigned_to: '',
  qc_result: '',
  rework_reason: '',
  progress_pct: 0,
  planned_start_at: '',
  planned_end_at: '',
})

const PROD_WORKFLOW: Record<string, string[]> = {
  pending: ['in_progress', 'cancelled'],
  in_progress: ['completed', 'rework', 'cancelled'],
  rework: ['in_progress', 'cancelled'],
  completed: [],
  cancelled: [],
}

const prodSteps = [
  { key: 'pending', label: '待制作' },
  { key: 'in_progress', label: '制作中' },
  { key: 'completed', label: '已完成' },
]

async function handleWorkflowChange(to_status: string) {
  const labelMap: Record<string, string> = { pending: '待制作', in_progress: '制作中', rework: '返工', completed: '已完成', cancelled: '已取消' }
  if (to_status === 'cancelled') {
    const { value: reason } = await ElMessageBox.prompt('请输入取消原因', '取消任务', {
      confirmButtonText: '确定', cancelButtonText: '取消',
      inputPlaceholder: '取消原因',
    })
    if (!reason) return
    await doChangeStatus(to_status, reason)
  } else {
    await ElMessageBox.confirm(`确定将任务状态变更为「${labelMap[to_status]}」？`, '变更状态', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    await doChangeStatus(to_status, '')
  }
}

async function doChangeStatus(to_status: string, reason: string) {
  changing.value = true
  try {
    await changeProductionTaskStatus(route.params.id as string, { to_status, reason })
    ElMessage.success('状态已变更')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待制作',  in_progress: '制作中',  rework: '返工', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info',  in_progress: '',  rework: 'danger', completed: 'success', cancelled: 'info' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function progressPct(value: number | undefined) {
  return Math.min(100, Math.max(0, Number(value ?? 0)))
}

function dateTimeInput(value: string | null | undefined) {
  if (!value) return ''
  const normalized = /(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value.slice(0, 19)
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function dateTimePayload(value: string | null | undefined) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toISOString().slice(0, 19)
}

async function fetchTask() {
  loading.value = true
  try {
    const data = await getProductionTask(route.params.id as string)
    task.value = data
    Object.assign(editForm, {
      assigned_to: data.assigned_to || '',
      qc_result: data.qc_result || '',
      rework_reason: data.rework_reason || '',
      progress_pct: progressPct(data.progress_pct),
      planned_start_at: dateTimeInput(data.planned_start_at),
      planned_end_at: dateTimeInput(data.planned_end_at),
    })
  } finally { loading.value = false }
}

async function loadUsers() {
  const data = await getUsers({ page_size: 100 })
  userOptions.value = data.items
}

async function loadEmployees() {
  try {
    const data = await getEmployees({ page_size: 100, employment_status: 'active' })
    employeeOptions.value = data.items
  } catch { /* employees module may not be ready */ }
}

async function handleAssign() {
  if (!assignTarget.value) return
  assigning.value = true
  try {
    await updateProductionTask(route.params.id as string, { assigned_to: assignTarget.value || null })
    ElMessage.success('已派发')
    assignTarget.value = ''
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { assigning.value = false }
}

async function handleUpdate() {
  updating.value = true
  try {
    await updateProductionTask(route.params.id as string, {
      ...editForm,
      assigned_to: editForm.assigned_to || null,
      progress_pct: progressPct(editForm.progress_pct),
      planned_start_at: dateTimePayload(editForm.planned_start_at),
      planned_end_at: dateTimePayload(editForm.planned_end_at),
    })
    ElMessage.success('保存成功')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { updating.value = false }
}



async function handleUpload(req: UploadRequestOptions) {
  try {
    await uploadAttachment('production_task', route.params.id as string, req.file, 'production')
    ElMessage.success('上传成功')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ }
}

async function handleDeleteAttachment(id: string) {
  await ElMessageBox.confirm('确定删除此附件？删除后无法恢复。', '删除附件', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  await deleteAttachment(id)
  ElMessage.success('已删除')
  fetchTask()
}

async function handleDelete() {
  await ElMessageBox.confirm(
    `确定删除制作任务 ${task.value?.production_no || ''}？删除后不可恢复，关联订单将回退到设计中状态。`,
    '删除任务', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
  )
  deleting.value = true
  try {
    await deleteProductionTask(route.params.id as string)
    ElMessage.success('任务已删除')
    router.push('/projects/board')
  } catch { /* handled */ } finally { deleting.value = false }
}

onMounted(() => {
  void fetchTask()
  void loadUsers()
  void loadEmployees()
})
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.progress-suffix { margin-left: 8px; color: var(--ad-text-secondary); }
</style>
