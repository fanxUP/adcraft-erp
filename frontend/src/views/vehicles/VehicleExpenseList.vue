<template>
  <div class="vehicle-expense-page">
    <div class="page-header">
      <h2>车辆费用管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showAddFuel">新增油费</el-button>
        <el-button type="success" @click="showAddMaintenance">新增维修保养</el-button>
        <el-button type="warning" @click="showAddCost">新增其他费用</el-button>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="油费记录" name="fuel">
        <!-- 油费筛选 -->
        <el-form :inline="true" class="filter-form">
          <el-form-item label="车辆">
            <el-select v-model="fuelFilter.vehicle_id" clearable placeholder="选择车辆" style="width: 160px">
              <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.plate_number} ${v.vehicle_name}`" :value="v.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="fuelFilter.status" clearable placeholder="选择状态" style="width: 120px">
              <el-option label="待审核" value="pending_review" />
              <el-option label="已审核" value="approved" />
              <el-option label="已驳回" value="rejected" />
              <el-option label="已报销" value="reimbursed" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="loadFuelRecords">查询</el-button>
          </el-form-item>
        </el-form>

        <!-- 油费列表 -->
        <el-table :data="fuelRecords" v-loading="fuelLoading" stripe>
          <el-table-column prop="vehicle_name" label="车辆" width="120">
            <template #default="{ row }">
              {{ row.plate_number }} {{ row.vehicle_name }}
            </template>
          </el-table-column>
          <el-table-column prop="driver_name" label="司机" width="100" />
          <el-table-column prop="fuel_time" label="加油时间" width="160">
            <template #default="{ row }">
              {{ row.fuel_time ? new Date(row.fuel_time).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="金额" width="100">
            <template #default="{ row }">
              ¥{{ row.amount?.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="liters" label="升数" width="80" />
          <el-table-column prop="unit_price" label="单价" width="80">
            <template #default="{ row }">
              {{ row.unit_price ? `¥${row.unit_price.toFixed(2)}` : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="gas_station" label="加油站" min-width="120" />
          <el-table-column prop="mileage" label="里程(km)" width="100" />
          <el-table-column prop="payment_method" label="支付方式" width="100">
            <template #default="{ row }">
              {{ paymentMethodLabel(row.payment_method) }}
            </template>
          </el-table-column>
          <el-table-column prop="payer_name" label="支付人" width="100" />
          <el-table-column prop="is_driver_advance" label="司机垫付" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_driver_advance ? 'warning' : 'info'" size="small">
                {{ row.is_driver_advance ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="fuelStatusType(row.status)" size="small">{{ fuelStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="viewFuelDetail(row)">详情</el-button>
              <el-button v-if="row.status === 'pending_review' && hasFinanceRole" link type="success" size="small" @click="reviewFuel(row)">审核</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="fuelTotal > fuelPageSize"
          layout="total, prev, pager, next"
          :total="fuelTotal"
          :page-size="fuelPageSize"
          :current-page="fuelPage"
          @current-change="handleFuelPageChange"
          style="margin-top: 16px; justify-content: flex-end"
        />
      </el-tab-pane>

      <el-tab-pane label="维修保养" name="maintenance">
        <!-- 维修保养筛选 -->
        <el-form :inline="true" class="filter-form">
          <el-form-item label="车辆">
            <el-select v-model="maintFilter.vehicle_id" clearable placeholder="选择车辆" style="width: 160px">
              <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.plate_number} ${v.vehicle_name}`" :value="v.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="maintFilter.maintenance_type" clearable placeholder="选择类型" style="width: 120px">
              <el-option label="维修" value="repair" />
              <el-option label="保养" value="maintenance" />
              <el-option label="轮胎" value="tire" />
              <el-option label="电瓶" value="battery" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="maintFilter.status" clearable placeholder="选择状态" style="width: 120px">
              <el-option label="待审核" value="pending_review" />
              <el-option label="已审核" value="approved" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="loadMaintenanceRecords">查询</el-button>
          </el-form-item>
        </el-form>

        <!-- 维修保养列表 -->
        <el-table :data="maintenanceRecords" v-loading="maintLoading" stripe>
          <el-table-column prop="vehicle_name" label="车辆" width="120">
            <template #default="{ row }">
              {{ row.plate_number }} {{ row.vehicle_name }}
            </template>
          </el-table-column>
          <el-table-column prop="maintenance_type" label="类型" width="80">
            <template #default="{ row }">
              {{ maintenanceTypeLabel(row.maintenance_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="maintenance_date" label="日期" width="120">
            <template #default="{ row }">
              {{ row.maintenance_date ? new Date(row.maintenance_date).toLocaleDateString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="maintenance_item" label="维修项目" min-width="150" />
          <el-table-column prop="repair_shop" label="维修厂" width="120" />
          <el-table-column prop="amount" label="金额" width="100">
            <template #default="{ row }">
              ¥{{ row.amount?.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="mileage" label="里程(km)" width="100" />
          <el-table-column prop="handler_name" label="经办人" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="maintStatusType(row.status)" size="small">{{ maintStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="viewMaintenanceDetail(row)">详情</el-button>
              <el-button v-if="row.status === 'pending_review' && hasFinanceRole" link type="success" size="small" @click="reviewMaintenance(row)">审核</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="maintTotal > maintPageSize"
          layout="total, prev, pager, next"
          :total="maintTotal"
          :page-size="maintPageSize"
          :current-page="maintPage"
          @current-change="handleMaintPageChange"
          style="margin-top: 16px; justify-content: flex-end"
        />
      </el-tab-pane>

      <el-tab-pane label="其他费用" name="cost">
        <!-- 其他费用筛选 -->
        <el-form :inline="true" class="filter-form">
          <el-form-item label="车辆">
            <el-select v-model="costFilter.vehicle_id" clearable placeholder="选择车辆" style="width: 160px">
              <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.plate_number} ${v.vehicle_name}`" :value="v.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="费用类型">
            <el-select v-model="costFilter.cost_type" clearable placeholder="选择类型" style="width: 120px">
              <el-option v-for="t in costTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="loadCostAllocations">查询</el-button>
          </el-form-item>
        </el-form>

        <!-- 其他费用列表 -->
        <el-table :data="costAllocations" v-loading="costLoading" stripe>
          <el-table-column prop="vehicle_name" label="车辆" width="120">
            <template #default="{ row }">
              {{ row.plate_number }} {{ row.vehicle_name }}
            </template>
          </el-table-column>
          <el-table-column prop="cost_type" label="费用类型" width="100">
            <template #default="{ row }">
              {{ costTypeLabel(row.cost_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="金额" width="100">
            <template #default="{ row }">
              ¥{{ row.amount?.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="allocation_date" label="日期" width="120">
            <template #default="{ row }">
              {{ row.allocation_date ? new Date(row.allocation_date).toLocaleDateString('zh-CN') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="source_type" label="来源" width="100" />
          <el-table-column prop="remark" label="备注" min-width="150" />
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="{ row }">
              {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="costTotal > costPageSize"
          layout="total, prev, pager, next"
          :total="costTotal"
          :page-size="costPageSize"
          :current-page="costPage"
          @current-change="handleCostPageChange"
          style="margin-top: 16px; justify-content: flex-end"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 新增油费对话框 -->
    <el-dialog v-model="fuelDialogVisible" title="新增油费记录" width="600px" destroy-on-close>
      <el-form :model="fuelForm" label-width="100px">
        <el-form-item label="车辆" required>
          <el-select v-model="fuelForm.vehicle_id" placeholder="选择车辆" style="width: 100%">
            <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.plate_number} ${v.vehicle_name}`" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="司机">
          <el-select v-model="fuelForm.driver_id" clearable placeholder="选择司机" style="width: 100%">
            <el-option v-for="d in driverOptions" :key="d.id" :label="d.driver_name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="加油时间">
          <el-date-picker v-model="fuelForm.fuel_time" type="datetime" placeholder="选择时间" style="width: 100%" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="金额" required>
              <el-input-number v-model="fuelForm.amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="升数">
              <el-input-number v-model="fuelForm.liters" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单价">
              <el-input-number v-model="fuelForm.unit_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="加油站">
          <el-input v-model="fuelForm.gas_station" placeholder="加油站名称" />
        </el-form-item>
        <el-form-item label="当前里程(km)">
          <el-input-number v-model="fuelForm.mileage" :min="0" :precision="1" style="width: 100%" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="支付方式">
              <el-select v-model="fuelForm.payment_method" clearable placeholder="选择支付方式" style="width: 100%">
                <el-option label="现金" value="cash" />
                <el-option label="微信" value="wechat" />
                <el-option label="支付宝" value="alipay" />
                <el-option label="油卡" value="card" />
                <el-option label="公司支付" value="company" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="支付人">
              <el-select v-model="fuelForm.payer_id" clearable placeholder="选择支付人" style="width: 100%">
                <el-option v-for="u in userOptions" :key="u.id" :label="u.real_name" :value="u.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="司机垫付">
              <el-switch v-model="fuelForm.is_driver_advance" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="fuelForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fuelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitFuel" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 新增维修保养对话框 -->
    <el-dialog v-model="maintDialogVisible" title="新增维修保养记录" width="600px" destroy-on-close>
      <el-form :model="maintForm" label-width="100px">
        <el-form-item label="车辆" required>
          <el-select v-model="maintForm.vehicle_id" placeholder="选择车辆" style="width: 100%">
            <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.plate_number} ${v.vehicle_name}`" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="maintForm.maintenance_type" placeholder="选择类型" style="width: 100%">
            <el-option label="维修" value="repair" />
            <el-option label="保养" value="maintenance" />
            <el-option label="轮胎" value="tire" />
            <el-option label="电瓶" value="battery" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="维修日期">
          <el-date-picker v-model="maintForm.maintenance_date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="维修项目">
          <el-input v-model="maintForm.maintenance_item" placeholder="维修项目描述" />
        </el-form-item>
        <el-form-item label="维修厂">
          <el-input v-model="maintForm.repair_shop" placeholder="维修厂名称" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="金额" required>
              <el-input-number v-model="maintForm.amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当前里程(km)">
              <el-input-number v-model="maintForm.mileage" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="下次保养里程">
              <el-input-number v-model="maintForm.next_maintenance_mileage" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="下次保养日期">
              <el-date-picker v-model="maintForm.next_maintenance_date" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="经办人">
          <el-select v-model="maintForm.handler_id" clearable placeholder="选择经办人" style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="maintForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="maintDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMaintenance" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 新增其他费用对话框 -->
    <el-dialog v-model="costDialogVisible" title="新增其他费用" width="600px" destroy-on-close>
      <el-form :model="costForm" label-width="100px">
        <el-form-item label="车辆" required>
          <el-select v-model="costForm.vehicle_id" placeholder="选择车辆" style="width: 100%">
            <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.plate_number} ${v.vehicle_name}`" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="费用类型" required>
          <el-select v-model="costForm.cost_type" placeholder="选择费用类型" style="width: 100%">
            <el-option v-for="t in costTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="costForm.amount" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="costForm.allocation_date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="costForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="costDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCost" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 审核对话框 -->
    <el-dialog v-model="reviewDialogVisible" title="费用审核" width="400px" destroy-on-close>
      <el-form :model="reviewForm" label-width="80px">
        <el-form-item label="审核结果">
          <el-radio-group v-model="reviewForm.status">
            <el-radio value="approved">通过</el-radio>
            <el-radio value="rejected">驳回</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="reviewForm.remark" type="textarea" :rows="3" placeholder="审核意见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReview" :loading="submitting">确认</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="费用详情" width="600px">
      <el-descriptions :column="2" border v-if="detailData">
        <el-descriptions-item v-for="(value, key) in detailData" :key="key" :label="key">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import {
  getFuelRecords, createFuelRecord, reviewFuelRecord,
  getMaintenanceRecords, createMaintenanceRecord, reviewMaintenanceRecord,
  getCostAllocations, createCostAllocation,
  type FuelRecordResponse, type MaintenanceRecordResponse, type CostAllocationResponse,
} from '@/api/vehicles'
import { getVehicles, getDrivers, type VehicleResponse, type VehicleDriverResponse } from '@/api/vehicles'
import { getUsers } from '@/api/users'

const authStore = useAuthStore()
const hasFinanceRole = computed(() => authStore.hasAnyRole(['admin', 'finance']))

// ── 车辆/司机选项 ──────────────────────────────────────────────────────────────
const vehicleOptions = ref<VehicleResponse[]>([])
const driverOptions = ref<VehicleDriverResponse[]>([])
const userOptions = ref<{ id: string; real_name: string }[]>([])

const loadVehicleOptions = async () => {
  try {
    const res = await getVehicles({ page: 1, page_size: 100 })
    vehicleOptions.value = res.items || []
  } catch { /* ignore */ }
}

const loadDriverOptions = async () => {
  try {
    const res = await getDrivers({ page: 1, page_size: 100 })
    driverOptions.value = res.items || []
  } catch { /* ignore */ }
}

const loadUserOptions = async () => {
  try {
    const res = await getUsers({ page: 1, page_size: 100 })
    userOptions.value = res.items || []
  } catch { /* ignore */ }
}

// ── Tab 切换 ──────────────────────────────────────────────────────────────────
const activeTab = ref('fuel')

const handleTabChange = (tab: string) => {
  if (tab === 'fuel') loadFuelRecords()
  else if (tab === 'maintenance') loadMaintenanceRecords()
  else if (tab === 'cost') loadCostAllocations()
}

// ── 油费记录 ──────────────────────────────────────────────────────────────────
const fuelRecords = ref<FuelRecordResponse[]>([])
const fuelLoading = ref(false)
const fuelTotal = ref(0)
const fuelPage = ref(1)
const fuelPageSize = ref(20)
const fuelFilter = reactive({ vehicle_id: '', status: '' })

const loadFuelRecords = async () => {
  fuelLoading.value = true
  try {
    const res = await getFuelRecords({
      page: fuelPage.value,
      page_size: fuelPageSize.value,
      vehicle_id: fuelFilter.vehicle_id || undefined,
      status: fuelFilter.status || undefined,
    })
    fuelRecords.value = res.items || []
    fuelTotal.value = res.total || 0
  } catch { /* handled by interceptor */ } finally {
    fuelLoading.value = false
  }
}

const handleFuelPageChange = (page: number) => {
  fuelPage.value = page
  loadFuelRecords()
}

// ── 维修保养 ──────────────────────────────────────────────────────────────────
const maintenanceRecords = ref<MaintenanceRecordResponse[]>([])
const maintLoading = ref(false)
const maintTotal = ref(0)
const maintPage = ref(1)
const maintPageSize = ref(20)
const maintFilter = reactive({ vehicle_id: '', maintenance_type: '', status: '' })

const loadMaintenanceRecords = async () => {
  maintLoading.value = true
  try {
    const res = await getMaintenanceRecords({
      page: maintPage.value,
      page_size: maintPageSize.value,
      vehicle_id: maintFilter.vehicle_id || undefined,
      maintenance_type: maintFilter.maintenance_type || undefined,
      status: maintFilter.status || undefined,
    })
    maintenanceRecords.value = res.items || []
    maintTotal.value = res.total || 0
  } catch { /* handled by interceptor */ } finally {
    maintLoading.value = false
  }
}

const handleMaintPageChange = (page: number) => {
  maintPage.value = page
  loadMaintenanceRecords()
}

// ── 其他费用 ──────────────────────────────────────────────────────────────────
const costAllocations = ref<CostAllocationResponse[]>([])
const costLoading = ref(false)
const costTotal = ref(0)
const costPage = ref(1)
const costPageSize = ref(20)
const costFilter = reactive({ vehicle_id: '', cost_type: '' })

const loadCostAllocations = async () => {
  costLoading.value = true
  try {
    const res = await getCostAllocations({
      page: costPage.value,
      page_size: costPageSize.value,
      vehicle_id: costFilter.vehicle_id || undefined,
      cost_type: costFilter.cost_type || undefined,
    })
    costAllocations.value = res.items || []
    costTotal.value = res.total || 0
  } catch { /* handled by interceptor */ } finally {
    costLoading.value = false
  }
}

const handleCostPageChange = (page: number) => {
  costPage.value = page
  loadCostAllocations()
}

// ── 对话框 ──────────────────────────────────────────────────────────────────
const submitting = ref(false)
const fuelDialogVisible = ref(false)
const maintDialogVisible = ref(false)
const costDialogVisible = ref(false)
const reviewDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const detailData = ref<Record<string, unknown> | null>(null)

const fuelForm = reactive({
  vehicle_id: '', driver_id: '', fuel_time: '', amount: 0, liters: undefined as number | undefined,
  unit_price: undefined as number | undefined, gas_station: '', mileage: undefined as number | undefined,
  payment_method: '', payer_id: '', is_driver_advance: false, remark: '',
})

const maintForm = reactive({
  vehicle_id: '', maintenance_type: 'maintenance', maintenance_date: '', maintenance_item: '',
  repair_shop: '', amount: 0, mileage: undefined as number | undefined,
  next_maintenance_mileage: undefined as number | undefined, next_maintenance_date: '',
  handler_id: '', remark: '',
})

const costForm = reactive({
  vehicle_id: '', cost_type: '', amount: 0, allocation_date: '', remark: '',
})

const reviewForm = reactive({ status: 'approved', remark: '' })
let reviewTarget = { type: '', id: '' }

const showAddFuel = () => {
  Object.assign(fuelForm, {
    vehicle_id: '', driver_id: '', fuel_time: '', amount: 0, liters: undefined,
    unit_price: undefined, gas_station: '', mileage: undefined,
    payment_method: '', payer_id: '', is_driver_advance: false, remark: '',
  })
  fuelDialogVisible.value = true
}

const showAddMaintenance = () => {
  Object.assign(maintForm, {
    vehicle_id: '', maintenance_type: 'maintenance', maintenance_date: '', maintenance_item: '',
    repair_shop: '', amount: 0, mileage: undefined, next_maintenance_mileage: undefined,
    next_maintenance_date: '', handler_id: '', remark: '',
  })
  maintDialogVisible.value = true
}

const showAddCost = () => {
  Object.assign(costForm, { vehicle_id: '', cost_type: '', amount: 0, allocation_date: '', remark: '' })
  costDialogVisible.value = true
}

const submitFuel = async () => {
  if (!fuelForm.vehicle_id) return ElMessage.warning('请选择车辆')
  if (!fuelForm.amount) return ElMessage.warning('请输入金额')
  submitting.value = true
  try {
    await createFuelRecord(fuelForm as Partial<FuelRecordResponse>)
    ElMessage.success('油费记录已提交')
    fuelDialogVisible.value = false
    loadFuelRecords()
  } catch { /* handled */ } finally { submitting.value = false }
}

const submitMaintenance = async () => {
  if (!maintForm.vehicle_id) return ElMessage.warning('请选择车辆')
  if (!maintForm.amount) return ElMessage.warning('请输入金额')
  submitting.value = true
  try {
    await createMaintenanceRecord(maintForm as Partial<MaintenanceRecordResponse>)
    ElMessage.success('维修保养记录已提交')
    maintDialogVisible.value = false
    loadMaintenanceRecords()
  } catch { /* handled */ } finally { submitting.value = false }
}

const submitCost = async () => {
  if (!costForm.vehicle_id) return ElMessage.warning('请选择车辆')
  if (!costForm.cost_type) return ElMessage.warning('请选择费用类型')
  if (!costForm.amount) return ElMessage.warning('请输入金额')
  submitting.value = true
  try {
    await createCostAllocation(costForm as Partial<CostAllocationResponse>)
    ElMessage.success('费用记录已创建')
    costDialogVisible.value = false
    loadCostAllocations()
  } catch { /* handled */ } finally { submitting.value = false }
}

const reviewFuel = (row: FuelRecordResponse) => {
  reviewTarget = { type: 'fuel', id: row.id }
  reviewForm.status = 'approved'
  reviewForm.remark = ''
  reviewDialogVisible.value = true
}

const reviewMaintenance = (row: MaintenanceRecordResponse) => {
  reviewTarget = { type: 'maintenance', id: row.id }
  reviewForm.status = 'approved'
  reviewForm.remark = ''
  reviewDialogVisible.value = true
}

const submitReview = async () => {
  submitting.value = true
  try {
    if (reviewTarget.type === 'fuel') {
      await reviewFuelRecord(reviewTarget.id, reviewForm)
    } else {
      await reviewMaintenanceRecord(reviewTarget.id, reviewForm)
    }
    ElMessage.success('审核完成')
    reviewDialogVisible.value = false
    if (reviewTarget.type === 'fuel') loadFuelRecords()
    else loadMaintenanceRecords()
  } catch { /* handled */ } finally { submitting.value = false }
}

const viewFuelDetail = (row: FuelRecordResponse) => {
  detailData.value = row as Record<string, unknown>
  detailDialogVisible.value = true
}

const viewMaintenanceDetail = (row: MaintenanceRecordResponse) => {
  detailData.value = row as Record<string, unknown>
  detailDialogVisible.value = true
}

// ── 标签映射 ──────────────────────────────────────────────────────────────────
const paymentMethodLabel = (m?: string) => {
  const map: Record<string, string> = { cash: '现金', wechat: '微信', alipay: '支付宝', card: '油卡', company: '公司支付' }
  return map[m || ''] || m || '-'
}

const fuelStatusLabel = (s: string) => {
  const map: Record<string, string> = { pending_review: '待审核', approved: '已审核', rejected: '已驳回', reimbursed: '已报销', paid: '已付款' }
  return map[s] || s
}

const fuelStatusType = (s: string) => {
  const map: Record<string, string> = { pending_review: 'warning', approved: 'success', rejected: 'danger', reimbursed: 'info', paid: '' }
  return map[s] || 'info'
}

const maintenanceTypeLabel = (t?: string) => {
  const map: Record<string, string> = { repair: '维修', maintenance: '保养', tire: '轮胎', battery: '电瓶', other: '其他' }
  return map[t || ''] || t || '-'
}

const maintStatusLabel = (s: string) => {
  const map: Record<string, string> = { pending_review: '待审核', approved: '已审核', rejected: '已驳回', paid: '已付款' }
  return map[s] || s
}

const maintStatusType = (s: string) => {
  const map: Record<string, string> = { pending_review: 'warning', approved: 'success', rejected: 'danger', paid: '' }
  return map[s] || 'info'
}

const costTypeOptions = [
  { label: '油费', value: 'fuel' },
  { label: '过路费', value: 'toll' },
  { label: '停车费', value: 'parking' },
  { label: '维修费', value: 'repair' },
  { label: '保养费', value: 'maintenance' },
  { label: '保险费', value: 'insurance' },
  { label: '年检费', value: 'inspection' },
  { label: '违章罚款', value: 'violation' },
  { label: '事故维修', value: 'accident' },
  { label: '轮胎', value: 'tire' },
  { label: '电瓶', value: 'battery' },
  { label: '洗车费', value: 'wash' },
  { label: '外租车辆费', value: 'rent' },
  { label: '司机补贴', value: 'driver_subsidy' },
  { label: '其他', value: 'other' },
]

const costTypeLabel = (t?: string) => {
  const found = costTypeOptions.find(o => o.value === t)
  return found?.label || t || '-'
}

// ── 初始化 ──────────────────────────────────────────────────────────────────
onMounted(() => {
  loadVehicleOptions()
  loadDriverOptions()
  loadUserOptions()
  loadFuelRecords()
})
</script>

<style scoped>
.vehicle-expense-page {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.filter-form {
  margin-bottom: 16px;
}
</style>
