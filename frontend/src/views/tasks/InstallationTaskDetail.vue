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
        :current-item-ids="task.order_item_ids"
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
            <span>现场照片与视频 <el-tag size="small" type="info">{{ mediaAttachments.length }} 个</el-tag></span>
            <span class="photo-header-hint">拖拽或点击上传</span>
          </div>
        </template>
        <div
          class="photo-dropzone"
          :class="{ 'is-dragover': dragActive, 'is-disabled': photoUploadDisabled }"
          role="button"
          tabindex="0"
          @click="openPhotoPicker"
          @keydown.enter.prevent="openPhotoPicker"
          @keydown.space.prevent="openPhotoPicker"
          @dragenter.prevent="handleDragEnter"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handlePhotoDrop"
        >
          <input
            ref="photoInput"
            class="photo-input"
            type="file"
            multiple
            :accept="INSTALLATION_MEDIA_ACCEPT"
            :disabled="photoUploadDisabled"
            @click.stop
            @change="handlePhotoInputChange"
          />
          <el-icon class="photo-drop-icon"><UploadFilled /></el-icon>
          <div class="photo-drop-title">将现场照片或视频拖到这里上传</div>
          <div class="photo-drop-subtitle">或点击选择文件，支持批量上传</div>
          <div class="photo-drop-hint">图片支持 JPG、PNG、WEBP（≤10MB）；视频支持 MP4、WEBM、MOV（≤45MB）</div>
        </div>

        <div v-if="mediaUploadQueue.length" class="photo-upload-queue">
          <div v-for="item in mediaUploadQueue" :key="item.id" class="photo-upload-row">
            <span class="photo-upload-name" :title="item.name">{{ item.name }}</span>
            <el-tag v-if="item.status === 'uploading'" size="small" type="warning">上传中</el-tag>
            <template v-else-if="item.status === 'error'">
              <el-tag size="small" type="danger">{{ item.error || '上传失败' }}</el-tag>
              <el-button text type="primary" size="small" @click="retryMedia(item)">重试</el-button>
            </template>
          </div>
        </div>

        <div class="photo-grid" v-if="mediaAttachments.length">
          <div v-for="att in mediaAttachments" :key="att.id" class="photo-item">
            <button
              v-if="isInstallationVideoAttachment(att)"
              type="button"
              class="video-thumb"
              :aria-label="`播放视频 ${att.filename}`"
              @click="openVideoPreview(att)"
            >
              <video
                class="photo-img"
                :src="getAttachmentUrl(att.file_path)"
                :aria-label="att.filename"
                preload="metadata"
                muted
                playsinline
              />
              <span class="video-play-badge" aria-hidden="true">▶</span>
            </button>
            <el-image
              v-else
              class="photo-img"
              :src="getAttachmentUrl(att.file_path)"
              :alt="att.filename"
              fit="cover"
              lazy
              :preview-src-list="imageUrls"
              :initial-index="imagePreviewIndex(att.id)"
              :zoom-rate="INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE"
              preview-teleported
            />
            <div class="photo-actions">
              <span class="photo-label" :title="att.filename">{{ isInstallationVideoAttachment(att) ? '视频' : '照片' }} · {{ att.filename }}</span>
              <el-button text type="danger" size="small" @click="handleDeleteAttachment(att.id)">删除</el-button>
            </div>
          </div>
        </div>
        <div v-else class="photo-empty">暂无现场照片或视频，拖入或点击上方区域上传</div>
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
          class="video-player"
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
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { ProgressBar, StatusTag } from '@/components/ui'
import { getInstallationTask, updateInstallationTask, changeInstallationTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { AttachmentResponse, InstallationTaskResponse } from '@/types/api'
import { getEmployees } from '@/api/employees'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteInstallationTask } from '@/api/tasks'
import {
  INSTALLATION_MEDIA_ACCEPT,
  INSTALLATION_MEDIA_MAX_BATCH,
  INSTALLATION_PHOTO_PREVIEW_ZOOM_RATE,
  getAttachmentUrl,
  isInstallationMediaAttachment,
  isInstallationVideoAttachment,
  validateInstallationMedia,
} from '@/utils/taskPhotoUpload'

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
const photoInput = ref<HTMLInputElement | null>(null)
const dragActive = ref(false)
const mediaUploadQueue = ref<MediaUploadItem[]>([])
const videoPreviewVisible = ref(false)
const videoPreviewAttachment = ref<AttachmentResponse | null>(null)
let dragDepth = 0
let activeMediaUploads = 0

interface MediaUploadItem {
  id: string
  file: File
  name: string
  status: 'queued' | 'uploading' | 'error'
  error?: string
}

const mediaAttachments = computed(() =>
  (task.value?.attachments || []).filter(isInstallationMediaAttachment),
)
const imageAttachments = computed(() => mediaAttachments.value.filter(att => !isInstallationVideoAttachment(att)))
const imageUrls = computed(() => imageAttachments.value.map(att => getAttachmentUrl(att.file_path)))
const photoUploadDisabled = computed(() => !task.value || deleting.value)
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

function openPhotoPicker() {
  if (photoUploadDisabled.value) return
  photoInput.value?.click()
}

function handleDragEnter() {
  if (photoUploadDisabled.value) return
  dragDepth += 1
  dragActive.value = true
}

function handleDragOver() {
  if (!photoUploadDisabled.value) dragActive.value = true
}

function handleDragLeave() {
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragActive.value = false
}

