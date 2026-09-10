<template>
  <el-card
    shadow="hover"
    class="board-card"
    role="button"
    tabindex="0"
    :aria-label="`打开任务 ${task.task_no}`"
    @click="openTask"
    @keydown="handleKeydown"
  >
    <div class="card-topline">
      <span class="card-no" :title="task.task_no">{{ task.task_no }}</span>
      <div class="card-statuses">
        <el-tag v-if="task.is_overdue" size="small" type="danger">逾期</el-tag>
        <StatusTag :status="task.status_view || task.status" size="sm" />
      </div>
    </div>

    <div class="card-name" :title="task.project_name">{{ task.project_name }}</div>

    <div class="card-order-context">
      <div class="card-field">
        <span class="card-field-label">客户名称</span>
        <span class="card-field-value" :title="task.customer_name || undefined">{{ task.customer_name || '-' }}</span>
      </div>
      <div class="card-field">
        <span class="card-field-label">部门/科室</span>
        <span class="card-field-value" :title="task.department || undefined">{{ task.department || '-' }}</span>
      </div>
    </div>

    <div v-if="authStore.hasPermission('order:view_price')" class="card-amount">
      <span class="card-field-label">订单金额</span>
      <strong>{{ formatMoney(task.total_amount) }}</strong>
    </div>

    <ProgressBar
      :percentage="taskProgress(task)"
      :tone="task.status_view?.tone"
      label="任务进度"
      size="sm"
      aria-label="任务进度"
    />

    <div class="card-footer">
      <span class="card-order-no" :title="task.order_no || undefined">订单：{{ task.order_no || '-' }}</span>
      <span v-if="task.planned_end_at" class="card-detail">计划结束：{{ formatDateTimeFull(task.planned_end_at) }}</span>
    </div>
    <div v-if="task.assigned_to_name" class="assignee">负责人：{{ task.assigned_to_name }}</div>
  </el-card>
</template>

<script setup lang="ts">
import type { TaskQueueItem } from '@/types/api'
import ProgressBar from './ProgressBar.vue'
import StatusTag from './StatusTag.vue'
import { formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { taskProgress } from '@/utils/task-board'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

defineProps<{
  task: TaskQueueItem
}>()

const emit = defineEmits<{
  open: []
}>()

function openTask() {
  emit('open')
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openTask()
  }
}
</script>

<style scoped>
.board-card {
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  color: var(--ad-text);
  outline: none;
}

.board-card:hover,
.board-card:focus-visible {
  border-color: var(--ad-primary, #409eff);
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

.card-statuses {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 0;
}

.card-no,
.card-order-no,
.card-detail {
  overflow: hidden;
  color: var(--ad-text-secondary, #888);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-no {
  min-width: 0;
}

.card-name {
  margin: 8px 0 4px;
  overflow: hidden;
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-order-context {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.card-field {
  min-width: 0;
}

.card-field-label {
  display: block;
  margin-bottom: 2px;
  color: var(--ad-text-secondary, #888);
  font-size: 11px;
}

.card-field-value {
  display: block;
  overflow: hidden;
  color: var(--ad-text);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-amount {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--ad-border);
}

.card-amount strong {
  overflow: hidden;
  color: var(--ad-text);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  margin-top: 8px;
}

.card-order-no {
  min-width: 0;
  flex: 1;
}

.card-detail {
  flex-shrink: 0;
}

.assignee {
  margin-top: 8px;
  color: var(--ad-text-secondary, #888);
  font-size: 12px;
}

@media (max-width: 640px) {
  .card-order-context {
    grid-template-columns: 1fr;
  }

  .card-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
}
</style>
