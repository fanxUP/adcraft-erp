<template>
  <div class="site-photo-recognition">
    <div class="page-header">
      <h2>现场照片识别</h2>
      <el-tag type="success">规则引擎 — 无需 AI Key</el-tag>
    </div>

    <el-row :gutter="16">
      <!-- Upload section -->
      <el-col :span="12">
        <el-card class="upload-card">
          <template #header>上传现场照片</template>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept="image/*"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            drag
          >
            <el-icon :size="48"><UploadFilled /></el-icon>
            <div class="upload-text">将现场照片拖到此处，或点击上传</div>
            <template #tip>
              <div class="upload-tip">支持 JPG/PNG，建议拍摄墙面、环境全貌</div>
            </template>
          </el-upload>

          <el-form style="margin-top: 16px">
            <el-form-item label="关联安装任务">
              <el-input v-model="taskId" placeholder="可选：输入安装任务ID" clearable />
            </el-form-item>
            <el-form-item label="备注">
              <el-input
                v-model="remark"
                type="textarea"
                :rows="2"
                placeholder="可选：备注信息"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" :disabled="!selectedFile" @click="doAnalyze">
                <el-icon><Camera /></el-icon> 分析照片
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Preview section -->
      <el-col :span="12">
        <el-card v-if="previewUrl" class="preview-card">
          <template #header>照片预览</template>
          <el-image :src="previewUrl" fit="contain" style="width: 100%; max-height: 400px" />
        </el-card>
        <el-card v-else class="preview-card">
          <template #header>照片预览</template>
          <div class="empty-preview">
            <el-icon :size="48"><Picture /></el-icon>
            <p>上传照片后此处显示预览</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Results -->
    <el-card v-if="result" class="results-card" style="margin-top: 16px">
      <template #header>
        <span>
          分析结果
          <el-tag v-if="result.mode === 'ai_enhanced'" size="small" type="success" style="margin-left: 8px">AI 增强</el-tag>
        </span>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="墙面状况">
          <el-tag :type="checkTag(result.checklist.wall_condition)">
            {{ checkText(result.checklist.wall_condition) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="高空风险">
          <el-tag :type="checkTag(result.checklist.height_risk)">
            {{ checkText(result.checklist.height_risk) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="需要脚手架/吊车">
          <el-tag :type="checkTag(result.checklist.scaffolding_needed)">
            {{ checkText(result.checklist.scaffolding_needed) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="障碍物">
          <el-tag :type="checkTag(result.checklist.obstacles_found)">
            {{ checkText(result.checklist.obstacles_found) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="成本影响预估">
          {{ result.checklist.cost_impact_estimated ? '是' : '否' }}
        </el-descriptions-item>
        <el-descriptions-item label="备注">
          {{ result.checklist.notes || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <div v-if="!result && !loading" class="empty-state">
      <el-icon :size="64"><Picture /></el-icon>
      <p>上传现场照片，系统将分析安装风险和注意事项</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Camera, Picture } from '@element-plus/icons-vue'
import { analyzeSitePhoto } from '@/api/ai'
import type { SitePhotoAnalyzeResponse } from '@/types/api'
import type { UploadFile } from 'element-plus'

const loading = ref(false)
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const taskId = ref('')
const remark = ref('')
const result = ref<SitePhotoAnalyzeResponse | null>(null)

const CHECK_MAP: Record<string, string> = {
  awaiting_review: '待评估',
  normal: '正常',
  poor: '不佳',
  needs_attention: '需关注',
  high_risk: '高风险',
  low_risk: '低风险',
  required: '需要',
  not_required: '不需要',
  found: '发现',
  not_found: '未发现',
}

function checkTag(val: string): 'info' | 'warning' | 'danger' | 'success' {
  const map: Record<string, 'info' | 'warning' | 'danger' | 'success'> = {
    awaiting_review: 'info',
    normal: 'success',
    poor: 'danger',
    needs_attention: 'warning',
    high_risk: 'danger',
    low_risk: 'success',
    required: 'warning',
    not_required: 'success',
    found: 'warning',
    not_found: 'success',
  }
  return map[val] || 'info'
}

function checkText(val: string): string {
  return CHECK_MAP[val] || val
}

function handleFileChange(file: UploadFile) {
  if (file.raw) {
    selectedFile.value = file.raw
    previewUrl.value = URL.createObjectURL(file.raw)
  }
}

function handleFileRemove() {
  selectedFile.value = null
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
  result.value = null
}

async function doAnalyze() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择照片')
    return
  }
  loading.value = true
  try {
    result.value = await analyzeSitePhoto(
      selectedFile.value,
      taskId.value || undefined,
    )
    ElMessage.success('分析完成')
  } catch {
    ElMessage.error('分析失败')
    result.value = null
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.site-photo-recognition { padding: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; color: var(--ad-text); }

.upload-card { margin-bottom: 16px; }

.upload-text { color: var(--ad-text-muted); margin-top: 8px; }
.upload-tip { color: var(--ad-text-muted); font-size: 12px; margin-top: 4px; }

.preview-card { margin-bottom: 16px; min-height: 300px; }

.empty-preview {
  text-align: center;
  padding: 60px 20px;
  color: var(--ad-text-muted);
}

.results-card { margin-bottom: 16px; }

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--ad-text-muted);
}
</style>
