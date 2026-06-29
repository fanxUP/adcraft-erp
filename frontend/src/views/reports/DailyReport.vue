<template>
  <div class="page">
    <div class="page-header">
      <h2>销售日报</h2>
      <div style="display: flex; gap: 12px; align-items: center">
        <el-date-picker v-model="reportDate" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" @change="fetchData" />
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>
    </div>

    <el-row :gutter="16" style="margin-bottom: 16px" v-loading="loading">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">日期</div>
          <div class="stat-value-date">{{ data.date }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">订单数 / 金额</div>
          <div class="stat-value">{{ data.order_count }} 单 / ¥ {{ data.order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">收款笔数 / 金额</div>
          <div class="stat-value" style="color: #22c55e">{{ data.payment_count }} 笔 / ¥ {{ data.payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">新增客户</div>
          <div class="stat-value">{{ data.new_customer_count }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
      <template #header><span>当日订单</span></template>
      <el-table :data="data.orders || []" stripe size="small">
        <el-table-column prop="order_no" label="订单编号" width="180" />
        <el-table-column prop="project_name" label="项目名称" min-width="200" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="orderStatusColor(row.status)" size="small">{{ orderStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!data.orders?.length" style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无订单</div>
    </el-card>

    <el-card shadow="never" class="info-card">
      <template #header><span>当日收款</span></template>
      <el-table :data="data.payments || []" stripe size="small">
        <el-table-column prop="payment_no" label="收款编号" width="180" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="payment_method" label="方式" width="100" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_voided ? 'danger' : 'success'" size="small">{{ row.is_voided ? '作废' : '有效' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!data.payments?.length" style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无收款</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getDailyReport } from '@/api/payments'

const loading = ref(false)
const reportDate = ref('')
const data = reactive({ date: '', order_count: 0, order_amount: 0, payment_count: 0, payment_amount: 0, new_customer_count: 0, orders: [] as any[], payments: [] as any[] })

function orderStatusLabel(s: string) {
  const map: Record<string, string> = { pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function orderStatusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', completed: 'success', cancelled: 'danger' }
  return map[s] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const d = await getDailyReport(reportDate.value || undefined)
    Object.assign(data, d)
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.stat-card { background: var(--ad-card); border: 1px solid var(--ad-border); text-align: center; padding: 12px 0; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 6px; }
.stat-value { font-size: 16px; font-weight: bold; color: var(--ad-text); margin-top: 4px; }
.stat-value-date { font-size: 20px; font-weight: bold; color: var(--ad-text); margin-top: 4px; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
</style>
