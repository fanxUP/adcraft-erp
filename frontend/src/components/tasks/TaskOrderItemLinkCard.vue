<template>
  <el-card shadow="never" class="info-card task-processing-card">
    <template #header>
      <div class="card-header">
        <span>任务处理</span>
        <el-tag v-if="isHistoricalReadOnly" type="info" size="small">
          历史任务（只读）
        </el-tag>
        <el-tag v-else-if="linkedItemIds.length" type="success" size="small">
          已关联 {{ linkedItemIds.length }} 条明细
        </el-tag>
        <el-tag v-else type="warning" size="small">历史任务待关联明细</el-tag>
      </div>
    </template>

    <section class="task-section order-item-section" aria-labelledby="order-item-section-title">
      <div id="order-item-section-title" class="section-heading">
        <div class="section-heading-main">
          <span>订单明细</span>
          <span class="section-note">勾选要推进的明细，未勾选明细不会变更</span>
        </div>
        <el-button
          text
          size="small"
          :loading="loadingItems"
          :disabled="saving || changing"
          @click="loadItems"
        >
          刷新状态
        </el-button>
      </div>

      <div v-if="linkedItemIds.length" class="linked-item-summary">
        <div class="linked-item-tags">
          <el-tag
            v-for="(itemName, index) in linkedItemNames"
            :key="linkedItemIds[index] || index"
            type="success"
            effect="plain"
            size="small"
          >
            {{ itemName || `明细 ${index + 1}` }}
          </el-tag>
        </div>
        <span class="linked-item-note">已纳入 {{ linkedItemIds.length }} 条明细；可继续勾选其中未完成的明细推进状态</span>
      </div>

      <el-alert
        :title="isHistoricalReadOnly
          ? '该历史任务未关联订单明细且已结束，不能再次变更任务状态；如需补录历史明细，可使用上方关联操作。'
          : '状态变更只作用于下方勾选的订单明细；新勾选明细会在提交状态时自动纳入本任务。'"
        :type="isHistoricalReadOnly ? 'warning' : 'info'"
        :closable="false"
        show-icon
      />
      <el-alert
        v-if="!canChangeTaskStatus && !isHistoricalReadOnly"
        type="warning"
        :title="changeStatusDisabledReason"
        :closable="false"
        show-icon
      />

      <div v-loading="loadingItems" class="link-panel">
        <div v-if="items.length" class="item-list" role="group" aria-label="订单明细（可多选）">
          <label
            v-for="item in items"
            :key="item.id"
            class="item-option"
            :class="{
              'is-selected': selectedItemIds.includes(item.id),
              'is-disabled': !canSelect(item),
            }"
            :aria-disabled="!canSelect(item)"
          >
            <input
              v-model="selectedItemIds"
              class="item-option-checkbox"
              type="checkbox"
              :value="item.id"
              :disabled="saving || changing || !canSelect(item)"
              :aria-label="`选择订单明细 ${item.item_name}`"
            />
            <span class="item-option-body">
              <span class="item-option-title-row">
                <span class="item-option-title">{{ item.item_name }}</span>
                <StatusTag :status="item.stage_view || item.stage" :label="item.stage_label" size="sm" />
                <span v-if="item.is_linked && (item.task_status_view || item.task_status_label)" class="item-status-label">
                  本任务：
                  <StatusTag :status="item.task_status_view || item.task_status" :label="item.task_status_label" size="sm" />
                </span>
                <el-tag v-if="item.outsource_blocked" type="warning" effect="light" size="small">
                  {{ item.outsource_status_label || '外协任务进行中' }}
                </el-tag>
              </span>
              <span v-if="item.material_process || itemSpec(item)" class="item-option-subtitle">
                <span v-if="item.material_process">{{ item.material_process }}</span>
                <span v-if="item.material_process && itemSpec(item)"> · </span>
                <span v-if="itemSpec(item)">{{ itemSpec(item) }}</span>
              </span>
              <span class="item-option-meta">
                <span class="item-option-metric">数量 {{ item.quantity }}{{ item.unit ? ` ${item.unit}` : '' }}</span>
                <span class="item-option-metric">金额 {{ formatMoney(item.unit_price) }}</span>
                <span class="item-option-metric">小计 {{ formatMoney(item.subtotal_amount) }}</span>
                <span v-if="item.is_linked && item.task_progress_pct != null" class="item-option-metric">
                  本任务进度 {{ item.task_progress_pct }}%
                </span>
              </span>
              <span v-if="!canSelect(item) && disabledReason(item)" class="item-option-disabled-reason">
                {{ disabledReason(item) }}
              </span>
              <span v-if="item.outsource_blocked && canSelect(item)" class="item-option-outsourcing-reason">
                外协完成后才能推进该明细到下一阶段
              </span>
            </span>
          </label>
        </div>

        <div v-if="loadError" class="link-tip error-tip">订单明细加载失败，请刷新后重试。</div>
        <div v-else-if="!loadingItems && !items.length" class="link-tip">
          当前订单没有可关联的有效明细。
        </div>

        <div class="link-actions">
          <el-button
            type="primary"
            plain
            :loading="saving"
            :disabled="!selectedItemIds.length || !items.length || changing"
            @click="handleLink"
          >
            {{ selectedItemIds.length ? `保存关联 ${selectedItemIds.length} 条明细` : '保存关联' }}
          </el-button>
        </div>
      </div>
    </section>

    <el-divider />

    <section class="task-section status-section" aria-labelledby="task-status-section-title">
      <div id="task-status-section-title" class="section-heading">
        <span>变更状态</span>
        <span class="section-note">
          {{ isHistoricalReadOnly
            ? '历史终态仅支持查看'
            : workflowControl.hasMixedStatuses
              ? '已选明细状态不同，请选择状态相同的明细后再批量推进'
              : '点击可执行的下一步或回退' }}
        </span>
      </div>
      <TaskWorkflow
        :steps="steps"
        :current-status="workflowControl.currentStatus"
        :workflow="workflowControl.workflow"
        :changing="changing || saving || isHistoricalReadOnly || !canChangeTaskStatus"
        @change="handleWorkflowChange"
      />
    </section>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTaskOrderItemOptions,
  updateDesignTask,
  updateProductionTask,
  updateInstallationTask,
} from '@/api/tasks'
import type { ActionCapability, TaskType, TaskOrderItemOption } from '@/types/api'
import { StatusTag } from '@/components/ui'
import TaskWorkflow from '@/components/workflow/TaskWorkflow.vue'
import { getTaskWorkflowControl } from '@/utils/taskItemWorkflow'
import { formatMoney } from '@/utils/format'

