<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">安装任务 {{ task.installation_no }}</h2>

      <TaskOverviewCard
        data-ai-targets="task-status-assigned task-status-completed task-status-in_progress task-status-pending_acceptance"
        :task-no="task.installation_no"
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
        :review-required="task.review_required"
        :review-reason="task.review_reason"
        :can-acknowledge-review="authStore.hasPermission('installation_task:change_status')"
        :acknowledging-review="acknowledgingReview"
        @acknowledge-review="handleAcknowledgeReview"
        :extra-fields="installationOverviewFields"
      />

      <TaskOrderItemLinkCard
        :task-type="'installation'"
        :task-id="task.id"
        :order-id="task.order_id"
        :current-item-id="task.order_item_id"
        :current-item-ids="task.order_item_ids"
        :current-status="task.status"
        :workflow="INST_WORKFLOW"
        :refresh-key="task.updated_at"
        :changing="changing"
        @linked="fetchTask"
        @change="handleWorkflowChange"
        @rollback="handleRollback"
        @complete="handleItemCompletion"
      />

      <OrderTaskAttachments
        :order-id="task.order_id"
        stage="installation"
        :task-id="task.id"
        :refresh-key="task.updated_at"
        :allow-upload="false"
        compact
      />

      <OutsourceTaskCard
        v-if="authStore.hasPermission('outsource_task:read')"
        :task-type="'installation'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
      />

      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button :loading="deleting" @click="handleDelete" type="danger">删除此任务</el-button>
        <span style="color: var(--ad-text-secondary); margin-left: 12px; font-size: 12px;">删除后订单将回退到生产中状态，下游任务将被清除</span>
      </el-card>

    </div>
  </div>
</template>

<script setup lang="ts">
import { formatDateTimeFull } from '@/utils/datetime'
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OrderTaskAttachments from '@/components/orders/OrderTaskAttachments.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { TaskOverviewCard } from '@/components/ui'
import { acknowledgeTaskOrderReview, getInstallationTask, changeInstallationTaskStatus, rollbackInstallationTaskItems, completeTaskItem } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { InstallationTaskResponse } from '@/types/api'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteInstallationTask } from '@/api/tasks'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const changing = ref(false)
const deleting = ref(false)
const acknowledgingReview = ref(false)
const task = ref<InstallationTaskResponse | null>(null)
const installationOverviewFields = computed(() => [
  { label: '安装地址', value: task.value?.address, wide: true },
  { label: '计划安装时间', value: formatDateTimeFull(task.value?.scheduled_at) },
])

async function handleAcknowledgeReview() {
  if (!task.value) return
  acknowledgingReview.value = true
  try {
    task.value = await acknowledgeTaskOrderReview('installation', task.value.id) as InstallationTaskResponse
    ElMessage.success('订单变更已确认，任务可以继续完成')
    await aiStore.notifyBusinessMutation()
  } finally {
    acknowledgingReview.value = false
  }
}
const INST_WORKFLOW: Record<string, string[]> = {
  pending: ['assigned', 'in_progress'],
  assigned: ['in_progress', 'pending'],
  in_progress: ['completed', 'pending_acceptance', 'pending'],
  pending_acceptance: ['completed', 'in_progress'],
  completed: [],
  cancelled: [],
}

async function handleWorkflowChange(to_status: string, orderItemIds: string[], reason = '') {
  await doChangeStatus(to_status, reason, orderItemIds)
}

async function handleItemCompletion(orderItemId: string, files: File[], skipped: boolean) {
  changing.value = true
  try {
    await completeTaskItem('installation', route.params.id as string, orderItemId, files, skipped)
    ElMessage.success(skipped ? '安装已完成（已跳过资料上传）' : '安装已完成，现场资料已归档')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function handleRollback(targetStage: 'design' | 'production', orderItemIds: string[], reason = '') {
  if (targetStage !== 'production') return
  changing.value = true
  try {
    await rollbackInstallationTaskItems(route.params.id as string, {
      order_item_ids: orderItemIds,
      reason,
    })
    ElMessage.success('明细已退回制作')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function doChangeStatus(to_status: string, reason: string, orderItemIds: string[]) {
  changing.value = true
  try {
    await changeInstallationTaskStatus(route.params.id as string, {
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
    const data = await getInstallationTask(route.params.id as string)
    task.value = data
  } finally { loading.value = false }
}

async function handleDelete() {
  await ElMessageBox.confirm(
    `确定删除安装任务 ${task.value?.installation_no || ''}？删除后不可恢复，关联订单将回退到生产中状态。`,
    '删除任务', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
  )
  deleting.value = true
  try {
    await deleteInstallationTask(route.params.id as string)
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
