<template>
  <el-card shadow="never" class="task-overview-card">
    <div class="task-overview-header">
      <div class="task-overview-heading">
        <span class="task-overview-label">任务概览</span>
        <h3>{{ display(projectName) }}</h3>
      </div>
      <StatusTag :status="status" size="sm" />
    </div>

    <el-alert v-if="reviewRequired" type="warning" :closable="false" show-icon class="task-review-alert">
      <template #title>订单变更待复核</template>
      <div class="task-review-content">
        <span>{{ reviewReason || '订单关键执行字段已变更，请先复核任务执行参数。' }}</span>
        <el-button text type="primary" @click="emit('view-order-changes')">查看变更对比</el-button>
        <el-button v-if="canAcknowledgeReview" size="small" type="warning" plain
          :loading="acknowledgingReview" @click="emit('acknowledge-review')">确认已复核</el-button>
      </div>
    </el-alert>

    <div class="task-overview-progress-row">
      <div class="task-overview-progress-block">
        <div class="task-overview-progress-label">
          <el-tooltip content="百分比表示阶段状态进度，由任务明细汇总；已完成条数单独展示。" placement="top">
            <span class="task-overview-label">阶段进度</span>
          </el-tooltip>
          <span v-if="completion.total" class="completion-summary">{{ completion.completed }} / {{ completion.total }} 条明细已完成</span>
        </div>
        <ProgressBar :percentage="progressPct" :tone="progressTone" aria-label="任务进度" />
      </div>
      <div class="task-overview-plan-block">
        <span class="task-overview-label">计划时间</span>
        <span>{{ plannedTime }}</span>
        <el-tag v-if="isOverdue" type="danger" size="small">逾期{{ overdueDays ? ` ${overdueDays} 天` : '' }}</el-tag>
      </div>
    </div>

    <dl v-if="extraFields.length" class="task-overview-extra-grid">
      <div v-for="field in extraFields" :key="field.label" class="task-overview-field" :class="{ 'is-wide': field.wide }">
        <dt>{{ field.label }}</dt><dd>{{ display(field.value) }}</dd>
      </div>
    </dl>

    <details class="task-overview-details">
      <summary>更多信息<span>{{ [customerName, department].filter(Boolean).join(' · ') }}</span></summary>
      <dl class="task-overview-contact-grid">
        <div class="task-overview-field"><dt>创建时间</dt><dd>{{ formatDateTimeFull(createdAt) || '—' }}</dd></div>
        <div class="task-overview-field"><dt>任务编号</dt><dd>{{ display(taskNo) }}</dd></div>
        <div class="task-overview-field"><dt>订单编号</dt><dd>{{ display(orderNo) }}</dd></div>
        <div class="task-overview-field"><dt>客户名称</dt><dd>{{ display(customerName) }}</dd></div>
        <div class="task-overview-field"><dt>部门/科室</dt><dd>{{ display(department) }}</dd></div>
        <div class="task-overview-field"><dt>联系人</dt><dd>{{ display(contactName) }}</dd></div>
        <div class="task-overview-field"><dt>联系电话</dt><dd><a v-if="phoneLink" :href="phoneLink">{{ contactPhone }}</a><span v-else>{{ display(contactPhone) }}</span></dd></div>
      </dl>
    </details>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDateTimeFull } from '@/utils/datetime'
import { taskCompletionSummary } from '@/utils/taskDetailPresentation'
import type { StatusView, UiTone, TaskOrderItemState, TaskType } from '@/types/api'
import ProgressBar from './ProgressBar.vue'
import StatusTag from './StatusTag.vue'

