<template>
  <el-card shadow="never" class="info-card task-history-card" style="margin-top: 16px">
    <template #header>
      <div class="history-header">
        <span>变更历史</span>
        <el-button text size="small" :loading="loading" @click="loadHistory">刷新</el-button>
      </div>
    </template>

    <el-skeleton v-if="loading && !history.length" :rows="3" animated />
    <el-empty v-else-if="!history.length" description="暂无变更记录" />
    <el-timeline v-else>
      <el-timeline-item
        v-for="item in history"
        :key="item.id"
        :timestamp="formatDateTimeFull(item.changed_at) || '-'"
        placement="top"
        :type="item.action === 'status_change' ? 'primary' : 'info'"
      >
        <div class="history-title">
          <span>{{ actionLabel(item.action) }}</span>
          <span class="history-user">{{ item.user_name || '系统' }}</span>
        </div>
        <div v-if="item.from_status || item.to_status" class="history-line">
          状态：{{ statusLabel(item.from_status) || '-' }} → {{ statusLabel(item.to_status) || '-' }}
        </div>
        <div v-if="item.from_progress_pct != null || item.to_progress_pct != null" class="history-line">
          进度：{{ item.from_progress_pct ?? '-' }}% → {{ item.to_progress_pct ?? '-' }}%
        </div>
        <div v-if="item.changed_fields.length" class="history-line history-muted">
          字段：{{ item.changed_fields.map(fieldLabel).join('、') }}
        </div>
        <div v-if="item.reason" class="history-line history-reason">原因：{{ item.reason }}</div>
      </el-timeline-item>
    </el-timeline>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { getTaskHistory } from '@/api/tasks'
import { formatDateTimeFull } from '@/utils/datetime'
import type { TaskDependencyTaskType, TaskHistoryItem } from '@/types/api'

const props = defineProps<{
  taskType: TaskDependencyTaskType
  taskId: string
}>()

const history = ref<TaskHistoryItem[]>([])
const loading = ref(false)

const statusNames: Record<string, string> = {
  pending: '待处理',
  designing: '设计中',
  pending_review: '待确认',
  revision: '需修改',
  assigned: '已分配',
  in_progress: '进行中',
  rework: '返工',
  pending_acceptance: '待验收',
  confirmed: '已完成',
  completed: '已完成',
  cancelled: '已取消',
}

const fieldNames: Record<string, string> = {
  status: '状态',
  progress_pct: '进度',
  planned_start_at: '计划开始时间',
  planned_end_at: '计划结束时间',
  assigned_to: '负责人',
}

function actionLabel(action: TaskHistoryItem['action']) {
  return { create: '创建任务', update: '编辑任务', status_change: '变更状态' }[action]
}

function statusLabel(status: string | null | undefined) {
  return status ? (statusNames[status] || status) : ''
}

function fieldLabel(field: string) {
  return fieldNames[field] || field
}

async function loadHistory() {
  loading.value = true
  try {
    const data = await getTaskHistory(props.taskType, props.taskId)
    history.value = data.items
  } finally {
    loading.value = false
  }
}

watch(() => [props.taskType, props.taskId], loadHistory)
onMounted(loadHistory)
</script>

<style scoped>
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-title {
  display: flex;
  gap: 10px;
  align-items: center;
  color: var(--ad-text);
  font-weight: 600;
}

.history-user,
.history-muted {
  color: var(--ad-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.history-line {
  margin-top: 5px;
  color: var(--ad-text-secondary);
  font-size: 13px;
}

.history-reason {
  color: var(--ad-text);
}
</style>
