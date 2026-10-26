<template>
  <el-card
    shadow="hover"
    class="board-card"
    role="group"
    :aria-label="`任务 ${task.task_no}`"
    @click="openTask"
  >
    <div class="card-topline">
      <button
        type="button"
        class="card-no card-open"
        :title="task.task_no"
        :aria-label="`打开任务 ${task.task_no}`"
        @click.stop="openTask"
      >{{ task.task_no }}</button>
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

    <div v-if="authStore.can('order:view_price')" class="card-amount">
      <span class="card-field-label">订单金额</span>
      <strong>{{ formatMoney(task.total_amount) }}</strong>
    </div>

    <div class="scope-notices">
      <el-tag v-if="task.is_followup" size="small" type="warning">追加 / 补做</el-tag>
      <el-tag v-if="task.is_outsourced" size="small">含外协</el-tag>
      <el-tag v-if="task.pending_action_count" size="small" type="warning">待处理事项 {{ task.pending_action_count }}</el-tag>
    </div>
    <el-alert v-if="task.review_required" :title="task.review_reason || '订单已变更，请先核对任务范围'" type="warning" :closable="false" show-icon />
    <button
      type="button"
      class="scope-toggle"
      :aria-expanded="detailsExpanded"
      :aria-controls="detailsId"
      @click.stop="detailsExpanded = !detailsExpanded"
    >
      <span>项目明细<span v-if="itemCount">（{{ itemCount }} 项）</span></span>
      <span class="scope-toggle-action">
        {{ detailsExpanded ? '收起' : '展开' }}
        <el-icon aria-hidden="true"><ArrowUp v-if="detailsExpanded" /><ArrowDown v-else /></el-icon>
      </span>
    </button>
    <div v-show="detailsExpanded" :id="detailsId" class="scope-items">
      <div v-for="item in task.scope_items" :key="item.order_item_id" class="scope-item">
        <strong>{{ item.scope_item_name || item.item_name }}</strong>
        <span>本次计划 {{ quantity(item.planned_quantity, item.scope_unit) }} · 已完成 {{ quantity(item.completed_quantity, item.scope_unit) }}</span>
        <span>订单当前需求 {{ quantity(item.current_quantity, item.unit) }}</span>
        <span v-if="item.assignee_name">执行人：{{ item.assignee_name }}</span>
      </div>
      <span v-if="!task.scope_items?.length">{{ task.item_names?.join('、') || task.item_name || '明细范围未记录' }}</span>
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
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import type { TaskQueueItem } from '@/types/api'
import ProgressBar from './ProgressBar.vue'
import StatusTag from './StatusTag.vue'
import { formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { taskProgress } from '@/utils/task-board'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const props = defineProps<{
  task: TaskQueueItem
}>()

const detailsExpanded = ref(false)
const detailsId = `task-scope-${useId()}`
const itemCount = computed(() => props.task.scope_items?.length
  || props.task.order_item_ids?.length
  || props.task.item_names?.length
  || (props.task.item_name ? 1 : 0))

const emit = defineEmits<{
  open: []
}>()

function quantity(value?: number | null, unit?: string | null) {
  return value === null || value === undefined ? '未记录' : `${value}${unit ? ` ${unit}` : ''}`
}

function openTask() {
  emit('open')
}
</script>

<style scoped>
.scope-notices { display: flex; flex-wrap: wrap; gap: 4px; margin: 8px 0; }
.scope-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-height: 36px;
  margin: 8px 0;
  padding: 6px 0;
  border: 0;
  border-top: 1px solid var(--ad-border);
  background: transparent;
  color: var(--ad-text-secondary);
  font: inherit;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.scope-toggle-action { display: flex; align-items: center; gap: 4px; color: var(--ad-primary, #409eff); }
.scope-toggle:hover { color: var(--ad-primary, #409eff); }
.scope-toggle:focus-visible,
.card-open:focus-visible { outline: 2px solid var(--ad-primary, #409eff); outline-offset: 2px; border-radius: 2px; }
.scope-items { display: grid; gap: 8px; margin: 10px 0; font-size: 12px; color: var(--ad-text-secondary); }
.scope-item { display: grid; gap: 3px; }
.scope-item strong { color: var(--ad-text); font-weight: 600; }
.board-card {
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  color: var(--ad-text);
  outline: none;
}

.board-card:hover,
.board-card:focus-within {
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

.card-open {
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
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
