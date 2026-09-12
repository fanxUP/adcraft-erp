<template>
  <el-card shadow="never" class="info-card order-task-attachments-card">
    <template #header>
      <div class="card-header">
        <span>任务资料</span>
        <span class="header-hint">查看订单权限可上传、下载和删除</span>
      </div>
    </template>

    <div v-loading="loading">
      <el-alert
        v-if="loadError"
        type="error"
        :closable="false"
        show-icon
        title="任务资料加载失败，请刷新订单详情后重试"
        style="margin-bottom: 16px"
      />

      <section v-for="group in groups" :key="group.task_type" class="stage-section">
        <div class="stage-heading">
          <div>
            <h3>{{ group.label }}</h3>
            <span class="stage-summary">
              {{ group.task_count }} 个任务 · {{ group.attachment_count }} 个资料
            </span>
          </div>
          <el-tag size="small" type="info">
            {{ group.task_type === 'installation' ? '仅图片/视频' : '图片、视频及文件' }}
          </el-tag>
        </div>

        <el-empty v-if="!group.tasks.length" :description="`暂无${group.task_label}`" :image-size="64" />

        <div v-for="task in group.tasks" :key="task.task_id" class="task-material-block">
          <div class="task-material-heading">
            <div class="task-material-title">
              <span>{{ task.task_no || `${group.task_label}（未编号）` }}</span>
              <el-tag size="small" :type="statusTagType(task.status)">
                {{ task.status_label || task.status }}
              </el-tag>
            </div>
            <span class="task-material-count">{{ task.attachments.length }} 个资料</span>
          </div>

          <div
            class="material-dropzone"
            :class="{ 'is-dragover': dragTaskId === task.task_id, 'is-disabled': !task.upload_allowed }"
            role="button"
            tabindex="0"
            @click="openPicker(group, task)"
            @keydown.enter.prevent="openPicker(group, task)"
            @keydown.space.prevent="openPicker(group, task)"
            @dragenter.prevent="handleDragEnter(task)"
            @dragover.prevent="handleDragEnter(task)"
            @dragleave.prevent="handleDragLeave(task)"
            @drop.prevent="handleDrop(group, task, $event)"
          >
            <el-icon class="dropzone-icon"><UploadFilled /></el-icon>
            <div v-if="task.upload_allowed" class="dropzone-title">拖拽或点击上传资料</div>
            <div v-else class="dropzone-title">{{ task.read_only_reason || '该任务当前只能查看资料' }}</div>
            <div v-if="task.upload_allowed" class="dropzone-hint">
              支持批量上传 · {{ group.task_type === 'installation' ? 'JPG、PNG、WEBP、MP4、WEBM、MOV' : '图片、视频、PDF、Word、Excel、CAD、压缩包' }}
            </div>
          </div>

          <div v-if="taskUploadQueue(task.task_id).length" class="upload-queue">
            <div v-for="item in taskUploadQueue(task.task_id)" :key="item.id" class="upload-queue-row">
              <span class="upload-queue-name" :title="item.name">{{ item.name }}</span>
              <el-tag v-if="item.status === 'uploading'" size="small" type="warning">上传中</el-tag>
              <el-tag v-else-if="item.status === 'done'" size="small" type="success">已完成</el-tag>
              <template v-else>
                <el-tag size="small" type="danger">{{ item.error || '上传失败' }}</el-tag>
                <el-button text type="primary" size="small" @click="retryUpload(group, task, item)">重试</el-button>
              </template>
            </div>
          </div>

          <div v-if="previewAttachments(task).length" class="preview-grid">
            <div v-for="attachment in previewAttachments(task)" :key="attachment.id" class="preview-item">
              <button
                v-if="isVideo(attachment)"
                type="button"
                class="video-preview-button"
                :aria-label="`播放视频 ${attachment.filename}`"
                @click="openVideoPreview(attachment)"
              >
                <video
                  v-if="attachment.preview_url"
                  class="preview-image"
                  :src="attachment.preview_url"
                  preload="metadata"
                  muted
                  playsinline
                />
                <span v-else class="preview-placeholder"><el-icon><VideoPlay /></el-icon></span>
                <span class="video-play-badge" aria-hidden="true">▶</span>
              </button>
              <el-image
                v-else-if="attachment.preview_url"
                class="preview-image"
                :src="attachment.preview_url"
                :alt="attachment.filename"
                fit="cover"
                lazy
                :preview-src-list="imageUrls(task)"
                :initial-index="imagePreviewIndex(task, attachment.id)"
                preview-teleported
                :zoom-rate="1.05"
              />
              <div v-else class="preview-placeholder"><el-icon><Picture /></el-icon></div>
              <div class="preview-caption">
                <span :title="attachment.filename">{{ attachment.filename }}</span>
                <el-button text type="danger" size="small" @click="removeAttachment(attachment)">删除</el-button>
              </div>
            </div>
          </div>

          <el-table
            v-if="fileAttachments(task).length"
            :data="fileAttachments(task)"
            stripe
            size="small"
            class="file-table"
          >
            <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
            <el-table-column label="类型" width="105">
              <template #default="{ row }">{{ getTaskAttachmentTypeLabel(row) }}</template>
            </el-table-column>
            <el-table-column label="大小" width="105">
              <template #default="{ row }">{{ formatAttachmentSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column label="上传时间" width="180">
              <template #default="{ row }">{{ formatDateTimeFull(row.created_at) || '-' }}</template>
            </el-table-column>
            <el-table-column label="上传人" width="120">
              <template #default="{ row }">{{ row.uploaded_by_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="downloadAttachment(row)">下载</el-button>
                <el-button text type="danger" size="small" @click="removeAttachment(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!task.attachments.length" class="material-empty">暂无资料</div>
        </div>
      </section>
    </div>

    <input
      ref="fileInput"
      class="file-input"
      type="file"
      multiple
      :accept="activeAccept"
      @change="handleInputChange"
    />

    <el-dialog
      v-model="videoDialogVisible"
      title="视频预览"
      width="min(900px, 92vw)"
      destroy-on-close
    >
      <video v-if="videoPreviewUrl" class="video-player" :src="videoPreviewUrl" controls autoplay playsinline>
        您的浏览器不支持视频播放
      </video>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, UploadFilled, VideoPlay } from '@element-plus/icons-vue'
