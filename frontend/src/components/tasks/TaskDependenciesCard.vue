<template>
  <el-card shadow="never" class="info-card dependency-card">
    <template #header>
      <div class="card-header">
        <span>任务依赖</span>
        <el-tag v-if="isBlocked" type="warning" size="small">当前被阻塞</el-tag>
      </div>
    </template>

    <el-alert
      v-if="isBlocked"
      type="warning"
      :title="blockedReason || '前置任务未完成'"
      :closable="false"
      show-icon
      class="block-alert"
    />

    <div v-if="orderId" class="dependency-create-row">
      <el-select
        v-model="predecessorKey"
        filterable
        clearable
        placeholder="选择前置任务"
        class="predecessor-select"
      >
        <el-option
          v-for="candidate in candidates"
          :key="taskKey(candidate.task_type, candidate.id)"
          :label="`${candidate.task_no} · ${candidate.project_name}`"
          :value="taskKey(candidate.task_type, candidate.id)"
        >
          <div class="candidate-option">
            <span>{{ candidate.task_no }} · {{ candidate.project_name }}</span>
            <span class="muted">{{ statusLabel(candidate.status) }} {{ progress(candidate.progress_pct) }}%</span>
          </div>
        </el-option>
      </el-select>
      <el-button type="primary" :loading="saving" :disabled="!predecessorKey" @click="handleCreate">
        添加前置依赖
      </el-button>
    </div>

    <el-table v-if="dependencies.length" :data="dependencies" stripe size="small">
      <el-table-column label="前置任务" min-width="220">
        <template #default="{ row }">
          <div>{{ row.predecessor.task_no }} · {{ row.predecessor.project_name }}</div>
          <span class="muted">{{ statusLabel(row.predecessor.status) }} {{ progress(row.predecessor.progress_pct) }}%</span>
        </template>
      </el-table-column>
      <el-table-column label="后置任务" min-width="220">
        <template #default="{ row }">
          <div>{{ row.successor.task_no }} · {{ row.successor.project_name }}</div>
          <span class="muted">{{ statusLabel(row.successor.status) }} {{ progress(row.successor.progress_pct) }}%</span>
        </template>
      </el-table-column>
      <el-table-column label="依赖状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.is_satisfied ? 'success' : 'warning'" size="small">
            {{ row.is_satisfied ? '已满足' : '未完成' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button text type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-else description="暂未设置任务依赖" :image-size="56" />
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTaskDependency,
  deleteTaskDependency,
  getTaskDependencies,
  getTaskQueue,
} from '@/api/tasks'
import type {
  TaskDependencyResponse,
  TaskDependencyTaskType,
  TaskQueueItem,
} from '@/types/api'

const props = defineProps<{
  taskType: TaskDependencyTaskType
  taskId: string
  orderId?: string | null
  isBlocked?: boolean
  blockedReason?: string | null
}>()

const emit = defineEmits<{
  changed: []
}>()

const dependencies = ref<TaskDependencyResponse[]>([])
const candidates = ref<TaskQueueItem[]>([])
const predecessorKey = ref('')
const saving = ref(false)

const relatedTaskKeys = computed(() => {
  const keys = new Set<string>()
  for (const dependency of dependencies.value) {
    keys.add(taskKey(dependency.predecessor.task_type, dependency.predecessor.task_id))
    keys.add(taskKey(dependency.successor.task_type, dependency.successor.task_id))
  }
  return keys
})

function taskKey(type: TaskDependencyTaskType, id: string) {
  return `${type}:${id}`
}

function progress(value: number | undefined) {
  return Math.min(100, Math.max(0, Number(value ?? 0)))
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待开始',
    designing: '设计中',
    pending_review: '待确认',
    revision: '需修改',
    confirmed: '设计完成',
    in_progress: '进行中',
    assigned: '已分配',
    pending_acceptance: '待验收',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[status] || status
}

async function loadData() {
  if (!props.taskId) return
  try {
    dependencies.value = await getTaskDependencies(props.taskType, props.taskId)
    if (!props.orderId) {
      candidates.value = []
      return
    }
    const queue = await getTaskQueue({ order_id: props.orderId, page: 1, page_size: 200 })
    const currentKey = taskKey(props.taskType, props.taskId)
    candidates.value = queue.items.filter((candidate) => {
      const key = taskKey(candidate.task_type, candidate.id)
      return key !== currentKey && !relatedTaskKeys.value.has(key)
    })
  } catch {
    // The shared API client already displays the server error.
  }
}

function parseTaskKey(value: string) {
  const separator = value.indexOf(':')
  return {
    type: value.slice(0, separator) as TaskDependencyTaskType,
    id: value.slice(separator + 1),
  }
}

async function handleCreate() {
  if (!props.orderId || !predecessorKey.value) return
  const predecessor = parseTaskKey(predecessorKey.value)
  saving.value = true
  try {
    await createTaskDependency({
      predecessor_task_type: predecessor.type,
      predecessor_task_id: predecessor.id,
      successor_task_type: props.taskType,
      successor_task_id: props.taskId,
      dependency_type: 'finish_to_start',
    })
    predecessorKey.value = ''
    ElMessage.success('依赖已添加')
    await loadData()
    emit('changed')
  } catch {
    // The shared API client already displays the server error.
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: string) {
  await ElMessageBox.confirm('确定删除这条任务依赖吗？删除后后置任务将不再受此前置任务限制。', '删除依赖', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  try {
    await deleteTaskDependency(id)
    ElMessage.success('依赖已删除')
    await loadData()
    emit('changed')
  } catch {
    // The shared API client already displays the server error.
  }
}

watch(
  () => [props.taskType, props.taskId, props.orderId],
  () => void loadData(),
  { immediate: true },
)
</script>

<style scoped>
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.block-alert { margin-bottom: 14px; }
.dependency-create-row { display: flex; gap: 10px; margin-bottom: 14px; }
.predecessor-select { flex: 1; min-width: 220px; }
.candidate-option { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.muted { color: var(--ad-text-secondary); font-size: 12px; }
@media (max-width: 640px) {
  .dependency-create-row { align-items: stretch; flex-direction: column; }
}
</style>
