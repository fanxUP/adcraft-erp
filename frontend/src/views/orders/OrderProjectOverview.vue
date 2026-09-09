<template>
  <div class="project-overview">
    <div class="metric-grid">
      <el-card v-for="metric in metrics" :key="metric.label" shadow="never">
        <div class="metric-label">{{ metric.label }}</div>
        <div class="metric-value" :class="metric.className">{{ metric.value }}</div>
      </el-card>
    </div>

    <el-card shadow="never" class="shortcut-card">
      <template #header>
        <div class="card-header">
          <strong>项目工作台</strong>
          <StatusTag :status="statusView || status" size="sm" />
        </div>
      </template>
      <div class="overall-progress">
        <ProgressBar :percentage="projectProgress" label="项目总进度" aria-label="项目总进度" />
        <div class="progress-note">按每条订单明细的设计、制作、安装三阶段进度汇总；历史未关联明细任务按任务进度回退计算</div>
      </div>
      <el-alert
        v-if="overdueTaskCount > 0"
        class="overdue-summary"
        type="error"
        :closable="false"
        show-icon
        :title="`${overdueTaskCount} 个任务已超过计划结束时间`"
      />
      <el-divider />
      <div class="delivery-summary">
        <div>
          <span>设计任务</span>
          <strong>{{ designCompleted }}/{{ designCount }}</strong>
        </div>
        <div>
          <span>制作任务</span>
          <strong>{{ productionCompleted }}/{{ productionCount }}</strong>
        </div>
        <div>
          <span>安装任务</span>
          <strong>{{ installationCompleted }}/{{ installationCount }}</strong>
        </div>
      </div>
      <el-divider />
      <div class="shortcuts">
        <el-button @click="$emit('select-tab', 'tasks')">查看交付任务</el-button>
        <el-button @click="$router.push('/acceptances')">验收管理</el-button>
        <el-button @click="$router.push(`/project-costs/${orderId}`)">成本台账</el-button>
        <el-button @click="$router.push('/receivables')">收款与对账</el-button>
        <el-button @click="$router.push('/contracts')">关联合同</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ProgressBar, StatusTag } from '@/components/ui'
import type { StatusView } from '@/types/api'

const props = defineProps<{
  orderId: string
  status: string
  statusView?: StatusView | null
  totalAmount: number
  paidAmount: number
  costAmount: number
  grossProfit: number
  designCount: number
  designCompleted: number
  productionCount: number
  productionCompleted: number
  installationCount: number
  installationCompleted: number
  overdueTaskCount: number
  projectProgress: number
}>()

defineEmits<{
  'select-tab': [tab: string]
}>()

const money = (value: number) => `¥ ${value.toFixed(2)}`
const metrics = computed(() => [
  { label: '订单金额', value: money(props.totalAmount), className: '' },
  { label: '已收金额', value: money(props.paidAmount), className: 'success' },
  { label: '项目成本', value: money(props.costAmount), className: '' },
  {
    label: '项目毛利',
    value: money(props.grossProfit),
    className: props.grossProfit >= 0 ? 'success' : 'danger',
  },
])
</script>

<style scoped>
.project-overview { margin-bottom: 16px; }
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.metric-label { color: var(--ad-text-secondary); font-size: 13px; }
.metric-value { color: var(--ad-text); font-size: 22px; font-weight: 700; margin-top: 8px; }
.metric-value.success { color: var(--el-color-success); }
.metric-value.danger { color: var(--el-color-danger); }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.delivery-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.overall-progress { padding: 10px 12px 0; }
.overdue-summary { margin-top: 12px; }
.progress-note { margin-top: 6px; color: var(--ad-text-secondary); font-size: 12px; }
.delivery-summary > div {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--ad-darker);
}
.delivery-summary span { color: var(--ad-text-secondary); }
.shortcuts { display: flex; flex-wrap: wrap; gap: 8px; }
@media (max-width: 900px) {
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
  .delivery-summary { grid-template-columns: 1fr; }
}
</style>
