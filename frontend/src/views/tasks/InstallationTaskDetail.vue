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
            <el-tag :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="安装地址">{{ task.address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ task.contact_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ task.contact_phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划时间">{{ task.scheduled_at?.slice(0, 19).replace('T', ' ') || '-' }}</el-descriptions-item>
          <el-descriptions-item label="验收结果">{{ task.acceptance_result || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>变更状态</span>  <span data-ai-target="task-status-assigned" style="display:none"></span>
  <span data-ai-target="task-status-completed" style="display:none"></span>
  <span data-ai-target="task-status-in_progress" style="display:none"></span>
  <span data-ai-target="task-status-pending_acceptance" style="display:none"></span>
</template>
        <TaskWorkflow
          :steps="instSteps"
          :current-status="task.status"
          :workflow="INST_WORKFLOW"
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
      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button type="danger" :loading="deleting" @click="handleDelete">删除此任务</el-button>
        <span style="color: #999; margin-left: 12px; font-size: 12px;">删除后订单将回退到生产中状态，下游任务将被清除</span>
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
        <div v-else style="color: #666; padding: 20px; text-align: center">暂无照片</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskWorkflow from '@/components/workflow/TaskWorkflow.vue'
import { getInstallationTask, updateInstallationTask, changeInstallationTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { getUsers } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { InstallationTaskResponse, UserResponse } from '@/types/api'
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
const pendingTarget = ref('')
const statusForm = reactive({ to_status: '', reason: '' })
const showReason = computed(() => {
  return !!pendingTarget.value && isReasonRequired(pendingTarget.value)
})
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
  pending: ['assigned', 'in_progress'],
  assigned: ['in_progress', 'pending'],
  in_progress: ['pending_acceptance', 'pending'],
  pending_acceptance: ['completed', 'in_progress'],
  completed: [],
  cancelled: [],
}

const instSteps = [
  { key: 'pending', label: '待分配' },
  { key: 'assigned', label: '已分配' },
  { key: 'in_progress', label: '安装中' },
  { key: 'pending_acceptance', label: '工人验收' },
  { key: 'completed', label: '已完成' },
]

function isReasonRequired(status: string) {
  return status === 'pending' || status.startsWith('cancel')
}

function handleWorkflowChange(status: string) {
  pendingTarget.value = status
  if (isReasonRequired(status)) return
  doChangeStatus(status, '')
}

async function doChangeStatus(to_status: string, reason: string) {
  await ElMessageBox.confirm(`确定将安装任务状态变更为「${instSteps.find(s => s.key === to_status)?.label || to_status}」？`, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  changing.value = true
  try {
    await changeInstallationTaskStatus(route.params.id as string, { to_status, reason })
    ElMessage.success('状态已变更')
    pendingTarget.value = ''
    statusForm.reason = ''
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function confirmChange() {
  if (!pendingTarget.value) return
  await doChangeStatus(pendingTarget.value, statusForm.reason)
}

function cancelChange() {
  pendingTarget.value = ''
  statusForm.reason = ''
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
    await aiStore.notifyBusinessMutation()
    router.back()
  } catch { /* handled */ } finally { deleting.value = false }
}

onMounted(() => {
  void fetchTask()
  void loadUsers()
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
