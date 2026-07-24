<template>
  <div class="page">
    <h2 style="margin-bottom: 16px">高空车统计报表</h2>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- 月度统计 -->
      <el-tab-pane label="月度统计" name="monthly">
        <el-form :inline="true" style="margin-bottom: 16px">
          <el-form-item label="月份"><el-date-picker v-model="month" type="month" value-format="YYYY-MM" /></el-form-item>
          <el-button type="primary" @click="loadMonthly">查询</el-button>
        </el-form>
        <el-row :gutter="16" v-if="monthlyData">
          <el-col :span="6" v-for="card in monthlyCards" :key="card.label" style="margin-bottom: 12px">
            <el-card shadow="hover" body-style="padding: 16px">
              <div style="font-size: 13px; color: #909399">{{ card.label }}</div>
              <div style="font-size: 22px; font-weight: 700; margin-top: 4px" :style="{ color: card.color || '#303133' }">{{ card.value }}</div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 待收款 -->
      <el-tab-pane label="待收款" name="receivables">
        <el-table :data="receivables.items || []" stripe v-loading="loading">
          <el-table-column prop="work_date" label="日期" width="100" />
          <el-table-column prop="customer_name" label="客户" width="120" />
          <el-table-column prop="work_location" label="地点" width="140" />
          <el-table-column prop="final_amount" label="应收" width="90" align="right"><template #default="{ row }">¥{{ row.final_amount }}</template></el-table-column>
          <el-table-column prop="received_amount" label="实收" width="90" align="right"><template #default="{ row }">¥{{ row.received_amount }}</template></el-table-column>
          <el-table-column prop="unpaid_amount" label="未收" width="90" align="right"><template #default="{ row }"><span style="color: #f56c6c">¥{{ row.unpaid_amount }}</span></template></el-table-column>
        </el-table>
        <div style="margin-top: 12px; font-weight: 600">待收总额：¥{{ receivables.total_unpaid || 0 }}</div>
      </el-tab-pane>

      <!-- 待报销 -->
      <el-tab-pane label="待报销" name="reimbursements">
        <h4>待审核垫付</h4>
        <el-table :data="reimbursements.pending_review || []" stripe v-loading="loading" size="small" style="margin-bottom: 20px">
          <el-table-column prop="expense_date" label="日期" width="100" />
          <el-table-column prop="driver_name" label="驾驶员" width="80" />
          <el-table-column prop="expense_type" label="类型" width="80" />
          <el-table-column prop="amount" label="金额" width="80" align="right"><template #default="{ row }">¥{{ row.amount }}</template></el-table-column>
          <el-table-column prop="description" label="说明" min-width="150" />
        </el-table>
        <h4>待报销垫付</h4>
        <el-table :data="reimbursements.pending_reimbursement || []" stripe v-loading="loading" size="small">
          <el-table-column prop="expense_date" label="日期" width="100" />
          <el-table-column prop="driver_name" label="驾驶员" width="80" />
          <el-table-column prop="expense_type" label="类型" width="80" />
          <el-table-column prop="amount" label="金额" width="80" align="right"><template #default="{ row }">¥{{ row.amount }}</template></el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 费用分类 -->
      <el-tab-pane label="费用分类" name="costs">
        <el-form :inline="true" style="margin-bottom: 16px">
          <el-form-item label="月份"><el-date-picker v-model="costMonth" type="month" value-format="YYYY-MM" clearable /></el-form-item>
          <el-button type="primary" @click="loadCosts">查询</el-button>
        </el-form>
        <el-table :data="costData" stripe v-loading="loading">
          <el-table-column prop="cost_type" label="费用类型" width="150"><template #default="{ row }">{{ costTypeLabel(row.cost_type) }}</template></el-table-column>
          <el-table-column prop="total" label="金额" width="120" align="right"><template #default="{ row }">¥{{ row.total }}</template></el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 驾驶员汇总 -->
      <el-tab-pane label="驾驶员汇总" name="drivers">
        <el-form :inline="true" style="margin-bottom: 16px">
          <el-form-item label="月份"><el-date-picker v-model="driverMonth" type="month" value-format="YYYY-MM" /></el-form-item>
          <el-button type="primary" @click="loadDrivers">查询</el-button>
        </el-form>
        <el-table :data="driverData" stripe v-loading="loading">
          <el-table-column prop="driver_name" label="驾驶员" width="120" />
          <el-table-column prop="trip_count" label="出车趟数" width="90" />
          <el-table-column prop="receivable" label="应收" width="100" align="right"><template #default="{ row }">¥{{ row.receivable }}</template></el-table-column>
          <el-table-column prop="received" label="实收" width="100" align="right"><template #default="{ row }">¥{{ row.received }}</template></el-table-column>
          <el-table-column prop="wages" label="工资" width="100" align="right"><template #default="{ row }">¥{{ row.wages }}</template></el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getAerialReportMonthly, getAerialReportReceivables, getAerialReportReimbursements,
  getAerialReportCosts, getAerialReportDriverSummary,
} from '@/api/aerial'

