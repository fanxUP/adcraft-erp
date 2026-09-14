<template>
  <el-card
    shadow="never"
    class="info-card order-task-attachments-card"
    :class="{ 'is-compact': compact }"
  >
    <template #header>
      <div class="card-header">
        <span>{{ stage ? (groups[0]?.label || '阶段资料') : '订单资料' }}</span>
        <span class="header-hint">订单为资料源头，任务详情仅显示对应阶段</span>
      </div>
    </template>

    <div v-loading="loading">
      <el-alert
        v-if="loadError"
        type="error"
        :closable="false"
        show-icon
        title="订单资料加载失败，请刷新后重试"
        style="margin-bottom: 16px"
      />

      <section v-for="group in groups" :key="group.stage || group.task_type" class="stage-section">
        <div class="stage-heading">
          <div>
            <h3>{{ group.label }}</h3>
            <span class="stage-summary">{{ group.attachment_count }} 个资料</span>
          </div>
          <el-tag size="small" type="info">
            {{ group.stage === 'installation' ? '图片/视频' : '图片、视频及文件' }}
          </el-tag>
        </div>

        <div
          v-if="!readonly"
          class="material-dropzone"
          :class="{
            'is-dragover': dragStage === group.stage,
            'is-disabled': !canUpload(group),
          }"
          role="button"
          tabindex="0"
          @click="openPicker(group)"
          @keydown.enter.prevent="openPicker(group)"
          @keydown.space.prevent="openPicker(group)"
          @dragenter.prevent="handleDragEnter(group)"
          @dragover.prevent="handleDragEnter(group)"
          @dragleave.prevent="handleDragLeave(group)"
          @drop.prevent="handleDrop(group, $event)"
        >
          <el-icon class="dropzone-icon"><UploadFilled /></el-icon>
          <div v-if="canUpload(group)" class="dropzone-title">拖拽或点击上传资料</div>
          <div v-else class="dropzone-title">当前账号只能查看该阶段资料</div>
          <div v-if="canUpload(group)" class="dropzone-hint">
            支持批量上传 · {{ group.stage === 'installation' ? 'JPG、PNG、WEBP、MP4、WEBM、MOV' : '图片、视频、PDF、Word、Excel、CAD、压缩包' }}
          </div>
        </div>

        <div v-if="groupUploadQueue(group.stage).length" class="upload-queue">
          <div v-for="item in groupUploadQueue(group.stage)" :key="item.id" class="upload-queue-row">
            <span class="upload-queue-name" :title="item.name">{{ item.name }}</span>
            <el-tag v-if="item.status === 'uploading'" size="small" type="warning">上传中</el-tag>
            <el-tag v-else-if="item.status === 'done'" size="small" type="success">已完成</el-tag>
            <template v-else>
              <el-tag size="small" type="danger">{{ item.error || '上传失败' }}</el-tag>
              <el-button text type="primary" size="small" @click="retryUpload(group, item)">重试</el-button>
            </template>
          </div>
        </div>

        <div
          v-for="album in attachmentAlbums(group)"
          :key="`${group.stage}-${album.key}`"
          class="album-section"
        >
          <div class="album-heading">
            <span class="album-date">{{ album.label }}</span>
            <span class="stage-summary">{{ album.attachments.length }} 个资料</span>
          </div>

          <div v-if="previewAttachments(album.attachments).length" class="preview-grid">
            <div v-for="attachment in previewAttachments(album.attachments)" :key="attachment.id" class="preview-item">
              <button
                v-if="isVideo(attachment)"
                type="button"
                class="video-preview-button"
                :aria-label="`播放视频 ${attachment.filename}`"
                @click="openVideoPreview(attachment, group)"
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
                :preview-src-list="imageUrls(album.attachments)"
                :initial-index="imagePreviewIndex(album.attachments, attachment.id)"
                preview-teleported
                :zoom-rate="1.05"
              />
              <div v-else class="preview-placeholder"><el-icon><Picture /></el-icon></div>
              <div class="preview-caption">
                <div class="preview-caption-main">
                  <span :title="attachment.filename">{{ attachment.filename }}</span>
                  <small>{{ attachment.created_at ? formatDateTimeFull(attachment.created_at) : '时间未知' }}</small>
                </div>
                <el-button
                  v-if="canDelete(group)"
                  text
                  type="danger"
                  size="small"
                  @click="removeAttachment(attachment, group)"
                >删除</el-button>
              </div>
            </div>
          </div>

          <el-table
            v-if="fileAttachments(album.attachments).length"
            :data="fileAttachments(album.attachments)"
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
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="isPreviewableAttachment(row)"
                  text
                  type="primary"
                  size="small"
                  @click="previewAttachment(row, group)"
                >预览</el-button>
                <el-button text size="small" @click="downloadAttachment(row, group)">下载</el-button>
                <el-button
                  v-if="canDelete(group)"
                  text
                  type="danger"
                  size="small"
                  @click="removeAttachment(row, group)"
                >删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="!group.attachments.length" class="material-empty">
          {{ group.stage === 'installation' ? '暂无现场照片或视频' : '暂无订单阶段资料' }}
        </div>
      </section>

      <el-empty v-if="!groups.length && !loading" description="暂无可见阶段资料" :image-size="64" />
    </div>

    <input
      v-if="!readonly"
      ref="fileInput"
      class="file-input"
      type="file"
      multiple
      :accept="activeAccept"
      :capture="capture ? 'environment' : undefined"
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
import { onUnmounted, ref, watch } from 'vue'
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
  deleteOrderAttachment,
  downloadOrderAttachment,
  getOrderAttachments,
  uploadOrderAttachment,
} from '@/api/orders'
import { groupAttachmentsByDate } from '@/utils/orderAttachmentAlbum'
import type {
  OrderTaskAttachmentGroup,
  OrderTaskAttachmentResponse,
  TaskType,
} from '@/types/api'

