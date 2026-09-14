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
          <span class="section-note">点击每条明细的操作按钮，只改变当前明细</span>
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

      <div v-if="canManageTaskItems" class="item-assignee-toolbar">
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
          <span class="item-assignee-toolbar-note">只对勾选的已关联、未完成明细生效</span>
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

      <div v-if="canManageTaskItems && items.length" class="selection-context-note">
        <span>勾选仅用于批量改派，不用于变更状态。</span>
        <span v-if="selectedItemIds.length">已选 {{ selectedItemIds.length }} 条</span>
      </div>

      <div v-loading="loadingItems" class="link-panel">
        <div
          v-if="items.length"
          class="item-table"
          :class="{
            'has-selection-column': selectionEnabled,
            'has-price-columns': canViewItemPrice,
            'has-outsource-column': canViewOutsourceTask,
          }"
          role="table"
          aria-label="订单明细逐条操作列表"
        >
          <div class="item-table-header" role="row">
            <span v-if="selectionEnabled" class="item-table-cell item-table-select" role="columnheader">
              选择
            </span>
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
            <span class="item-table-cell item-table-actions-header" role="columnheader">操作</span>
          </div>

          <div
            v-for="item in items"
            :key="item.id"
            class="item-table-row"
            :class="{
              'is-selected': selectedItemIds.includes(item.id),
              'is-disabled': rowDisabled(item),
            }"
            :aria-disabled="rowDisabled(item)"
            role="row"
          >
            <span v-if="selectionEnabled" class="item-table-cell item-table-select" data-label="选择" role="cell">
              <input
                v-model="selectedItemIds"
                class="item-table-checkbox"
                type="checkbox"
                :value="item.id"
                :disabled="changing || reassigning || !canSelect(item)"
                :aria-label="`选择订单明细 ${item.item_name} 用于改派`"
                @click.stop
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
            <span class="item-table-cell item-table-actions" data-label="操作" role="cell">
              <el-button
                v-if="primaryAction(item)"
                :type="primaryAction(item)?.kind === 'primary' ? 'primary' : 'warning'"
                size="small"
                :plain="primaryAction(item)?.kind !== 'primary'"
                :loading="actionLoadingId === item.id"
                :disabled="changing || reassigning || actionLoadingId === item.id || !primaryAction(item)?.allowed"
                @click.stop="handleItemAction(item, primaryAction(item)!)"
              >
                {{ primaryAction(item)?.label }}
              </el-button>
              <el-button
                v-for="action in secondaryActions(item)"
                :key="`${item.id}-${action.key}-${action.to_status}`"
                text
                :type="action.key === 'cancel' ? 'danger' : 'warning'"
                size="small"
                :disabled="changing || reassigning || actionLoadingId === item.id || !action.allowed"
                @click.stop="handleItemAction(item, action)"
              >
                {{ action.label }}
              </el-button>
              <span v-if="disabledReason(item)" class="item-action-reason">
                {{ disabledReason(item) }}
              </span>
            </span>
          </div>
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
  updateInstallationTask,
  updateProductionTask,
} from '@/api/tasks'
import type { TaskAssigneeOption, TaskItemAction, TaskOrderItemOption, TaskType } from '@/types/api'
import { StatusTag } from '@/components/ui'
import { useAuthStore } from '@/stores/auth'
import { getTaskItemActions, isTaskOrderItemSelectable } from '@/utils/taskItemActions'
import { formatMoney } from '@/utils/format'

const authStore = useAuthStore()

const props = withDefaults(defineProps<{
  taskType: TaskType
  taskId: string
  orderId: string
  currentItemId?: string | null
  currentItemIds?: string[] | null
  currentStatus: string
  workflow: Record<string, string[]>
  refreshKey?: string | null
  changing: boolean
}>(), {
  currentItemId: null,
  currentItemIds: () => [],
  refreshKey: null,
})