function handlePhotoDrop(event: DragEvent) {
  dragDepth = 0
  dragActive.value = false
  if (photoUploadDisabled.value) return
  const files = Array.from(event.dataTransfer?.files || [])
  enqueueMediaFiles(files)
}

function handlePhotoInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  enqueueMediaFiles(files)
}

function enqueueMediaFiles(files: File[]) {
  if (!files.length) return
  const selectedFiles = files.slice(0, INSTALLATION_MEDIA_MAX_BATCH)
  if (files.length > INSTALLATION_MEDIA_MAX_BATCH) {
    ElMessage.warning(`一次最多上传 ${INSTALLATION_MEDIA_MAX_BATCH} 个文件，超出部分未加入队列`)
  }

  const rejected: File[] = []
  const accepted: File[] = []
  for (const file of selectedFiles) {
    if (validateInstallationMedia(file)) rejected.push(file)
    else accepted.push(file)
  }
  if (rejected.length) {
    ElMessage.warning(`${rejected.length} 个文件不符合现场照片或视频格式、大小要求，未加入队列`)
  }
  if (!accepted.length) return

  mediaUploadQueue.value.push(...accepted.map(file => ({
    id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
    file,
    name: file.name,
    status: 'queued' as const,
  })))
  startMediaUploadQueue()
}

function startMediaUploadQueue() {
  while (activeMediaUploads < 3) {
    const next = mediaUploadQueue.value.find(item => item.status === 'queued')
    if (!next) return
    next.status = 'uploading'
    activeMediaUploads += 1
    void uploadMediaItem(next).finally(() => {
      activeMediaUploads -= 1
      startMediaUploadQueue()
    })
  }
}

async function uploadMediaItem(item: MediaUploadItem) {
  try {
    const uploaded = await uploadAttachment('installation_task', route.params.id as string, item.file, 'site_media')
    if (task.value && uploaded) {
      const existing = task.value.attachments || []
      task.value.attachments = [...existing, uploaded]
    }
    mediaUploadQueue.value = mediaUploadQueue.value.filter(queueItem => queueItem.id !== item.id)
    ElMessage.success('现场照片或视频上传成功')
    await aiStore.notifyBusinessMutation()
  } catch {
    item.status = 'error'
    item.error = '上传失败，请重试'
  }
}

function retryMedia(item: MediaUploadItem) {
  item.status = 'queued'
  item.error = undefined
  startMediaUploadQueue()
}

function imagePreviewIndex(attachmentId: string) {
  return imageAttachments.value.findIndex(att => att.id === attachmentId)
}

function openVideoPreview(attachment: AttachmentResponse) {
  videoPreviewAttachment.value = attachment
  videoPreviewVisible.value = true
}

async function handleDeleteAttachment(id: string) {
  await ElMessageBox.confirm('确定删除此照片或视频？删除后无法恢复。', '删除现场媒体', {
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
.photo-header-hint { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.progress-suffix { margin-left: 8px; color: var(--ad-text-secondary); }
.photo-dropzone {
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
.photo-dropzone:hover,
.photo-dropzone.is-dragover {
  border-color: var(--el-color-primary);
  background: color-mix(in srgb, var(--ad-card) 84%, var(--el-color-primary) 16%);
}
.photo-dropzone.is-disabled { cursor: not-allowed; opacity: 0.65; }
.photo-input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.photo-drop-icon { font-size: 30px; color: var(--el-color-primary); margin-bottom: 8px; }
.photo-drop-title { color: var(--ad-text); font-size: 15px; font-weight: 600; }
.photo-drop-subtitle { margin-top: 6px; font-size: 13px; }
.photo-drop-hint { margin-top: 8px; font-size: 12px; color: var(--ad-text-secondary); }
.photo-upload-queue { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
.photo-upload-row { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 6px 10px; border-radius: 6px; background: var(--ad-bg-secondary, rgba(255, 255, 255, 0.04)); }
.photo-upload-name { overflow: hidden; flex: 1; color: var(--ad-text-secondary); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }
.photo-item { background: #252540; border-radius: 6px; overflow: hidden; border: 1px solid var(--ad-border); }
.photo-img { display: block; width: 100%; height: 160px; cursor: zoom-in; }
.video-thumb { position: relative; display: block; width: 100%; padding: 0; border: 0; background: #111; cursor: pointer; }
.video-thumb .photo-img { cursor: pointer; object-fit: cover; }
.video-play-badge { position: absolute; top: 50%; left: 50%; display: grid; width: 44px; height: 44px; place-items: center; border-radius: 50%; color: #fff; background: rgb(0 0 0 / 62%); font-size: 20px; transform: translate(-50%, -50%); transition: background-color 0.2s ease, transform 0.2s ease; }
.video-thumb:hover .video-play-badge { background: var(--el-color-primary); transform: translate(-50%, -50%) scale(1.06); }
.photo-actions { padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; }
.photo-label { overflow: hidden; max-width: calc(100% - 40px); font-size: 12px; color: #888; text-overflow: ellipsis; white-space: nowrap; }
.photo-empty { padding: 18px 8px 4px; color: var(--ad-text-secondary); text-align: center; font-size: 13px; }
.video-player { display: block; width: 100%; max-height: 70vh; background: #000; }

@media (max-width: 600px) {
  .card-header { align-items: flex-start; gap: 8px; }
  .photo-header-hint { text-align: right; }
  .photo-dropzone { min-height: 130px; padding: 18px 12px; }
  .photo-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .photo-img { height: 120px; }
}
</style>
