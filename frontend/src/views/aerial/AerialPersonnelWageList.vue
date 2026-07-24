<template>
  <div class="page">
    <div class="page-header">
      <h2>人员工资</h2>
      <el-button @click="handleExport" :disabled="!month">导出 Excel</el-button>
    </div>
    <div class="search-bar">
      <el-date-picker v-model="month" type="month" value-format="YYYY-MM" placeholder="月份" style="width: 160px" />
      <el-select v-model="filters.personnel_id" placeholder="人员" clearable style="width: 120px">
        <el-option v-for="d in personnelOptions" :key="d.id" :label="d.name" :value="d.id" />
      </el-select>
      <el-select v-model="filters.payment_status" placeholder="支付状态" clearable style="width: 120px">
        <el-option label="待核算" value="pending" /><el-option label="已核算" value="calculated" />
        <el-option label="待发放" value="pending_payment" /><el-option label="已发放" value="paid" />
      </el-select>
      <el-button type="primary" @click="fetchData">搜索</el-button>
    </div>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="wage_month" label="月份" width="90" />
      <el-table-column prop="name" label="人员" width="80" />
      <el-table-column prop="wage_type" label="工资类型" width="90">
        <template #default="{ row }">{{ wageTypeLabel(row.wage_type) }}</template>
      </el-table-column>
      <el-table-column prop="base_wage" label="基础工资" width="90" align="right"><template #default="{ row }">¥{{ row.base_wage }}</template></el-table-column>
      <el-table-column prop="trip_wage" label="趟次工资" width="90" align="right"><template #default="{ row }">¥{{ row.trip_wage }}</template></el-table-column>
      <el-table-column prop="allowance_amount" label="补贴" width="80" align="right"><template #default="{ row }">¥{{ row.allowance_amount }}</template></el-table-column>
      <el-table-column prop="deduction_amount" label="扣款" width="80" align="right"><template #default="{ row }">¥{{ row.deduction_amount }}</template></el-table-column>
      <el-table-column prop="final_wage_amount" label="最终工资" width="100" align="right"><template #default="{ row }"><b>¥{{ row.final_wage_amount }}</b></template></el-table-column>
      <el-table-column prop="payment_status" label="支付状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.payment_status === 'paid' ? 'success' : row.payment_status === 'pending_payment' ? 'warning' : 'info'" size="small">{{ payLabel(row.payment_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" size="small" @click="handlePay(row)" v-if="row.payment_status !== 'paid'">标记已发</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAerialPersonnelWages, payAerialPersonnelWage, getAerialPersonnel, exportAerialWages } from '@/api/aerial'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const month = ref('')
const personnelOptions = ref<any[]>([])
const filters = reactive({ personnel_id: '', payment_status: '' })

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (month.value) params.wage_month = month.value
    if (filters.personnel_id) params.personnel_id = filters.personnel_id
    if (filters.payment_status) params.payment_status = filters.payment_status
    const res = await getAerialPersonnelWages(params)
    list.value = res.items || []; total.value = res.total || 0
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

async function handlePay(row: any) {
  try {
    await ElMessageBox.confirm(`确定标记 ${row.name} 的工资 ¥${row.final_wage_amount} 已发放？`, '工资发放')
    await payAerialPersonnelWage(row.id)
    ElMessage.success('已标记发放'); fetchData()
  } catch {}
}

async function handleExport() {
  if (!month.value) return ElMessage.warning('请先选择月份')
  try {
    await exportAerialWages(month.value)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e.message || '导出失败')
  }
}

function wageTypeLabel(t: string) { return { daily: '日工资', trip: '按趟', hourly: '按小时', commission: '提成', base_plus_commission: '底薪+提成' }[t] || t }
function payLabel(s: string) { return { pending: '待核算', calculated: '已核算', pending_payment: '待发放', paid: '已发放' }[s] || s }

onMounted(async () => {
  fetchData()
  try { const d = await getAerialPersonnel({ page_size: 100 }); personnelOptions.value = d.items || [] } catch {}
})
</script>

<style scoped>
.page-header { margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
