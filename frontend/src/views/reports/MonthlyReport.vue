<template>
  <div class="page">
    <div class="page-header">
      <h2>销售月报</h2>
      <div style="display: flex; gap: 12px; align-items: center">
        <el-select v-model="reportYear" style="width: 100px" @change="fetchData">
          <el-option v-for="y in years" :key="y" :label="String(y)" :value="y" />
        </el-select>
        <span style="color: var(--ad-text)">年</span>
        <el-select v-model="reportMonth" style="width: 80px" @change="fetchData">
          <el-option v-for="m in 12" :key="m" :label="String(m)" :value="m" />
        </el-select>
        <span style="color: var(--ad-text)">月</span>
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>
    </div>

    <el-row :gutter="16" style="margin-bottom: 16px" v-loading="loading">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">订单数</div>
          <div class="stat-value">{{ data.order_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">订单金额</div>
          <div class="stat-value">¥ {{ data.order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">收款金额</div>
          <div class="stat-value" style="color: #22c55e">¥ {{ data.payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">未收金额</div>
          <div class="stat-value" style="color: #e63946">¥ {{ data.unpaid_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
      <template #header><span>订单状态分布</span></template>
      <div v-if="Object.keys(data.status_breakdown || {}).length" style="display: flex; gap: 16px; flex-wrap: wrap; padding: 8px 0">
        <el-tag v-for="(count, status) in data.status_breakdown" :key="status" :type="orderStatusColor(status as string)" size="large">
          {{ orderStatusLabel(status as string) }}: {{ count }}
        </el-tag>
      </div>
      <div v-else style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无数据</div>
    </el-card>

    <el-card shadow="never" class="info-card">
      <template #header><span>订单明细</span></template>
      <el-table :data="data.orders || []" stripe size="small">
        <el-table-column prop="order_no" label="订单编号" width="180" />
        <el-table-column prop="project_name" label="项目名称" min-width="200" />
        <el-table-column label="订单金额" width="120">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="已收" width="120">
          <template #default="{ row }">¥ {{ row.paid_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="未收" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.unpaid_amount > 0 ? '#e63946' : '#22c55e' }">¥ {{ row.unpaid_amount?.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="orderStatusColor(row.status)" size="small">{{ orderStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!data.orders?.length" style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无订单</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getMonthlyReport } from '@/api/payments'
import type { MonthlyReportOrder } from '@/types/api'

const loading = ref(false)
const now = new Date()
const reportYear = ref(now.getFullYear())
const reportMonth = ref(now.getMonth() + 1)
const years = Array.from({ length: 5 }, (_, i) => now.getFullYear() - 2 + i)
const data = reactive({ year: 0, month: 0, order_count: 0, order_amount: 0, payment_count: 0, payment_amount: 0, unpaid_amount: 0, status_breakdown: {} as Record<string, number>, orders: [] as MonthlyReportOrder[] })

function orderStatusLabel(s: string) {
  const map: Record<string, string> = { pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function orderStatusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const d = await getMonthlyReport(reportYear.value, reportMonth.value)
    Object.assign(data, d)
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.stat-card { background: var(--ad-card); border: 1px solid var(--ad-border); text-align: center; padding: 12px 0; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 6px; }
.stat-value { font-size: 22px; font-weight: bold; color: var(--ad-text); margin-top: 4px; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
</style>
