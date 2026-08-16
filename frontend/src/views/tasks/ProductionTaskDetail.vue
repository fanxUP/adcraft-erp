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
          <el-descriptions-item label="状态">
            <el-tag data-ai-targets="task-status-completed task-status-in_progress task-status-qc_check task-status-queued task-status-rework" :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="尺寸">长{{ task.length }}m × 宽{{ task.width }}m × 高{{ task.height }}m</el-descriptions-item>
          <el-descriptions-item label="数量">{{ task.quantity }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>变更状态</span></template>
        <TaskWorkflow
          :steps="prodSteps"
          :current-status="task.status"
          :workflow="PROD_WORKFLOW"
          :changing="changing"
          @change="handleWorkflowChange"
        />
        <el-form v-if="showReason" :model="statusForm" inline style="margin-top: 12px">
          <el-form-item label="原因">
            <el-input v-model="statusForm.reason" style="width: 240px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="changing" @click="confirmChange">确认变更</el-button>
            <el-button @click="cancelChange">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>
      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>任务分配</span></template>
        <div data-ai-targets="task-assignee" style="display: flex; align-items: center; gap: 12px;">
          <el-select v-model="assignTarget" placeholder="选择员工" clearable filterable style="width: 300px">
            <el-option v-for="emp in employeeOptions" :key="emp.id" :label="emp.name + (emp.employee_no ? '(' + emp.employee_no + ')' : '')" :value="emp.user_id || emp.id" :disabled="!emp.user_id" />
          </el-select>
          <el-button type="primary" :loading="assigning" @click="handleAssign">派发</el-button>
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
        <el-button type="danger" :loading="deleting" @click="handleDelete">删除此任务</el-button>
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
          <el-form-item>
            <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
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
              <el-button type="danger" size="small">上传文件</el-button>
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
import { useRoute, useRouter } from 'vue-router'
import TaskWorkflow from '@/components/workflow/TaskWorkflow.vue'
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
const editForm = reactive({ assigned_to: '', qc_result: '', rework_reason: '' })

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

async function fetchTask() {
  loading.value = true
  try {
    const data = await getProductionTask(route.params.id as string)
    task.value = data
    Object.assign(editForm, {
      assigned_to: data.assigned_to || '',
      qc_result: data.qc_result || '',
      rework_reason: data.rework_reason || '',
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
</style>
