<template>
  <el-card shadow="never" class="info-card task-activity-card">
    <details ref="disclosure" @toggle="handleToggle">
      <summary>变更与操作记录<span>订单变更对比、任务执行、资料及外协</span></summary>
      <div class="activity-toolbar">
        <el-radio-group v-model="kind" aria-label="记录分类" @change="changeFilter">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="change">订单变更</el-radio-button>
          <el-radio-button value="execution">执行记录</el-radio-button>
        </el-radio-group>
        <el-button text :loading="loading" @click="load">刷新记录</el-button>
      </div>
      <p class="activity-hint">按已保存的记录展示；历史缺失的时间、操作人及具体变更不会推测补全。</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon>
        <el-button text type="primary" @click="load">重试</el-button>
      </el-alert>
      <div v-loading="loading" class="activity-content" aria-live="polite">
        <el-empty v-if="!events.length && !loading && !error" description="暂无相关记录" :image-size="64" />
        <ol v-if="events.length" class="activity-list">
          <li v-for="event in events" :key="event.id">
            <div class="activity-heading">
              <strong>{{ event.title }}</strong>
              <span>{{ event.occurred_at ? formatDateTimeFull(event.occurred_at) : '时间未记录' }} · {{ event.actor || '操作人未记录' }}</span>
            </div>
            <p v-if="event.detail" class="activity-detail">{{ event.detail }}</p>
            <details v-if="event.changes.length" class="change-disclosure" :open="kind === 'change'">
              <summary>查看 {{ event.changes.length }} 项前后变化<span v-if="event.version_no">订单版本 {{ event.version_no }}</span></summary>
              <div class="change-table-scroll">
                <table class="change-table">
                  <caption class="sr-only">{{ event.title }}的字段变更</caption>
                  <thead><tr><th scope="col">明细 / 字段</th><th scope="col">修改前</th><th scope="col">修改后</th></tr></thead>
                  <tbody><tr v-for="(change, index) in event.changes" :key="index">
                    <th scope="row"><small v-if="change.item">{{ change.item }}</small>{{ change.label }}</th>
                    <td>{{ changeValue(change.before, change.field) }}</td><td>{{ changeValue(change.after, change.field) }}</td>
                  </tr></tbody>
                </table>
              </div>
            </details>
            <p v-else-if="event.kind === 'change'" class="activity-hint">本记录未保留涉及当前任务的可展示字段差异。</p>
          </li>
        </ol>
      </div>
      <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="prev, pager, next" :disabled="loading" @current-change="load" />
    </details>
  </el-card>
</template>

<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { getTaskActivity } from '@/api/tasks'
import type { TaskActivityChange, TaskActivityEvent } from '@/api/tasks'
import type { TaskType } from '@/types/api'
import { formatApiError } from '@/api/requestContract'
import { formatDateTimeFull } from '@/utils/datetime'
import { resolveStatusPresentation } from '@/utils/uiPresentation'

const props = defineProps<{ taskType: TaskType; taskId: string; refreshKey?: number | string }>()
const disclosure = ref<HTMLDetailsElement | null>(null)
const loading = ref(false)
const error = ref('')
const events = ref<TaskActivityEvent[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const kind = ref<'all' | 'change' | 'execution'>('all')
let requestVersion = 0
let loaded = false

function changeValue(value: TaskActivityChange['before'], field: string) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (field === 'status') return resolveStatusPresentation(String(value)).label
  if (field === 'progress_pct') return `${value}%`
  if (field === 'planned_start_at' || field === 'planned_end_at') return formatDateTimeFull(String(value))
  if (field === 'quantity_mode') return ({ quantity: '按数量', area: '按面积' }[String(value)] || String(value))
  return String(value)
}
async function load() {
  const version = ++requestVersion
  loading.value = true
  error.value = ''
  try {
    const response = await getTaskActivity(props.taskType, props.taskId, { page: page.value, page_size: pageSize, kind: kind.value })
    if (version !== requestVersion) return
    events.value = response.items
    total.value = response.total
    loaded = true
  } catch (cause) {
    if (version === requestVersion) error.value = formatApiError(cause, '记录加载失败，请重试')
  } finally {
    if (version === requestVersion) loading.value = false
  }
}
function handleToggle(event: Event) {
  if ((event.target as HTMLDetailsElement).open && !loaded && !loading.value) void load()
}
function changeFilter() {
  page.value = 1
  events.value = []
  total.value = 0
  void load()
}
function showOrderChanges() {
  if (disclosure.value) {
    disclosure.value.open = true
    disclosure.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  kind.value = 'change'
  changeFilter()
}
defineExpose({ showOrderChanges })
watch(() => [props.taskType, props.taskId, props.refreshKey], () => {
  requestVersion++
  loaded = false
  loading.value = false
  events.value = []
  total.value = 0
  error.value = ''
  page.value = 1
  if (disclosure.value?.open) void load()
})
onUnmounted(() => { requestVersion++ })
</script>

<style scoped>
.task-activity-card { container-type: inline-size; }
summary { cursor: pointer; min-height: 32px; line-height: 1.7; font-weight: 600; }
summary span { margin-left: 12px; font-size: 13px; font-weight: 400; color: var(--el-text-color-secondary); }
summary:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 4px; }
.activity-toolbar, .activity-heading { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.activity-toolbar { margin-top: 12px; }
.activity-hint, .activity-heading span { font-size: 13px; color: var(--el-text-color-secondary); }
.activity-content { min-height: 60px; }
.activity-list { margin: 0; padding: 0; list-style: none; }
.activity-list > li { border-top: 1px solid var(--el-border-color-lighter); padding: 16px 0; }
.activity-detail { white-space: pre-wrap; overflow-wrap: anywhere; margin: 8px 0; }
.change-disclosure { margin-top: 8px; }
.change-table-scroll { overflow-x: auto; }
.change-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
.change-table th, .change-table td { text-align: left; padding: 8px; border: 1px solid var(--el-border-color-lighter); white-space: pre-wrap; overflow-wrap: anywhere; }
.change-table thead th { background: var(--el-fill-color-light); }
.change-table small { display: block; color: var(--el-text-color-secondary); font-weight: 400; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media (max-width: 640px) { summary span { display: block; margin-left: 0; } .activity-heading { align-items: flex-start; flex-direction: column; gap: 4px; } }
@container (max-width: 640px) { summary span { display: block; margin-left: 0; } .activity-heading { align-items: flex-start; flex-direction: column; gap: 4px; } }
</style>
