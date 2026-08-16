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
          <el-descriptions-item label="状态">
            <el-tag data-ai-targets="task-status-assigned task-status-completed task-status-in_progress task-status-pending_acceptance" :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="安装地址">{{ task.address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ task.contact_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ task.contact_phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划时间">{{ formatDateTimeFull(task.scheduled_at) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="验收结果">{{ task.acceptance_result || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>变更状态</span></template>
        <TaskWorkflow
          :steps="instSteps"
          :current-status="task.status"
          :workflow="INST_WORKFLOW"
          :changing="changing"
          @change="handleWorkflowChange"
        />

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
        :task-type="'installation'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
      />

      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button type="danger" :loading="deleting" @click="handleDelete">删除此任务</el-button>
        <span style="color: var(--ad-text-secondary); margin-left: 12px; font-size: 12px;">删除后订单将回退到生产中状态，下游任务将被清除</span>
      </el-card>

      <AiInstallationDraftCard
        v-if="activeDraft"
        :draft="activeDraft"
        :current-values="draftCurrentValues"
        @apply="handleApplyDraft"
      />

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>任务信息与验收</span></template>
        <el-form :model="editForm" label-width="120px">
          <el-form-item label="负责人" data-ai-target="task-assignee">
            <el-select
              v-model="editForm.assigned_to"
              placeholder="选择安装负责人"
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
          <el-form-item label="安装地址" data-ai-target="installation-address">
            <el-input v-model="editForm.address" placeholder="填写准确安装地址" />
          </el-form-item>
          <el-form-item label="计划安装时间" data-ai-target="installation-schedule">
            <el-date-picker
              v-model="editForm.scheduled_at"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              placeholder="选择计划安装时间"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="联系人">
            <el-input v-model="editForm.contact_name" />
          </el-form-item>
          <el-form-item label="联系电话">
            <el-input v-model="editForm.contact_phone" />
          </el-form-item>
          <el-form-item label="验收结果">
            <el-input v-model="editForm.acceptance_result" type="textarea" :rows="3" placeholder="填写验收意见..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
          </el-form-item>
        </el-form>
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
              <el-button type="danger" size="small">上传照片</el-button>
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
import { computed, ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskWorkflow from '@/components/workflow/TaskWorkflow.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { getInstallationTask, updateInstallationTask, changeInstallationTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { getUsers } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { InstallationTaskResponse, UserResponse } from '@/types/api'
import { getEmployees } from '@/api/employees'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteInstallationTask } from '@/api/tasks'
import { isSameWorkflowPath } from '@/utils/pageActionGuide'
import { applyInstallationDraft } from '@/utils/installationDraft'
import AiInstallationDraftCard from '@/components/ai-assistant/AiInstallationDraftCard.vue'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const deleting = ref(false)
const task = ref<InstallationTaskResponse | null>(null)
const userOptions = ref<UserResponse[]>([])
const employeeOptions = ref<{ id: string; name: string; employee_no?: string; user_id?: string | null }[]>([])
const assignTarget = ref('')
const assigning = ref(false)
const editForm = reactive({
  assigned_to: '',
  address: '',
  scheduled_at: '',
  contact_name: '',
  contact_phone: '',
  acceptance_result: '',
})
const activeDraft = computed(() => {
  const guide = aiStore.activePageGuide
  if (
    guide?.draft?.kind !== 'installation_task_update'
    || !isSameWorkflowPath(route.path, guide.target_path)
  ) {
    return null
  }
  return guide.draft
})
const draftCurrentValues = computed<Record<string, string>>(() => ({
  assigned_to: (() => {
    const user = userOptions.value.find(option => option.id === editForm.assigned_to)
    return user?.real_name || user?.username || editForm.assigned_to
  })(),
  address: editForm.address,
  scheduled_at: editForm.scheduled_at.replace('T', ' '),
}))

const INST_WORKFLOW: Record<string, string[]> = {
  pending: ['assigned', 'in_progress', 'cancelled'],
  assigned: ['in_progress', 'pending', 'cancelled'],
  in_progress: ['pending_acceptance', 'pending', 'cancelled'],
  pending_acceptance: ['completed', 'in_progress', 'cancelled'],
  completed: [],
  cancelled: [],
}

const instSteps = [
  { key: 'pending', label: '待分配' },
  { key: 'assigned', label: '已分配' },
  { key: 'in_progress', label: '安装中' },
  { key: 'pending_acceptance', label: '待验收' },
  { key: 'completed', label: '已完成' },
]

async function handleWorkflowChange(to_status: string) {
  const labelMap: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成', cancelled: '已取消' }
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
    await changeInstallationTaskStatus(route.params.id as string, { to_status, reason })
    ElMessage.success('状态已变更')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '工人验收', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success', cancelled: 'info' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchTask() {
  loading.value = true
  try {
    const data = await getInstallationTask(route.params.id as string)
    task.value = data
    Object.assign(editForm, {
      assigned_to: data.assigned_to || '',
      address: data.address || '',
      scheduled_at: data.scheduled_at || '',
      contact_name: data.contact_name || '',
      contact_phone: data.contact_phone || '',
      acceptance_result: data.acceptance_result || '',
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
    await updateInstallationTask(route.params.id as string, { assigned_to: assignTarget.value || null })
    ElMessage.success('已派发')
    assignTarget.value = ''
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { assigning.value = false }
}

async function handleUpdate() {
  updating.value = true
  try {
    await updateInstallationTask(route.params.id as string, {
      ...editForm,
      assigned_to: editForm.assigned_to || null,
      scheduled_at: editForm.scheduled_at || null,
    })
    ElMessage.success('保存成功')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { updating.value = false }
}

function handleApplyDraft() {
  if (!activeDraft.value) return
  const applied = applyInstallationDraft(editForm, activeDraft.value)
  if (!applied.length) {
    ElMessage.warning('草稿中没有可直接填入的内容，请按提示手动完善')
    return
  }
  ElMessage.success(`已填入 ${applied.length} 项建议，请核对后点击保存`)
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
  void loadUsers()
  void loadEmployees()
})
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.photo-item { background: #252540; border-radius: 6px; overflow: hidden; border: 1px solid var(--ad-border); }
.photo-img { width: 100%; height: 160px; object-fit: cover; }
.photo-actions { padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; }
.photo-label { font-size: 12px; color: #888; }
</style>
