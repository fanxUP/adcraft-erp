<template>
  <div class="page">
    <div class="page-header">
      <h2>外协付款</h2>
      <el-button type="danger" @click="handleCreate">新建付款</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无外协付款记录">
      <el-table-column prop="payment_no" label="付款编号" width="160" />
      <el-table-column prop="vendor_name" label="外协商" width="150" />
      <el-table-column prop="amount" label="金额" width="140" align="right">
        <template #default="{ row }">¥{{ row.amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="付款方式" width="120">
        <template #default="{ row }">{{ paymentMethodLabel(row.payment_method) }}</template>
      </el-table-column>
      <el-table-column prop="paid_at" label="付款日期" width="180" />
      <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <el-dialog v-model="dialogVisible" title="新建外协付款" width="500px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="外协商" prop="vendor_id">
          <el-select v-model="form.vendor_id" filterable clearable style="width: 100%">
            <el-option v-for="v in vendors" :key="v.id" :label="v.name" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="form.payment_method" clearable style="width: 100%">
            <el-option label="银行转账" value="bank_transfer" />
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="现金" value="cash" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款日期">
          <el-date-picker v-model="form.paid_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import {
  getOutsourceVendors, getOutsourcePayments, createOutsourcePayment,
} from '@/api/outsource'
import { ElMessage } from 'element-plus'
import { OutsourcePaymentResponse, VendorResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<OutsourcePaymentResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const vendors = ref<VendorResponse[]>([])
const form = reactive({
  vendor_id: '', amount: 0, payment_method: 'bank_transfer', paid_at: '', remark: '',
})
const rules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
}

function paymentMethodLabel(val: string | null) {
  const map: Record<string, string> = { bank_transfer: '银行转账', wechat: '微信', alipay: '支付宝', cash: '现金' }
  return map[val || ''] || val || '-'
}

async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 100 })
    vendors.value = data.items
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getOutsourcePayments({ page: page.value, page_size: pageSize.value })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  Object.assign(form, { vendor_id: '', amount: 0, payment_method: 'bank_transfer', paid_at: '', remark: '' })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    await createOutsourcePayment(form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

onMounted(() => { fetchData(); loadVendors() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
</style>
