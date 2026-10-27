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
        <h2>设计任务</h2>
        <el-button text :loading="loading" @click="fetchTask">刷新页面</el-button>
      </div>

      <TaskOverviewCard
        data-ai-targets="design-file task-status-pending_review task-status-designing task-status-confirmed task-status-revision"
        :task-no="task.design_no"
        :created-at="task.created_at"
        :order-no="task.order_no"
        :item-states="task.order_item_states"
        task-type="design"
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
        :can-acknowledge-review="authStore.hasPermission('design_task:change_status')"
        :acknowledging-review="acknowledgingReview"
        @acknowledge-review="handleAcknowledgeReview"
        @view-order-changes="activityCardRef?.showOrderChanges()"
      />

      <TaskOrderItemLinkCard
        :task-type="'design'"
        :task-id="task.id"
        :order-id="task.order_id"
        :project-name="task.project_name"
        :current-item-id="task.order_item_id"
        :current-item-ids="task.order_item_ids"
        :current-status="task.status"
        :workflow="DESIGN_WORKFLOW"
        :refresh-key="refreshVersion"
        :changing="changing"
        :completion-success-key="completionSuccessKey"
        @linked="fetchTask"
        @change="handleWorkflowChange"
        @complete="handleItemCompletion"
        @outsource-changed="fetchTask"
      />

      <OrderTaskAttachments
        :order-id="task.order_id"
        stage="design"
        :task-id="task.id"
        :refresh-key="refreshVersion"
        :allow-upload="false"
        :collapsible="false"
        compact
      />

      <TaskActivityCard ref="activityCardRef" task-type="design" :task-id="task.id" :refresh-key="refreshVersion" />

      <div v-if="authStore.can('design_task:delete')" class="task-danger-actions">
        <el-button text type="danger" @click="deleteVisible = true">删除此任务</el-button>
        <span>删除前将列出订单及关联业务的实际影响</span>
      </div>
      <TaskDeleteDialog
        v-if="authStore.can('design_task:delete')"
        v-model="deleteVisible"
        task-type="design"
        :task-id="task.id"
        @deleted="handleBack"
      />

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { acknowledgeTaskOrderReview, getDesignTask, changeDesignTaskStatus, completeTaskItem } from '@/api/tasks'
import { ElMessage } from 'element-plus'
import { formatApiError } from '@/api/requestContract'
import type { DesignTaskResponse } from '@/types/api'
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import OrderTaskAttachments from '@/components/orders/OrderTaskAttachments.vue'
import { TaskOverviewCard } from '@/components/ui'
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
const refreshVersion = ref(0)
const activityCardRef = ref<{ showOrderChanges: () => void } | null>(null)
const completionSuccessKey = ref(0)
let fetchVersion = 0
const acknowledgingReview = ref(false)
const task = ref<DesignTaskResponse | null>(null)
const DESIGN_WORKFLOW: Record<string, string[]> = {
  pending: ['designing'],
  designing: ['confirmed', 'pending_review', 'pending'],
  pending_review: ['confirmed', 'revision'],
  revision: ['designing', 'pending_review'],
  confirmed: [],
  cancelled: [],
}

async function handleAcknowledgeReview() {
  if (!task.value) return
  acknowledgingReview.value = true
  try {
    task.value = await acknowledgeTaskOrderReview('design', task.value.id) as DesignTaskResponse
    refreshVersion.value++
    ElMessage.success('订单变更已确认，任务可以继续完成')
    void aiStore.notifyBusinessMutation().catch(() => undefined)
  } catch (cause) {
    ElMessage.error(formatApiError(cause, '订单变更复核失败，请重试'))
  } finally {
    acknowledgingReview.value = false
  }
}

async function handleWorkflowChange(to_status: string, orderItemIds: string[], reason = '') {
  await doChangeStatus(to_status, reason, orderItemIds)
}

async function handleItemCompletion(orderItemId: string, files: File[], skipped: boolean) {
  changing.value = true
  try {
    await completeTaskItem('design', route.params.id as string, orderItemId, files, skipped)
    completionSuccessKey.value++
    ElMessage.success(skipped ? '设计已完成（已跳过资料上传）' : '设计已完成，资料已归档')
    await fetchTask()
    void aiStore.notifyBusinessMutation().catch(() => undefined)
  } catch (cause) {
    ElMessage.error(formatApiError(cause, '完成失败，已保留所选资料，请重试'))
  } finally { changing.value = false }
}

async function doChangeStatus(to_status: string, reason: string, orderItemIds: string[]) {
  changing.value = true
  try {
    await changeDesignTaskStatus(route.params.id as string, {
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

async function fetchTask() {
  const version = ++fetchVersion
  loading.value = true
  loadError.value = ''
  try {
    const data = await getDesignTask(route.params.id as string)
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
  else void router.push('/design-tasks')
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
