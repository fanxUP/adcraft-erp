<template>
  <div class="page">
    <div class="page-header">
      <h2>收款记录</h2>
      <el-button type="danger" @click="showDialog = true">登记收款</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="filterOrderId" placeholder="筛选订单" clearable filterable style="width: 240px" @change="fetchData">
        <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} ${o.project_name}`" :value="o.id" />
      </el-select>
      <el-select v-model="filterCustomerId" placeholder="筛选客户" clearable filterable style="width: 200px; margin-left: 12px" @change="fetchData">
        <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-button style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="payment_no" label="收款编号" width="180" />
      <el-table-column label="金额" width="120">
        <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="payment_method" label="方式" width="100" />
      <el-table-column label="收款日期" width="120">
        <template #default="{ row }">{{ row.paid_at?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_voided ? 'danger' : 'success'" size="small">{{ row.is_voided ? '已作废' : '有效' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="180" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-if="!row.is_voided" text type="danger" size="small" @click="handleVoid(row as PaymentResponse)">作废</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next" style="margin-top: 16px; justify-content: flex-end" @change="fetchData" />

    <el-dialog v-model="showDialog" title="登记收款" width="480px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="订单">
          <el-select v-model="form.order_id" placeholder="选择订单" filterable style="width: 100%" @change="onOrderSelect">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} ${o.project_name}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款金额">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="收款方式">
          <el-select v-model="form.payment_method" style="width: 100%">
            <el-option label="银行转账" value="银行转账" />
            <el-option label="微信" value="微信" />
            <el-option label="支付宝" value="支付宝" />
            <el-option label="现金" value="现金" />
            <el-option label="支票" value="支票" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款日期">
          <el-date-picker v-model="form.paid_at" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleCreate">确认收款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getPayments, createPayment, voidPayment } from '@/api/payments'
import { getOrders } from '@/api/orders'
import { getCustomers } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PaymentResponse, OrderListResponse, CustomerResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<PaymentResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterOrderId = ref('')
const filterCustomerId = ref('')
const showDialog = ref(false)
const orderOptions = ref<OrderListResponse[]>([])
const customerOptions = ref<CustomerResponse[]>([])
const form = reactive({ order_id: '', customer_id: '', amount: 0, payment_method: '', paid_at: '', remark: '' })

async function fetchData() {
  loading.value = true
  try {
    const data = await getPayments({ page: page.value, page_size: pageSize.value, order_id: filterOrderId.value || undefined, customer_id: filterCustomerId.value || undefined })
    list.value = data.items; total.value = data.total
  } finally { loading.value = false }
}

async function loadOptions() {
  const [oRes, cRes] = await Promise.all([getOrders({ page_size: 200 }), getCustomers({ page_size: 200 })])
  orderOptions.value = oRes.items; customerOptions.value = cRes.items
}

function onOrderSelect(oid: string) {
  const o = orderOptions.value.find(o => o.id === oid)
  if (o) form.customer_id = o.customer_id
}

async function handleCreate() {
  saving.value = true
  try {
    const o = orderOptions.value.find(o => o.id === form.order_id)
    await createPayment({ ...form, customer_id: form.customer_id || (o as OrderListResponse)?.customer_id })
    ElMessage.success('收款登记成功')
    showDialog.value = false
    Object.assign(form, { order_id: '', customer_id: '', amount: 0, payment_method: '', paid_at: '', remark: '' })
    fetchData()
  } catch {
    // API error handled by interceptor
  } finally { saving.value = false }
}

async function handleVoid(row: PaymentResponse) {
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '作废收款', { confirmButtonText: '确定', cancelButtonText: '取消' })
    if (value) {
      await voidPayment(row.id, { void_reason: value })
      ElMessage.success('已作废')
      fetchData()
    }
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}

onMounted(() => { fetchData(); loadOptions() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