const props = withDefaults(defineProps<{
  taskType: TaskType
  taskId: string
  orderId: string
  currentItemId?: string | null
  currentItemName?: string | null
  currentItemIds?: string[] | null
  currentItemNames?: string[] | null
  taskCapabilities?: Record<string, ActionCapability> | null
  steps: { key: string; label: string }[]
  currentStatus: string
  workflow: Record<string, string[]>
  changing: boolean
}>(), {
  currentItemId: null,
  currentItemName: null,
  currentItemIds: () => [],
  currentItemNames: () => [],
  taskCapabilities: null,
})

const emit = defineEmits<{
  linked: []
  change: [status: string, orderItemIds: string[]]
}>()

const items = ref<TaskOrderItemOption[]>([])
const selectedItemIds = ref<string[]>([])
const loadingItems = ref(false)
const saving = ref(false)
const loadError = ref(false)

const linkedItemIds = computed(() => {
  if (props.currentItemIds?.length) return props.currentItemIds
  return props.currentItemId ? [props.currentItemId] : []
})

const linkedItemNames = computed(() => {
  if (props.currentItemNames?.length) return props.currentItemNames
  if (props.currentItemName) return [props.currentItemName]
  return linkedItemIds.value.map(() => '明细未命名')
})

const terminalStatuses: Record<TaskType, string[]> = {
  design: ['confirmed', 'cancelled'],
  production: ['completed', 'cancelled'],
  installation: ['completed', 'cancelled'],
}

const isHistoricalReadOnly = computed(() => {
  if (linkedItemIds.value.length) return false
  return terminalStatuses[props.taskType]?.includes(props.currentStatus) ?? false
})

const changeStatusCapability = computed(() => props.taskCapabilities?.change_status)
const canChangeTaskStatus = computed(() => (
  changeStatusCapability.value?.allowed ?? !isHistoricalReadOnly.value
))
const changeStatusDisabledReason = computed(() => (
  changeStatusCapability.value?.disabled_reason || '该任务当前状态不允许继续变更'
))

const workflowControl = computed(() => getTaskWorkflowControl(
  items.value,
  selectedItemIds.value,
  props.currentStatus,
  props.workflow,
))

function itemLabel(item: TaskOrderItemOption) {
  return item.material_process
    ? `${item.item_name} · ${item.material_process}`
    : item.item_name
}

function itemSpec(item: TaskOrderItemOption) {
  if (item.specification) return item.specification

  return [
    item.length != null ? `${item.length}${item.length_unit || ''}` : '',
    item.width != null ? `${item.width}${item.width_unit || ''}` : '',
    item.height != null ? `${item.height}${item.height_unit || ''}` : '',
  ].filter(Boolean).join(' × ')
}

function canSelect(item: TaskOrderItemOption) {
  return item.capabilities?.select?.allowed ?? item.can_select
}

function disabledReason(item: TaskOrderItemOption) {
  return item.capabilities?.select?.disabled_reason || item.disabled_reason || ''
}

async function loadItems() {
  if (!props.orderId) {
    selectedItemIds.value = []
    return
  }
  selectedItemIds.value = []
  loadingItems.value = true
  loadError.value = false
  try {
    items.value = await getTaskOrderItemOptions(props.taskType, props.taskId)
  } catch {
    items.value = []
    loadError.value = true
  } finally {
    loadingItems.value = false
  }
}

