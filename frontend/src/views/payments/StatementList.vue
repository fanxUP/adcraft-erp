<template>
  <div class="page">
    <div class="page-header">
      <h2>对账单</h2>
      <el-button type="danger" @click="showDialog = true">生成对账单</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="filterCustomerId" placeholder="筛选客户" clearable filterable style="width: 200px" @change="fetchData">
        <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-button style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="statement_no" label="对账单号" width="180" />
      <el-table-column label="期间" width="240">
        <template #default="{ row }">{{ row.start_date?.slice(0, 10) }} ~ {{ row.end_date?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="订单金额" width="140">
        <template #default="{ row }">¥ {{ row.total_order_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="已收金额" width="140">
        <template #default="{ row }">¥ {{ row.total_paid_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="未收金额" width="140">
        <template #default="{ row }">
          <span :style="{ color: row.total_unpaid_amount > 0 ? '#e63946' : '', fontWeight: row.total_unpaid_amount > 0 ? 'bold' : '' }">¥ {{ row.total_unpaid_amount?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'confirmed' ? 'success' : 'info'" size="small">{{ row.status === 'confirmed' ? '已确认' : '草稿' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="$router.push(`/statements/${row.id}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" style="margin-top: 16px; justify-content: flex-end" @change="fetchData" />

    <el-dialog v-model="showDialog" title="生成对账单" width="480px">
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
        <el-button type="danger" :loading="saving" @click="handleCreate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getStatements, createStatement } from '@/api/payments'
import { getCustomers } from '@/api/customers'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterCustomerId = ref('')
const showDialog = ref(false)
const customerOptions = ref<any[]>([])
const form = reactive({ customer_id: '', start_date: '', end_date: '' })

async function fetchData() {
  loading.value = true
  try {
    const data = await getStatements({ page: page.value, page_size: pageSize.value, customer_id: filterCustomerId.value || undefined })
    list.value = data.items; total.value = data.total
  } finally { loading.value = false }
}

async function loadOptions() {
  const cRes = await getCustomers({ page_size: 200 })
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
  } catch { } finally { saving.value = false }
}

onMounted(() => { fetchData(); loadOptions() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
