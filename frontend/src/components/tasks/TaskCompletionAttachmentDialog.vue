<template>
  <el-dialog
    :model-value="modelValue"
    :title="`完成${stageLabel}`"
    width="min(620px, 92vw)"
    :close-on-click-modal="false"
    destroy-on-close
    @update:model-value="handleVisibleChange"
  >
    <div class="completion-dialog">
      <p class="completion-description">
        当前明细：<strong>{{ itemLabel }}</strong>
      </p>
      <p class="completion-description">
        可以上传本次完成资料，也可以明确跳过。上传的资料会和这条订单明细、完成时间绑定。
      </p>

      <div
        class="completion-dropzone"
        :class="{ 'is-dragover': dragover, 'is-disabled': loading }"
        role="button"
        tabindex="0"
        @click="openPicker"
        @keydown.enter.prevent="openPicker"
        @keydown.space.prevent="openPicker"
        @dragenter.prevent="dragover = true"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="handleDrop"
      >
        <el-icon class="dropzone-icon"><UploadFilled /></el-icon>
        <span class="dropzone-title">拖拽或点击选择资料</span>
        <span class="dropzone-hint">
          {{ taskType === 'installation' ? '支持 JPG、PNG、WEBP、MP4、WEBM、MOV' : '支持图片、视频、PDF、Word、Excel、CAD、压缩包' }}，最多 20 个
        </span>
      </div>
      <input
        ref="fileInput"
        class="file-input"
        type="file"
        multiple
        :accept="accept"
        :disabled="loading"
        @change="handleInputChange"
      />

      <div v-if="selectedFiles.length" class="selected-files">
        <div class="selected-files-heading">
          <span>待上传资料（{{ selectedFiles.length }}）</span>
          <el-button text size="small" :disabled="loading" @click="selectedFiles = []">清空</el-button>
        </div>
        <div v-for="file in selectedFiles" :key="fileKey(file)" class="selected-file-row">
          <span class="selected-file-name" :title="file.name">{{ file.name }}</span>
          <span class="selected-file-size">{{ formatAttachmentSize(file.size) }}</span>
          <el-button text type="danger" size="small" :disabled="loading" @click="removeFile(file)">删除</el-button>
        </div>
      </div>
      <div v-else class="selected-files-empty">暂未选择资料</div>
    </div>

    <template #footer>
      <el-button :disabled="loading" @click="handleVisibleChange(false)">取消</el-button>
      <el-button :disabled="loading" @click="submit(true)">跳过资料并完成</el-button>
      <el-button type="primary" :loading="loading" :disabled="!selectedFiles.length" @click="submit(false)">
        上传资料并完成
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { TaskType } from '@/types/api'
import {
  INSTALLATION_MEDIA_ACCEPT,
  INSTALLATION_MEDIA_MAX_BATCH,
  TASK_ATTACHMENT_ACCEPT,
  TASK_ATTACHMENT_MAX_BATCH,
  formatAttachmentSize,
  validateInstallationMedia,
  validateTaskAttachment,
} from '@/utils/taskPhotoUpload'

const props = withDefaults(defineProps<{
  modelValue: boolean
  taskType: TaskType
  itemLabel: string
  loading?: boolean
}>(), {
  loading: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [files: File[], skipped: boolean]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])
const dragover = ref(false)

const stageLabel = computed(() => ({
  design: '设计',
  production: '制作',
  installation: '安装',
}[props.taskType]))
const accept = computed(() => props.taskType === 'installation'
  ? INSTALLATION_MEDIA_ACCEPT
  : TASK_ATTACHMENT_ACCEPT)
const maxBatch = computed(() => props.taskType === 'installation'
  ? INSTALLATION_MEDIA_MAX_BATCH
  : TASK_ATTACHMENT_MAX_BATCH)

function fileKey(file: File) {
  return `${file.name}-${file.size}-${file.lastModified}`
}

function openPicker() {
  if (!props.loading) fileInput.value?.click()
}

function validateFile(file: File) {
  return props.taskType === 'installation'
    ? validateInstallationMedia(file)
    : validateTaskAttachment(file)
}

function addFiles(files: File[]) {
  const existing = new Set(selectedFiles.value.map(fileKey))
  const remaining = Math.max(0, maxBatch.value - selectedFiles.value.length)
  const available = files.slice(0, remaining)
  if (files.length > remaining) {
    ElMessage.warning(`单次最多选择 ${maxBatch.value} 个资料，超出部分已忽略`)
  }

  for (const file of available) {
    const error = validateFile(file)
    if (error) {
      ElMessage.error(`${file.name}：${error}`)
      continue
    }
    if (!existing.has(fileKey(file))) {
      selectedFiles.value.push(file)
      existing.add(fileKey(file))
    }
  }
}

function handleDrop(event: DragEvent) {
  dragover.value = false
  if (!props.loading && event.dataTransfer?.files.length) {
    addFiles(Array.from(event.dataTransfer.files))
  }
}

function handleInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) addFiles(Array.from(input.files))
  input.value = ''
}

function removeFile(file: File) {
  selectedFiles.value = selectedFiles.value.filter(item => item !== file)
}

function submit(skipped: boolean) {
  if (skipped) {
    emit('submit', [], true)
    return
  }
  if (!selectedFiles.value.length) {
    ElMessage.info('请先选择资料，或点击“跳过资料并完成”')
    return
  }
  emit('submit', [...selectedFiles.value], false)
}

function handleVisibleChange(value: boolean) {
  if (!props.loading) emit('update:modelValue', value)
}

watch(() => props.modelValue, value => {
  if (!value) {
    selectedFiles.value = []
    dragover.value = false
  }
})
</script>

<style scoped>
.completion-description { margin: 0 0 8px; color: var(--ad-text-secondary); line-height: 1.6; }
.completion-description strong { color: var(--ad-text); }
.completion-dropzone { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 132px; margin-top: 18px; padding: 18px; border: 1px dashed var(--ad-border); border-radius: 8px; background: var(--ad-bg-secondary, #f8fafc); cursor: pointer; transition: border-color .15s, background .15s; }
.completion-dropzone:hover, .completion-dropzone.is-dragover { border-color: var(--ad-primary, #409eff); background: var(--ad-primary-light, #ecf5ff); }
.completion-dropzone.is-disabled { cursor: not-allowed; opacity: .7; }
.dropzone-icon { margin-bottom: 8px; color: var(--ad-primary, #409eff); font-size: 28px; }
.dropzone-title { color: var(--ad-text); font-size: 14px; }
.dropzone-hint { margin-top: 6px; color: var(--ad-text-secondary); font-size: 12px; text-align: center; }
.file-input { display: none; }
.selected-files { margin-top: 14px; border: 1px solid var(--ad-border); border-radius: 7px; }
.selected-files-heading, .selected-file-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; }
.selected-files-heading { justify-content: space-between; border-bottom: 1px solid var(--ad-border); color: var(--ad-text); font-size: 13px; font-weight: 600; }
.selected-file-row + .selected-file-row { border-top: 1px solid var(--ad-border); }
.selected-file-name { min-width: 0; flex: 1; overflow: hidden; color: var(--ad-text); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.selected-file-size { color: var(--ad-text-secondary); font-size: 12px; }
.selected-files-empty { margin-top: 14px; color: var(--ad-text-secondary); font-size: 12px; text-align: center; }
</style>
