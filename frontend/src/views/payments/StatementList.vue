<template>
  <AppPage>
    <template #header>
      <PageHeader title="对账单" description="按客户和期间生成、确认并追踪对账结果。">
        <template #actions><el-button @click="showDialog = true" type="danger">生成对账单</el-button></template>
      </PageHeader>
    </template>

    <template #toolbar>
      <PageToolbar aria-label="对账单筛选">
      <el-select v-model="filterCustomerId" placeholder="筛选客户" clearable filterable style="width: 200px" @change="fetchData">
        <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-button style="margin-left: 12px" @click="fetchData" type="primary">搜索</el-button>
      </PageToolbar>
    </template>

    <DataTableShell :state="tableState" aria-label="对账单列表">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="list" stripe>
      <el-table-column prop="statement_no" label="对账单号" width="180" />
      <el-table-column label="期间" width="240">
        <template #default="{ row }">{{ formatDate(row.start_date) }} ~ {{ formatDate(row.end_date) }}</template>
      </el-table-column>
      <el-table-column label="订单金额" width="120">
        <template #default="{ row }">{{ formatMoney(row.total_order_amount) }}</template>
      </el-table-column>
      <el-table-column label="已收金额" width="120">
        <template #default="{ row }">{{ formatMoney(row.total_paid_amount) }}</template>
      </el-table-column>
      <el-table-column label="未收金额" width="120">
        <template #default="{ row }">
          <span :class="{ 'text-danger': row.total_unpaid_amount > 0 }">{{ formatMoney(row.total_unpaid_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusTag :status="row.status_view || row.status" size="sm" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="$router.push(`/statements/${row.id}`)">详情</el-button>
        </template>
      </el-table-column>
      </el-table>
      <template #footer>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" @change="fetchData" />
      </template>
    </DataTableShell>

    <el-dialog v-model="showDialog" title="生成对账单" width="480px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户">
          <el-select v-model="form.customer_id" placeholder="选择客户" filterable style="width: 100%">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" @click="handleCreate" type="danger">生成</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { ref, reactive, computed, onMounted } from 'vue'
import { getStatements, createStatement } from '@/api/payments'
import { getCustomers } from '@/api/customers'
import { ElMessage } from 'element-plus'
import { StatementResponse, CustomerResponse } from '@/types/api'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel, StatusTag } from '@/components/ui'

const loading = ref(false)
const saving = ref(false)
const list = ref<StatementResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loadError = ref(false)
const filterCustomerId = ref('')
const showDialog = ref(false)
const customerOptions = ref<CustomerResponse[]>([])
const form = reactive({ customer_id: '', start_date: '', end_date: '' })

const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return list.value.length ? 'ready' : 'empty'
})

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const data = await getStatements({ page: page.value, page_size: pageSize.value, customer_id: filterCustomerId.value || undefined })
    list.value = data.items; total.value = data.total
  } catch {
    loadError.value = true
  } finally { loading.value = false }
}

async function loadOptions() {
  const cRes = await getCustomers({ page_size: 100 })
  customerOptions.value = cRes.items
}

async function handleCreate() {
  if (!form.start_date || !form.end_date) { ElMessage.warning('请选择日期范围'); return }
  saving.value = true
  try {
    await createStatement(form)
    ElMessage.success('对账单已生成')
    showDialog.value = false
    Object.assign(form, { customer_id: '', start_date: '', end_date: '' })
    fetchData()
  } catch {
    // API error handled by interceptor
  } finally { saving.value = false }
}

onMounted(() => { fetchData(); loadOptions() })
</script>

<style scoped>
</style>
