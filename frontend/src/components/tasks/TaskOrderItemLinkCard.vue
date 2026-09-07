<template>
  <el-card shadow="never" class="info-card task-processing-card">
    <template #header>
      <div class="card-header">
        <span>任务处理</span>
        <el-tag v-if="currentItemId" type="success" size="small">已关联明细</el-tag>
        <el-tag v-else type="warning" size="small">历史整单任务</el-tag>
      </div>
    </template>

    <section class="task-section order-item-section" aria-labelledby="order-item-section-title">
      <div id="order-item-section-title" class="section-heading">
        <span>订单明细</span>
        <span v-if="currentItemId" class="section-note">当前任务归属</span>
        <span v-else class="section-note">请选择一条明细进行关联</span>
      </div>

      <template v-if="currentItemId">
        <div class="linked-item-summary">
          <span class="linked-item-title">{{ currentItemName || '明细未命名' }}</span>
          <span class="linked-item-note">该任务已纳入此明细的进度统计</span>
        </div>
      </template>

      <template v-else>
        <el-alert
          title="只把这条任务绑定到一个明确的订单明细，不会自动拆分任务或创建下游任务。"
          type="info"
          :closable="false"
          show-icon
        />

        <div v-loading="loadingItems" class="link-panel">
          <div v-if="items.length" class="item-list" role="radiogroup" aria-label="订单明细">
            <label
              v-for="item in items"
              :key="item.id"
              class="item-option"
              :class="{ 'is-selected': selectedItemId === item.id }"
            >
              <input
                v-model="selectedItemId"
                class="item-option-radio"
                type="radio"
                name="task-order-item-link"
                :value="item.id"
                :disabled="saving || changing"
              />
              <span class="item-option-body">
                <span class="item-option-title">{{ item.item_name }}</span>
                <span v-if="item.material_process || itemSpec(item)" class="item-option-subtitle">
                  <span v-if="item.material_process">{{ item.material_process }}</span>
                  <span v-if="item.material_process && itemSpec(item)"> · </span>
                  <span v-if="itemSpec(item)">{{ itemSpec(item) }}</span>
                </span>
                <span class="item-option-meta">数量 {{ item.quantity }}{{ item.unit ? ` ${item.unit}` : '' }}</span>
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
              :loading="saving"
              :disabled="!selectedItemId || !items.length || changing"
              @click="handleLink"
            >
              关联到明细
            </el-button>
          </div>
        </div>
      </template>
    </section>

    <el-divider />

    <section class="task-section status-section" aria-labelledby="task-status-section-title">
      <div id="task-status-section-title" class="section-heading">
        <span>变更状态</span>
        <span class="section-note">点击可执行的下一步</span>
      </div>
      <TaskWorkflow
        :steps="steps"
        :current-status="currentStatus"
        :workflow="workflow"
        :changing="changing || saving"
        @change="handleWorkflowChange"
      />
    </section>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrder } from '@/api/orders'
import {
  updateDesignTask,
  updateProductionTask,
  updateInstallationTask,
} from '@/api/tasks'
import type { OrderItemResponse, TaskDependencyTaskType } from '@/types/api'
import TaskWorkflow from '@/components/workflow/TaskWorkflow.vue'

const props = withDefaults(defineProps<{
  taskType: TaskDependencyTaskType
  taskId: string
  orderId: string
  currentItemId?: string | null
  currentItemName?: string | null
  steps: { key: string; label: string }[]
  currentStatus: string
  workflow: Record<string, string[]>
  changing: boolean
}>(), {
  currentItemId: null,
  currentItemName: null,
})

const emit = defineEmits<{
  linked: []
  change: [status: string]
}>()

const items = ref<OrderItemResponse[]>([])
const selectedItemId = ref('')
const loadingItems = ref(false)
const saving = ref(false)
const loadError = ref(false)

function itemLabel(item: OrderItemResponse) {
  return item.material_process
    ? `${item.item_name} · ${item.material_process}`
    : item.item_name
}

function itemSpec(item: OrderItemResponse) {
  if (item.specification) return item.specification

  return [
    item.length != null ? `${item.length}${item.length_unit || ''}` : '',
    item.width != null ? `${item.width}${item.width_unit || ''}` : '',
    item.height != null ? `${item.height}${item.height_unit || ''}` : '',
  ].filter(Boolean).join(' × ')
}

async function loadItems() {
  if (!props.orderId || props.currentItemId) return
  selectedItemId.value = ''
  loadingItems.value = true
  loadError.value = false
  try {
    const order = await getOrder(props.orderId)
    items.value = (order.items || []).filter(item => item.lifecycle_status !== 'voided')
  } catch {
    loadError.value = true
  } finally {
    loadingItems.value = false
  }
}

async function updateTaskItem(itemId: string) {
  if (props.taskType === 'design') {
    return updateDesignTask(props.taskId, { order_item_id: itemId })
  }
  if (props.taskType === 'production') {
    return updateProductionTask(props.taskId, { order_item_id: itemId })
  }
  return updateInstallationTask(props.taskId, { order_item_id: itemId })
}

async function handleLink() {
  const selected = items.value.find(item => item.id === selectedItemId.value)
  if (!selected) return

  try {
    await ElMessageBox.confirm(
      `确认将此任务关联到「${itemLabel(selected)}」？关联后会纳入该明细的进度统计。`,
      '确认关联订单明细',
      { confirmButtonText: '确认关联', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  saving.value = true
  try {
    await updateTaskItem(selected.id)
    ElMessage.success('已关联订单明细')
    emit('linked')
  } catch {
    // API error message is handled by the shared request interceptor.
  } finally {
    saving.value = false
  }
}

function handleWorkflowChange(status: string) {
  emit('change', status)
}

watch([() => props.orderId, () => props.currentItemId], loadItems)
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
  gap: 10px;
  margin-bottom: 12px;
  color: var(--ad-text);
  font-size: 15px;
  font-weight: 600;
}

.section-note {
  color: var(--ad-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.linked-item-summary {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 14px 16px;
  border: 1px solid var(--el-color-success-light-5);
  border-radius: 6px;
  background: var(--el-color-success-light-9);
}

.linked-item-title {
  color: var(--ad-text);
  font-weight: 600;
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

.item-option.is-selected {
  background: var(--el-color-primary-light-9);
}

.item-option-radio {
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

.item-option-title {
  color: var(--ad-text);
  font-weight: 600;
}

.item-option-subtitle,
.item-option-meta {
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.item-option-meta {
  margin-left: auto;
  white-space: nowrap;
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

  .linked-item-summary {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
