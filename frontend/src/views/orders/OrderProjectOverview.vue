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
          <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
        </div>
      </template>
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

const props = defineProps<{
  orderId: string
  status: string
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
}>()

defineEmits<{
  'select-tab': [tab: string]
}>()

const labels: Record<string, string> = {
  pending_confirm: '待确认',
  confirmed: '已确认',
  designing: '设计中',
  in_production: '生产中',
  in_installation: '安装中',
  completed: '已完成',
  cancelled: '已取消',
}

const statusLabel = computed(() => labels[props.status] || props.status)
const statusType = computed(() => {
  if (props.status === 'completed') return 'success'
  if (props.status === 'cancelled') return 'danger'
  return 'primary'
})

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
