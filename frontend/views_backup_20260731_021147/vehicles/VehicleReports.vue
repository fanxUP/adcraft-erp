<template>
  <div class="vehicle-reports">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="selectedYear" placeholder="年份" style="width: 120px" @change="loadAll">
        <el-option v-for="y in yearOptions" :key="y" :label="y + '年'" :value="y" />
      </el-select>
      <el-select v-model="selectedMonth" placeholder="月份" style="width: 120px" @change="loadAll" clearable>
        <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="m" />
      </el-select>
      <el-button type="primary" @click="loadAll" :icon="Refresh">刷新</el-button>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #409eff">
              <el-icon size="24"><Van /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ overview.total_vehicles }}</div>
              <div class="stat-label">车辆总数</div>
            </div>
          </div>
          <div class="stat-sub">可用: {{ overview.available_vehicles }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon size="24"><Odometer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ overview.month_dispatches }}</div>
              <div class="stat-label">本月出车</div>
            </div>
          </div>
          <div class="stat-sub">里程: {{ overview.month_mileage }} km</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon size="24"><Money /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">¥{{ formatMoney(overview.month_total_cost) }}</div>
              <div class="stat-label">本月总费用</div>
            </div>
          </div>
          <div class="stat-sub">油费: ¥{{ formatMoney(overview.month_fuel_cost) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon size="24"><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">¥{{ formatMoney(overview.avg_cost_per_km) }}</div>
              <div class="stat-label">每公里成本</div>
            </div>
          </div>
          <div class="stat-sub">每次出车: ¥{{ formatMoney(overview.avg_cost_per_dispatch) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 费用明细统计 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="4">
        <el-card shadow="hover" class="mini-stat">
          <div class="mini-value">¥{{ formatMoney(overview.month_fuel_cost) }}</div>
          <div class="mini-label">油费</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="mini-stat">
          <div class="mini-value">¥{{ formatMoney(overview.month_maintenance_cost) }}</div>
          <div class="mini-label">维修费</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="mini-stat">
          <div class="mini-value">¥{{ formatMoney(overview.month_insurance_cost) }}</div>
          <div class="mini-label">保险年检</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="mini-stat">
          <div class="mini-value">¥{{ formatMoney(overview.month_incident_cost) }}</div>
          <div class="mini-label">违章事故</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="mini-stat">
          <div class="mini-value">¥{{ formatMoney(overview.month_allocation_cost) }}</div>
          <div class="mini-label">其他分摊</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 车辆费用排名 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>车辆费用排名</span>
        </div>
      </template>
      <el-table :data="vehicleCosts" stripe max-height="400">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="vehicle_name" label="车辆" width="150" />
        <el-table-column prop="plate_number" label="车牌" width="120" />
        <el-table-column prop="fuel_cost" label="油费" width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.fuel_cost) }}</template>
        </el-table-column>
        <el-table-column prop="maintenance_cost" label="维修" width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.maintenance_cost) }}</template>
        </el-table-column>
        <el-table-column prop="insurance_cost" label="保险年检" width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.insurance_cost) }}</template>
        </el-table-column>
        <el-table-column prop="incident_cost" label="违章事故" width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.incident_cost) }}</template>
        </el-table-column>
        <el-table-column prop="total_cost" label="总费用" width="120" align="right">
          <template #default="{ row }">
            <span style="font-weight: bold; color: #f56c6c">¥{{ formatMoney(row.total_cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dispatch_count" label="出车次数" width="90" align="center" />
        <el-table-column prop="total_mileage" label="总里程(km)" width="110" align="right">
          <template #default="{ row }">{{ row.total_mileage.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column prop="avg_cost_per_km" label="每公里" width="90" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.avg_cost_per_km) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-row :gutter="16">
      <!-- 司机出车统计 -->
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>司机出车统计</span>
            </div>
          </template>
          <el-table :data="driverStats" stripe max-height="350">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="driver_name" label="司机" width="100" />
            <el-table-column prop="phone" label="手机号" width="120" />
            <el-table-column prop="dispatch_count" label="出车次数" width="90" align="center">
              <template #default="{ row }">
                <el-tag type="primary">{{ row.dispatch_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_mileage" label="总里程(km)" align="right">
              <template #default="{ row }">{{ row.total_mileage.toFixed(1) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 费用类型分析 -->
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>费用类型分析</span>
            </div>
          </template>
          <el-table :data="costTypes" stripe max-height="350">
            <el-table-column prop="cost_type" label="费用类型" width="150">
              <template #default="{ row }">
                <el-tag :type="costTypeTag(row.cost_type)">{{ costTypeLabel(row.cost_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" align="right">
              <template #default="{ row }">
                <span style="font-weight: bold">¥{{ formatMoney(row.amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="占比" width="120" align="center">
              <template #default="{ row }">
                <el-progress
                  :percentage="costTypePercent(row.amount)"
                  :stroke-width="12"
                  :text-inside="true"
                  :format="() => costTypePercent(row.amount) + '%'"
                />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 月度里程趋势 -->
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>{{ selectedYear }}年 月度里程趋势</span>
            </div>
          </template>
          <el-table :data="mileageStats" stripe>
            <el-table-column prop="month" label="月份" width="80">
              <template #default="{ row }">{{ row.month }}月</template>
            </el-table-column>
            <el-table-column prop="dispatch_count" label="出车次数" width="100" align="center" />
            <el-table-column prop="total_mileage" label="总里程(km)" align="right">
              <template #default="{ row }">{{ row.total_mileage.toFixed(1) }}</template>
            </el-table-column>
            <el-table-column label="里程占比" width="180">
              <template #default="{ row }">
                <el-progress
                  :percentage="mileagePercent(row.total_mileage)"
                  :stroke-width="14"
                  :show-text="false"
                />
                <span style="font-size: 12px; color: #909399">{{ mileagePercent(row.total_mileage) }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 派车状态分布 -->
      <el-col :span="12">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>派车状态分布</span>
            </div>
          </template>
          <el-table :data="dispatchStats.by_status" stripe>
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="dispatchStatusType(row.status)">{{ dispatchStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="数量" align="center">
              <template #default="{ row }">
                <span style="font-weight: bold; font-size: 16px">{{ row.count }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="dispatchStats.by_reason.length" style="margin-top: 16px">
            <div style="font-weight: bold; margin-bottom: 8px; color: #606266">按用途分布</div>
            <el-table :data="dispatchStats.by_reason" stripe size="small">
              <el-table-column prop="reason" label="用途" width="120">
                <template #default="{ row }">{{ reasonLabel(row.reason) }}</template>
              </el-table-column>
              <el-table-column prop="count" label="数量" align="center" />
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 订单车辆成本 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>订单车辆运输成本</span>
        </div>
      </template>
      <el-table :data="orderCosts" stripe max-height="350">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="order_id" label="订单ID" width="280">
          <template #default="{ row }">
            <span style="font-family: monospace; font-size: 12px">{{ row.order_id.substring(0, 8) }}...</span>
          </template>
        </el-table-column>
        <el-table-column prop="dispatch_count" label="派车次数" width="100" align="center" />
        <el-table-column prop="total_mileage" label="总里程(km)" width="120" align="right">
          <template #default="{ row }">{{ row.total_mileage.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column prop="allocated_cost" label="已分摊费用" width="140" align="right">
          <template #default="{ row }">
            <span style="font-weight: bold; color: #e6a23c">¥{{ formatMoney(row.allocated_cost) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!orderCosts.length" description="暂无订单车辆成本数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh, Van, Odometer, Money, TrendCharts } from '@element-plus/icons-vue'
import {
  getVehicleReportOverview,
  getVehicleCosts,
  getDriverStats,
  getMileageStats,
  getDispatchReportStats,
  getOrderVehicleCosts,
  getCostByType,
  type VehicleReportOverview,
  type VehicleCostItem,
  type DriverStatItem,
  type MileageStatItem,
  type DispatchStats as DispatchStatsType,
  type OrderCostItem,
  type CostTypeItem,
} from '@/api/vehicles'

const now = new Date()
const selectedYear = ref(now.getFullYear())
const selectedMonth = ref(now.getMonth() + 1)

const yearOptions = computed(() => {
  const years = []
  for (let y = now.getFullYear(); y >= now.getFullYear() - 3; y--) years.push(y)
  return years
})

const overview = ref<VehicleReportOverview>({
  total_vehicles: 0, available_vehicles: 0,
  month_dispatches: 0, month_mileage: 0,
  month_fuel_cost: 0, month_maintenance_cost: 0, month_insurance_cost: 0,
  month_incident_cost: 0, month_allocation_cost: 0, month_total_cost: 0,
  avg_cost_per_dispatch: 0, avg_cost_per_km: 0,
  year: now.getFullYear(), month: now.getMonth() + 1,
})
const vehicleCosts = ref<VehicleCostItem[]>([])
const driverStats = ref<DriverStatItem[]>([])
const mileageStats = ref<MileageStatItem[]>([])
const dispatchStats = ref<DispatchStatsType>({ by_status: [], by_reason: [] })
const orderCosts = ref<OrderCostItem[]>([])
const costTypes = ref<CostTypeItem[]>([])

const formatMoney = (v: number) => v != null ? v.toFixed(2) : '0.00'

const costTypeLabel = (t: string) => {
  const m: Record<string, string> = {
    fuel: '油费', toll: '过路费', parking: '停车费', repair: '维修', maintenance: '保养',
    insurance: '保险', inspection: '年检', violation: '违章', accident: '事故',
    tire: '轮胎', battery: '电池', wash: '洗车', rent: '外租', driver_subsidy: '司机补贴', other: '其他',
  }
  return m[t] || t
}

const costTypeTag = (t: string) => {
  const m: Record<string, string> = {
    fuel: 'warning', maintenance: 'danger', insurance: '', inspection: '',
    violation: 'danger', accident: 'danger', rent: 'info',
  }
  return m[t] || 'info'
}

const totalCostAmount = computed(() => costTypes.value.reduce((s, r) => s + r.amount, 0))
const costTypePercent = (amount: number) => totalCostAmount.value ? Math.round(amount / totalCostAmount.value * 100) : 0

const totalMileage = computed(() => mileageStats.value.reduce((s, r) => s + r.total_mileage, 0))
const mileagePercent = (v: number) => totalMileage.value ? Math.round(v / totalMileage.value * 100) : 0

const dispatchStatusLabel = (s: string) => {
  const m: Record<string, string> = {
    assigned: '待出车', started: '已出车', arrived: '已到达', completed: '已完成',
    returned: '已收车', cancelled: '已取消', abnormal: '异常',
  }
  return m[s] || s
}

const dispatchStatusType = (s: string) => {
  const m: Record<string, string> = {
    assigned: 'info', started: 'primary', arrived: 'warning', completed: 'success',
    returned: 'success', cancelled: 'info', abnormal: 'danger',
  }
  return m[s] || ''
}

const reasonLabel = (r: string) => {
  const m: Record<string, string> = {
    installation: '安装', delivery: '送货', purchase: '采购', after_sales: '售后',
    field: '外勤', customer_measure: '客户量尺', other: '其他',
  }
  return m[r] || r
}

const loadAll = async () => {
  const params = { year: selectedYear.value, month: selectedMonth.value || undefined }
  try {
    const results = await Promise.all([
      getVehicleReportOverview(params),
      getVehicleCosts(params),
      getDriverStats(params),
      getMileageStats({ year: selectedYear.value }),
      getDispatchReportStats(params),
      getOrderVehicleCosts(params),
      getCostByType(params),
    ])
    overview.value = results[0] as VehicleReportOverview
    vehicleCosts.value = results[1] as VehicleCostItem[]
    driverStats.value = results[2] as DriverStatItem[]
    mileageStats.value = results[3] as MileageStatItem[]
    dispatchStats.value = results[4] as DispatchStatsType
    orderCosts.value = results[5] as OrderCostItem[]
    costTypes.value = results[6] as CostTypeItem[]
  } catch (e) {
    console.error('Load reports failed:', e)
  }
}

onMounted(loadAll)
</script>

<style scoped>
.vehicle-reports {
  padding: 16px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.stat-cards {
  margin-bottom: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.stat-info .stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}
.stat-info .stat-label {
  font-size: 13px;
  color: #909399;
}
.stat-sub {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  padding-left: 60px;
}
.mini-stat {
  text-align: center;
}
.mini-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}
.mini-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.section-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>