import { formatDateTimeFull } from '@/utils/datetime'
import {
  formatAttachmentSize,
  getTaskAttachmentKind,
  getTaskAttachmentTypeLabel,
  validateInstallationMedia,
  validateTaskAttachment,
} from '@/utils/taskPhotoUpload'
import { downloadBlob } from '@/utils/download'
import {
  deleteOrderTaskAttachment,
  downloadOrderTaskAttachment,
  getOrderTaskAttachments,
  uploadOrderTaskAttachment,
} from '@/api/orders'
import type {
  OrderTaskAttachmentGroup,
  OrderTaskAttachmentResponse,
  OrderTaskAttachmentTask,
} from '@/types/api'

const props = defineProps<{ orderId: string }>()

type LocalAttachment = OrderTaskAttachmentResponse & {
  preview_url?: string
  preview_error?: boolean
}
type LocalTask = Omit<OrderTaskAttachmentTask, 'attachments'> & { attachments: LocalAttachment[] }
type LocalGroup = Omit<OrderTaskAttachmentGroup, 'tasks'> & { tasks: LocalTask[] }
type UploadQueueItem = {
  id: string
  taskId: string
  name: string
  file: File
  status: 'uploading' | 'done' | 'error'
  error?: string
}

const loading = ref(false)
const loadError = ref(false)
const groups = ref<LocalGroup[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const activeTaskId = ref<string | null>(null)
const activeAccept = ref('')
const dragTaskId = ref<string | null>(null)
const uploadQueue = ref<UploadQueueItem[]>([])
const videoDialogVisible = ref(false)
const videoPreviewUrl = ref('')
const objectUrls = new Map<string, string>()

const taskGroupMap = computed(() => {
  const map = new Map<string, LocalGroup>()
  for (const group of groups.value) {
    for (const task of group.tasks) map.set(task.task_id, group)
  }
  return map
})

function statusTagType(status: string): 'success' | 'warning' | 'primary' | 'info' | 'danger' {
  if (['completed', 'confirmed'].includes(status)) return 'success'
  if (['cancelled', 'canceled'].includes(status)) return 'info'
  if (['pending', 'pending_review', 'revision', 'rework'].includes(status)) return 'warning'
  if (status === 'blocked') return 'danger'
  return 'primary'
}

function attachmentKind(attachment: LocalAttachment) {
  return getTaskAttachmentKind(attachment)
}

function isImage(attachment: LocalAttachment) {
  return attachmentKind(attachment) === 'image'
}

function isVideo(attachment: LocalAttachment) {
  return attachmentKind(attachment) === 'video'
}

function previewAttachments(task: LocalTask) {
  return task.attachments.filter(attachment => isImage(attachment) || isVideo(attachment))
}

function fileAttachments(task: LocalTask) {
  return task.attachments.filter(attachment => !isImage(attachment) && !isVideo(attachment))
}

function imageUrls(task: LocalTask) {
  return task.attachments
    .filter(attachment => isImage(attachment) && attachment.preview_url)
    .map(attachment => attachment.preview_url as string)
}

function imagePreviewIndex(task: LocalTask, attachmentId: string) {
  const attachment = task.attachments.find(item => item.id === attachmentId)
  if (!attachment) return 0
  return imageUrls(task).indexOf(attachment.preview_url || '')
}

function taskUploadQueue(taskId: string) {
  return uploadQueue.value.filter(item => item.taskId === taskId)
}

function openPicker(group: LocalGroup, task: LocalTask) {
  if (!task.upload_allowed) return
  activeTaskId.value = task.task_id
  activeAccept.value = group.accept
  fileInput.value?.click()
}

function handleDragEnter(task: LocalTask) {
  if (task.upload_allowed) dragTaskId.value = task.task_id
}

function handleDragLeave(task: LocalTask) {
  if (dragTaskId.value === task.task_id) dragTaskId.value = null
}

function handleDrop(group: LocalGroup, task: LocalTask, event: DragEvent) {
  dragTaskId.value = null
  if (!task.upload_allowed || !event.dataTransfer?.files.length) return
  handleFiles(group, task, Array.from(event.dataTransfer.files))
}

function handleInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  const task = activeTaskId.value ? findTask(activeTaskId.value) : null
  const group = activeTaskId.value ? taskGroupMap.value.get(activeTaskId.value) : null
  if (task && group && input.files?.length) handleFiles(group, task, Array.from(input.files))
  input.value = ''
}

