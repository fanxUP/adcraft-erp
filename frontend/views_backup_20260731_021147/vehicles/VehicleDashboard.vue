<template>
  <div class="vehicle-dashboard">
    <!-- 14 项核心指标 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="8" :md="6" v-for="card in overviewCards" :key="card.key">
        <el-card shadow="hover" class="stat-card" :class="card.class">
          <div class="stat-value">{{ overviewData[card.key] ?? '-' }}</div>
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-icon"><el-icon :size="28"><component :is="card.icon" /></el-icon></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <!-- 今日统计 -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header><span>📊 今日统计</span></template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="今日出车">{{ todayData.today_dispatches_count }} 次</el-descriptions-item>
            <el-descriptions-item label="待收车">{{ todayData.pending_return_count }} 辆</el-descriptions-item>
            <el-descriptions-item label="今日异常">{{ todayData.today_incidents_count }} 条</el-descriptions-item>
            <el-descriptions-item label="今日油费">¥{{ todayData.today_fuel_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="其他费用">¥{{ todayData.today_other_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="明日预计用车">{{ todayData.tomorrow_dispatches }} 次</el-descriptions-item>
            <el-descriptions-item label="到期提醒">{{ todayData.reminders_count }} 条</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 本月费用 -->
      <el-col :xs="24" :md="12" style="margin-top: 16px; margin-top: 0;">
        <el-card shadow="hover">
          <template #header><span>💰 本月费用（{{ monthlyData.year }}-{{ String(monthlyData.month).padStart(2, '0') }}）</span></template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="油费">¥{{ monthlyData.fuel_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="维修费">¥{{ monthlyData.maintenance_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="保险年检">¥{{ monthlyData.insurance_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="违章事故">¥{{ monthlyData.incident_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="其他分摊">¥{{ monthlyData.allocation_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="总费用"><strong>¥{{ monthlyData.total_cost?.toFixed(2) }}</strong></el-descriptions-item>
            <el-descriptions-item label="出车次数">{{ monthlyData.dispatch_count }} 次</el-descriptions-item>
            <el-descriptions-item label="总里程">{{ monthlyData.total_mileage }} km</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <!-- 到期提醒 -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header><span>⚠️ 到期提醒</span></template>
          <div v-if="remindersData.insurance.length || remindersData.inspection.length || remindersData.license.length">
            <div v-if="remindersData.insurance.length" class="reminder-section">
              <h4>保险到期</h4>
              <div v-for="r in remindersData.insurance" :key="r.id" class="reminder-item" :class="r.urgency">
                <el-tag :type="urgencyTagType(r.urgency)" size="small">{{ urgencyLabel(r.urgency) }}</el-tag>
                <span class="reminder-text">{{ r.plate_number }} ({{ r.vehicle_name }}) — {{ r.expiry_date?.slice(0, 10) }}</span>
              </div>
            </div>
            <div v-if="remindersData.inspection.length" class="reminder-section">
              <h4>年检到期</h4>
              <div v-for="r in remindersData.inspection" :key="r.id" class="reminder-item" :class="r.urgency">
                <el-tag :type="urgencyTagType(r.urgency)" size="small">{{ urgencyLabel(r.urgency) }}</el-tag>
                <span class="reminder-text">{{ r.plate_number }} ({{ r.vehicle_name }}) — {{ r.expiry_date?.slice(0, 10) }}</span>
              </div>
            </div>
            <div v-if="remindersData.license.length" class="reminder-section">
              <h4>驾驶证到期</h4>
              <div v-for="r in remindersData.license" :key="r.id" class="reminder-item" :class="r.urgency">
                <el-tag :type="urgencyTagType(r.urgency)" size="small">{{ urgencyLabel(r.urgency) }}</el-tag>
                <span class="reminder-text">{{ r.driver_name }} ({{ r.phone }}) — {{ r.license_expiry?.slice(0, 10) }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无到期提醒" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 老板日报 -->
      <el-col :xs="24" :md="12" style="margin-top: 16px; margin-top: 0;">
        <el-card shadow="hover">
          <template #header><span>📋 车辆日报（{{ dailyData.date }}）</span></template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="今日出车">{{ dailyData.today_dispatches }} 次</el-descriptions-item>
            <el-descriptions-item label="安装关联派车">{{ dailyData.install_dispatches }} 次</el-descriptions-item>
            <el-descriptions-item label="今日未收车">{{ dailyData.pending_return }} 辆</el-descriptions-item>
            <el-descriptions-item label="今日车辆异常">{{ dailyData.today_incidents }} 条</el-descriptions-item>
            <el-descriptions-item label="今日油费">¥{{ dailyData.today_fuel_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="其他车辆费用">¥{{ dailyData.today_other_cost?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="明日预计用车">{{ dailyData.tomorrow_dispatches }} 次</el-descriptions-item>
            <el-descriptions-item label="即将到期提醒">{{ dailyData.reminders_count }} 条</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <!-- 单车费用排行 -->
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header><span>🏆 单车费用排行（{{ currentYearMonth }}）</span></template>
          <el-table :data="expenseRanking" size="small" max-height="300" stripe>
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="plate_number" label="车牌号" width="120" />
            <el-table-column prop="fuel_cost" label="油费" width="100" align="right">
              <template #default="{ row }">¥{{ row.fuel_cost.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="maintenance_cost" label="维修费" width="100" align="right">
              <template #default="{ row }">¥{{ row.maintenance_cost.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="total_cost" label="合计" align="right">
              <template #default="{ row }"><strong>¥{{ row.total_cost.toFixed(2) }}</strong></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 司机出车排行 -->
      <el-col :xs="24" :md="12" style="margin-top: 16px; margin-top: 0;">
        <el-card shadow="hover">
          <template #header><span>🏆 司机出车排行（{{ currentYearMonth }}）</span></template>
          <el-table :data="driverRanking" size="small" max-height="300" stripe>
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="driver_name" label="司机" width="100" />
            <el-table-column prop="phone" label="电话" width="130" />
            <el-table-column prop="dispatch_count" label="出车次数" width="100" align="right" />
            <el-table-column prop="total_mileage" label="总里程(km)" align="right">
              <template #default="{ row }">{{ row.total_mileage.toFixed(1) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  Van, Warning, Money, Clock, Document, TrendCharts,
} from '@element-plus/icons-vue'
import {
  getVehicleOverview, getVehicleTodayStats, getVehicleMonthlyCosts,
  getVehicleReminders, getVehicleDailyReport, getVehicleExpenseRanking,
  getVehicleDriverRanking,
  type VehicleOverviewData, type TodayStatsData, type MonthlyCostsData,
  type RemindersData, type DailyReportData, type ExpenseRankingItem,
  type DriverRankingItem,
} from '@/api/vehicles'

const overviewData = ref<VehicleOverviewData>({
  total_vehicles: 0, available_vehicles: 0, in_use_vehicles: 0,
  maintenance_vehicles: 0, disabled_vehicles: 0, today_dispatches: 0,
  pending_return: 0, today_incidents: 0, month_fuel_cost: 0,
  month_maintenance_cost: 0, month_total_cost: 0, expiring_insurance: 0,
  expiring_inspection: 0, expiring_license: 0,
})
const todayData = ref<TodayStatsData>({
  today_dispatches_count: 0, pending_return_count: 0, today_incidents_count: 0,
  today_fuel_cost: 0, today_other_cost: 0, tomorrow_dispatches: 0,
  reminders_count: 0, dispatches: [], pending_returns: [], incidents: [],
})
const monthlyData = ref<MonthlyCostsData>({
  year: 0, month: 0, fuel_cost: 0, maintenance_cost: 0, insurance_cost: 0,
  incident_cost: 0, allocation_cost: 0, total_cost: 0, dispatch_count: 0,
  total_mileage: 0, avg_cost_per_dispatch: 0,
})
const remindersData = ref<RemindersData>({ insurance: [], inspection: [], license: [] })
const dailyData = ref<DailyReportData>({
  date: '', today_dispatches: 0, install_dispatches: 0, pending_return: 0,
  today_incidents: 0, today_fuel_cost: 0, today_other_cost: 0,
  tomorrow_dispatches: 0, reminders_count: 0,
})
const expenseRanking = ref<ExpenseRankingItem[]>([])
const driverRanking = ref<DriverRankingItem[]>([])

const now = new Date()
const currentYearMonth = computed(() => `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)

const overviewCards = [
  { key: 'total_vehicles', label: '车辆总数', icon: Van, class: '' },
  { key: 'available_vehicles', label: '可用车辆', icon: Van, class: 'card-green' },
  { key: 'in_use_vehicles', label: '使用中', icon: Van, class: 'card-blue' },
  { key: 'maintenance_vehicles', label: '维修中', icon: Warning, class: 'card-orange' },
  { key: 'disabled_vehicles', label: '停用车辆', icon: Van, class: 'card-gray' },
  { key: 'today_dispatches', label: '今日出车', icon: TrendCharts, class: 'card-blue' },
  { key: 'pending_return', label: '待收车', icon: Clock, class: 'card-orange' },
  { key: 'today_incidents', label: '今日异常', icon: Warning, class: 'card-red' },
  { key: 'month_fuel_cost', label: '本月油费(元)', icon: Money, class: '' },
  { key: 'month_maintenance_cost', label: '本月维修(元)', icon: Money, class: '' },
  { key: 'month_total_cost', label: '本月总费用(元)', icon: Money, class: 'card-purple' },
  { key: 'expiring_insurance', label: '保险即将到期', icon: Document, class: 'card-orange' },
  { key: 'expiring_inspection', label: '年检即将到期', icon: Document, class: 'card-orange' },
  { key: 'expiring_license', label: '驾驶证即将到期', icon: Document, class: 'card-orange' },
]

function urgencyTagType(urgency: string) {
  if (urgency === 'expired') return 'danger'
  if (urgency === 'urgent') return 'warning'
  return 'info'
}
function urgencyLabel(urgency: string) {
  if (urgency === 'expired') return '已过期'
  if (urgency === 'urgent') return '紧急'
  return '即将'
}

onMounted(async () => {
  const [overview, today, monthly, reminders, daily, expense, driver] = await Promise.all([
    getVehicleOverview(),
    getVehicleTodayStats(),
    getVehicleMonthlyCosts(),
    getVehicleReminders(),
    getVehicleDailyReport(),
    getVehicleExpenseRanking({ year: now.getFullYear(), month: now.getMonth() + 1 }),
    getVehicleDriverRanking({ year: now.getFullYear(), month: now.getMonth() + 1 }),
  ])
  if (overview) overviewData.value = overview
  if (today) todayData.value = today
  if (monthly) monthlyData.value = monthly
  if (reminders) remindersData.value = reminders
  if (daily) dailyData.value = daily
  if (expense) expenseRanking.value = expense
  if (driver) driverRanking.value = driver
})
</script>
<style scoped>
.vehicle-dashboard { padding: 0; }
.stat-row .el-col { margin-bottom: 16px; }
.stat-card {
  position: relative;
  overflow: hidden;
  text-align: center;
  padding: 20px 0;
}
.stat-card .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}
.stat-card .stat-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.stat-card .stat-icon {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.15;
}
.card-green .stat-value { color: #67c23a; }
.card-blue .stat-value { color: #409eff; }
.card-orange .stat-value { color: #e6a23c; }
.card-red .stat-value { color: #f56c6c; }
.card-gray .stat-value { color: #909399; }
.card-purple .stat-value { color: #9b59b6; }
.reminder-section { margin-bottom: 12px; }
.reminder-section h4 { margin: 0 0 6px; font-size: 14px; color: var(--el-text-color-primary); }
.reminder-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; }
.reminder-text { color: var(--el-text-color-regular); }
.reminder-item.expired .reminder-text { color: #f56c6c; text-decoration: line-through; }
.reminder-item.urgent .reminder-text { color: #e6a23c; font-weight: 600; }
</style>
