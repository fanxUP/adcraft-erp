<template>
  <div class="aerial-dashboard">
    <h2>高空作业车看板</h2>

    <!-- KPI 卡片 -->
    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :xs="12" :sm="8" :md="6" v-for="card in overviewCards" :key="card.label" style="margin-bottom: 12px">
        <el-card shadow="hover" body-style="padding: 16px">
          <div style="font-size: 13px; color: #909399; margin-bottom: 8px">{{ card.label }}</div>
          <div style="font-size: 24px; font-weight: 700" :style="{ color: card.color || '#303133' }">
            {{ card.value }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 今日出车台账 -->
      <el-col :span="16" style="margin-bottom: 20px">
        <el-card>
          <template #header><span style="font-weight: 600">今日出车台账</span></template>
          <el-table :data="todayLedgers" stripe size="small" v-loading="loading">
            <el-table-column prop="work_date" label="日期" width="100" />
            <el-table-column prop="ledger_no" label="台账编号" width="150" />
            <el-table-column prop="driver_name" label="驾驶员" width="80" />
            <el-table-column prop="customer_name" label="客户" width="120" />
            <el-table-column prop="work_location" label="作业地点" min-width="120" />
            <el-table-column prop="receivable_amount" label="应收" width="80" align="right">
              <template #default="{ row }">¥{{ row.receivable_amount }}</template>
            </el-table-column>
            <el-table-column prop="received_amount" label="实收" width="80" align="right">
              <template #default="{ row }">¥{{ row.received_amount }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && todayLedgers.length === 0" description="今日暂无出车记录" />
        </el-card>
      </el-col>

      <!-- 提醒 -->
      <el-col :span="8" style="margin-bottom: 20px">
        <el-card>
          <template #header><span style="font-weight: 600">到期提醒</span></template>
          <div v-if="reminders.length === 0" style="color: #909399; text-align: center; padding: 20px">暂无提醒</div>
          <div v-for="r in reminders" :key="r.type + r.plate" style="padding: 8px 0; border-bottom: 1px solid #f0f0f0">
            <el-tag :type="r.urgent ? 'danger' : 'warning'" size="small" style="margin-right: 8px">
              {{ r.type === 'insurance' ? '保险' : r.type === 'inspection' ? '年检' : '保养' }}
            </el-tag>
            <span>{{ r.vehicle }} ({{ r.plate }})</span>
            <div style="font-size: 12px; color: #909399; margin-top: 4px">
              {{ r.expire_date || r.due_date }} · 剩余 {{ r.days_left }} 天
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getAerialDashboardOverview,
  getAerialDashboardToday,
  getAerialDashboardReminders,
} from '@/api/aerial'

const loading = ref(false)
const overview = ref<any>({ today: {}, monthly: {} })
const todayLedgers = ref<any[]>([])
const reminders = ref<any[]>([])

const overviewCards = computed(() => {
  const t = overview.value.today || {}
  const m = overview.value.monthly || {}
  return [
    { label: '今日出车', value: t.trip_count || 0, color: '#409eff' },
    { label: '今日应收', value: `¥${t.receivable || 0}`, color: '#67c23a' },
    { label: '今日实收', value: `¥${t.received || 0}` },
    { label: '今日待收', value: `¥${t.unpaid || 0}`, color: t.unpaid > 0 ? '#f56c6c' : '#909399' },
    { label: '今日工资', value: `¥${t.wages || 0}` },
    { label: '今日报销', value: `¥${t.reimbursements || 0}` },
    { label: '今日车辆费', value: `¥${t.vehicle_costs || 0}` },
    { label: '今日毛利', value: `¥${t.gross_profit || 0}`, color: (t.gross_profit || 0) >= 0 ? '#67c23a' : '#f56c6c' },
    { label: '本月应收', value: `¥${m.receivable || 0}`, color: '#409eff' },
    { label: '本月实收', value: `¥${m.received || 0}` },
    { label: '本月待收', value: `¥${m.unpaid || 0}`, color: m.unpaid > 0 ? '#f56c6c' : '#909399' },
    { label: '本月毛利', value: `¥${m.gross_profit || 0}`, color: (m.gross_profit || 0) >= 0 ? '#67c23a' : '#f56c6c' },
  ]
})

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: '草稿', assigned: '已派', started: '已出发', working: '作业中',
    completed: '已完成', returned: '已收车', reviewed: '已审核', settled: '已结算',
    cancelled: '已作废', abnormal: '异常',
  }
  return map[s] || s
}

function statusTagType(s: string) {
  const map: Record<string, string> = {
    draft: 'info', cancelled: 'info', abnormal: 'danger', reviewed: 'success', settled: 'success',
  }
  return map[s] || ''
}

async function loadData() {
  loading.value = true
  try {
    const [ov, today, rem] = await Promise.all([
      getAerialDashboardOverview(),
      getAerialDashboardToday(),
      getAerialDashboardReminders(),
    ])
    overview.value = ov || { today: {}, monthly: {} }
    todayLedgers.value = today || []
    reminders.value = rem || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.aerial-dashboard { padding: 0; }
</style>