function findTask(taskId: string) {
  for (const group of groups.value) {
    const task = group.tasks.find(item => item.task_id === taskId)
    if (task) return task
  }
  return null
}

function validateFile(group: LocalGroup, file: File) {
  return group.task_type === 'installation'
    ? validateInstallationMedia(file)
    : validateTaskAttachment(file)
}

async function handleFiles(group: LocalGroup, task: LocalTask, files: File[]) {
  const validFiles: File[] = []
  for (const file of files.slice(0, 20)) {
    const error = validateFile(group, file)
    if (error) ElMessage.error(`${file.name}：${error}`)
    else validFiles.push(file)
  }
  if (files.length > 20) ElMessage.warning('单次最多上传 20 个资料，已忽略超出部分')
  const queueItems: UploadQueueItem[] = validFiles.map(file => ({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    taskId: task.task_id,
    name: file.name,
    file,
    status: 'uploading' as const,
  }))
  uploadQueue.value.push(...queueItems)
  for (const item of queueItems) await uploadOne(group, task, item)
  uploadQueue.value = uploadQueue.value.filter(item => item.status !== 'done')
}

async function uploadOne(group: LocalGroup, task: LocalTask, item: UploadQueueItem) {
  try {
    const attachment = await uploadOrderTaskAttachment(props.orderId, group.task_type, task.task_id, item.file)
    const localAttachment: LocalAttachment = { ...attachment }
    task.attachments.unshift(localAttachment)
    await loadPreview(localAttachment)
    item.status = 'done'
  } catch (error: unknown) {
    item.status = 'error'
    item.error = error instanceof Error ? error.message : '上传失败'
  }
}

async function retryUpload(group: LocalGroup, task: LocalTask, item: UploadQueueItem) {
  item.status = 'uploading'
  item.error = ''
  await uploadOne(group, task, item)
  if ((item.status as string) === 'done') uploadQueue.value = uploadQueue.value.filter(queueItem => queueItem.id !== item.id)
}

async function loadPreview(attachment: LocalAttachment) {
  if (!isImage(attachment) && !isVideo(attachment)) return
  if (attachment.preview_url || attachment.preview_error) return
  try {
    const blob = await downloadOrderTaskAttachment(props.orderId, attachment.id)
    const url = URL.createObjectURL(blob)
    objectUrls.set(attachment.id, url)
    attachment.preview_url = url
  } catch {
    attachment.preview_error = true
  }
}

async function loadAllPreviews() {
  const pending: Promise<void>[] = []
  for (const group of groups.value) {
    for (const task of group.tasks) {
      for (const attachment of task.attachments) pending.push(loadPreview(attachment))
    }
  }
  await Promise.all(pending)
}

