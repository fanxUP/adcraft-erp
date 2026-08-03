<template>
  <div class="page">
    <div class="page-header">
      <h2>人员垫付/报销</h2>
    </div>

    <div class="search-bar">
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" />
      <el-select v-model="filters.personnel_id" placeholder="人员" clearable style="width: 120px">
        <el-option v-for="d in personnelOptions" :key="d.id" :label="d.name" :value="d.id" />
      </el-select>
      <el-select v-model="filters.reimbursement_status" placeholder="报销状态" clearable style="width: 120px">
        <el-option label="未报销" value="unpaid" /><el-option label="待报销" value="pending_reimbursement" /><el-option label="已报销" value="reimbursed" />
      </el-select>
      <el-button type="primary" @click="fetchData">搜索</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="expense_date" label="日期" width="120" />
      <el-table-column prop="name" label="人员" width="100" />
      <el-table-column prop="expense_type" label="费用类型" width="100">
        <template #default="{ row }">{{ expenseTypeLabel(row.expense_type) }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="120" align="right">
        <template #default="{ row }">¥{{ row.amount }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column prop="reimbursement_status" label="报销状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.reimbursement_status === 'reimbursed' ? 'success' : row.reimbursement_status === 'pending_reimbursement' ? 'warning' : 'info'" size="small">
            {{ reimbLabel(row.reimbursement_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleReimburse(row)" v-if="row.reimbursement_status === 'pending_reimbursement'">标记已报销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[20, 50]" layout="total, sizes, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" @size-change="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAerialPersonnelExpenses,
  reimburseAerialPersonnelExpense,
  getAerialPersonnel,
  type AerialPersonnel,
  type AerialPersonnelExpense,
  type AerialQueryParams,
} from '@/api/aerial'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const list = ref<AerialPersonnelExpense[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const personnelOptions = ref<AerialPersonnel[]>([])
const filters = reactive({ dateRange: [] as string[], personnel_id: '', reimbursement_status: '' })

async function fetchData() {
  loading.value = true
  try {
    const params: AerialQueryParams = { page: page.value, page_size: pageSize.value }
    if (filters.dateRange?.length === 2) { params.date_from = filters.dateRange[0]; params.date_to = filters.dateRange[1] }
    if (filters.personnel_id) params.personnel_id = filters.personnel_id
    if (filters.reimbursement_status) params.reimbursement_status = filters.reimbursement_status
    const res = await getAerialPersonnelExpenses(params)
    list.value = res.items || []; total.value = res.total || 0
  } catch (error: unknown) { ElMessage.error(getErrorMessage(error)) } finally { loading.value = false }
}

function resetFilters() {
  filters.dateRange = []; filters.personnel_id = ''; filters.reimbursement_status = ''
  page.value = 1; fetchData()
}

async function handleReimburse(row: AerialPersonnelExpense) {
  try {
    await ElMessageBox.confirm('确定标记此垫付已报销？', '报销确认')
    await reimburseAerialPersonnelExpense(row.id)
    ElMessage.success('已标记报销'); fetchData()
  } catch {}
}

function expenseTypeLabel(t: string) {
  const m: Record<string, string> = { fuel: '油费', toll: '过路费', parking: '停车费', meal: '餐费', temporary_repair: '临时维修', material: '材料', other: '其他' }
  return m[t] || t
}
function reimbLabel(s: string) { return { unpaid: '未报销', pending_reimbursement: '待报销', reimbursed: '已报销' }[s] || s }

onMounted(async () => {
  fetchData()
  try { const d = await getAerialPersonnel({ page_size: 100 }); personnelOptions.value = d.items || [] } catch {}
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
