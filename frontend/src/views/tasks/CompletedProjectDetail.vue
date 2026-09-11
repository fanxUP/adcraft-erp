<template>
  <div class="page completed-project-detail-page">
    <div class="page-header">
      <div>
        <el-button text class="back-button" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回完成看板
        </el-button>
        <h1>完成项目详情</h1>
      </div>
    </div>

    <el-card shadow="never" class="detail-card" v-loading="loading">
      <el-alert
        v-if="error"
        :title="error"
        type="warning"
        :closable="false"
        show-icon
        class="detail-alert"
      />

      <template v-if="project">
        <div class="project-header">
          <div class="project-heading">
            <span class="project-no">{{ project.project_no }}</span>
            <h2>{{ project.project_name }}</h2>
          </div>
          <StatusTag status="completed" size="md" />
        </div>

        <dl class="project-meta">
          <div>
            <dt>客户名称</dt>
            <dd>{{ project.customer_name || '-' }}</dd>
          </div>
          <div>
            <dt>部门/科室</dt>
            <dd>{{ project.department || '-' }}</dd>
          </div>
          <div>
            <dt>完成时间</dt>
            <dd>{{ formatDateTimeFull(project.completed_at) }}</dd>
          </div>
          <div v-if="project.total_amount !== null && project.total_amount !== undefined">
            <dt>订单金额</dt>
            <dd>¥ {{ formatMoney(project.total_amount) }}</dd>
          </div>
        </dl>

        <section class="detail-section">
          <div class="section-heading">
            <div>
              <h3>订单明细</h3>
              <span>{{ project.items.length }} 条明细</span>
            </div>
            <span class="readonly-hint">只读</span>
          </div>

          <el-table
            v-if="project.items.length"
            :data="project.items"
            row-key="order_item_id"
            size="small"
            stripe
            class="detail-table"
            empty-text="暂无可见的完成明细"
          >
            <el-table-column label="项目内容" min-width="180">
              <template #default="{ row }">
                <span class="item-name">{{ row.item_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="产品/材质/工艺" min-width="260">
              <template #default="{ row }">
                <span class="wrap-cell">{{ row.material_process || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="规格" min-width="150">
              <template #default="{ row }">
                <span class="wrap-cell">{{ row.specification || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="100" align="right">
              <template #default="{ row }">{{ formatQuantity(row) }}</template>
            </el-table-column>
            <el-table-column label="设计" min-width="170">
              <template #default="{ row }">
                <div v-if="row.stages.design" class="stage-cell">
                  <span class="stage-status">{{ row.stages.design.status_label }}</span>
                  <span class="stage-executor">执行人：{{ row.stages.design.employee_name || '未分配' }}</span>
                  <span class="stage-date">完成时间：{{ formatStageDate(row.stages.design) }}</span>
                </div>
                <span v-else class="stage-empty">—</span>
              </template>
            </el-table-column>
            <el-table-column label="制作" min-width="170">
              <template #default="{ row }">
                <div v-if="row.stages.production" class="stage-cell">
                  <span class="stage-status">{{ row.stages.production.status_label }}</span>
                  <span class="stage-executor">执行人：{{ row.stages.production.employee_name || '未分配' }}</span>
                  <span class="stage-date">完成时间：{{ formatStageDate(row.stages.production) }}</span>
                </div>
                <span v-else class="stage-empty">—</span>
              </template>
            </el-table-column>
            <el-table-column label="安装" min-width="170">
              <template #default="{ row }">
                <div v-if="row.stages.installation" class="stage-cell">
                  <span class="stage-status">{{ row.stages.installation.status_label }}</span>
                  <span class="stage-executor">执行人：{{ row.stages.installation.employee_name || '未分配' }}</span>
                  <span class="stage-date">完成时间：{{ formatStageDate(row.stages.installation) }}</span>
                </div>
                <span v-else class="stage-empty">—</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无可见的完成明细" :image-size="64" />
        </section>

        <section class="detail-section resource-section">
          <div class="section-heading">
            <div>
              <h3>任务资料</h3>
              <span>三类资料分行展示，现场资料按安装任务归档</span>
            </div>
          </div>

          <div class="resource-grid">
            <el-card
              v-for="stage in RESOURCE_STAGES"
              :key="stage.key"
              shadow="never"
              class="resource-card"
            >
              <template #header>
                <div class="resource-heading">
                  <span>{{ stage.title }}</span>
                  <div v-if="resourceFor(stage.key)" class="resource-heading-meta">
                    <el-tag size="small" type="info">
                      {{ resourceFor(stage.key)?.task_count || 0 }} 个任务
                    </el-tag>
                    <span class="resource-attachment-count">
                      {{ resourceFor(stage.key)?.attachment_count || 0 }} 个资料
                    </span>
                  </div>
                </div>
              </template>

              <template v-if="resourceFor(stage.key)?.tasks.length">
                <div
                  v-for="task in resourceFor(stage.key)?.tasks || []"
                  :key="task.task_id"
                  class="resource-task"
                >
                  <div class="resource-task-heading">
                    <span>{{ stage.label }} {{ task.task_no || '未编号任务' }}</span>
                    <span class="resource-task-count">{{ task.attachments.length }} 个资料</span>
                  </div>

                  <div v-if="visualAttachments(task, stage.key).length" class="media-grid">
                    <template v-for="attachment in visualAttachments(task, stage.key)" :key="attachment.id">
                      <button
                        v-if="isVideoAttachment(attachment)"
                        type="button"
                        class="media-thumb video-thumb"
                        :aria-label="`播放视频 ${attachment.filename}`"
                        @click="openVideoPreview(attachment)"
                      >
                        <video
                          :src="getAttachmentUrl(attachment.file_path)"
                          :aria-label="attachment.filename"
                          preload="metadata"
                          muted
                          playsinline
                        />
                        <span class="video-play-badge" aria-hidden="true">▶</span>
                      </button>
                      <el-image
                        v-else
                        class="media-thumb"
                        :src="getAttachmentUrl(attachment.file_path)"
                        :alt="attachment.filename"
                        fit="cover"
                        lazy
                        :preview-src-list="imageUrls(task, stage.key)"
                        :initial-index="imagePreviewIndex(attachment, task, stage.key)"
                        :zoom-rate="TASK_ATTACHMENT_PREVIEW_ZOOM_RATE"
                        preview-teleported
                      />
                    </template>
                  </div>

                  <el-table
                    v-if="fileAttachments(task, stage.key).length"
                    :data="fileAttachments(task, stage.key)"
                    stripe
                    size="small"
                    class="resource-file-table"
                  >
                    <el-table-column prop="filename" label="文件名" min-width="180" show-overflow-tooltip />
                    <el-table-column label="类型" width="100">
                      <template #default="{ row }">{{ getTaskAttachmentTypeLabel(row) }}</template>
                    </el-table-column>
                    <el-table-column label="大小" width="90">
                      <template #default="{ row }">{{ formatAttachmentSize(row.file_size) }}</template>
                    </el-table-column>
                    <el-table-column label="上传时间" width="155">
                      <template #default="{ row }">{{ formatDateTimeFull(row.created_at) }}</template>
                    </el-table-column>
                    <el-table-column label="操作" width="120">
                      <template #default="{ row }">
                        <el-button
                          v-if="isPreviewableAttachment(row)"
                          text
                          type="primary"
                          size="small"
                          @click="previewAttachment(row)"
                        >预览</el-button>
                        <el-button text size="small" @click="downloadAttachment(row)">下载</el-button>
                      </template>
                    </el-table-column>
                  </el-table>

                  <div
                    v-if="!visualAttachments(task, stage.key).length && !fileAttachments(task, stage.key).length"
                    class="resource-empty"
                  >{{ stage.key === 'installation' ? '暂无现场照片或视频' : '暂无任务附件' }}</div>
                  <div v-else-if="visualAttachments(task, stage.key).length" class="media-caption">
                    图片点击放大，视频点击播放
                  </div>
                </div>
              </template>
              <div v-else class="resource-empty">暂无可见资料</div>
            </el-card>
          </div>
        </section>
      </template>

      <el-empty v-else-if="!loading && !error" description="暂无项目详情" :image-size="64" />
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
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getCompletedProject } from '@/api/tasks'
import type {
  AttachmentResponse,
  CompletedProjectDetail as CompletedProjectDetailType,
  CompletedProjectDetailItem,
  CompletedProjectResourceTask,
  CompletedProjectStage,
  TaskCompletionType,
} from '@/types/api'
import StatusTag from '@/components/ui/StatusTag.vue'
import { formatDate, formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import {
  TASK_ATTACHMENT_PREVIEW_ZOOM_RATE,
  formatAttachmentSize,
  getAttachmentUrl,
  getTaskAttachmentKind,
  getTaskAttachmentTypeLabel,
} from '@/utils/taskPhotoUpload'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const project = ref<CompletedProjectDetailType | null>(null)
const videoPreviewVisible = ref(false)
const videoPreviewAttachment = ref<AttachmentResponse | null>(null)

const RESOURCE_STAGES: ReadonlyArray<{
  key: TaskCompletionType
  label: string
  title: string
}> = [
  { key: 'design', label: '设计任务', title: '设计任务：任务附件' },
  { key: 'production', label: '制作任务', title: '制作任务：任务附件' },
  { key: 'installation', label: '安装任务', title: '安装任务：现场照片与视频' },
]

async function fetchProject() {
  const projectId = String(route.params.projectId || '')
  project.value = null
  error.value = ''
  if (!projectId) {
    error.value = '无法确定要查看的完成项目'
    return
  }

  loading.value = true
  try {
    project.value = await getCompletedProject(projectId)
  } catch {
    error.value = '完成项目详情暂时无法加载，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (typeof window !== 'undefined' && typeof window.history.state?.back === 'string') {
    router.back()
    return
  }
  router.push({ name: 'ProjectKanbanBoard' })
}

function formatQuantity(row: CompletedProjectDetailItem) {
  if (row.quantity === null || row.quantity === undefined) return '-'
  const quantity = Number.isInteger(row.quantity) ? String(row.quantity) : String(row.quantity)
  return row.unit ? `${quantity} ${row.unit}` : quantity
}

function formatStageDate(stage?: CompletedProjectStage | null) {
  return formatDate(stage?.completed_at)
}

function resourceFor(taskType: TaskCompletionType) {
  return project.value?.resources?.[taskType]
}

function attachmentKind(attachment: AttachmentResponse) {
  return getTaskAttachmentKind(attachment)
}

function isVideoAttachment(attachment: AttachmentResponse) {
  return attachmentKind(attachment) === 'video'
}

function visualAttachments(task: CompletedProjectResourceTask, taskType: TaskCompletionType) {
  return task.attachments.filter(attachment => {
    const kind = attachmentKind(attachment)
    return taskType === 'installation'
      ? kind === 'image' || kind === 'video'
      : kind === 'image' || kind === 'video'
  })
}

function imageUrls(task: CompletedProjectResourceTask, taskType: TaskCompletionType) {
  return visualAttachments(task, taskType)
    .filter(attachment => attachmentKind(attachment) === 'image')
    .map(attachment => getAttachmentUrl(attachment.file_path))
}

function imagePreviewIndex(
  attachment: AttachmentResponse,
  task: CompletedProjectResourceTask,
  taskType: TaskCompletionType,
) {
  return visualAttachments(task, taskType)
    .filter(item => attachmentKind(item) === 'image')
    .findIndex(item => item.id === attachment.id)
}

function fileAttachments(task: CompletedProjectResourceTask, taskType: TaskCompletionType) {
  if (taskType === 'installation') return []
  return task.attachments.filter(attachment => {
    const kind = attachmentKind(attachment)
    return kind !== 'image' && kind !== 'video'
  })
}

function isPreviewableAttachment(attachment: AttachmentResponse) {
  const kind = attachmentKind(attachment)
  return kind === 'video' || kind === 'pdf'
}

function openVideoPreview(attachment: AttachmentResponse) {
  videoPreviewAttachment.value = attachment
  videoPreviewVisible.value = true
}

function previewAttachment(attachment: AttachmentResponse) {
  if (isVideoAttachment(attachment)) {
    openVideoPreview(attachment)
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

watch(() => route.params.projectId, () => {
  void fetchProject()
})

onMounted(() => {
  void fetchProject()
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { margin-bottom: 16px; }
.back-button { padding-left: 0; color: var(--ad-text-secondary); }
.page-header h1 { margin: 6px 0 0; color: var(--ad-text); font-size: 24px; }
.detail-card { min-height: 280px; border: 1px solid var(--ad-border); background: var(--ad-card); color: var(--ad-text); }
.detail-alert { margin-bottom: 16px; }
.project-header, .section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.project-header { padding-bottom: 18px; border-bottom: 1px solid var(--ad-border); }
.project-heading { min-width: 0; }
.project-no { color: var(--ad-text-secondary); font-size: 13px; font-variant-numeric: tabular-nums; }
.project-heading h2 { margin: 6px 0 0; color: var(--ad-text); font-size: 22px; line-height: 1.45; }
.project-meta { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 0; padding: 20px 0 24px; }
.project-meta div { min-width: 0; }
.project-meta dt { margin-bottom: 5px; color: var(--ad-text-secondary); font-size: 12px; }
.project-meta dd { margin: 0; overflow: hidden; color: var(--ad-text); font-size: 14px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.detail-section { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--ad-border); }
.section-heading { margin-bottom: 12px; }
.section-heading h3 { display: inline; margin: 0 10px 0 0; color: var(--ad-text); font-size: 17px; }
.section-heading span { color: var(--ad-text-secondary); font-size: 12px; }
.readonly-hint { padding: 3px 8px; border: 1px solid var(--ad-border); border-radius: 999px; }
.detail-table { width: 100%; }
.detail-table :deep(.cell) { line-height: 1.45; white-space: normal; word-break: break-word; }
.item-name { color: var(--ad-text); font-weight: 600; }
.wrap-cell { color: var(--ad-text); white-space: normal; word-break: break-word; }
.stage-cell { display: flex; flex-direction: column; gap: 3px; min-width: 132px; padding: 2px 0; }
.stage-status { color: var(--el-color-success); font-weight: 600; }
.stage-executor { color: #d93025; font-size: 12px; }
.stage-date { color: var(--ad-text-secondary); font-size: 12px; }
.stage-empty { color: var(--ad-text-placeholder); }
.resource-section { padding-bottom: 4px; }
.resource-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
.resource-card { min-width: 0; border-color: var(--ad-border); background: var(--ad-card); }
.resource-heading, .resource-task-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.resource-heading { color: var(--ad-text); font-weight: 600; }
.resource-heading-meta { display: flex; align-items: center; gap: 10px; }
.resource-attachment-count { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.resource-task + .resource-task { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--ad-border); }
.resource-task-heading { margin-bottom: 10px; color: var(--ad-text); font-size: 13px; font-weight: 600; }
.resource-task-count, .media-caption { color: var(--ad-text-secondary); font-size: 12px; font-weight: normal; }
.media-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.media-thumb { display: block; width: 100%; height: 116px; overflow: hidden; border: 0; border-radius: 6px; background: #151525; cursor: zoom-in; object-fit: cover; }
.media-thumb :deep(img), .media-thumb video { display: block; width: 100%; height: 100%; object-fit: cover; }
.video-thumb { position: relative; padding: 0; cursor: pointer; }
.video-play-badge { position: absolute; top: 50%; left: 50%; display: grid; width: 38px; height: 38px; place-items: center; border-radius: 50%; color: #fff; background: rgb(0 0 0 / 64%); font-size: 18px; transform: translate(-50%, -50%); }
.resource-file-table { margin-top: 10px; }
.resource-file-table :deep(.cell) { line-height: 1.35; white-space: normal; word-break: break-word; }
.media-caption { margin-top: 8px; }
.resource-empty { padding: 20px 8px; color: var(--ad-text-secondary); text-align: center; font-size: 13px; }
.video-player { display: block; width: 100%; max-height: 70vh; background: #000; }

@media (max-width: 900px) {
  .project-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .project-header { align-items: flex-start; flex-direction: column; }
  .project-heading h2 { font-size: 19px; }
  .project-meta { grid-template-columns: 1fr; gap: 12px; }
  .detail-card :deep(.el-card__body) { padding: 16px 12px; }
}
</style>
