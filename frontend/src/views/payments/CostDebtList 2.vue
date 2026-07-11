<template>
  <div class="page">
    <div class="page-header">
      <h2>成本欠款</h2>
      <div class="summary-bar">
        <span style="color: #e6a23c; font-weight: bold; font-size: 16px">
          待结清欠款：¥ {{ pendingTotal.toFixed(2) }}
        </span>
      </div>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="订单编号/项目名称/客户" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.is_settled" clearable placeholder="全部" style="width: 120px" @change="handleSearch">
            <el-option label="待结清" :value="false" />
            <el-option label="已结清" :value="true" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="cost_no" label="成本编号" width="160" />
      <el-table-column prop="order_no" label="订单编号" width="160" />
      <el-table-column prop="project_name" label="项目名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="customer_name" label="客户" min-width="120" show-overflow-tooltip />
      <el-table-column label="成本类别" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="成本金额" width="120" align="right">
        <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="欠款金额" width="120" align="right">
        <template #default="{ row }">
          <span style="color: #e6a23c; font-weight: bold">¥ {{ row.debt_amount?.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="!row.is_settled" type="danger" size="small">待结清</el-tag>
          <el-tag v-else type="success" size="small">已结清</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="日期" width="110">
        <template #default="{ row }">{{ row.cost_date?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.is_settled"
            type="success"
            size="small"
            @click="openSettle(row)"
          >
            冲红结清
          </el-button>
          <span v-else style="color: #c0c4cc; font-size: 12px">{{ row.settled_at?.slice(0, 10) }}</span>
        </template>
      </el-table-column>
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

    <!-- Settle Dialog -->
    <el-dialog v-model="showSettle" title="冲红结清欠款" width="480px" :close-on-click-modal="false">
      <el-form :model="settleForm" label-width="100px">
        <el-form-item label="成本编号">
          <el-input :value="settleTarget?.cost_no" disabled />
        </el-form-item>
        <el-form-item label="订单编号">
          <el-input :value="settleTarget?.order_no" disabled />
        </el-form-item>
        <el-form-item label="欠款金额" required>
          <el-input-number v-model="settleForm.settle_amount" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="支付方式" required>
          <el-select v-model="settleForm.payment_method" placeholder="选择付款方式" style="width: 100%">
            <el-option v-for="pm in PAYMENT_METHODS" :key="pm" :label="pm" :value="pm" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="settleForm.remark" type="textarea" :rows="2" placeholder="结清备注…" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettle = false">取消</el-button>
        <el-button type="success" :loading="settling" @click="handleSettle">确认冲红结清</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { getCostDebts, settleCostDebt } from '@/api/payments'
import { ElMessage } from 'element-plus'
import type { DebtResponse } from '@/types/api'

const PAYMENT_METHODS = ['现金支付', '微信支付', '转账支付', '对公支付', '其它支付']

const loading = ref(false)
const settling = ref(false)
const list = ref<DebtResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const showSettle = ref(false)
const settleTarget = ref<DebtResponse | null>(null)

const filters = reactive({
  keyword: '',
  is_settled: undefined as boolean | undefined,
})

const pendingTotal = computed(() => {
  return list.value
    .filter(d => !d.is_settled)
    .reduce((sum, d) => sum + (d.debt_amount || 0), 0)
})

const settleForm = reactive({
  settle_amount: 0,
  payment_method: '转账支付',
  remark: '',
})

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.is_settled !== undefined) params.is_settled = filters.is_settled
    const data = await getCostDebts(params)
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleReset() {
  filters.keyword = ''
  filters.is_settled = undefined
  page.value = 1
  fetchData()
}

function openSettle(row: DebtResponse) {
  settleTarget.value = row
  settleForm.settle_amount = row.debt_amount
  settleForm.payment_method = '转账支付'
  settleForm.remark = ''
  showSettle.value = true
}

async function handleSettle() {
  if (!settleTarget.value) return
  settling.value = true
  try {
    await settleCostDebt(settleTarget.value.id, {
      settle_amount: settleForm.settle_amount,
      payment_method: settleForm.payment_method,
      remark: settleForm.remark || undefined,
    })
    ElMessage.success('欠款已冲红结清')
    showSettle.value = false
    fetchData()
  } catch {
    // handled by interceptor
  } finally {
    settling.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.summary-bar { display: flex; align-items: center; gap: 8px; }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
</style>
