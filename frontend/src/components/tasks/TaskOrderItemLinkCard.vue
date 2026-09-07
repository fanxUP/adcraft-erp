<template>
  <el-card v-if="!currentItemId" shadow="never" class="info-card task-item-link-card">
    <template #header>
      <div class="card-header">
        <span>关联订单明细</span>
        <el-tag type="warning" size="small">历史整单任务</el-tag>
      </div>
    </template>

    <el-alert
      title="只把这条任务绑定到一个明确的订单明细，不会自动拆分任务或创建下游任务。"
      type="info"
      :closable="false"
      show-icon
    />

    <div v-loading="loadingItems" class="link-row">
      <el-select
        v-model="selectedItemId"
        placeholder="选择要关联的订单明细"
        filterable
        clearable
        style="min-width: 320px; flex: 1"
        :disabled="loadingItems || saving || !items.length"
      >
        <el-option
          v-for="item in items"
          :key="item.id"
          :label="itemLabel(item)"
          :value="item.id"
        />
      </el-select>
      <el-button
        type="primary"
        :loading="saving"
        :disabled="!selectedItemId || !items.length"
        @click="handleLink"
      >
        关联到明细
      </el-button>
    </div>

    <div v-if="loadError" class="link-tip error-tip">订单明细加载失败，请刷新后重试。</div>
    <div v-else-if="!loadingItems && !items.length" class="link-tip">
      当前订单没有可关联的有效明细。
    </div>
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

const props = withDefaults(defineProps<{
  taskType: TaskDependencyTaskType
  taskId: string
  orderId: string
  currentItemId?: string | null
}>(), {
  currentItemId: null,
})

const emit = defineEmits<{
  linked: []
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

async function loadItems() {
  if (!props.orderId || props.currentItemId) return
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

watch(() => props.orderId, loadItems)
onMounted(loadItems)
</script>

<style scoped>
.task-item-link-card {
  margin-top: 16px;
}

.link-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 16px;
}

.link-tip {
  margin-top: 10px;
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.error-tip {
  color: var(--el-color-danger);
}

@media (max-width: 640px) {
  .link-row {
    align-items: stretch;
    flex-direction: column;
  }

  .link-row .el-select {
    min-width: 0 !important;
    width: 100%;
  }
}
</style>
