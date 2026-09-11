<template>
  <el-card shadow="never" class="info-card task-processing-card">
    <template #header>
      <div class="card-header">
        <span>任务处理</span>
        <el-tag v-if="isHistoricalReadOnly" type="info" size="small">
          历史任务（状态只读）
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
          :disabled="changing"
          @click="loadItems"
        >
          刷新状态
        </el-button>
      </div>

      <div
        v-if="stageSelectionGroups.length && !isHistoricalReadOnly"
        class="stage-selection-toolbar"
        role="group"
        :aria-label="stageSelectionAriaLabel"
      >
        <div class="stage-selection-controls">
          <el-checkbox
            v-for="group in stageSelectionGroups"
            :key="group.key"
            :model-value="stageSelectionState[group.key].checked"
            :indeterminate="stageSelectionState[group.key].indeterminate"
            :disabled="changing || !stageSelectionItemIds[group.key].length"
            :aria-label="`选择${group.label}明细，共 ${stageSelectionItemIds[group.key].length} 条可选`"
            @change="handleStageSelection(group.key, $event)"
          >
            {{ group.label }}（{{ stageSelectionItemIds[group.key].length }} 条可选）
          </el-checkbox>
        </div>
        <span class="stage-selection-summary">已选 {{ selectedItemIds.length }} 条</span>
      </div>

      <div
        v-if="canManageTaskItems"
        data-ai-target="task-item-assignee"
        class="item-assignee-toolbar"
      >
        <div class="item-assignee-toolbar-main">
          <span class="item-assignee-toolbar-label">明细改派</span>
          <el-select
            v-model="assigneeTargetUserId"
            class="item-assignee-select"
            clearable
            filterable
            :loading="assigneeOptionsLoading"
            :disabled="changing || reassigning"
            placeholder="选择新的执行人"
          >
            <el-option
              v-for="option in assigneeOptions"
              :key="option.user_id"
              :label="`${option.name}（${option.employee_no}）`"
              :value="option.user_id"
            />
          </el-select>
          <span class="item-assignee-toolbar-note">只对已关联、未完成的已选明细生效</span>
        </div>
        <div class="item-assignee-toolbar-actions">
          <el-button
            type="primary"
            plain
            :loading="reassigning"
            :disabled="changing || reassigning || !reassignableSelectedItemIds.length || !assigneeTargetUserId"
            @click="reassignSelectedItems(false)"
          >
            改派已选明细
          </el-button>
          <el-button
            :loading="reassigning"
            :disabled="changing || reassigning || !reassignableSelectedItemIds.length"
            @click="reassignSelectedItems(true)"
          >
            释放执行人
          </el-button>
        </div>
      </div>

      <div v-loading="loadingItems" class="link-panel">
        <div
          v-if="items.length"
          class="item-table"
          :class="{
            'has-price-columns': canViewItemPrice,
            'has-outsource-column': canViewOutsourceTask,
          }"
          role="table"
          aria-label="订单明细（可多选）"
        >
          <div class="item-table-header" role="row">
            <span class="item-table-cell item-table-select" role="columnheader" aria-label="选择" />
            <span class="item-table-cell" role="columnheader">项目内容</span>
            <span class="item-table-cell" role="columnheader">产品/材质/工艺</span>
            <span class="item-table-cell" role="columnheader">规格</span>
            <span class="item-table-cell item-table-number" role="columnheader">数量</span>
            <span class="item-table-cell" role="columnheader">订单阶段</span>
            <span class="item-table-cell" role="columnheader">本任务</span>
            <span class="item-table-cell" role="columnheader">执行人</span>
            <span v-if="canViewItemPrice" class="item-table-cell item-table-number" role="columnheader">金额</span>
            <span v-if="canViewItemPrice" class="item-table-cell item-table-number" role="columnheader">小计</span>
            <span class="item-table-cell item-table-number" role="columnheader">本任务进度</span>
            <span v-if="canViewOutsourceTask" class="item-table-cell" role="columnheader">外协</span>
          </div>

          <label
            v-for="item in items"
            :key="item.id"
            class="item-table-row"
            :class="{
              'is-selected': selectedItemIds.includes(item.id),
              'is-disabled': !canSelect(item),
            }"
            :aria-disabled="!canSelect(item)"
            role="row"
          >
            <span class="item-table-cell item-table-select" data-label="选择" role="cell">
              <input
                v-model="selectedItemIds"
                class="item-table-checkbox"
                type="checkbox"
                :value="item.id"
                :disabled="changing || !canSelect(item)"
                :aria-label="`选择订单明细 ${item.item_name}`"
              />
            </span>
            <span class="item-table-cell item-table-name" data-label="项目内容" role="cell">
              {{ item.item_name }}
            </span>
            <span class="item-table-cell item-table-product" data-label="产品/材质/工艺" role="cell">
              {{ item.material_process || '—' }}
            </span>
            <span class="item-table-cell item-table-spec" data-label="规格" role="cell">
              {{ itemSpec(item) || '—' }}
            </span>
            <span class="item-table-cell item-table-number" data-label="数量" role="cell">
              {{ item.quantity }}{{ item.unit ? ` ${item.unit}` : '' }}
            </span>
            <span class="item-table-cell" data-label="订单阶段" role="cell">
              <StatusTag :status="item.stage_view || item.stage" :label="item.stage_label" size="sm" />
            </span>
            <span class="item-table-cell" data-label="本任务" role="cell">
              <StatusTag
                v-if="item.is_linked && (item.task_status_view || item.task_status_label)"
                :status="item.task_status_view || item.task_status"
                :label="item.task_status_label"
                size="sm"
              />
              <span v-else class="item-table-placeholder">{{ item.is_linked ? '—' : '未关联' }}</span>
            </span>
            <span class="item-table-cell item-table-assignee" data-label="执行人" role="cell">
              <span v-if="item.is_linked && item.assignee_name" class="item-assignee-name">
                {{ item.assignee_name }}
              </span>
              <span v-else-if="item.is_linked" class="item-assignee-placeholder">
                {{ itemAssigneeLabel(item) }}
              </span>
              <span v-else class="item-table-placeholder">—</span>
            </span>
            <template v-if="canViewItemPrice">
              <span class="item-table-cell item-table-number" data-label="金额" role="cell">
                {{ formatMoney(item.unit_price) }}
              </span>
              <span class="item-table-cell item-table-number" data-label="小计" role="cell">
                {{ formatMoney(item.subtotal_amount) }}
              </span>
            </template>
            <span class="item-table-cell item-table-number" data-label="本任务进度" role="cell">
              <span v-if="item.is_linked && item.task_progress_pct != null">
                {{ item.task_progress_pct }}%
              </span>
              <span v-else class="item-table-placeholder">—</span>
            </span>
            <span v-if="canViewOutsourceTask" class="item-table-cell item-table-outsourcing" data-label="外协" role="cell">
              <el-tag v-if="item.outsource_blocked" type="warning" effect="light" size="small">
                {{ item.outsource_status_label || '外协任务进行中' }}
              </el-tag>
              <span v-else class="item-table-placeholder">—</span>
            </span>
            <span v-if="!canSelect(item) && disabledReason(item)" class="item-table-detail-reason" role="cell">
              {{ disabledReason(item) }}
            </span>
            <span v-if="canViewOutsourceTask && item.outsource_blocked && canSelect(item)" class="item-table-outsourcing-reason" role="cell">
              外协完成后才能推进该明细到下一阶段
            </span>
          </label>
        </div>

        <div v-if="loadError" class="link-tip error-tip">订单明细加载失败，请刷新后重试。</div>
        <div v-else-if="!loadingItems && !items.length" class="link-tip">
          当前订单没有可关联的有效明细。
        </div>

        <div v-if="isHistoricalReadOnly" class="link-actions">
          <el-button
            type="primary"
            plain
            :loading="linking"
            :disabled="!selectedItemIds.length || !items.length || changing"
            @click="handleAddHistoricalItems"
          >
            {{ selectedItemIds.length ? `添加 ${selectedItemIds.length} 条到本任务` : '添加到本任务' }}
          </el-button>
          <span class="link-context-note">仅用于补录历史明细，不会改变任务状态。</span>
        </div>
      </div>
    </section>

    <el-divider />

    <section class="task-section status-section" aria-labelledby="task-status-section-title">
      <div id="task-status-section-title" class="section-heading status-heading">
        <div class="section-heading-main">
          <span>变更状态</span>
          <span class="section-note">{{ statusSectionNote }}</span>
        </div>
      </div>
      <TaskWorkflow
        :steps="steps"
        :current-status="workflowControl.currentStatus"
        :workflow="workflowControl.workflow"
        :changing="changing || isHistoricalReadOnly || !canChangeTaskStatus"
        @change="handleWorkflowChange"
      />
    </section>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTaskAssigneeOptions,
  getTaskOrderItemOptions,
  reassignDesignTaskItems,
  reassignInstallationTaskItems,
  reassignProductionTaskItems,
  updateDesignTask,
  updateProductionTask,
  updateInstallationTask,
} from '@/api/tasks'
import type { ActionCapability, TaskAssigneeOption, TaskType, TaskOrderItemOption } from '@/types/api'
import { StatusTag } from '@/components/ui'
import TaskWorkflow from '@/components/workflow/TaskWorkflow.vue'
import { getTaskWorkflowControl } from '@/utils/taskItemWorkflow'
import { useAuthStore } from '@/stores/auth'
import {
  getTaskStageSelectionGroups,
  getTaskStageSelectionItemIds,
  getStageSelectionState,
  isTaskOrderItemSelectable,
  toggleStageSelection,
  type StageSelectionState,
  type TaskStageSelectionKey,
} from '@/utils/taskStageSelection'
import { formatMoney } from '@/utils/format'

