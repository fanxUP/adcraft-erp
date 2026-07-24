<template>
  <div class="page">
    <div class="page-header"><h2>车辆费用</h2><el-button type="primary" @click="handleCreate">+ 新增费用</el-button></div>
    <div class="search-bar">
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" />
      <el-select v-model="filters.cost_type" placeholder="费用类型" clearable style="width: 120px">
        <el-option v-for="t in costTypes" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.review_status" placeholder="审核状态" clearable style="width: 120px">
        <el-option label="待审核" value="pending" /><el-option label="已通过" value="approved" /><el-option label="已驳回" value="rejected" />
      </el-select>
      <el-button type="primary" @click="fetchData">搜索</el-button>
    </div>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="cost_date" label="日期" width="100" />
      <el-table-column prop="cost_type" label="费用类型" width="100"><template #default="{ row }">{{ costTypeLabel(row.cost_type) }}</template></el-table-column>
      <el-table-column prop="amount" label="金额" width="90" align="right"><template #default="{ row }">¥{{ row.amount }}</template></el-table-column>
      <el-table-column prop="plate_number" label="车辆" width="100" />
      <el-table-column prop="allocation_type" label="分摊方式" width="90"><template #default="{ row }">{{ allocLabel(row.allocation_type) }}</template></el-table-column>
      <el-table-column prop="review_status" label="审核" width="80">
        <template #default="{ row }">
          <el-tag :type="row.review_status === 'approved' ? 'success' : row.review_status === 'rejected' ? 'danger' : 'warning'" size="small">{{ reviewLabel(row.review_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" size="small" @click="handleReview(row, 'approved')" v-if="row.review_status === 'pending'">通过</el-button>
          <el-button link type="danger" size="small" @click="handleReview(row, 'rejected')" v-if="row.review_status === 'pending'">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" />

    <el-dialog v-model="dialogVisible" title="新增车辆费用" width="600px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-form-item label="高空车" required>
          <el-select v-model="form.aerial_vehicle_id" style="width: 100%">
            <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.vehicle_name} (${v.plate_number})`" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="费用日期" required><el-date-picker v-model="form.cost_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="费用类型" required>
              <el-select v-model="form.cost_type" style="width: 100%"><el-option v-for="t in costTypes" :key="t.value" :label="t.label" :value="t.value" /></el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="金额" required><el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分摊方式"><el-select v-model="form.allocation_type" style="width: 100%"><el-option label="不分摊" value="none" /><el-option label="按趟" value="per_trip" /><el-option label="按日" value="daily" /><el-option label="按月" value="monthly" /><el-option label="按年" value="annual" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="支付人">
          <el-select v-model="form.payer_id" clearable placeholder="选择驾驶员" style="width: 100%">
            <el-option v-for="d in driverOptions" :key="d.id" :label="d.driver_name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAerialVehicleCosts, createAerialVehicleCost, reviewAerialVehicleCost, getAerialVehicles, getAerialDrivers } from '@/api/aerial'

const loading = ref(false); const saving = ref(false); const dialogVisible = ref(false)
const list = ref<any[]>([]); const total = ref(0); const page = ref(1); const pageSize = ref(20)
const vehicleOptions = ref<any[]>([])
const driverOptions = ref<{ id: string; driver_name: string }[]>([])
const filters = reactive({ dateRange: [] as string[], cost_type: '', review_status: '' })
const form = reactive({ aerial_vehicle_id: '', cost_date: '', cost_type: '', amount: 0, allocation_type: 'none', payer_id: '', remark: '' })

const costTypes = [
  { value: 'fuel', label: '油费' }, { value: 'maintenance', label: '维修费' }, { value: 'insurance', label: '保险费' },
  { value: 'inspection', label: '年检费' }, { value: 'violation', label: '违章罚款' }, { value: 'tire', label: '轮胎' },
  { value: 'hydraulic_system', label: '液压系统' }, { value: 'boom_repair', label: '升降臂维修' },
  { value: 'platform_repair', label: '平台维修' }, { value: 'safety_equipment', label: '安全用品' },
  { value: 'tool_consumables', label: '工具耗材' }, { value: 'parking', label: '停车费' },
  { value: 'loan', label: '贷款/月供' }, { value: 'depreciation', label: '折旧' }, { value: 'other', label: '其他' },
]

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.dateRange?.length === 2) { params.date_from = filters.dateRange[0]; params.date_to = filters.dateRange[1] }
    if (filters.cost_type) params.cost_type = filters.cost_type
    if (filters.review_status) params.review_status = filters.review_status
    const res = await getAerialVehicleCosts(params); list.value = res.items || []; total.value = res.total || 0
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

function handleCreate() {
  Object.assign(form, { aerial_vehicle_id: '', cost_date: '', cost_type: '', amount: 0, allocation_type: 'none', payer_id: '', remark: '' })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.aerial_vehicle_id) return ElMessage.warning('请选择高空车')
  if (!form.cost_date) return ElMessage.warning('请选择费用日期')
  if (!form.cost_type) return ElMessage.warning('请选择费用类型')
  if (form.amount <= 0) return ElMessage.warning('金额必须大于0')
  saving.value = true
  try { await createAerialVehicleCost(form); ElMessage.success('新增成功'); dialogVisible.value = false; fetchData() }
  catch (e: any) { ElMessage.error(e.message) } finally { saving.value = false }
}

async function handleReview(row: any, status: string) {
  try { await ElMessageBox.confirm(`确定${status === 'approved' ? '通过' : '驳回'}？`, '审核'); await reviewAerialVehicleCost(row.id, status); ElMessage.success('操作成功'); fetchData() } catch {}
}

function costTypeLabel(t: string) { return costTypes.find(c => c.value === t)?.label || t }
function allocLabel(t: string) { return { none: '不分摊', per_trip: '按趟', daily: '按日', monthly: '按月', annual: '按年' }[t] || t }
function reviewLabel(s: string) { return { pending: '待审核', approved: '已通过', rejected: '已驳回' }[s] || s }

onMounted(async () => {
  fetchData()
  try { const v = await getAerialVehicles({ page_size: 100 }); vehicleOptions.value = v.items || [] } catch {}
  try { const d = await getAerialDrivers({ page_size: 100 }); driverOptions.value = d.items || [] } catch {}
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