const loading = ref(false)
const activeTab = ref('monthly')
const month = ref(new Date().toISOString().slice(0, 7))
const costMonth = ref('')
const driverMonth = ref(new Date().toISOString().slice(0, 7))

const monthlyData = ref<any>(null)
const receivables = ref<any>({})
const reimbursements = ref<any>({})
const costData = ref<any[]>([])
const driverData = ref<any[]>([])

const monthlyCards = computed(() => {
  const d = monthlyData.value || {}
  return [
    { label: '出车天数', value: d.work_days || 0, color: '#409eff' },
    { label: '出车趟数', value: d.trip_count || 0 },
    { label: '应收金额', value: `¥${d.receivable || 0}` },
    { label: '实收金额', value: `¥${d.received || 0}` },
    { label: '待收金额', value: `¥${d.unpaid || 0}`, color: (d.unpaid || 0) > 0 ? '#f56c6c' : '#909399' },
    { label: '驾驶员工资', value: `¥${d.wages || 0}` },
    { label: '报 销', value: `¥${d.reimbursements || 0}` },
    { label: '车辆费用', value: `¥${d.vehicle_costs || 0}` },
    { label: '毛利润', value: `¥${d.gross_profit || 0}`, color: (d.gross_profit || 0) >= 0 ? '#67c23a' : '#f56c6c' },
    { label: '平均趟收入', value: `¥${d.avg_trip_revenue || 0}` },
    { label: '平均趟利润', value: `¥${d.avg_trip_profit || 0}` },
  ]
})

async function loadMonthly() {
  if (!month.value) return
  loading.value = true
  try { monthlyData.value = await getAerialReportMonthly(month.value) }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function loadReceivables() {
  loading.value = true
  try { receivables.value = await getAerialReportReceivables({ page_size: 100 }) }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function loadReimbursements() {
  loading.value = true
  try { reimbursements.value = await getAerialReportReimbursements() }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function loadCosts() {
  loading.value = true
  try { costData.value = await getAerialReportCosts(costMonth.value || undefined) || [] }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function loadDrivers() {
  if (!driverMonth.value) return
  loading.value = true
  try { driverData.value = await getAerialReportDriverSummary(driverMonth.value) || [] }
  catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

function handleTabChange(tab: string) {
  if (tab === 'monthly') loadMonthly()
  else if (tab === 'receivables') loadReceivables()
  else if (tab === 'reimbursements') loadReimbursements()
  else if (tab === 'costs') loadCosts()
  else if (tab === 'drivers') loadDrivers()
}

function costTypeLabel(t: string) {
  const m: Record<string, string> = { fuel: '油费', maintenance: '维修费', insurance: '保险费', inspection: '年检费', violation: '违章罚款', tire: '轮胎', hydraulic_system: '液压系统', boom_repair: '升降臂维修', platform_repair: '平台维修', safety_equipment: '安全用品', tool_consumables: '工具耗材', parking: '停车费', loan: '贷款/月供', depreciation: '折旧', other: '其他' }
  return m[t] || t
}

onMounted(loadMonthly)
</script>

<style scoped>.page-header { margin-bottom: 16px; }</style>
