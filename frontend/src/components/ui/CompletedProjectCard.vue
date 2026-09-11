<template>
  <el-card
    shadow="hover"
    class="completed-project-card"
    role="button"
    tabindex="0"
    :aria-label="`打开完成项目 ${project.project_no}`"
    @click="openProject"
    @keydown="handleKeydown"
  >
    <div class="card-topline">
      <span class="project-no" :title="project.project_no">{{ project.project_no }}</span>
      <StatusTag status="completed" size="sm" />
    </div>

    <div class="project-name" :title="project.project_name">{{ project.project_name }}</div>

    <div class="project-context">
      <div class="project-field">
        <span class="field-label">客户名称</span>
        <span class="field-value" :title="project.customer_name || undefined">{{ project.customer_name || '-' }}</span>
      </div>
      <div class="project-field">
        <span class="field-label">部门/科室</span>
        <span class="field-value" :title="project.department || undefined">{{ project.department || '-' }}</span>
      </div>
    </div>

    <div class="project-stats">
      <span><strong>{{ project.completed_detail_count }}</strong> 完成明细</span>
      <span><strong>{{ project.completed_work_unit_count }}</strong> 工作单元</span>
    </div>

    <div class="project-stages" aria-label="完成阶段">
      <el-tag v-for="stage in project.stages" :key="stage" size="small" type="success" effect="plain">
        {{ stageLabel(stage) }}
      </el-tag>
      <span v-if="!project.stages.length" class="empty-stage">暂无明细事件</span>
    </div>

    <div class="card-footer">
      <span class="completed-at">完成时间：{{ formatDateTimeFull(project.completed_at) }}</span>
      <strong v-if="project.total_amount !== null && project.total_amount !== undefined" class="project-amount">
        ¥ {{ formatMoney(project.total_amount) }}
      </strong>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { CompletedProjectCard as CompletedProjectCardType, TaskCompletionType } from '@/types/api'
import StatusTag from './StatusTag.vue'
import { formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'

defineProps<{
  project: CompletedProjectCardType
}>()

const emit = defineEmits<{
  open: []
}>()

const STAGE_LABELS: Record<TaskCompletionType, string> = {
  design: '设计',
  production: '制作',
  installation: '安装',
}

function stageLabel(stage: TaskCompletionType) {
  return STAGE_LABELS[stage] || stage
}

function openProject() {
  emit('open')
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openProject()
  }
}
</script>

<style scoped>
.completed-project-card {
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  color: var(--ad-text);
  outline: none;
}

.completed-project-card:hover,
.completed-project-card:focus-visible {
  border-color: var(--ad-success, #67c23a);
}

:deep(.el-card__body) {
  padding: 12px;
}

.card-topline,
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.project-no,
.completed-at,
.empty-stage {
  overflow: hidden;
  color: var(--ad-text-secondary, #888);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-no {
  min-width: 0;
}

.project-name {
  margin: 8px 0 10px;
  overflow: hidden;
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-context {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.project-field {
  min-width: 0;
}

.field-label {
  display: block;
  margin-bottom: 2px;
  color: var(--ad-text-secondary, #888);
  font-size: 11px;
}

.field-value {
  display: block;
  overflow: hidden;
  color: var(--ad-text);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 10px;
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.project-stats strong {
  color: var(--ad-success, #67c23a);
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.project-stages {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-height: 24px;
  margin-bottom: 10px;
}

.card-footer {
  padding-top: 8px;
  border-top: 1px solid var(--ad-border);
}

.completed-at {
  min-width: 0;
}

.project-amount {
  flex-shrink: 0;
  color: var(--ad-text);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .project-context {
    grid-template-columns: 1fr;
  }

  .card-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
}
</style>