async function updateTaskItems(itemIds: string[]) {
  if (props.taskType === 'design') {
    return updateDesignTask(props.taskId, { order_item_ids: itemIds })
  }
  if (props.taskType === 'production') {
    return updateProductionTask(props.taskId, { order_item_ids: itemIds })
  }
  return updateInstallationTask(props.taskId, { order_item_ids: itemIds })
}

async function handleLink() {
  const selected = items.value.filter(item => selectedItemIds.value.includes(item.id))
  if (!selected.length) return
  const selectedLabel = selected.map(itemLabel).join('、')

  try {
    await ElMessageBox.confirm(
      `确认将此任务关联到以下 ${selected.length} 条明细：${selectedLabel}？关联后会纳入这些明细的进度统计。`,
      '确认关联订单明细',
      { confirmButtonText: '确认关联', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  saving.value = true
  try {
    const allLinkedIds = items.value.filter(item => item.is_linked).map(item => item.id)
    const itemIds = Array.from(new Set([...allLinkedIds, ...selected.map(item => item.id)]))
    await updateTaskItems(itemIds)
    ElMessage.success(`已关联 ${selected.length} 条订单明细`)
    emit('linked')
  } catch {
    // API error message is handled by the shared request interceptor.
  } finally {
    saving.value = false
  }
}

function handleWorkflowChange(status: string) {
  if (!canChangeTaskStatus.value) {
    ElMessage.info(changeStatusDisabledReason.value)
    return
  }
  if (!selectedItemIds.value.length) {
    ElMessage.warning('请先勾选要变更状态的订单明细')
    return
  }
  if (
    status === 'completed'
    && (props.taskType === 'production' || props.taskType === 'installation')
  ) {
    const blockedItems = items.value.filter(
      item => selectedItemIds.value.includes(item.id) && item.outsource_blocked,
    )
    if (blockedItems.length) {
      const names = blockedItems.map(itemLabel).join('、')
      ElMessage.warning(`${names}存在未完成的外协任务，外协完成后才能完成本任务`)
      return
    }
  }
  emit('change', status, [...selectedItemIds.value])
}

watch([() => props.orderId, () => props.taskId, () => props.taskType, linkedItemIds], loadItems)
onMounted(loadItems)
</script>

<style scoped>
.task-processing-card {
  margin-top: 16px;
}

.task-section {
  min-width: 0;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  color: var(--ad-text);
  font-size: 15px;
  font-weight: 600;
}

.section-heading-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-note {
  color: var(--ad-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.linked-item-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 14px 16px;
  border: 1px solid var(--el-color-success-light-5);
  border-radius: 6px;
  background: var(--el-color-success-light-9);
}

.linked-item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.linked-item-note {
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.link-panel {
  margin-top: 16px;
}

.item-list {
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
}

.item-option {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.item-option:last-child {
  border-bottom: 0;
}

.item-option:hover {
  background: var(--el-fill-color-light);
}

.item-option.is-disabled {
  cursor: not-allowed;
  opacity: 0.72;
  background: var(--el-fill-color-lighter);
}

.item-option.is-disabled:hover {
  background: var(--el-fill-color-lighter);
}

.item-option.is-selected {
  background: var(--el-color-primary-light-9);
}

.item-option-checkbox {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  margin: 3px 0 0;
  accent-color: var(--el-color-primary);
}

.item-option-body {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 4px 12px;
  min-width: 0;
  align-items: baseline;
}

.item-option-title-row {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.item-option-title {
  color: var(--ad-text);
  font-weight: 600;
}

.item-status-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.item-option-subtitle,
.item-option-meta {
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.item-option-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-left: auto;
  line-height: 1.5;
}

.item-option-metric {
  white-space: nowrap;
}

.item-option-metric + .item-option-metric::before {
  content: '·';
  margin: 0 10px;
  color: var(--el-text-color-placeholder);
}

.item-option-disabled-reason {
  flex-basis: 100%;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.item-option-outsourcing-reason {
  flex-basis: 100%;
  color: var(--el-color-warning-dark-2);
  font-size: 12px;
}

.link-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.link-tip {
  margin-top: 10px;
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.error-tip {
  color: var(--el-color-danger);
}

.status-section :deep(.tw-bar) {
  margin: 0;
  padding: 4px 0 0;
  border: 0;
  background: transparent;
}

.status-section :deep(.tw-flow) {
  max-width: 100%;
  overflow-x: auto;
  padding: 4px 4px 8px;
}

@media (max-width: 640px) {
  .item-option {
    padding: 12px;
  }

  .item-option-meta {
    flex-basis: 100%;
    margin-left: 0;
  }

  .link-actions,
  .link-actions .el-button {
    width: 100%;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .section-heading-main {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .linked-item-summary {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