const emit = defineEmits<{
  linked: []
  change: [status: string, orderItemIds: string[], reason?: string]
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
const actionLoadingId = ref<string | null>(null)

const terminalStatuses: Record<TaskType, string[]> = {
  design: ['confirmed', 'cancelled'],
  production: ['completed', 'cancelled'],
  installation: ['completed', 'cancelled'],
}

const canViewItemPrice = computed(() => authStore.hasPermission('order_item:view_price'))
const canViewOutsourceTask = computed(() => authStore.hasPermission('outsource_task:read'))
const canManageTaskItems = computed(() => authStore.hasPermission(`${props.taskType}_task:assign`))
const linkedItemIds = computed(() => {
  if (props.currentItemIds?.length) return props.currentItemIds
  return props.currentItemId ? [props.currentItemId] : []
})
const isHistoricalReadOnly = computed(() => {
  if (linkedItemIds.value.length) return false
  return terminalStatuses[props.taskType]?.includes(props.currentStatus) ?? false
})
const selectionEnabled = computed(() => canManageTaskItems.value || isHistoricalReadOnly.value)

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

function itemActions(item: TaskOrderItemOption) {
  return getTaskItemActions(props.taskType, item, props.workflow)
}

function primaryAction(item: TaskOrderItemOption): TaskItemAction | undefined {
  const actions = itemActions(item)
  return actions.find(action => action.kind === 'primary') || actions[0]
}

function secondaryActions(item: TaskOrderItemOption) {
  const actions = itemActions(item)
  const primary = actions.find(action => action.kind === 'primary') || actions[0]
  return actions.filter(action => action !== primary)
}

function disabledReason(item: TaskOrderItemOption) {
  const actionReason = itemActions(item).find(action => !action.allowed)?.disabled_reason
  return actionReason || item.capabilities?.select?.disabled_reason || item.disabled_reason || ''
}

function rowDisabled(item: TaskOrderItemOption) {
  return !canSelect(item) && !itemActions(item).some(action => action.allowed)
}

function currentItemStatusLabel(item: TaskOrderItemOption) {
  if (!item.is_linked) return '未关联'
  return item.task_status_label || item.task_status || '待分配'
}

async function handleItemAction(item: TaskOrderItemOption, action: TaskItemAction) {
  if (!action.allowed) {
    ElMessage.info(action.disabled_reason || '当前账号不能操作该明细')
    return
  }
  if (actionLoadingId.value) return

  let reason = ''
  try {
    if (action.to_status === 'cancelled') {
      const result = await ElMessageBox.prompt(
        `请输入取消“${itemLabel(item)}”的原因`,
        '取消明细任务',
        {
          confirmButtonText: '确认取消',
          cancelButtonText: '返回',
          inputPlaceholder: '请输入取消原因',
        },
      )
      reason = result.value?.trim() || ''
      if (!reason) {
        ElMessage.warning('请输入取消原因')
        return
      }
    } else {
      await ElMessageBox.confirm(
        `确认将“${itemLabel(item)}”从“${currentItemStatusLabel(item)}”变更为“${action.label}”吗？`,
        '变更明细状态',
        {
          confirmButtonText: '确认操作',
          cancelButtonText: '取消',
          type: action.kind === 'primary' ? 'warning' : 'info',
        },
      )
    }
  } catch {
    return
  }

  actionLoadingId.value = item.id
  emit('change', action.to_status, [item.id], reason)
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
    if (canManageTaskItems.value) await loadAssigneeOptions()
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
  if (props.taskType === 'design') return updateDesignTask(props.taskId, { order_item_ids: itemIds })
  if (props.taskType === 'production') return updateProductionTask(props.taskId, { order_item_ids: itemIds })
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

const reassignableSelectedItemIds = computed(() => items.value
  .filter(item => (
    selectedItemIds.value.includes(item.id)
    && item.is_linked
    && item.assignee_state !== 'terminal'
  ))
  .map(item => item.id))

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

watch(
  [() => props.orderId, () => props.taskId, () => props.taskType, () => props.refreshKey],
  () => void loadItems(),
)
watch(() => props.changing, value => {
  if (!value) actionLoadingId.value = null
})
onMounted(loadItems)
</script>

<style scoped>
.task-processing-card { margin-top: 16px; }
.task-section { min-width: 0; }
.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; color: var(--ad-text); font-size: 15px; font-weight: 600; }
.section-heading-main { display: flex; align-items: center; gap: 10px; }
.section-note { color: var(--ad-text-secondary); font-size: 12px; font-weight: 400; }
.item-assignee-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px 16px; margin-bottom: 10px; padding: 10px 12px; border: 1px solid var(--el-color-primary-light-7); border-radius: 6px; background: var(--el-color-primary-light-9); }
.item-assignee-toolbar-main, .item-assignee-toolbar-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.item-assignee-toolbar-label { color: var(--ad-text); font-size: 13px; font-weight: 600; }
.item-assignee-select { width: 220px; }
.item-assignee-toolbar-note, .selection-context-note { color: var(--ad-text-secondary); font-size: 12px; }
.selection-context-note { display: flex; justify-content: space-between; gap: 12px; margin: 0 0 8px; padding: 0 4px; }
.link-panel { margin-top: 16px; }
.item-table { --item-table-columns: minmax(76px, 1fr) minmax(120px, 1.55fr) minmax(80px, .9fr) minmax(56px, .65fr) minmax(70px, .75fr) minmax(72px, .75fr) minmax(84px, .85fr) minmax(80px, .7fr) minmax(150px, 1.2fr); overflow: visible; border: 1px solid var(--el-border-color); border-radius: 6px; }
.item-table.has-selection-column { --item-table-columns: 36px minmax(76px, 1fr) minmax(120px, 1.55fr) minmax(80px, .9fr) minmax(56px, .65fr) minmax(70px, .75fr) minmax(72px, .75fr) minmax(84px, .85fr) minmax(80px, .7fr) minmax(150px, 1.2fr); }
.item-table.has-price-columns { --item-table-columns: minmax(76px, 1fr) minmax(120px, 1.45fr) minmax(80px, .85fr) minmax(56px, .6fr) minmax(70px, .7fr) minmax(72px, .7fr) minmax(84px, .8fr) minmax(72px, .6fr) minmax(72px, .65fr) minmax(80px, .7fr) minmax(150px, 1.1fr); }
.item-table.has-selection-column.has-price-columns { --item-table-columns: 36px minmax(76px, 1fr) minmax(120px, 1.45fr) minmax(80px, .85fr) minmax(56px, .6fr) minmax(70px, .7fr) minmax(72px, .7fr) minmax(84px, .8fr) minmax(72px, .6fr) minmax(72px, .65fr) minmax(80px, .7fr) minmax(150px, 1.1fr); }
.item-table.has-outsource-column:not(.has-price-columns) { --item-table-columns: minmax(76px, 1fr) minmax(120px, 1.45fr) minmax(80px, .85fr) minmax(56px, .6fr) minmax(70px, .7fr) minmax(72px, .7fr) minmax(84px, .8fr) minmax(80px, .7fr) minmax(100px, .7fr) minmax(150px, 1.1fr); }
.item-table.has-selection-column.has-outsource-column:not(.has-price-columns) { --item-table-columns: 36px minmax(76px, 1fr) minmax(120px, 1.45fr) minmax(80px, .85fr) minmax(56px, .6fr) minmax(70px, .7fr) minmax(72px, .7fr) minmax(84px, .8fr) minmax(80px, .7fr) minmax(100px, .7fr) minmax(150px, 1.1fr); }
.item-table.has-price-columns.has-outsource-column { --item-table-columns: minmax(76px, 1fr) minmax(120px, 1.35fr) minmax(80px, .8fr) minmax(56px, .55fr) minmax(70px, .65fr) minmax(72px, .65fr) minmax(84px, .75fr) minmax(72px, .6fr) minmax(72px, .6fr) minmax(80px, .65fr) minmax(100px, .7fr) minmax(150px, 1fr); }
.item-table.has-selection-column.has-price-columns.has-outsource-column { --item-table-columns: 36px minmax(76px, 1fr) minmax(120px, 1.35fr) minmax(80px, .8fr) minmax(56px, .55fr) minmax(70px, .65fr) minmax(72px, .65fr) minmax(84px, .75fr) minmax(72px, .6fr) minmax(72px, .6fr) minmax(80px, .65fr) minmax(100px, .7fr) minmax(150px, 1fr); }
.item-table-header, .item-table-row { display: grid; grid-template-columns: var(--item-table-columns); align-items: stretch; }
.item-table-header { padding: 10px 12px; border-bottom: 1px solid var(--el-border-color); background: var(--el-fill-color-lighter); color: var(--ad-text-secondary); font-size: 12px; font-weight: 600; }
.item-table-row { min-width: 0; padding: 12px; border-bottom: 1px solid var(--el-border-color-lighter); transition: background-color .15s ease; }
.item-table-row:last-child { border-bottom: 0; }
.item-table-row:hover { background: var(--el-fill-color-light); }
.item-table-row.is-disabled { background: var(--el-fill-color-lighter); }
.item-table-row.is-selected { background: var(--el-color-primary-light-9); }
.item-table-cell { display: flex; min-width: 0; align-items: center; padding: 0 6px; color: var(--ad-text); line-height: 1.5; overflow-wrap: anywhere; }
.item-table-header .item-table-cell { color: var(--ad-text-secondary); }
.item-table-select { justify-content: center; padding-right: 2px; padding-left: 2px; }
.item-table-checkbox { width: 16px; height: 16px; margin: 0; accent-color: var(--el-color-primary); }
.item-table-name, .item-table-product, .item-table-spec { align-items: flex-start; white-space: normal; word-break: break-word; }
.item-table-name { font-weight: 600; }
.item-table-number { justify-content: flex-end; text-align: right; font-variant-numeric: tabular-nums; white-space: normal; }
.item-table-assignee, .item-table-outsourcing { align-items: flex-start; }
.item-assignee-name { color: var(--el-color-danger); font-weight: 600; overflow-wrap: anywhere; }
.item-assignee-placeholder, .item-table-placeholder { color: var(--ad-text-secondary); }
.item-table-actions-header { justify-content: flex-start; }
.item-table-actions { align-items: flex-start; flex-wrap: wrap; gap: 4px; }
.item-action-reason { flex-basis: 100%; color: var(--el-color-warning-dark-2); font-size: 12px; line-height: 1.5; }
.link-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 12px; margin-top: 12px; }
.link-context-note, .link-tip { color: var(--ad-text-secondary); font-size: 12px; }
.link-tip { margin-top: 10px; }
.error-tip { color: var(--el-color-danger); }
@media (max-width: 900px) {
  .item-table-header { display: none; }
  .item-table, .item-table.has-selection-column, .item-table.has-price-columns, .item-table.has-selection-column.has-price-columns, .item-table.has-outsource-column:not(.has-price-columns), .item-table.has-selection-column.has-outsource-column:not(.has-price-columns), .item-table.has-price-columns.has-outsource-column, .item-table.has-selection-column.has-price-columns.has-outsource-column { --item-table-columns: minmax(0, 1fr) minmax(128px, auto); }
  .item-table-row { grid-template-columns: var(--item-table-columns); padding: 10px; }
  .item-table-row .item-table-cell:not(.item-table-actions):not(.item-table-select):not(.item-action-reason) { grid-column: 1 / -1; flex-direction: column; align-items: flex-start; gap: 2px; padding: 5px 6px; }
  .item-table-row .item-table-cell:not(.item-table-actions):not(.item-table-select):not(.item-action-reason)::before { content: attr(data-label); color: var(--ad-text-secondary); font-size: 11px; line-height: 1.4; }
  .item-table-row .item-table-select { grid-column: 1; grid-row: 1; align-self: flex-start; }
  .item-table-row .item-table-actions { grid-column: 2; grid-row: 1; justify-content: flex-end; }
  .item-table-row .item-table-number { justify-content: flex-start; text-align: left; }
  .item-table-row .item-action-reason { grid-column: 1 / -1; padding: 6px; }
}
@media (max-width: 640px) {
  .section-heading { align-items: flex-start; flex-direction: column; gap: 4px; }
  .section-heading-main { align-items: flex-start; flex-direction: column; gap: 4px; }
  .item-assignee-toolbar, .selection-context-note { align-items: flex-start; flex-direction: column; }
  .item-assignee-select, .item-assignee-toolbar-actions, .item-assignee-toolbar-actions .el-button { width: 100%; }
  .link-actions, .link-actions .el-button { width: 100%; }
  .item-table, .item-table.has-selection-column, .item-table.has-price-columns, .item-table.has-selection-column.has-price-columns, .item-table.has-outsource-column:not(.has-price-columns), .item-table.has-selection-column.has-outsource-column:not(.has-price-columns), .item-table.has-price-columns.has-outsource-column, .item-table.has-selection-column.has-price-columns.has-outsource-column { --item-table-columns: minmax(0, 1fr); }
  .item-table-row .item-table-select, .item-table-row .item-table-actions { grid-column: 1; grid-row: auto; justify-content: flex-start; }
}
</style>