async function openVideoPreview(attachment: LocalAttachment) {
  await loadPreview(attachment)
  if (!attachment.preview_url) {
    ElMessage.error('视频加载失败，请稍后重试')
    return
  }
  videoPreviewUrl.value = attachment.preview_url
  videoDialogVisible.value = true
}

async function downloadAttachment(attachment: LocalAttachment) {
  const blob = await downloadOrderTaskAttachment(props.orderId, attachment.id, true)
  downloadBlob(blob, attachment.filename || '任务资料')
}

async function removeAttachment(attachment: LocalAttachment) {
  await ElMessageBox.confirm('确定删除此资料？删除后无法恢复。', '删除任务资料', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await deleteOrderTaskAttachment(props.orderId, attachment.id)
  const task = findTask(attachment.related_id)
  if (task) task.attachments = task.attachments.filter(item => item.id !== attachment.id)
  const url = objectUrls.get(attachment.id)
  if (url) {
    URL.revokeObjectURL(url)
    objectUrls.delete(attachment.id)
  }
  ElMessage.success('资料已删除')
}

async function loadMaterials() {
  loading.value = true
  loadError.value = false
  try {
    const response = await getOrderTaskAttachments(props.orderId)
    groups.value = response.groups.map(group => ({
      ...group,
      tasks: group.tasks.map(task => ({
        ...task,
        attachments: task.attachments.map(attachment => ({ ...attachment })),
      })),
    }))
    await loadAllPreviews()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadMaterials)
onUnmounted(() => {
  for (const url of objectUrls.values()) URL.revokeObjectURL(url)
  objectUrls.clear()
})
</script>

<style scoped>
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.header-hint, .stage-summary, .task-material-count { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.stage-section + .stage-section { margin-top: 26px; padding-top: 22px; border-top: 1px solid var(--ad-border); }
.stage-heading, .task-material-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.stage-heading h3 { margin: 0 0 5px; color: var(--ad-text); font-size: 16px; }
.task-material-block { margin-top: 14px; padding: 14px; border: 1px solid var(--ad-border); border-radius: 8px; }
.task-material-heading { margin-bottom: 12px; }
.task-material-title { display: flex; align-items: center; gap: 8px; color: var(--ad-text); font-weight: 600; }
.material-dropzone { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 116px; padding: 16px; border: 1px dashed var(--ad-border); border-radius: 8px; background: var(--ad-bg-secondary, #f8fafc); cursor: pointer; transition: border-color .15s, background .15s; }
.material-dropzone:hover, .material-dropzone.is-dragover { border-color: var(--ad-primary, #409eff); background: var(--ad-primary-light, #ecf5ff); }
.material-dropzone.is-disabled { cursor: not-allowed; opacity: .72; }
.dropzone-icon { margin-bottom: 6px; color: var(--ad-primary, #409eff); font-size: 25px; }
.dropzone-title { color: var(--ad-text); font-size: 14px; }
.dropzone-hint { margin-top: 5px; color: var(--ad-text-secondary); font-size: 12px; text-align: center; }
.file-input { display: none; }
.upload-queue { margin-top: 10px; padding: 8px 10px; background: var(--ad-bg-secondary, #f8fafc); border-radius: 6px; }
.upload-queue-row { display: flex; align-items: center; gap: 8px; min-height: 28px; }
.upload-queue-name { flex: 1; overflow: hidden; color: var(--ad-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.preview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-top: 14px; }
.preview-item { min-width: 0; overflow: hidden; border: 1px solid var(--ad-border); border-radius: 7px; background: var(--ad-card); }
.preview-image, .preview-placeholder { display: flex; align-items: center; justify-content: center; width: 100%; height: 120px; background: var(--ad-bg-secondary, #f1f5f9); color: var(--ad-text-secondary); font-size: 28px; }
.video-preview-button { position: relative; display: block; width: 100%; padding: 0; border: 0; cursor: pointer; }
.video-play-badge { position: absolute; inset: 50% auto auto 50%; display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; transform: translate(-50%, -50%); border-radius: 50%; background: rgba(0, 0, 0, .62); color: #fff; font-size: 16px; }
.preview-caption { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 6px 8px; }
.preview-caption > span { flex: 1; overflow: hidden; color: var(--ad-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.file-table { margin-top: 14px; }
.material-empty { padding: 12px 0 2px; color: var(--ad-text-secondary); font-size: 12px; text-align: center; }
.video-player { display: block; width: 100%; max-height: 70vh; background: #000; }
</style>
