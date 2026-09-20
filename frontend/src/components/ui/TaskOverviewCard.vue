<template>
  <el-card shadow="never" class="task-overview-card">
    <template #header>
      <div class="task-overview-header">
        <span class="task-overview-title">任务概览</span>
        <StatusTag :status="status" size="sm" />
      </div>
    </template>

    <div class="task-overview-content">
      <el-alert
        v-if="reviewRequired"
        type="warning"
        :closable="false"
        show-icon
        class="task-review-alert"
      >
        <template #title>订单变更待复核</template>
        <div class="task-review-content">
          <span>{{ reviewReason || '订单关键执行字段已变更，请先复核任务执行参数。' }}</span>
          <el-button
            v-if="canAcknowledgeReview"
            size="small"
            type="warning"
            plain
            :loading="acknowledgingReview"
            @click="emit('acknowledge-review')"
          >
            确认已复核
          </el-button>
        </div>
      </el-alert>

      <div class="task-overview-identity">
        <span class="task-overview-label">任务编号</span>
        <span class="task-overview-value task-overview-number">{{ display(taskNo) }}</span>
      </div>

      <div class="task-overview-project">
        <span class="task-overview-label">项目名称</span>
        <div class="task-overview-project-value">{{ display(projectName) }}</div>
      </div>

      <dl class="task-overview-contact-grid">
        <div class="task-overview-field">
          <dt>客户名称</dt>
          <dd>{{ display(customerName) }}</dd>
        </div>
        <div class="task-overview-field">
          <dt>部门/科室</dt>
          <dd>{{ display(department) }}</dd>
        </div>
        <div class="task-overview-field">
          <dt>联系人</dt>
          <dd>{{ display(contactName) }}</dd>
        </div>
        <div class="task-overview-field">
          <dt>联系电话</dt>
          <dd>{{ display(contactPhone) }}</dd>
        </div>
      </dl>

      <div v-if="extraFields.length" class="task-overview-extra">
        <div class="task-overview-section-label">任务信息</div>
        <dl class="task-overview-extra-grid">
          <div
            v-for="field in extraFields"
            :key="field.label"
            class="task-overview-field"
            :class="{ 'is-wide': field.wide }"
          >
            <dt>{{ field.label }}</dt>
            <dd>{{ display(field.value) }}</dd>
          </div>
        </dl>
      </div>

      <div class="task-overview-progress-row">
        <div class="task-overview-progress-block">
          <div class="task-overview-section-label">任务进度</div>
          <ProgressBar
            :percentage="progressPct"
            :tone="progressTone"
            aria-label="任务进度"
          />
        </div>
        <div class="task-overview-plan-block">
          <span class="task-overview-section-label">计划时间</span>
          <span class="task-overview-plan-value">{{ plannedTime }}</span>
          <el-tag v-if="isOverdue" type="danger" size="small">
            逾期{{ overdueDays ? ` ${overdueDays} 天` : '' }}
          </el-tag>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDateTimeFull } from '@/utils/datetime'
import type { StatusView, UiTone } from '@/types/api'
import ProgressBar from './ProgressBar.vue'
import StatusTag from './StatusTag.vue'

export interface TaskOverviewField {
  label: string
  value?: string | number | null
  wide?: boolean
}

const props = withDefaults(defineProps<{
  taskNo: string | null | undefined
  projectName: string | null | undefined
  status: string | StatusView | null | undefined
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
  progressPct: 0,
  progressTone: undefined,
  plannedStartAt: null,
  plannedEndAt: null,
  isOverdue: false,
  overdueDays: 0,
  customerName: null,
  department: null,
  contactName: null,
  contactPhone: null,
  reviewRequired: false,
  reviewReason: null,
  canAcknowledgeReview: false,
  acknowledgingReview: false,
  extraFields: () => [],
})

const emit = defineEmits<{
  'acknowledge-review': []
}>()

const plannedTime = computed(() => {
  const start = formatDateTimeFull(props.plannedStartAt) || '-'
  const end = formatDateTimeFull(props.plannedEndAt) || '-'
  if (start === '-' && end === '-') return '-'
  return `${start} 至 ${end}`
})

function display(value: string | number | null | undefined) {
  if (value == null || (typeof value === 'string' && !value.trim())) return '-'
  return value
}
</script>

<style scoped>
.task-overview-card {
  margin-top: 16px;
  border: 1px solid var(--ad-border);
  background: var(--ad-card);
  color: var(--ad-text);
}

.task-overview-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid var(--ad-border);
}

.task-overview-card :deep(.el-card__body) {
  padding: 20px 24px 24px;
}

.task-overview-header,
.task-overview-identity,
.task-overview-progress-row,
.task-overview-plan-block {
  display: flex;
  align-items: center;
}

.task-overview-header {
  justify-content: space-between;
  gap: 16px;
}

.task-overview-title {
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 650;
}

.task-overview-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.task-review-alert {
  margin-bottom: 2px;
}

.task-review-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  line-height: 1.5;
}

.task-overview-identity {
  gap: 16px;
  min-height: 28px;
}

.task-overview-label,
.task-overview-field dt,
.task-overview-section-label {
  color: var(--ad-text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.task-overview-label {
  flex: 0 0 auto;
}

.task-overview-value,
.task-overview-field dd,
.task-overview-plan-value {
  margin: 0;
  color: var(--ad-text);
  font-size: 14px;
  line-height: 1.5;
}

.task-overview-number {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.task-overview-project {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  padding: 14px 0;
  border-top: 1px solid var(--ad-border);
  border-bottom: 1px solid var(--ad-border);
}

.task-overview-project-value {
  min-width: 0;
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.task-overview-contact-grid,
.task-overview-extra-grid {
  display: grid;
  gap: 16px 24px;
  margin: 0;
}

.task-overview-contact-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.task-overview-extra {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 2px;
}

.task-overview-extra-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.task-overview-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.task-overview-field dt {
  line-height: 1.4;
}

.task-overview-field dd {
  min-width: 0;
  overflow-wrap: anywhere;
}

.task-overview-extra-grid .is-wide {
  grid-column: 1 / -1;
}

.task-overview-progress-row {
  gap: 32px;
  align-items: flex-end;
  padding-top: 2px;
}

.task-overview-progress-block {
  flex: 1 1 auto;
  min-width: 180px;
}

.task-overview-progress-block :deep(.ui-progress-bar) {
  width: 100%;
  margin-top: 8px;
}

.task-overview-plan-block {
  flex: 0 0 min(46%, 420px);
  flex-wrap: wrap;
  gap: 8px 12px;
  justify-content: flex-end;
  min-width: 220px;
}

.task-overview-plan-value {
  text-align: right;
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .task-overview-contact-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-overview-progress-row {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }

  .task-review-content {
    align-items: flex-start;
    flex-direction: column;
  }

  .task-overview-plan-block {
    justify-content: flex-start;
    min-width: 0;
  }

  .task-overview-plan-value {
    text-align: left;
  }
}

@media (max-width: 560px) {
  .task-overview-card :deep(.el-card__header) {
    padding: 14px 16px;
  }

  .task-overview-card :deep(.el-card__body) {
    padding: 16px;
  }

  .task-overview-content {
    gap: 16px;
  }

  .task-overview-project {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .task-overview-contact-grid,
  .task-overview-extra-grid {
    grid-template-columns: 1fr;
  }

  .task-overview-extra-grid .is-wide {
    grid-column: auto;
  }
}
</style>
