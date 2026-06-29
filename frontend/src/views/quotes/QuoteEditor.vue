<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <h2 style="margin: 16px 0; color: var(--ad-text)">{{ isEdit ? '编辑报价' : '新建报价' }}</h2>

    <el-card shadow="never" class="section-card">
      <el-form :model="form" label-width="100px" inline>
        <el-form-item label="客户" required>
          <el-select v-model="form.customer_id" placeholder="选择客户" filterable remote :remote-method="searchCustomers" style="width: 260px">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.project_name" style="width: 260px" />
        </el-form-item>
        <el-form-item label="税率">
          <el-input-number v-model="form.tax_rate" :precision="4" :min="0" :step="0.01" style="width: 160px" />
        </el-form-item>
        <el-form-item label="有效期">
          <el-date-picker v-model="form.valid_until" type="date" value-format="YYYY-MM-DD" style="width: 160px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" style="width: 260px" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>报价明细</span>
          <el-button type="danger" size="small" @click="addItem">添加行</el-button>
        </div>
      </template>

      <el-table :data="items" stripe border>
        <el-table-column label="项目名称" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.item_name" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="长(m)" width="90">
          <template #default="{ row }">
            <el-input-number v-model="row.length" :precision="3" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="宽(m)" width="90">
          <template #default="{ row }">
            <el-input-number v-model="row.width" :precision="3" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="数量" width="90">
          <template #default="{ row }">
            <el-input-number v-model="row.quantity" :precision="3" :min="0.001" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="面积" width="90">
          <template #default="{ row }">{{ calcArea(row as QuoteItemResponse).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="单价" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.unit_price" :precision="2" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="工艺费" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.process_fee" :precision="2" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="安装费" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.installation_fee" :precision="2" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="设计费" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.design_fee" :precision="2" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="运输费" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.transport_fee" :precision="2" :min="0" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="小计" width="120">
          <template #default="{ row }">¥ {{ calcSubtotal(row as QuoteItemResponse).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button text type="danger" size="small" @click="items.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <el-row :gutter="20">
        <el-col :span="16" />
        <el-col :span="8">
          <div class="summary-item"><span>明细合计：</span><strong>¥ {{ calcQuoteSubtotal().toFixed(2) }}</strong></div>
          <div class="summary-item">
            <span>优惠金额：</span>
            <el-input-number v-model="form.discount_amount" :precision="2" :min="0" size="small" style="width: 140px" />
          </div>
          <div class="summary-item"><span>税额：</span><strong>¥ {{ calcTax().toFixed(2) }}</strong></div>
          <div class="summary-item total"><span>总计：</span><strong>¥ {{ calcTotal().toFixed(2) }}</strong></div>
        </el-col>
      </el-row>
    </el-card>

    <div style="margin-top: 24px; display: flex; gap: 12px">
      <el-button type="primary" :loading="saving" @click="handleSave">保存草稿</el-button>
      <el-button type="warning" :loading="calculating" @click="handleCalculate">服务端计算</el-button>
      <el-button v-if="isEdit && quote?.status === 'draft'" type="success" @click="handleConfirm">确认报价</el-button>
      <el-button v-if="isEdit && quote?.status === 'confirmed'" type="danger" :loading="converting" @click="handleConvert">转订单</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createQuote, getQuote, updateQuote, calculateQuote, confirmQuote, convertQuoteToOrder } from '@/api/quotes'
import { getCustomers } from '@/api/customers'
import { ElMessage } from 'element-plus'
import type { QuoteItemResponse, QuoteDetailResponse, CustomerResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()
const isEdit = !!route.params.id
const saving = ref(false)
const calculating = ref(false)
const converting = ref(false)
const quote = ref<QuoteDetailResponse | null>(null)
const customerOptions = ref<CustomerResponse[]>([])

const form = reactive({
  customer_id: '',
  project_name: '',
  tax_rate: 0,
  discount_amount: 0,
  valid_until: '',
  remark: '',
})

const newItem = (): QuoteItemResponse => ({
  id: '',
  quote_id: '',
  item_name: '',
  length: undefined,
  width: undefined,
  height: undefined,
  quantity: 1,
  unit: '㎡',
  unit_price: 0,
  process_fee: 0,
  installation_fee: 0,
  design_fee: 0,
  transport_fee: 0,
  other_fee: 0,
  subtotal_amount: 0,
  sort_order: 0,
})

const items = ref<QuoteItemResponse[]>([newItem()])

function calcArea(item: QuoteItemResponse) { return (item.length || 0) * (item.width || 0) * (item.quantity || 0) }
function calcSubtotal(item: QuoteItemResponse) { return calcArea(item) * (item.unit_price || 0) + (item.process_fee || 0) + (item.installation_fee || 0) + (item.design_fee || 0) + (item.transport_fee || 0) + (item.other_fee || 0) }
function calcQuoteSubtotal() { return items.value.reduce((s, i) => s + calcSubtotal(i), 0) }
function calcTax() { return (calcQuoteSubtotal() - (form.discount_amount || 0)) * (form.tax_rate || 0) }
function calcTotal() { return calcQuoteSubtotal() - (form.discount_amount || 0) + calcTax() }

function addItem() { items.value.push(newItem()) }

async function searchCustomers(query: string) {
  if (query) {
    const data = await getCustomers({ keyword: query, page_size: 50 })
    customerOptions.value = data.items
  }
}

async function fetchQuote() {
  quote.value = await getQuote(route.params.id as string)
  Object.assign(form, {
    customer_id: quote.value.customer_id,
    project_name: quote.value.project_name,
    tax_rate: quote.value.tax_rate,
    discount_amount: quote.value.discount_amount,
    valid_until: quote.value.valid_until || '',
    remark: quote.value.remark || '',
  })
  items.value = quote.value.items?.length ? quote.value.items.map(i => ({ ...i })) : [newItem()]
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form, items: items.value }
    if (isEdit) {
      await updateQuote(route.params.id as string, { project_name: form.project_name, tax_rate: form.tax_rate, discount_amount: form.discount_amount, valid_until: form.valid_until || undefined, remark: form.remark })
      ElMessage.success('保存成功')
    } else {
      const result = await createQuote(payload)
      ElMessage.success('创建成功')
      router.push(`/quotes/${result.id}/edit`)
    }
  } finally { saving.value = false }
}

async function handleCalculate() {
  if (!isEdit) { ElMessage.warning('请先保存草稿'); return }
  calculating.value = true
  try {
    quote.value = await calculateQuote(route.params.id as string)
    Object.assign(form, {
      tax_rate: quote.value.tax_rate,
      discount_amount: quote.value.discount_amount,
    })
    items.value = quote.value.items?.length ? quote.value.items.map(i => ({ ...i })) : items.value
    ElMessage.success('计算完成')
  } finally { calculating.value = false }
}

async function handleConfirm() {
  await confirmQuote(route.params.id as string)
  ElMessage.success('报价已确认')
  fetchQuote()
}

async function handleConvert() {
  converting.value = true
  try {
    const order = await convertQuoteToOrder(route.params.id as string)
    ElMessage.success('已转为订单')
    router.push(`/orders/${order.order_id || order.id}`)
  } finally { converting.value = false }
}

onMounted(async () => {
  if (isEdit) await fetchQuote()
})
</script>

<style scoped>
.page { padding: 0; }
.section-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.summary-item { margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.summary-item.total { font-size: 18px; color: #e63946; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--ad-border); }
</style>
