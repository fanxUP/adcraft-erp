<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">制作任务 {{ task.production_no }}</h2>

      <TaskOverviewCard
        data-ai-targets="task-status-completed task-status-in_progress task-status-qc_check task-status-queued task-status-rework"
        :task-no="task.production_no"
        :project-name="task.project_name"
        :status="task.status_view || task.status"
        :progress-pct="task.progress_pct"
        :progress-tone="task.status_view?.tone"
        :planned-start-at="task.planned_start_at"
        :planned-end-at="task.planned_end_at"
        :is-overdue="task.is_overdue"
        :overdue-days="task.overdue_days"
        :customer-name="task.customer_name"
        :department="task.department"
        :contact-name="task.contact_name"
        :contact-phone="task.contact_phone"
        :extra-fields="productionOverviewFields"
      />

      <TaskOrderItemLinkCard
        :task-type="'production'"
        :task-id="task.id"
        :order-id="task.order_id"
        :current-item-id="task.order_item_id"
        :current-item-ids="task.order_item_ids"
        :current-status="task.status"
        :workflow="PROD_WORKFLOW"
        :refresh-key="task.updated_at"
        :changing="changing"
        @linked="fetchTask"
        @change="handleWorkflowChange"
        @rollback="handleRollback"
        @complete="handleItemCompletion"
      />

      <OrderTaskAttachments
        :order-id="task.order_id"
        stage="production"
        :task-id="task.id"
        :refresh-key="task.updated_at"
        :allow-upload="false"
        compact
      />

      <OutsourceTaskCard
        v-if="authStore.hasPermission('outsource_task:read')"
        :task-type="'production'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
      />

      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button :loading="deleting" @click="handleDelete" type="danger">删除此任务</el-button>
        <span style="color: var(--ad-text-secondary); margin-left: 12px; font-size: 12px;">删除后订单将回退到设计中状态，下游任务将被清除</span>
      </el-card>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OrderTaskAttachments from '@/components/orders/OrderTaskAttachments.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { TaskOverviewCard } from '@/components/ui'
import { getProductionTask, changeProductionTaskStatus, rollbackProductionTaskItems, completeTaskItem } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ProductionTaskResponse } from '@/types/api'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteProductionTask } from '@/api/tasks'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const changing = ref(false)
const deleting = ref(false)
const task = ref<ProductionTaskResponse | null>(null)
const productionOverviewFields = computed(() => [
  { label: '尺寸', value: formatProductionDimensions(task.value) },
  { label: '数量', value: task.value?.quantity ?? '-' },
])

function formatProductionDimensions(value: ProductionTaskResponse | null) {
  if (!value) return '-'
  const dimensions = [
    { label: '长', value: value.length },
    { label: '宽', value: value.width },
    { label: '高', value: value.height },
  ].filter(item => item.value != null)
  return dimensions.length
    ? dimensions.map(item => `${item.label}${item.value}m`).join(' × ')
    : '-'
}
const PROD_WORKFLOW: Record<string, string[]> = {
  pending: ['in_progress'],
  in_progress: ['completed', 'rework', 'pending'],
  rework: ['in_progress'],
  completed: [],
  cancelled: [],
}

async function handleWorkflowChange(to_status: string, orderItemIds: string[], reason = '') {
  await doChangeStatus(to_status, reason, orderItemIds)
}

async function handleItemCompletion(orderItemId: string, files: File[], skipped: boolean) {
  changing.value = true
  try {
    await completeTaskItem('production', route.params.id as string, orderItemId, files, skipped)
    ElMessage.success(skipped ? '制作已完成（已跳过资料上传）' : '制作已完成，资料已归档')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function handleRollback(targetStage: 'design' | 'production', orderItemIds: string[], reason = '') {
  if (targetStage !== 'design') return
  changing.value = true
  try {
    await rollbackProductionTaskItems(route.params.id as string, {
      order_item_ids: orderItemIds,
      reason,
    })
    ElMessage.success('明细已退回设计')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function doChangeStatus(to_status: string, reason: string, orderItemIds: string[]) {
  changing.value = true
  try {
    await changeProductionTaskStatus(route.params.id as string, {
      to_status,
      reason,
      order_item_ids: orderItemIds,
    })
    ElMessage.success('状态已变更')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function fetchTask() {
  loading.value = true
  try {
    const data = await getProductionTask(route.params.id as string)
    task.value = data
  } finally { loading.value = false }
}

async function handleDelete() {
  await ElMessageBox.confirm(
    `确定删除制作任务 ${task.value?.production_no || ''}？删除后不可恢复，关联订单将回退到设计中状态。`,
    '删除任务', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
  )
  deleting.value = true
  try {
    await deleteProductionTask(route.params.id as string)
    ElMessage.success('任务已删除')
    router.push('/projects/board')
  } catch { /* handled */ } finally { deleting.value = false }
}

onMounted(() => {
  void fetchTask()
})
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
