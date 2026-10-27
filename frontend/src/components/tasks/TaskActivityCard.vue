<template>
  <el-card shadow="never" class="info-card task-activity-card">
    <section ref="activitySection" aria-label="变更与操作记录">
      <div class="activity-title"><h3>变更与操作记录</h3><span>最新记录在前</span></div>
      <div class="activity-toolbar">
        <el-radio-group v-model="kind" aria-label="记录分类" @change="changeFilter">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="change">订单变更</el-radio-button>
          <el-radio-button value="execution">执行记录</el-radio-button>
        </el-radio-group>
        <el-button text :loading="loading" @click="load">刷新记录</el-button>
      </div>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon>
        <el-button text type="primary" @click="load">重试</el-button>
      </el-alert>
      <div v-loading="loading" class="activity-content" aria-live="polite">
        <el-empty v-if="!events.length && !loading && !error" description="暂无相关记录" :image-size="64" />
        <ol v-if="events.length" class="activity-list" aria-label="任务日志" role="list">
          <li v-for="event in events" :key="event.id" class="activity-entry" :class="{ 'is-order-change': event.kind === 'change' }">
            <div class="activity-time">
              <time v-if="event.occurred_at" :datetime="event.occurred_at">{{ formatDateTimeFull(event.occurred_at) }}</time>
              <span v-else>时间未记录</span>
            </div>
            <div class="activity-body">
              <div class="activity-heading">
                <h4>{{ event.title }}</h4>
                <span class="activity-kind">{{ kindLabel(event.kind) }}</span>
              </div>
              <div class="activity-meta">
                <span>{{ event.actor ? `操作人：${event.actor}` : '操作人未记录' }}</span>
                <span v-if="event.version_no">订单版本 {{ event.version_no }}</span>
              </div>
              <p v-if="event.detail" class="activity-detail">{{ event.detail }}</p>
              <ul v-if="event.changes.length" class="activity-changes" aria-label="前后变化">
                <li v-for="(change, index) in event.changes" :key="index" class="activity-change">
                  <span class="change-label"><span v-if="change.item">{{ change.item }} / </span>{{ change.label }}：</span>
                  <span class="sr-only">修改前：</span><span class="change-before">{{ changeValue(change.before, change.field) }}</span>
                  <span class="change-arrow" aria-hidden="true">→</span>
                  <span class="sr-only">修改后：</span><span class="change-after">{{ changeValue(change.after, change.field) }}</span>
                </li>
              </ul>
              <p v-else-if="event.kind === 'change'" class="activity-hint">本记录未保留涉及当前任务的可展示字段差异。</p>
            </div>
          </li>
        </ol>
      </div>
      <el-pagination v-if="total > pageSize" v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="prev, pager, next" :disabled="loading" @current-change="load" />
    </section>
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
const activitySection = ref<HTMLElement | null>(null)
const loading = ref(false)
const error = ref('')
const events = ref<TaskActivityEvent[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const kind = ref<'all' | 'change' | 'execution'>('all')
let requestVersion = 0

function kindLabel(value: string) {
  return ({ change: '订单变更', operation: '任务操作', item: '明细状态', material: '阶段资料', attachment: '阶段资料', outsource: '外协操作' } as Record<string, string>)[value] || '任务记录'
}
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
  } catch (cause) {
    if (version === requestVersion) error.value = formatApiError(cause, '记录加载失败，请重试')
  } finally {
    if (version === requestVersion) loading.value = false
  }
}
function changeFilter() {
  page.value = 1
  events.value = []
  total.value = 0
  void load()
}
function showOrderChanges() {
  activitySection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  kind.value = 'change'
  changeFilter()
}
defineExpose({ showOrderChanges })
watch(() => [props.taskType, props.taskId, props.refreshKey], () => {
  requestVersion++
  loading.value = false
  events.value = []
  total.value = 0
  error.value = ''
  page.value = 1
  void load()
}, { immediate: true })
onUnmounted(() => { requestVersion++ })
</script>

<style scoped>
.task-activity-card { container-type: inline-size; }
.activity-title { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 12px; line-height: 1.7; }
.activity-title h3 { margin: 0; font-size: 16px; font-weight: 600; }
.activity-title span { font-size: 13px; color: var(--el-text-color-secondary); }
.activity-toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin: 12px 0 20px; }
.activity-hint { margin: 8px 0 0; font-size: 13px; color: var(--el-text-color-secondary); }
.activity-content { min-height: 60px; }
.activity-list { margin: 0; padding: 0; list-style: none; }
.activity-entry { display: grid; grid-template-columns: 156px minmax(0, 1fr); column-gap: 20px; font-size: 14px; line-height: 1.7; }
.activity-time { padding-top: 1px; font-size: 13px; color: var(--el-text-color-regular); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.activity-body { position: relative; min-width: 0; padding: 0 0 24px 24px; border-left: 1px solid var(--el-border-color); }
.activity-body::before { content: ''; position: absolute; top: 7px; left: -5px; width: 7px; height: 7px; border-radius: 50%; background: var(--el-text-color-secondary); border: 1px solid var(--el-bg-color); }
.is-order-change .activity-body::before { background: var(--el-color-primary); }
.activity-entry:last-child .activity-body { border-left-color: transparent; padding-bottom: 4px; }
.activity-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; }
.activity-heading h4 { margin: 0; font-size: 14px; font-weight: 600; color: var(--el-text-color-primary); overflow-wrap: anywhere; }
.activity-kind { padding: 0 6px; border-radius: 3px; background: var(--el-fill-color-light); color: var(--el-text-color-regular); font-size: 12px; }
.is-order-change .activity-kind { background: var(--el-color-primary-light-9); }
.activity-meta { display: flex; flex-wrap: wrap; gap: 0 16px; margin-top: 2px; font-size: 13px; color: var(--el-text-color-regular); overflow-wrap: anywhere; }
.activity-detail { white-space: pre-wrap; overflow-wrap: anywhere; margin: 8px 0 0; color: var(--el-text-color-regular); }
.activity-changes { margin: 8px 0 0; padding: 8px 12px; list-style: none; border-radius: 4px; background: var(--el-fill-color-light); }
.activity-change { white-space: pre-wrap; overflow-wrap: anywhere; color: var(--el-text-color-regular); }
.activity-change + .activity-change { margin-top: 4px; }
.change-label { font-weight: 500; }
.change-arrow { margin: 0 8px; }
.change-after { color: var(--el-text-color-primary); font-weight: 500; }
.el-pagination { margin-top: 20px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@container (max-width: 640px) {
  .activity-entry { grid-template-columns: minmax(0, 1fr); padding-left: 4px; }
  .activity-time { padding: 0 0 4px 20px; border-left: 1px solid var(--el-border-color); }
  .activity-body { padding-left: 20px; }
}
</style>
