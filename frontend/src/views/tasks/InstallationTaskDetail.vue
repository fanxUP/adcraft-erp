<template>
  <div class="page">
    <el-button text @click="handleBack">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <el-skeleton v-if="loading && !task" :rows="6" animated class="initial-loading" />
    <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon class="load-error">
      <el-button text type="primary" :loading="loading" @click="fetchTask">重试加载</el-button>
    </el-alert>
    <div v-if="task" v-loading="loading">
      <div class="page-heading">
        <h2>安装任务</h2>
        <el-button text :loading="loading" @click="fetchTask">刷新页面</el-button>
      </div>

      <TaskOverviewCard
        data-ai-targets="task-status-assigned task-status-completed task-status-in_progress task-status-pending_acceptance"
        :task-no="task.installation_no"
        :created-at="task.created_at"
        :order-no="task.order_no"
        :item-states="task.order_item_states"
        task-type="installation"
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
        @view-order-changes="activityCardRef?.showOrderChanges()"
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
        :refresh-key="refreshVersion"
        :changing="changing"
        :completion-success-key="completionSuccessKey"
        @linked="fetchTask"
        @change="handleWorkflowChange"
        @rollback="handleRollback"
        @complete="handleItemCompletion"
        @outsource="handleOutsourceItem"
      />

      <OrderTaskAttachments
        :order-id="task.order_id"
        stage="installation"
        :task-id="task.id"
        :refresh-key="refreshVersion"
        :allow-upload="false"
        compact
      />

      <OutsourceTaskCard
        v-if="authStore.hasPermission('outsource_task:read')"
        ref="outsourceCardRef"
        :task-type="'installation'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
        :refresh-key="refreshVersion"
        @changed="fetchTask"
      />

      <TaskActivityCard ref="activityCardRef" task-type="installation" :task-id="task.id" :refresh-key="refreshVersion" />

      <div v-if="authStore.can('installation_task:delete')" class="task-danger-actions">
        <el-button text type="danger" @click="deleteVisible = true">删除此任务</el-button>
        <span>删除前将列出订单及关联业务的实际影响</span>
      </div>
      <TaskDeleteDialog
        v-if="authStore.can('installation_task:delete')"
        v-model="deleteVisible"
        task-type="installation"
        :task-id="task.id"
        @deleted="handleBack"
      />

    </div>
  </div>
</template>

<script setup lang="ts">
import { formatDateTimeFull } from '@/utils/datetime'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OrderTaskAttachments from '@/components/orders/OrderTaskAttachments.vue'
import OutsourceTaskCard from '@/components/outsource/OutsourceTaskCard.vue'
import { TaskOverviewCard } from '@/components/ui'
import { acknowledgeTaskOrderReview, getInstallationTask, changeInstallationTaskStatus, rollbackInstallationTaskItems, completeTaskItem } from '@/api/tasks'
import { ElMessage } from 'element-plus'
import { formatApiError } from '@/api/requestContract'
import type { InstallationTaskResponse } from '@/types/api'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import TaskDeleteDialog from '@/components/tasks/TaskDeleteDialog.vue'
import TaskActivityCard from '@/components/tasks/TaskActivityCard.vue'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const changing = ref(false)
const deleteVisible = ref(false)
const loadError = ref('')
const outsourceCardRef = ref<{ focusItem: (itemId: string) => Promise<void> } | null>(null)
const refreshVersion = ref(0)
const activityCardRef = ref<{ showOrderChanges: () => void } | null>(null)
const completionSuccessKey = ref(0)
let fetchVersion = 0
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
    refreshVersion.value++
    ElMessage.success('订单变更已确认，任务可以继续完成')
    void aiStore.notifyBusinessMutation().catch(() => undefined)
  } catch (cause) {
    ElMessage.error(formatApiError(cause, '订单变更复核失败，请重试'))
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
    completionSuccessKey.value++
    ElMessage.success(skipped ? '安装已完成（已跳过资料上传）' : '安装已完成，现场资料已归档')
    await fetchTask()
    void aiStore.notifyBusinessMutation().catch(() => undefined)
  } catch (cause) {
    ElMessage.error(formatApiError(cause, '完成失败，已保留所选资料，请重试'))
  } finally { changing.value = false }
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
    void aiStore.notifyBusinessMutation().catch(() => undefined)
  } catch (cause) {
    ElMessage.error(formatApiError(cause, '操作失败，请刷新后重试'))
  } finally { changing.value = false }
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
    void aiStore.notifyBusinessMutation().catch(() => undefined)
  } catch (cause) {
    ElMessage.error(formatApiError(cause, '操作失败，请刷新后重试'))
  } finally { changing.value = false }
}

function handleOutsourceItem(itemId: string) {
  void outsourceCardRef.value?.focusItem(itemId)
}

async function fetchTask() {
  const version = ++fetchVersion
  loading.value = true
  loadError.value = ''
  try {
    const data = await getInstallationTask(route.params.id as string)
    if (version !== fetchVersion) return
    task.value = data
    refreshVersion.value++
  } catch (cause) {
    if (version === fetchVersion) loadError.value = formatApiError(cause, '任务不存在、无查看权限或加载失败，请重试')
  } finally {
    if (version === fetchVersion) loading.value = false
  }
}

function handleBack() {
  const previous = window.history.state?.back
  if (typeof previous === 'string' && previous.startsWith('/') && previous !== route.fullPath) router.back()
  else void router.push('/installation-tasks')
}

watch(() => route.params.id, () => {
  task.value = null
  deleteVisible.value = false
  void fetchTask()
}, { immediate: true })

</script>

<style scoped>
.page { padding: 0; }
.page-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 12px 0; }
.page-heading h2 { margin: 0; color: var(--ad-text); font-size: 20px; }
.initial-loading, .load-error { margin-top: 16px; }
.task-danger-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 16px; color: var(--ad-text-secondary); font-size: 12px; }
</style>