export interface TaskOverviewField { label: string; value?: string | number | null; wide?: boolean }
const props = withDefaults(defineProps<{
  taskNo: string | null | undefined
  projectName: string | null | undefined
  status: string | StatusView | null | undefined
  taskType?: TaskType
  itemStates?: Record<string, TaskOrderItemState>
  createdAt?: string | null
  orderNo?: string | null
  progressPct?: number | null
  progressTone?: UiTone
  plannedStartAt?: string | null
  plannedEndAt?: string | null
  isOverdue?: boolean
  overdueDays?: number | null
  customerName?: string | null
  department?: string | null
  contactName?: string | null
  contactPhone?: string | null
  reviewRequired?: boolean
  reviewReason?: string | null
  canAcknowledgeReview?: boolean
  acknowledgingReview?: boolean
  extraFields?: TaskOverviewField[]
}>(), {
  progressPct: 0, progressTone: undefined, plannedStartAt: null, plannedEndAt: null,
  isOverdue: false, overdueDays: 0, customerName: null, department: null, contactName: null,
  contactPhone: null, reviewRequired: false, reviewReason: null, canAcknowledgeReview: false,
  acknowledgingReview: false, extraFields: () => [], itemStates: () => ({}), createdAt: null, orderNo: null,
})
const emit = defineEmits<{ 'acknowledge-review': []; 'view-order-changes': [] }>()
const completion = computed(() => taskCompletionSummary(props.itemStates))
const phoneLink = computed(() => {
  const number = props.contactPhone?.replace(/[^\d+]/g, '')
  return number ? `tel:${number}` : ''
})
const plannedTime = computed(() => {
  const start = formatDateTimeFull(props.plannedStartAt)
  const end = formatDateTimeFull(props.plannedEndAt)
  if (!start && !end) return '未排期'
  if (!start) return `截止 ${end}`
  if (!end) return `${start} 开始`
  return `${start} 至 ${end}`
})
function display(value: string | number | null | undefined) {
  return value == null || (typeof value === 'string' && !value.trim()) ? '—' : value
}
</script>

<style scoped>
.task-overview-card { container-type: inline-size; border: 1px solid var(--ad-border); background: var(--ad-card); color: var(--ad-text); }
.task-overview-card :deep(.el-card__body) { padding: 18px 20px; }
.task-overview-header, .task-overview-progress-label, .task-review-content { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.task-overview-heading { min-width: 0; }
.task-overview-heading h3 { margin: 4px 0 0; font-size: 18px; line-height: 1.5; overflow-wrap: anywhere; }
.task-overview-label, .task-overview-field dt { color: var(--ad-text-secondary); font-size: 12px; }
.task-review-alert { margin-top: 14px; }
.task-review-content { line-height: 1.6; }
.task-overview-progress-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(200px, 1fr); align-items: center; gap: 16px 28px; margin-top: 16px; }
.task-overview-progress-label { margin-bottom: 8px; flex-wrap: wrap; }
.completion-summary { font-size: 12px; }
.task-overview-plan-block { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px 10px; font-size: 13px; }
.task-overview-contact-grid, .task-overview-extra-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px 20px; margin: 14px 0 0; }
.task-overview-extra-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.task-overview-field { min-width: 0; }
.task-overview-field dd { margin: 4px 0 0; font-size: 14px; line-height: 1.5; overflow-wrap: anywhere; }
.task-overview-field a { color: var(--el-color-primary); }
.task-overview-field.is-wide { grid-column: 1 / -1; }
.task-overview-details { margin-top: 14px; border-top: 1px solid var(--ad-border); padding-top: 10px; }
.task-overview-details summary { cursor: pointer; font-size: 13px; min-height: 28px; line-height: 28px; }
.task-overview-details summary span { margin-left: 14px; color: var(--ad-text-secondary); overflow-wrap: anywhere; }
@media (max-width: 900px) {
  .task-overview-contact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .task-overview-progress-row { grid-template-columns: 1fr; }
  .task-overview-plan-block { justify-content: flex-start; }
}
@media (max-width: 560px) {
  .task-overview-card :deep(.el-card__body) { padding: 14px; }
  .task-overview-contact-grid, .task-overview-extra-grid { grid-template-columns: 1fr; }
  .task-review-content { flex-direction: column; align-items: flex-start; }
  .task-overview-details summary span { display: block; margin-left: 14px; }
}
@container (max-width: 640px) {
  .task-overview-progress-row { grid-template-columns: 1fr; }
  .task-overview-plan-block { justify-content: flex-start; }
  .task-overview-contact-grid, .task-overview-extra-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .task-review-content { flex-direction: column; align-items: flex-start; }
}
</style>