const authStore = useAuthStore()

const props = withDefaults(defineProps<{
  taskType: TaskType
  taskId: string
  orderId: string
  currentItemId?: string | null
  currentItemIds?: string[] | null
  taskCapabilities?: Record<string, ActionCapability> | null
  steps: { key: string; label: string }[]
  currentStatus: string
  workflow: Record<string, string[]>
  changing: boolean
}>(), {
  currentItemId: null,
  currentItemIds: () => [],
  taskCapabilities: null,
})

const emit = defineEmits<{
  linked: []
  change: [status: string, orderItemIds: string[]]
}>()

const items = ref<TaskOrderItemOption[]>([])
const selectedItemIds = ref<string[]>([])
const loadingItems = ref(false)
const linking = ref(false)
const loadError = ref(false)
const assigneeOptions = ref<TaskAssigneeOption[]>([])
const assigneeOptionsLoading = ref(false)
const assigneeTargetUserId = ref<string | null>(null)
const reassigning = ref(false)

const taskTypeLabels: Record<TaskType, string> = {
  design: '设计',
  production: '制作',
  installation: '安装',
}

const canViewItemPrice = computed(() => authStore.hasPermission('order_item:view_price'))
const canViewOutsourceTask = computed(() => authStore.hasPermission('outsource_task:read'))
const canManageTaskItems = computed(() => authStore.hasPermission(`${props.taskType}_task:assign`))
const linkedItemIds = computed(() => {
  if (props.currentItemIds?.length) return props.currentItemIds
  return props.currentItemId ? [props.currentItemId] : []
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
const stageChangePermission = computed(() => `${props.taskType}_task:change_status`)
const canChangeStageByPermission = computed(() => authStore.hasPermission(stageChangePermission.value))
const canChangeTaskStatus = computed(() => (
  canChangeStageByPermission.value
  && (changeStatusCapability.value?.allowed ?? !isHistoricalReadOnly.value)
))
const changeStatusDisabledReason = computed(() => {
  if (!canChangeStageByPermission.value) {
    return `当前账号只能查看${taskTypeLabels[props.taskType]}流程，不能变更状态`
  }
  return changeStatusCapability.value?.disabled_reason || '该任务当前状态不允许继续变更'
})
const statusSectionNote = computed(() => {
  if (isHistoricalReadOnly.value) return '历史终态不可变更状态，可补录明细'
  if (workflowControl.value.hasMixedStatuses) {
    return '已选明细状态不同，请选择状态相同的明细后再批量推进'
  }
  return '点击可执行的下一步或回退'
})

const workflowControl = computed(() => getTaskWorkflowControl(
  items.value,
  selectedItemIds.value,
  props.currentStatus,
  props.workflow,
))

const stageSelectionGroups = computed(() => getTaskStageSelectionGroups(props.taskType))

const stageSelectionAriaLabel = computed(() => `按${taskTypeLabels[props.taskType]}状态选择订单明细`)

const stageSelectionItemIds = computed<Record<TaskStageSelectionKey, string[]>>(() => {
  const result: Record<TaskStageSelectionKey, string[]> = {
    pending: [],
    designing: [],
    assigned: [],
    in_progress: [],
  }
  for (const group of stageSelectionGroups.value) {
    result[group.key] = getTaskStageSelectionItemIds(items.value, props.taskType, group.key)
  }
  return result
})

const stageSelectionState = computed<Record<TaskStageSelectionKey, StageSelectionState>>(() => {
  const result: Record<TaskStageSelectionKey, StageSelectionState> = {
    pending: getStageSelectionState(selectedItemIds.value, []),
    designing: getStageSelectionState(selectedItemIds.value, []),
    assigned: getStageSelectionState(selectedItemIds.value, []),
    in_progress: getStageSelectionState(selectedItemIds.value, []),
  }
  for (const group of stageSelectionGroups.value) {
    result[group.key] = getStageSelectionState(
      selectedItemIds.value,
      stageSelectionItemIds.value[group.key],
    )
  }
  return result
})

const reassignableSelectedItemIds = computed(() => items.value
  .filter(item => (
    selectedItemIds.value.includes(item.id)
    && item.is_linked
    && item.assignee_state !== 'terminal'
  ))
  .map(item => item.id))

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

function itemAssigneeLabel(item: TaskOrderItemOption) {
  if (item.assignee_name) return item.assignee_name
  if (item.assignee_state === 'historical_unknown') return '历史未记录'
  if (item.assignee_state === 'terminal') return '已完成（未记录）'
  return '待领取'
}

function canSelect(item: TaskOrderItemOption) {
  return isTaskOrderItemSelectable(item)
}

function disabledReason(item: TaskOrderItemOption) {
  return item.capabilities?.select?.disabled_reason || item.disabled_reason || ''
}

function handleStageSelection(stage: TaskStageSelectionKey, checked: boolean) {
  selectedItemIds.value = toggleStageSelection(
    selectedItemIds.value,
    stageSelectionItemIds.value[stage],
    checked,
  )
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
    if (canManageTaskItems.value) {
      await loadAssigneeOptions()
    }
  } catch {
    items.value = []
    loadError.value = true
  } finally {
    loadingItems.value = false
  }
}

async function loadAssigneeOptions() {
  assigneeOptionsLoading.value = true
  try {
    assigneeOptions.value = await getTaskAssigneeOptions(props.taskType)
  } catch {
    assigneeOptions.value = []
  } finally {
    assigneeOptionsLoading.value = false
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

async function handleAddHistoricalItems() {
  const selected = items.value.filter(item => selectedItemIds.value.includes(item.id))
  if (!selected.length) return
  const selectedLabel = selected.map(itemLabel).join('、')

  try {
    await ElMessageBox.confirm(
      `确认将以下 ${selected.length} 条明细添加到本历史任务：${selectedLabel}？添加后会纳入这些明细的进度统计，但不会改变任务状态。`,
      '补录任务明细',
      { confirmButtonText: '添加到本任务', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  linking.value = true
  try {
    const allLinkedIds = items.value.filter(item => item.is_linked).map(item => item.id)
    const itemIds = Array.from(new Set([...allLinkedIds, ...selected.map(item => item.id)]))
    await updateTaskItems(itemIds)
    ElMessage.success(`已添加 ${selected.length} 条明细到本任务`)
    emit('linked')
  } catch {
    // API error message is handled by the shared request interceptor.
  } finally {
    linking.value = false
  }
}

async function reassignSelectedItems(release: boolean) {
  const selected = selectedItemIds.value
  const reassignable = reassignableSelectedItemIds.value
  if (!selected.length) {
    ElMessage.warning('请先勾选要改派的已关联订单明细')
    return
  }
  if (selected.length !== reassignable.length) {
    ElMessage.warning('明细改派只能选择当前任务中已关联且未完成的明细')
    return
  }
  if (!release && !assigneeTargetUserId.value) {
    ElMessage.warning('请先选择新的执行人')
    return
  }

  const targetName = release
    ? '待领取'
    : assigneeOptions.value.find(option => option.user_id === assigneeTargetUserId.value)?.name || '所选员工'
  try {
    await ElMessageBox.confirm(
      `确认将 ${reassignable.length} 条明细的执行人改为“${targetName}”吗？`,
      '明细执行人改派',
      { confirmButtonText: '确认改派', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  reassigning.value = true
  try {
    const payload = {
      order_item_ids: reassignable,
      assignee_user_id: release ? null : assigneeTargetUserId.value,
    }
    if (props.taskType === 'design') {
      await reassignDesignTaskItems(props.taskId, payload)
    } else if (props.taskType === 'production') {
      await reassignProductionTaskItems(props.taskId, payload)
    } else {
      await reassignInstallationTaskItems(props.taskId, payload)
    }
    ElMessage.success(release ? '已释放明细执行人' : '已完成明细改派')
    assigneeTargetUserId.value = null
    await loadItems()
    emit('linked')
  } catch {
    // API error message is handled by the shared request interceptor.
  } finally {
    reassigning.value = false
  }
}

function handleWorkflowChange(status: string) {
  if (!selectedItemIds.value.length) {
    ElMessage.warning('请先勾选要变更状态的订单明细')
    return
  }
  if (!canChangeTaskStatus.value) {
    ElMessage.info(changeStatusDisabledReason.value)
    return
  }
  if (
    status === 'completed'
    && (props.taskType === 'production' || props.taskType === 'installation')
    && canViewOutsourceTask.value
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

.stage-selection-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-bottom: 12px;
  padding: 8px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.stage-selection-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 20px;
}

.stage-selection-summary {
  flex: 0 0 auto;
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.item-assignee-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 6px;
  background: var(--el-color-primary-light-9);
}

.item-assignee-toolbar-main,
.item-assignee-toolbar-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.item-assignee-toolbar-label {
  color: var(--ad-text);
  font-size: 13px;
  font-weight: 600;
}

.item-assignee-select {
  width: 220px;
}

.item-assignee-toolbar-note {
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.link-panel {
  margin-top: 16px;
}

.item-table {
  --item-table-columns: 36px minmax(76px, 1fr) minmax(100px, 1.55fr) minmax(72px, 0.9fr) minmax(52px, 0.65fr) minmax(64px, 0.75fr) minmax(64px, 0.75fr) minmax(74px, 0.85fr) minmax(62px, 0.65fr);
  overflow: visible;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
}

.item-table.has-price-columns {
  --item-table-columns: 36px minmax(76px, 1fr) minmax(100px, 1.45fr) minmax(72px, 0.85fr) minmax(52px, 0.6fr) minmax(64px, 0.7fr) minmax(64px, 0.7fr) minmax(74px, 0.8fr) minmax(62px, 0.6fr) minmax(70px, 0.65fr) minmax(74px, 0.7fr);
}

.item-table.has-outsource-column:not(.has-price-columns) {
  --item-table-columns: 36px minmax(76px, 1fr) minmax(100px, 1.45fr) minmax(72px, 0.85fr) minmax(52px, 0.6fr) minmax(64px, 0.7fr) minmax(64px, 0.7fr) minmax(74px, 0.8fr) minmax(62px, 0.6fr) minmax(70px, 0.7fr);
}

.item-table.has-price-columns.has-outsource-column {
  --item-table-columns: 36px minmax(76px, 0.95fr) minmax(100px, 1.35fr) minmax(72px, 0.8fr) minmax(52px, 0.55fr) minmax(64px, 0.65fr) minmax(64px, 0.65fr) minmax(74px, 0.75fr) minmax(62px, 0.55fr) minmax(70px, 0.6fr) minmax(74px, 0.65fr) minmax(70px, 0.7fr);
}

.item-table-header,
.item-table-row {
  display: grid;
  grid-template-columns: var(--item-table-columns);
  align-items: stretch;
}

.item-table-header {
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-fill-color-lighter);
  color: var(--ad-text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.item-table-row {
  position: relative;
  min-width: 0;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.item-table-row:last-child {
  border-bottom: 0;
}

.item-table-row:hover {
  background: var(--el-fill-color-light);
}

.item-table-row.is-disabled {
  cursor: not-allowed;
  opacity: 0.72;
  background: var(--el-fill-color-lighter);
}

.item-table-row.is-disabled:hover {
  background: var(--el-fill-color-lighter);
}

.item-table-row.is-selected {
  background: var(--el-color-primary-light-9);
}

.item-table-cell {
  display: flex;
  min-width: 0;
  align-items: center;
  padding: 0 6px;
  color: var(--ad-text);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.item-table-header .item-table-cell {
  color: var(--ad-text-secondary);
}

.item-table-select {
  justify-content: center;
  padding-right: 2px;
  padding-left: 2px;
}

.item-table-checkbox {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: var(--el-color-primary);
}

.item-table-name,
.item-table-product,
.item-table-spec {
  align-items: flex-start;
  white-space: normal;
  word-break: break-word;
}

.item-table-name {
  font-weight: 600;
}

.item-table-product {
  overflow-wrap: anywhere;
}

.item-table-number {
  justify-content: flex-end;
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: normal;
}

.item-table-assignee {
  align-items: flex-start;
}

.item-assignee-name {
  color: var(--el-color-danger);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.item-assignee-placeholder,
.item-table-placeholder {
  color: var(--ad-text-secondary);
}

.item-table-outsourcing {
  align-items: flex-start;
}

.item-table-detail-reason,
.item-table-outsourcing-reason {
  grid-column: 1 / -1;
  min-width: 0;
  padding: 6px 6px 0;
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.item-table-detail-reason {
  color: var(--el-text-color-placeholder);
}

.item-table-outsourcing-reason {
  color: var(--el-color-warning-dark-2);
}

.link-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.link-context-note {
  color: var(--ad-text-secondary);
  font-size: 12px;
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

.status-heading {
  align-items: flex-start;
}

@media (max-width: 900px) {
  .item-table-header {
    display: none;
  }

  .item-table-row {
    grid-template-columns: 32px repeat(2, minmax(0, 1fr));
    padding: 10px;
  }

  .item-table-row .item-table-cell:not(.item-table-select):not(.item-table-detail-reason):not(.item-table-outsourcing-reason) {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    padding: 5px 6px;
  }

  .item-table-row .item-table-cell:not(.item-table-select):not(.item-table-detail-reason):not(.item-table-outsourcing-reason)::before {
    content: attr(data-label);
    color: var(--ad-text-secondary);
    font-size: 11px;
    line-height: 1.4;
  }

  .item-table-row .item-table-number {
    justify-content: flex-start;
    text-align: left;
  }

  .item-table-detail-reason,
  .item-table-outsourcing-reason {
    padding-right: 6px;
    padding-left: 6px;
  }
}

@media (max-width: 640px) {
  .item-table-row {
    grid-template-columns: 30px minmax(0, 1fr);
  }

  .item-table-row .item-table-cell:not(.item-table-select):not(.item-table-detail-reason):not(.item-table-outsourcing-reason) {
    grid-column: 2;
  }

  .item-table-row .item-table-select {
    grid-column: 1;
    grid-row: span 1;
    align-self: flex-start;
    padding-top: 8px;
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

  .status-heading {
    gap: 10px;
  }

  .stage-selection-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .item-assignee-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .item-assignee-select,
  .item-assignee-toolbar-actions,
  .item-assignee-toolbar-actions .el-button {
    width: 100%;
  }

}
</style>
