<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">安装任务 {{ task.installation_no }}</h2>

      <el-card shadow="never" class="info-card">
        <el-descriptions :column="2">
          <el-descriptions-item label="任务编号">{{ task.installation_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ task.project_name }}</el-descriptions-item>
          <el-descriptions-item label="订单明细">{{ task.item_names?.join('、') || task.item_name || (task.order_item_id ? '明细未命名' : '未关联订单明细') }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span data-ai-targets="task-status-assigned task-status-completed task-status-in_progress task-status-pending_acceptance">
              <StatusTag :status="task.status_view || task.status" size="sm" />
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="任务进度">
            <ProgressBar :percentage="task.progress_pct" :tone="task.status_view?.tone" style="width: 220px" aria-label="任务进度" />
          </el-descriptions-item>
          <el-descriptions-item label="安装地址">{{ task.address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ task.contact_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ task.contact_phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划时间">{{ formatDateTimeFull(task.scheduled_at) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="任务计划">
            <span v-if="task.planned_start_at || task.planned_end_at">
              {{ formatDateTimeFull(task.planned_start_at) || '-' }} 至 {{ formatDateTimeFull(task.planned_end_at) || '-' }}
            </span>
            <span v-else>-</span>
            <el-tag v-if="task.is_overdue" type="danger" size="small" style="margin-left: 8px">逾期{{ task.overdue_days ? ` ${task.overdue_days} 天` : '' }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <TaskOrderItemLinkCard
        :task-type="'installation'"
        :task-id="task.id"
        :order-id="task.order_id"
        :current-item-id="task.order_item_id"
        :current-item-name="task.item_name"
        :current-item-ids="task.order_item_ids"
        :current-item-names="task.item_names"
        :task-capabilities="task.capabilities"
        :steps="instSteps"
        :current-status="task.status"
        :workflow="instWorkflow"
        :changing="changing"
        @linked="fetchTask"
        @change="handleWorkflowChange"
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
        :task-type="'installation'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
      />

      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button :loading="deleting" @click="handleDelete" type="danger">删除此任务</el-button>
        <span style="color: var(--ad-text-secondary); margin-left: 12px; font-size: 12px;">删除后订单将回退到生产中状态，下游任务将被清除</span>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span>现场照片</span>
            <el-upload
              :http-request="handleUpload"
              :show-file-list="false"
              accept="image/*"
              multiple
            >
              <el-button size="small">上传照片</el-button>
            </el-upload>
          </div>
        </template>
        <div class="photo-grid" v-if="task.attachments?.length">
          <div v-for="att in task.attachments" :key="att.id" class="photo-item">
            <img :src="`/uploads/${att.file_path}`" :alt="att.filename" class="photo-img" />
            <div class="photo-actions">
              <span class="photo-label">{{ att.category || att.filename }}</span>
              <el-button text type="danger" size="small" @click="handleDeleteAttachment(att.id)">删除</el-button>
            </div>
          </div>
        </div>
        <div v-else style="color: var(--ad-text-secondary); padding: 20px; text-align: center">暂无照片</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatDateTimeFull } from '@/utils/datetime'
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { ProgressBar, StatusTag } from '@/components/ui'
import { getInstallationTask, updateInstallationTask, changeInstallationTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { InstallationTaskResponse } from '@/types/api'
import { getEmployees } from '@/api/employees'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteInstallationTask } from '@/api/tasks'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const changing = ref(false)
const deleting = ref(false)
const task = ref<InstallationTaskResponse | null>(null)
const employeeOptions = ref<{ id: string; name: string; employee_no?: string; user_id?: string | null }[]>([])
const assignTarget = ref('')
const assigning = ref(false)
const INST_WORKFLOW: Record<string, string[]> = {
  pending: ['assigned', 'in_progress', 'cancelled'],
  assigned: ['in_progress', 'pending', 'cancelled'],
  in_progress: ['completed', 'pending_acceptance', 'pending', 'cancelled'],
  pending_acceptance: ['completed', 'in_progress', 'cancelled'],
  completed: [],
  cancelled: [],
}

const instSteps = computed(() => {
  const currentStatus = task.value?.status
  const isLegacyAcceptanceTask = !task.value?.order_item_id || currentStatus === 'pending_acceptance'
  if (!isLegacyAcceptanceTask) {
    return [
      { key: 'pending', label: '待分配' },
      { key: 'assigned', label: '已分配' },
      { key: 'in_progress', label: '安装中' },
      { key: 'completed', label: '已完成' },
    ]
  }
  return [
    { key: 'pending', label: '待分配' },
    { key: 'assigned', label: '已分配' },
    { key: 'in_progress', label: '安装中' },
    { key: 'pending_acceptance', label: '历史待验收' },
    { key: 'completed', label: '已完成' },
  ]
})

const instWorkflow = computed(() => {
  if (task.value?.order_item_id) return INST_WORKFLOW
  return {
    ...INST_WORKFLOW,
    in_progress: INST_WORKFLOW.in_progress.filter(status => status !== 'completed'),
  }
})

async function handleWorkflowChange(to_status: string, orderItemIds: string[]) {
  const labelMap: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成', cancelled: '已取消' }
  if (to_status === 'cancelled') {
    const { value: reason } = await ElMessageBox.prompt('请输入取消原因', '取消任务', {
      confirmButtonText: '确定', cancelButtonText: '取消',
      inputPlaceholder: '取消原因',
    })
    if (!reason) return
    await doChangeStatus(to_status, reason, orderItemIds)
  } else {
    await ElMessageBox.confirm(`确定将任务状态变更为「${labelMap[to_status]}」？`, '变更状态', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    await doChangeStatus(to_status, '', orderItemIds)
  }
}

async function doChangeStatus(to_status: string, reason: string, orderItemIds: string[]) {
  changing.value = true
  try {
    await changeInstallationTaskStatus(route.params.id as string, { to_status, reason, order_item_ids: orderItemIds })
    ElMessage.success('状态已变更')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function fetchTask() {
  loading.value = true
  try {
    const data = await getInstallationTask(route.params.id as string)
    task.value = data
  } finally { loading.value = false }
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
    await updateInstallationTask(route.params.id as string, { assigned_to: assignTarget.value || null })
    ElMessage.success('已派发')
    assignTarget.value = ''
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { assigning.value = false }
}

async function handleUpload(req: UploadRequestOptions) {
  try {
    const cat = req.file.type.startsWith('image/') ? 'photo' : 'file'
    await uploadAttachment('installation_task', route.params.id as string, req.file, cat)
    ElMessage.success('上传成功')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ }
}

async function handleDeleteAttachment(id: string) {
  await ElMessageBox.confirm('确定删除此照片？删除后无法恢复。', '删除照片', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  await deleteAttachment(id)
  ElMessage.success('已删除')
  fetchTask()
}

async function handleDelete() {
  await ElMessageBox.confirm(
    `确定删除安装任务 ${task.value?.installation_no || ''}？删除后不可恢复，关联订单将回退到生产中状态。`,
    '删除任务', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
  )
  deleting.value = true
  try {
    await deleteInstallationTask(route.params.id as string)
    ElMessage.success('任务已删除')
    router.push('/projects/board')
  } catch { /* handled */ } finally { deleting.value = false }
}

onMounted(() => {
  void fetchTask()
  void loadEmployees()
})
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.progress-suffix { margin-left: 8px; color: var(--ad-text-secondary); }
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.photo-item { background: #252540; border-radius: 6px; overflow: hidden; border: 1px solid var(--ad-border); }
.photo-img { width: 100%; height: 160px; object-fit: cover; }
.photo-actions { padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; }
.photo-label { font-size: 12px; color: #888; }
</style>
