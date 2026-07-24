<template>
  <div class="page">
    <div class="page-header">
      <h2>驾驶员垫付/报销</h2>
    </div>

    <div class="search-bar">
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" />
      <el-select v-model="filters.driver_id" placeholder="驾驶员" clearable style="width: 120px">
        <el-option v-for="d in driverOptions" :key="d.id" :label="d.driver_name" :value="d.id" />
      </el-select>
      <el-select v-model="filters.review_status" placeholder="审核状态" clearable style="width: 120px">
        <el-option label="待审核" value="pending" /><el-option label="已通过" value="approved" /><el-option label="已驳回" value="rejected" />
      </el-select>
      <el-select v-model="filters.reimbursement_status" placeholder="报销状态" clearable style="width: 120px">
        <el-option label="未报销" value="unpaid" /><el-option label="待报销" value="pending_reimbursement" /><el-option label="已报销" value="reimbursed" />
      </el-select>
      <el-button type="primary" @click="fetchData">搜索</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="expense_date" label="日期" width="100" />
      <el-table-column prop="driver_name" label="驾驶员" width="80" />
      <el-table-column prop="expense_type" label="费用类型" width="90">
        <template #default="{ row }">{{ expenseTypeLabel(row.expense_type) }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="80" align="right">
        <template #default="{ row }">¥{{ row.amount }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
      <el-table-column prop="review_status" label="审核状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.review_status === 'approved' ? 'success' : row.review_status === 'rejected' ? 'danger' : 'warning'" size="small">
            {{ reviewLabel(row.review_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reimbursement_status" label="报销状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.reimbursement_status === 'reimbursed' ? 'success' : row.reimbursement_status === 'pending_reimbursement' ? 'warning' : 'info'" size="small">
            {{ reimbLabel(row.reimbursement_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" size="small" @click="handleReview(row, 'approved')" v-if="row.review_status === 'pending'">通过</el-button>
          <el-button link type="danger" size="small" @click="handleReview(row, 'rejected')" v-if="row.review_status === 'pending'">驳回</el-button>
          <el-button link type="primary" size="small" @click="handleReimburse(row)" v-if="row.review_status === 'approved' && row.reimbursement_status === 'pending_reimbursement'">标记已报销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[20, 50]" layout="total, sizes, prev, pager, next" style="margin-top: 16px" @current-change="fetchData" @size-change="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAerialDriverExpenses, reviewAerialDriverExpense, reimburseAerialDriverExpense, getAerialDrivers } from '@/api/aerial'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const driverOptions = ref<any[]>([])
const filters = reactive({ dateRange: [] as string[], driver_id: '', review_status: '', reimbursement_status: '' })

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.dateRange?.length === 2) { params.date_from = filters.dateRange[0]; params.date_to = filters.dateRange[1] }
    if (filters.driver_id) params.driver_id = filters.driver_id
    if (filters.review_status) params.review_status = filters.review_status
    if (filters.reimbursement_status) params.reimbursement_status = filters.reimbursement_status
    const res = await getAerialDriverExpenses(params)
    list.value = res.items || []; total.value = res.total || 0
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

function resetFilters() {
  filters.dateRange = []; filters.driver_id = ''; filters.review_status = ''; filters.reimbursement_status = ''
  page.value = 1; fetchData()
}

async function handleReview(row: any, status: string) {
  try {
    await ElMessageBox.confirm(`确定${status === 'approved' ? '通过' : '驳回'}此垫付记录？`, '审核')
    await reviewAerialDriverExpense(row.id, status)
    ElMessage.success('操作成功'); fetchData()
  } catch {}
}

async function handleReimburse(row: any) {
  try {
    await ElMessageBox.confirm('确定标记此垫付已报销？', '报销确认')
    await reimburseAerialDriverExpense(row.id)
    ElMessage.success('已标记报销'); fetchData()
  } catch {}
}

function expenseTypeLabel(t: string) {
  const m: Record<string, string> = { fuel: '油费', toll: '过路费', parking: '停车费', meal: '餐费', temporary_repair: '临时维修', material: '材料', other: '其他' }
  return m[t] || t
}
function reviewLabel(s: string) { return { pending: '待审核', approved: '已通过', rejected: '已驳回' }[s] || s }
function reimbLabel(s: string) { return { unpaid: '未报销', pending_reimbursement: '待报销', reimbursed: '已报销' }[s] || s }

onMounted(async () => {
  fetchData()
  try { const d = await getAerialDrivers({ page_size: 100 }); driverOptions.value = d.items || [] } catch {}
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
</style>
