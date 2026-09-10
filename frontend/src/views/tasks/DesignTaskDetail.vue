<template>
  <div class="page">
    <el-button text @click="$router.push('/projects/board')">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">设计任务 {{ task.design_no }}</h2>

      <el-card data-ai-targets="design-file" shadow="never" class="info-card">
        <el-descriptions :column="2">
          <el-descriptions-item label="任务编号">{{ task.design_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ task.project_name }}</el-descriptions-item>
          <el-descriptions-item label="订单明细">{{ task.item_names?.join('、') || task.item_name || (task.order_item_id ? '明细未命名' : '未关联订单明细') }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span data-ai-targets="task-status-pending_review task-status-designing task-status-confirmed task-status-revision">
              <StatusTag :status="task.status_view || task.status" size="sm" />
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="任务进度">
            <ProgressBar :percentage="task.progress_pct" :tone="task.status_view?.tone" style="width: 220px" aria-label="任务进度" />
          </el-descriptions-item>
          <el-descriptions-item label="计划时间">
            <span v-if="task.planned_start_at || task.planned_end_at">
              {{ formatDateTimeFull(task.planned_start_at) || '-' }} 至 {{ formatDateTimeFull(task.planned_end_at) || '-' }}
            </span>
            <span v-else>-</span>
            <el-tag v-if="task.is_overdue" type="danger" size="small" style="margin-left: 8px">逾期{{ task.overdue_days ? ` ${task.overdue_days} 天` : '' }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <TaskOrderItemLinkCard
        :task-type="'design'"
        :task-id="task.id"
        :order-id="task.order_id"
        :current-item-id="task.order_item_id"
        :current-item-ids="task.order_item_ids"
        :task-capabilities="task.capabilities"
        :assigned-to="task.assigned_to"
        :assigned-to-name="task.assigned_to_name"
        :employee-options="employeeOptions"
        :assigning="assigning"
        :steps="designSteps"
        :current-status="task.status"
        :workflow="DESIGN_WORKFLOW"
        :changing="changing"
        @linked="fetchTask"
        @assign="handleSaveAssignment"
        @change="handleWorkflowChange"
      />

      <OutsourceTaskCard
        :task-type="'design'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
      />

      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button :loading="deleting" @click="handleDelete" type="danger">删除此任务</el-button>
        <span style="color: var(--ad-text-secondary); margin-left: 12px; font-size: 12px;">删除后订单将回退到确认状态，下游任务将被清除</span>
      </el-card>

      <el-card shadow="never" class="info-card attachment-card" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span>任务附件 <el-tag size="small" type="info">{{ attachments.length }} 个</el-tag></span>
            <span class="attachment-header-hint">拖拽或点击上传</span>
          </div>
        </template>
        <div
          class="attachment-dropzone"
          :class="{ 'is-dragover': attachmentDragActive, 'is-disabled': attachmentUploadDisabled }"
          role="button"
          tabindex="0"
          @click="openAttachmentPicker"
          @keydown.enter.prevent="openAttachmentPicker"
          @keydown.space.prevent="openAttachmentPicker"
          @dragenter.prevent="handleAttachmentDragEnter"
          @dragover.prevent="handleAttachmentDragOver"
          @dragleave.prevent="handleAttachmentDragLeave"
          @drop.prevent="handleAttachmentDrop"
        >
          <input
            ref="attachmentInput"
            class="attachment-input"
            type="file"
            multiple
            :accept="TASK_ATTACHMENT_ACCEPT"
            :disabled="attachmentUploadDisabled"
            @click.stop
            @change="handleAttachmentInputChange"
          />
          <el-icon class="attachment-drop-icon"><UploadFilled /></el-icon>
          <div class="attachment-drop-title">将设计图片、视频或文件拖到这里上传</div>
          <div class="attachment-drop-subtitle">或点击选择文件，支持批量上传</div>
          <div class="attachment-drop-hint">图片仅支持 JPG、PNG、WEBP（≤10MB）；视频、PDF、Word、Excel、CAD、压缩包（≤45MB）</div>
        </div>

        <div v-if="attachmentUploadQueue.length" class="attachment-upload-queue">
          <div v-for="item in attachmentUploadQueue" :key="item.id" class="attachment-upload-row">
            <span class="attachment-upload-name" :title="item.name">{{ item.name }}</span>
            <el-tag v-if="item.status === 'uploading'" size="small" type="warning">上传中</el-tag>
            <template v-else-if="item.status === 'error'">
              <el-tag size="small" type="danger">{{ item.error || '上传失败' }}</el-tag>
              <el-button text type="primary" size="small" @click="retryAttachment(item)">重试</el-button>
            </template>
          </div>
        </div>

        <div v-if="imageAttachments.length" class="attachment-image-grid">
          <div v-for="att in imageAttachments" :key="att.id" class="attachment-image-item">
            <el-image
              class="attachment-image"
              :src="getAttachmentUrl(att.file_path)"
              :alt="att.filename"
              fit="cover"
              lazy
              :preview-src-list="imageUrls"
              :initial-index="imagePreviewIndex(att.id)"
              :zoom-rate="TASK_ATTACHMENT_PREVIEW_ZOOM_RATE"
              preview-teleported
            />
            <div class="attachment-image-actions">
              <span class="attachment-image-name" :title="att.filename">{{ att.filename }}</span>
              <span class="attachment-action-group">
                <el-button text size="small" @click="downloadAttachment(att)">下载</el-button>
                <el-button text type="danger" size="small" @click="handleDeleteAttachment(att.id)">删除</el-button>
              </span>
            </div>
          </div>
        </div>

        <el-table v-if="fileAttachments.length" :data="fileAttachments" stripe size="small" class="attachment-file-table">
          <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
          <el-table-column label="类型" width="110">
            <template #default="{ row }">{{ getTaskAttachmentTypeLabel(row) }}</template>
          </el-table-column>
          <el-table-column label="大小" width="110">
            <template #default="{ row }">{{ formatAttachmentSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column label="上传时间" width="180">
            <template #default="{ row }">{{ formatDateTimeFull(row.created_at) || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button v-if="isPreviewableAttachment(row)" text type="primary" size="small" @click="previewAttachment(row)">预览</el-button>
              <el-button text size="small" @click="downloadAttachment(row)">下载</el-button>
              <el-button text type="danger" size="small" @click="handleDeleteAttachment(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!attachments.length" class="attachment-empty">暂无附件，拖入或点击上方区域上传</div>
      </el-card>

      <el-dialog
        v-model="videoPreviewVisible"
        title="视频预览"
        width="min(900px, 92vw)"
        destroy-on-close
        @closed="videoPreviewAttachment = null"
      >
        <video
          v-if="videoPreviewAttachment"
          class="attachment-video-player"
          :src="getAttachmentUrl(videoPreviewAttachment.file_path)"
          controls
          autoplay
          playsinline
        >
          您的浏览器不支持视频播放
        </video>
      </el-dialog>

    </div>
  </div>
</template>

<script setup lang="ts">
import { formatDateTimeFull } from '@/utils/datetime'
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDesignTask, updateDesignTask, changeDesignTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { AttachmentResponse, DesignTaskResponse } from '@/types/api'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { ProgressBar, StatusTag } from '@/components/ui'
import { getEmployees } from '@/api/employees'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteDesignTask } from '@/api/tasks'
import {
  TASK_ATTACHMENT_ACCEPT,
  TASK_ATTACHMENT_MAX_BATCH,
  TASK_ATTACHMENT_MAX_CONCURRENCY,
  TASK_ATTACHMENT_PREVIEW_ZOOM_RATE,
  formatAttachmentSize,
  getAttachmentUrl,
  getTaskAttachmentKind,
  getTaskAttachmentTypeLabel,
  validateTaskAttachment,
} from '@/utils/taskPhotoUpload'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const changing = ref(false)
const deleting = ref(false)
const task = ref<DesignTaskResponse | null>(null)
const employeeOptions = ref<{ id: string; name: string; employee_no?: string; user_id?: string | null }[]>([])
const assigning = ref(false)
const attachmentInput = ref<HTMLInputElement | null>(null)
const attachmentDragActive = ref(false)
const attachmentUploadQueue = ref<AttachmentUploadItem[]>([])
const videoPreviewVisible = ref(false)
const videoPreviewAttachment = ref<AttachmentResponse | null>(null)
let attachmentDragDepth = 0
let activeAttachmentUploads = 0

interface AttachmentUploadItem {
  id: string
  file: File
  name: string
  status: 'queued' | 'uploading' | 'error'
  error?: string
}

const attachments = computed(() => task.value?.attachments || [])
const imageAttachments = computed(() => attachments.value.filter(att => getTaskAttachmentKind(att) === 'image'))
const fileAttachments = computed(() => attachments.value.filter(att => getTaskAttachmentKind(att) !== 'image'))
const imageUrls = computed(() => imageAttachments.value.map(att => getAttachmentUrl(att.file_path)))
const attachmentUploadDisabled = computed(() => !task.value || deleting.value)
const DESIGN_WORKFLOW: Record<string, string[]> = {
  pending: ['designing', 'cancelled'],
  designing: ['confirmed', 'pending_review', 'pending', 'cancelled'],
  pending_review: ['confirmed', 'revision', 'cancelled'],
  revision: ['designing', 'pending_review', 'cancelled'],
  confirmed: ['cancelled'],
  cancelled: [],
}

// 旧 pending_review/revision 仅保留给后端兼容，不再作为前端任务流程节点展示。
const designSteps = computed(() => {
  return [
    { key: 'pending', label: '待分配' },
    { key: 'designing', label: '设计中' },
    { key: 'confirmed', label: '已完成' },
  ]
})

async function handleWorkflowChange(to_status: string, orderItemIds: string[], assignedTo: string) {
  const labelMap: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待处理', revision: '需调整', confirmed: '已完成', cancelled: '已取消' }
  if (to_status === 'cancelled') {
    const { value: reason } = await ElMessageBox.prompt('请输入取消原因', '取消任务', {
      confirmButtonText: '确定', cancelButtonText: '取消',
      inputPlaceholder: '取消原因',
    })
    if (!reason) return
    await doChangeStatus(to_status, reason, orderItemIds, assignedTo)
  } else {
    await ElMessageBox.confirm(`确定将任务状态变更为「${labelMap[to_status]}」？`, '变更状态', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    await doChangeStatus(to_status, '', orderItemIds, assignedTo)
  }
}

async function doChangeStatus(to_status: string, reason: string, orderItemIds: string[], assignedTo: string) {
  changing.value = true
  try {
    await changeDesignTaskStatus(route.params.id as string, {
      to_status,
      reason,
      order_item_ids: orderItemIds,
      assigned_to: assignedTo,
    })
    ElMessage.success('状态已变更')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function fetchTask() {
  loading.value = true
  try {
    const data = await getDesignTask(route.params.id as string)
    task.value = data
  } finally { loading.value = false }
}

async function loadEmployees() {
  try {
    const data = await getEmployees({ page_size: 100, employment_status: 'active' })
    employeeOptions.value = data.items
  } catch { /* employees module may not be ready */ }
}

async function handleSaveAssignment(assignedTo: string | null) {
  assigning.value = true
  try {
    await updateDesignTask(route.params.id as string, { assigned_to: assignedTo })
    ElMessage.success(assignedTo ? '已保存分配' : '已取消分配')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { assigning.value = false }
}
function openAttachmentPicker() {
  if (!attachmentUploadDisabled.value) attachmentInput.value?.click()
}

function handleAttachmentDragEnter() {
  if (attachmentUploadDisabled.value) return
  attachmentDragDepth += 1
  attachmentDragActive.value = true
}

function handleAttachmentDragOver() {
  if (!attachmentUploadDisabled.value) attachmentDragActive.value = true
}

function handleAttachmentDragLeave() {
  attachmentDragDepth = Math.max(0, attachmentDragDepth - 1)
  if (attachmentDragDepth === 0) attachmentDragActive.value = false
}

function handleAttachmentDrop(event: DragEvent) {
  attachmentDragDepth = 0
  attachmentDragActive.value = false
  if (attachmentUploadDisabled.value) return
  enqueueAttachments(Array.from(event.dataTransfer?.files || []))
}

function handleAttachmentInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  enqueueAttachments(files)
}

function enqueueAttachments(files: File[]) {
  if (!files.length) return
  const selectedFiles = files.slice(0, TASK_ATTACHMENT_MAX_BATCH)
  if (files.length > TASK_ATTACHMENT_MAX_BATCH) {
    ElMessage.warning(`一次最多上传 ${TASK_ATTACHMENT_MAX_BATCH} 个文件，超出部分未加入队列`)
  }
  const accepted: File[] = []
  let rejectedCount = 0
  for (const file of selectedFiles) {
    if (validateTaskAttachment(file)) rejectedCount += 1
    else accepted.push(file)
  }
  if (rejectedCount) ElMessage.warning(`${rejectedCount} 个文件不符合格式或大小要求，未加入队列`)
  if (!accepted.length) return
  attachmentUploadQueue.value.push(...accepted.map(file => ({
    id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
    file,
    name: file.name,
    status: 'queued' as const,
  })))
  startAttachmentUploadQueue()
}

function startAttachmentUploadQueue() {
  while (activeAttachmentUploads < TASK_ATTACHMENT_MAX_CONCURRENCY) {
    const next = attachmentUploadQueue.value.find(item => item.status === 'queued')
    if (!next) return
    next.status = 'uploading'
    activeAttachmentUploads += 1
    void uploadAttachmentItem(next).finally(() => {
      activeAttachmentUploads -= 1
      startAttachmentUploadQueue()
    })
  }
}

async function uploadAttachmentItem(item: AttachmentUploadItem) {
  try {
    const category = getTaskAttachmentKind({ filename: item.file.name, file_type: item.file.type })
    const uploaded = await uploadAttachment('design_task', route.params.id as string, item.file, category)
    if (task.value && uploaded) task.value.attachments = [...(task.value.attachments || []), uploaded]
    attachmentUploadQueue.value = attachmentUploadQueue.value.filter(queueItem => queueItem.id !== item.id)
    ElMessage.success(`${item.name} 上传成功`)
    await aiStore.notifyBusinessMutation()
  } catch {
    item.status = 'error'
    item.error = '上传失败，请重试'
  }
}

function retryAttachment(item: AttachmentUploadItem) {
  item.status = 'queued'
  item.error = undefined
  startAttachmentUploadQueue()
}

function imagePreviewIndex(attachmentId: string) {
  return imageAttachments.value.findIndex(att => att.id === attachmentId)
}

function isPreviewableAttachment(attachment: AttachmentResponse) {
  const kind = getTaskAttachmentKind(attachment)
  return kind === 'video' || kind === 'pdf'
}

function previewAttachment(attachment: AttachmentResponse) {
  if (getTaskAttachmentKind(attachment) === 'video') {
    videoPreviewAttachment.value = attachment
    videoPreviewVisible.value = true
    return
  }
  window.open(getAttachmentUrl(attachment.file_path), '_blank', 'noopener,noreferrer')
}

function downloadAttachment(attachment: AttachmentResponse) {
  const link = document.createElement('a')
  link.href = getAttachmentUrl(attachment.file_path)
  link.download = attachment.filename || '附件'
  link.target = '_blank'
  link.rel = 'noreferrer'
  link.click()
}

async function handleDeleteAttachment(id: string) {
  await ElMessageBox.confirm('确定删除此附件？删除后无法恢复。', '删除附件', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  await deleteAttachment(id)
  if (task.value) task.value.attachments = (task.value.attachments || []).filter(attachment => attachment.id !== id)
  ElMessage.success('已删除')
}

async function handleDelete() {
  await ElMessageBox.confirm(
    `确定删除设计任务 ${task.value?.design_no || ''}？删除后不可恢复，关联订单将回退到确认状态。`,
    '删除任务', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
  )
  deleting.value = true
  try {
    await deleteDesignTask(route.params.id as string)
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
.attachment-header-hint { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.progress-suffix { margin-left: 8px; color: var(--ad-text-secondary); }
.design-file-field { display: flex; width: 100%; gap: 8px; }
.design-file-field .el-input { flex: 1; }
.attachment-dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  padding: 24px;
  border: 1px dashed var(--ad-border);
  border-radius: 8px;
  color: var(--ad-text-secondary);
  background: color-mix(in srgb, var(--ad-card) 92%, var(--el-color-primary) 8%);
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}
.attachment-dropzone:hover,
.attachment-dropzone.is-dragover {
  border-color: var(--el-color-primary);
  background: color-mix(in srgb, var(--ad-card) 84%, var(--el-color-primary) 16%);
}
.attachment-dropzone.is-disabled { cursor: not-allowed; opacity: 0.65; }
.attachment-input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.attachment-drop-icon { font-size: 30px; color: var(--el-color-primary); margin-bottom: 8px; }
.attachment-drop-title { color: var(--ad-text); font-size: 15px; font-weight: 600; }
.attachment-drop-subtitle { margin-top: 6px; font-size: 13px; }
.attachment-drop-hint { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); text-align: center; }
.attachment-upload-queue { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
.attachment-upload-row { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 6px 10px; border-radius: 6px; background: var(--ad-bg-secondary, rgba(255, 255, 255, 0.04)); }
.attachment-upload-name { overflow: hidden; flex: 1; color: var(--ad-text-secondary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.attachment-image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }
.attachment-image-item { overflow: hidden; background: #252540; border: 1px solid var(--ad-border); border-radius: 6px; }
.attachment-image { display: block; width: 100%; height: 160px; cursor: zoom-in; }
.attachment-image-actions { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 6px 8px; }
.attachment-image-name { overflow: hidden; flex: 1; color: var(--ad-text-secondary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.attachment-action-group { display: inline-flex; flex-shrink: 0; }
.attachment-file-table { margin-top: 16px; }
.attachment-empty { padding: 18px 8px 4px; color: var(--ad-text-secondary); text-align: center; font-size: 13px; }
.attachment-video-player { display: block; width: 100%; max-height: 70vh; background: #000; }
@media (max-width: 640px) {
  .design-file-field { align-items: stretch; flex-direction: column; }
  .card-header { align-items: flex-start; gap: 8px; }
  .attachment-header-hint { text-align: right; }
  .attachment-dropzone { min-height: 130px; padding: 18px 12px; }
  .attachment-image-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .attachment-image { height: 120px; }
}
</style>