const props = withDefaults(defineProps<{
  orderId: string
  stage?: TaskType
  taskId?: string
  readonly?: boolean
  compact?: boolean
  capture?: boolean
}>(), {
  readonly: false,
  compact: false,
  capture: false,
})

type LocalAttachment = OrderTaskAttachmentResponse & {
  preview_url?: string
  preview_error?: boolean
}
type LocalGroup = Omit<OrderTaskAttachmentGroup, 'attachments'> & {
  stage: TaskType
  attachments: LocalAttachment[]
}
type UploadQueueItem = {
  id: string
  stage: TaskType
  name: string
  file: File
  status: 'uploading' | 'done' | 'error'
  error?: string
}

const loading = ref(false)
const loadError = ref(false)
const groups = ref<LocalGroup[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const activeStage = ref<TaskType | null>(null)
const activeAccept = ref('')
const dragStage = ref<TaskType | null>(null)
const uploadQueue = ref<UploadQueueItem[]>([])
const videoDialogVisible = ref(false)
const videoPreviewUrl = ref('')
const objectUrls = new Map<string, string>()

function canUpload(group: LocalGroup) {
  return !props.readonly && group.can_upload !== false
}

function canDelete(group: LocalGroup) {
  return !props.readonly && group.can_delete !== false
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

function attachmentAlbums(group: LocalGroup) {
  return groupAttachmentsByDate(group.attachments)
}

function previewAttachments(attachments: readonly LocalAttachment[]) {
  return attachments.filter(attachment => isImage(attachment) || isVideo(attachment))
}

function fileAttachments(attachments: readonly LocalAttachment[]) {
  return attachments.filter(attachment => !isImage(attachment) && !isVideo(attachment))
}

function imageUrls(attachments: readonly LocalAttachment[]) {
  return attachments
    .filter(attachment => isImage(attachment) && attachment.preview_url)
    .map(attachment => attachment.preview_url as string)
}

function imagePreviewIndex(attachments: readonly LocalAttachment[], attachmentId: string) {
  const attachment = attachments.find(item => item.id === attachmentId)
  return attachment ? imageUrls(attachments).indexOf(attachment.preview_url || '') : 0
}

function groupUploadQueue(stage: TaskType) {
  return uploadQueue.value.filter(item => item.stage === stage)
}

function openPicker(group: LocalGroup) {
  if (!canUpload(group)) return
  activeStage.value = group.stage
  activeAccept.value = group.accept
  fileInput.value?.click()
}

function handleDragEnter(group: LocalGroup) {
  if (canUpload(group)) dragStage.value = group.stage
}

function handleDragLeave(group: LocalGroup) {
  if (dragStage.value === group.stage) dragStage.value = null
}

function handleDrop(group: LocalGroup, event: DragEvent) {
  dragStage.value = null
  if (!canUpload(group) || !event.dataTransfer?.files.length) return
  handleFiles(group, Array.from(event.dataTransfer.files))
}

function handleInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  const group = activeStage.value
    ? groups.value.find(item => item.stage === activeStage.value)
    : undefined
  if (group && input.files?.length) handleFiles(group, Array.from(input.files))
  input.value = ''
}

function validateFile(group: LocalGroup, file: File) {
  return group.stage === 'installation'
    ? validateInstallationMedia(file)
    : validateTaskAttachment(file)
}

async function handleFiles(group: LocalGroup, files: File[]) {
  const validFiles: File[] = []
  for (const file of files.slice(0, 20)) {
    const error = validateFile(group, file)
    if (error) ElMessage.error(`${file.name}：${error}`)
    else validFiles.push(file)
  }
  if (files.length > 20) ElMessage.warning('单次最多上传 20 个资料，已忽略超出部分')
  const queueItems: UploadQueueItem[] = validFiles.map(file => ({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    stage: group.stage,
    name: file.name,
    file,
    status: 'uploading' as const,
  }))
  uploadQueue.value.push(...queueItems)
  for (const item of queueItems) await uploadOne(group, item)
  uploadQueue.value = uploadQueue.value.filter(item => item.status !== 'done')
}

async function uploadOne(group: LocalGroup, item: UploadQueueItem): Promise<boolean> {
  try {
    const attachment = await uploadOrderAttachment(
      props.orderId,
      group.stage,
      item.file,
      props.taskId,
    )
    const localAttachment = { ...attachment }
    group.attachments.unshift(localAttachment)
    group.attachment_count += 1
    await loadPreview(localAttachment, group)
    item.status = 'done'
    return true
  } catch (error: unknown) {
    item.status = 'error'
    item.error = error instanceof Error ? error.message : '上传失败'
    return false
  }
}

async function retryUpload(group: LocalGroup, item: UploadQueueItem) {
  item.status = 'uploading'
  item.error = ''
  const success = await uploadOne(group, item)
  if (success) uploadQueue.value = uploadQueue.value.filter(queueItem => queueItem.id !== item.id)
}

async function loadPreview(attachment: LocalAttachment, group: LocalGroup) {
  if (!isImage(attachment) && !isVideo(attachment)) return
  if (attachment.preview_url || attachment.preview_error) return
  try {
    const blob = await downloadOrderAttachment(props.orderId, attachment.id, {
      stage: group.stage,
      task_id: props.taskId,
    })
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
    for (const attachment of group.attachments) pending.push(loadPreview(attachment, group))
  }
  await Promise.all(pending)
}

async function openVideoPreview(attachment: LocalAttachment, group: LocalGroup) {
  await loadPreview(attachment, group)
  if (!attachment.preview_url) {
    ElMessage.error('视频加载失败，请稍后重试')
    return
  }
  videoPreviewUrl.value = attachment.preview_url
  videoDialogVisible.value = true
}

async function downloadAttachment(attachment: LocalAttachment, group: LocalGroup) {
  const blob = await downloadOrderAttachment(props.orderId, attachment.id, {
    download: true,
    stage: group.stage,
    task_id: props.taskId,
  })
  downloadBlob(blob, attachment.filename || '订单资料')
}

function isPreviewableAttachment(attachment: LocalAttachment) {
  const kind = attachmentKind(attachment)
  return kind === 'video' || kind === 'pdf'
}

async function previewAttachment(attachment: LocalAttachment, group: LocalGroup) {
  if (isVideo(attachment)) {
    await openVideoPreview(attachment, group)
    return
  }
  try {
    const blob = await downloadOrderAttachment(props.orderId, attachment.id, {
      stage: group.stage,
      task_id: props.taskId,
    })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch {
    ElMessage.error('文件预览失败，请下载后查看')
  }
}

async function removeAttachment(attachment: LocalAttachment, group: LocalGroup) {
  if (!canDelete(group)) return
  await ElMessageBox.confirm('确定删除此资料？删除后无法恢复。', '删除订单资料', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await deleteOrderAttachment(props.orderId, attachment.id, {
    stage: group.stage,
    task_id: props.taskId,
  })
  group.attachments = group.attachments.filter(item => item.id !== attachment.id)
  group.attachment_count = Math.max(0, group.attachment_count - 1)
  const url = objectUrls.get(attachment.id)
  if (url) {
    URL.revokeObjectURL(url)
    objectUrls.delete(attachment.id)
  }
  ElMessage.success('资料已删除')
}

async function loadMaterials() {
  clearObjectUrls()
  groups.value = []
  loading.value = true
  loadError.value = false
  try {
    const response = await getOrderAttachments(props.orderId, {
      stage: props.stage,
      task_id: props.taskId,
    })
    groups.value = response.groups.map(group => ({
      ...group,
      stage: group.stage || group.task_type,
      attachments: group.attachments.map(attachment => ({ ...attachment })),
    }))
    await loadAllPreviews()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function clearObjectUrls() {
  for (const url of objectUrls.values()) URL.revokeObjectURL(url)
  objectUrls.clear()
}

watch(
  () => [props.orderId, props.stage, props.taskId],
  () => void loadMaterials(),
  { immediate: true },
)

onUnmounted(() => {
  clearObjectUrls()
})
</script>

<style scoped>
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.header-hint, .stage-summary { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.stage-section + .stage-section { margin-top: 26px; padding-top: 22px; border-top: 1px solid var(--ad-border); }
.stage-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.stage-heading h3 { margin: 0 0 5px; color: var(--ad-text); font-size: 16px; }
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
.album-section { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--ad-border); }
.album-section:first-of-type { margin-top: 8px; padding-top: 0; border-top: 0; }
.album-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.album-date { color: var(--ad-text); font-size: 14px; font-weight: 600; }
.preview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-top: 14px; }
.preview-item { min-width: 0; overflow: hidden; border: 1px solid var(--ad-border); border-radius: 7px; background: var(--ad-card); }
.preview-image, .preview-placeholder { display: flex; align-items: center; justify-content: center; width: 100%; height: 120px; background: var(--ad-bg-secondary, #f1f5f9); color: var(--ad-text-secondary); font-size: 28px; }
.video-preview-button { position: relative; display: block; width: 100%; padding: 0; border: 0; cursor: pointer; }
.video-play-badge { position: absolute; inset: 50% auto auto 50%; display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; transform: translate(-50%, -50%); border-radius: 50%; background: rgb(0 0 0 / 62%); color: #fff; font-size: 16px; }
.preview-caption { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 6px 8px; }
.preview-caption-main { min-width: 0; flex: 1; }
.preview-caption-main > span { display: block; overflow: hidden; color: var(--ad-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.preview-caption-main > small { display: block; margin-top: 2px; color: var(--ad-text-secondary); font-size: 11px; }
.file-table { margin-top: 14px; }
.material-empty { padding: 12px 0 2px; color: var(--ad-text-secondary); font-size: 12px; text-align: center; }
.video-player { display: block; width: 100%; max-height: 70vh; background: #000; }
.is-compact { margin-top: 16px; }
@media (max-width: 560px) {
  .card-header { align-items: flex-start; flex-direction: column; gap: 4px; }
  .preview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
}
</style>
