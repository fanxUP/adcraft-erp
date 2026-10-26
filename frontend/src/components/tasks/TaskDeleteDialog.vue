<template>
  <el-dialog
    :model-value="modelValue"
    title="删除任务 · 影响确认"
    width="min(740px, 94vw)"
    :close-on-click-modal="false"
    :close-on-press-escape="!deleting"
    :show-close="!deleting"
    @update:model-value="!deleting && emit('update:modelValue', $event)"
  >
    <div v-loading="loading" class="delete-impact">
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <template v-if="impact">
        <p>即将删除 <strong>{{ impact.task_no }}</strong><span v-if="impact.order_no">，关联订单 {{ impact.order_no }}</span>。</p>
        <p v-if="impact.target_order_status">
          订单状态：{{ orderStatus(impact.order_status) }} → <strong>{{ orderStatus(impact.target_order_status) }}</strong>
        </p>
        <el-alert type="warning" :closable="false" show-icon>
          <template #title>请核对以下关联项和处理方式</template>
          <div v-for="warning in impact.warnings" :key="warning">{{ warning }}</div>
        </el-alert>
        <el-table :data="impact.entries" size="small" max-height="380" class="impact-table">
          <el-table-column prop="label" label="关联项" min-width="220" />
          <el-table-column label="处理方式" min-width="140">
            <template #default="{ row }">{{ effects[row.effect as keyof typeof effects] }}</template>
          </el-table-column>
          <el-table-column label="影响说明" min-width="190">
            <template #default="{ row }">
              <span>{{ row.detail || '—' }}</span>
              <details v-if="row.items?.length" class="impact-items">
                <summary>查看 {{ row.items.length }} 条关联明细</summary>
                <ul><li v-for="(item, index) in row.items" :key="index">{{ item }}</li></ul>
              </details>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <el-empty v-else-if="!loading && !error" description="暂无删除影响信息" :image-size="50" />
    </div>
    <template #footer>
      <el-button :disabled="deleting" @click="emit('update:modelValue', false)">取消</el-button>
      <el-button :disabled="deleting" :loading="loading" @click="loadImpact">重新核对</el-button>
      <el-button type="danger" :disabled="loading || !impact" :loading="deleting" @click="confirmDelete">确认删除</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { deleteDesignTask, deleteProductionTask, deleteInstallationTask, getTaskDeleteImpact } from '@/api/tasks'
import type { TaskDeleteImpact } from '@/api/tasks'
import type { TaskType } from '@/types/api'
import { formatApiError } from '@/api/requestContract'

const props = defineProps<{ modelValue: boolean; taskType: TaskType; taskId: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; deleted: [] }>()
const impact = ref<TaskDeleteImpact | null>(null)
const loading = ref(false)
const deleting = ref(false)
const error = ref('')
let requestVersion = 0
const effects = { delete_task: '永久删除任务', recycle_acceptance: '移入回收站', unlink_outsource: '解除来源关联', reopen_task: '重新打开上一阶段' }
const deleteFunctions = { design: deleteDesignTask, production: deleteProductionTask, installation: deleteInstallationTask }

function orderStatus(status: string | null) {
  return ({ confirmed: '已确认', designing: '设计中', in_production: '制作中', in_installation: '安装中', completed: '已完成' } as Record<string, string>)[status || ''] || status || '—'
}

async function loadImpact() {
  const version = ++requestVersion
  impact.value = null
  loading.value = true
  try {
    const data = await getTaskDeleteImpact(props.taskType, props.taskId)
    if (version === requestVersion) impact.value = data
  } catch (cause) {
    if (version === requestVersion) error.value = formatApiError(cause, '删除影响加载失败，请重新核对')
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function confirmDelete() {
  if (!impact.value || deleting.value || loading.value) return
  deleting.value = true
  error.value = ''
  try {
    await deleteFunctions[props.taskType](props.taskId, impact.value.plan_hash)
    ElMessage.success('任务已删除')
    emit('update:modelValue', false)
    emit('deleted')
  } catch (cause) {
    error.value = formatApiError(cause, '删除失败，请核对关联项后重试')
    await loadImpact()
  } finally {
    deleting.value = false
  }
}

watch(() => [props.modelValue, props.taskType, props.taskId] as const, () => {
  error.value = ''
  if (props.modelValue) void loadImpact()
  else { requestVersion++; impact.value = null }
}, { immediate: true })
</script>

<style scoped>
.delete-impact { min-height: 120px; color: var(--ad-text); }
.delete-impact p { line-height: 1.6; }
.impact-items summary { color: var(--el-color-primary); cursor: pointer; margin-top: 6px; }
.impact-items ul { padding-left: 18px; margin: 6px 0; }
.impact-table { margin-top: 16px; }
</style>
