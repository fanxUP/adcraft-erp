<template>
  <div class="page">
    <div class="page-header">
      <h2>客户协议价</h2>
      <el-button type="danger" @click="dialogVisible = true">新建协议</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="filterCustomerId" placeholder="选择客户" filterable clearable style="width: 300px" @change="fetchData">
        <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">查询</el-button>
    </div>

    <el-table :data="agreements" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column label="客户" min-width="160">
        <template #default="{ row }">{{ getCustomerName(row.customer_id) }}</template>
      </el-table-column>
      <el-table-column prop="pricing_method" label="计价方式" width="100">
        <template #default="{ row }">
          {{ { area: '面积', length: '长度', quantity: '数量', fixed: '固定' }[row.pricing_method] || row.pricing_method }}
        </template>
      </el-table-column>
      <el-table-column prop="price_value" label="协议价" width="120" />
      <el-table-column prop="minimum_charge" label="最低消费" width="120" />
      <el-table-column prop="discount_rate" label="折扣率" width="100">
        <template #default="{ row }">{{ (row.discount_rate * 100).toFixed(0) }}%</template>
      </el-table-column>
      <el-table-column prop="effective_from" label="生效日期" width="120" />
      <el-table-column prop="effective_to" label="失效日期" width="120" />
      <el-table-column prop="remark" label="备注" min-width="180" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button text type="danger" @click="handleDeleteAgreement(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建协议弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑客户协议价' : '新建客户协议价'" width="550px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户" required>
          <el-select v-model="form.customer_id" filterable style="width: 100%">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="计价方式" required>
          <el-select v-model="form.pricing_method">
            <el-option label="面积" value="area" />
            <el-option label="长度" value="length" />
            <el-option label="数量" value="quantity" />
            <el-option label="固定价" value="fixed" />
          </el-select>
        </el-form-item>
        <el-form-item label="协议价" required>
          <el-input-number v-model="form.price_value" :min="0" :precision="4" style="width: 200px" />
        </el-form-item>
        <el-form-item label="最低消费">
          <el-input-number v-model="form.minimum_charge" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="折扣率">
          <el-slider v-model="discountPercent" :min="0" :max="100" style="width: 300px" show-input />
        </el-form-item>
        <el-form-item label="生效日期" required>
          <el-input v-model="form.effective_from" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="失效日期">
          <el-input v-model="form.effective_to" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleCreate" :loading="submitting">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import {
  listCustomerAgreements,
  createCustomerAgreement,
  updateCustomerAgreement,
  deleteCustomerAgreement,
  type CustomerAgreement,
} from '@/api/cdrQuote'
import type { CustomerResponse, PaginatedData } from '@/types/api'

const loading = ref(false)
const submitting = ref(false)
const agreements = ref<CustomerAgreement[]>([])
const customers = ref<CustomerResponse[]>([])
const filterCustomerId = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)

const discountPercent = computed({
  get: () => Math.round((form.value.discount_rate || 1) * 100),
  set: (v: number) => { form.value.discount_rate = v / 100 },
})

const form = ref({
  customer_id: '',
  pricing_method: 'area',
  price_value: 0,
  minimum_charge: 0,
  discount_rate: 1,
  effective_from: '',
  effective_to: '',
  remark: '',
})

async function fetchCustomers() {
  try {
    const response = await api.get<PaginatedData<CustomerResponse>>('/customers')
    customers.value = response.items
  } catch { /* ignore */ }
}

function getCustomerName(id: string): string {
  return customers.value.find(c => c.id === id)?.name || id
}

async function fetchData() {
  loading.value = true
  try {
    agreements.value = await listCustomerAgreements(filterCustomerId.value || undefined)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (editingId.value) {
    // Update existing
    if (!form.value.customer_id) { ElMessage.warning('请选择客户'); return }
    submitting.value = true
    try {
      await updateCustomerAgreement(editingId.value, { ...form.value, discount_rate: form.value.discount_rate })
      ElMessage.success('更新成功')
      dialogVisible.value = false
      editingId.value = null
      form.value = { customer_id: '', pricing_method: 'area', price_value: 0, minimum_charge: 0, discount_rate: 1, effective_from: '', effective_to: '', remark: '' }
      await fetchData()
    } finally { submitting.value = false }
    return
  }
  if (!form.value.customer_id) {
    ElMessage.warning('请选择客户')
    return
  }
  submitting.value = true
  try {
    await createCustomerAgreement({ ...form.value, discount_rate: form.value.discount_rate })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    form.value = { customer_id: '', pricing_method: 'area', price_value: 0, minimum_charge: 0, discount_rate: 1, effective_from: '', effective_to: '', remark: '' }
    await fetchData()
  } finally {
    submitting.value = false
  }
}

function openEdit(row: CustomerAgreement) {
  editingId.value = row.id
  form.value = {
    customer_id: row.customer_id,
    pricing_method: row.pricing_method,
    price_value: Number(row.price_value),
    minimum_charge: Number(row.minimum_charge),
    discount_rate: Number(row.discount_rate),
    effective_from: row.effective_from,
    effective_to: row.effective_to || '',
    remark: row.remark || '',
  }
  dialogVisible.value = true
}

async function handleDeleteAgreement(id: string) {
  await ElMessageBox.confirm('确认删除该协议价？', '确认', { type: 'warning' })
  await deleteCustomerAgreement(id)
  ElMessage.success('已删除')
  fetchData()
}

onMounted(() => { fetchCustomers(); fetchData() })
</script>
