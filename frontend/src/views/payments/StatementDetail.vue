<template>
  <AppPage class="page">
    <PageHeader
      :title="stmt ? `对账单 ${stmt.statement_no}` : '对账单详情'"
      :description="stmt ? `${formatDate(stmt.start_date)} ~ ${formatDate(stmt.end_date)}` : '查看对账单金额与收款记录'"
    >
      <template #actions>
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <el-button v-if="stmt" @click="handlePrintView" type="primary" plain>
          <el-icon><Printer /></el-icon> 打印
        </el-button>
        <el-button v-if="stmt && (stmt.capabilities?.confirm?.allowed ?? stmt.status === 'draft')" @click="handleConfirm" type="primary">确认对账单</el-button>
      </template>
    </PageHeader>

    <StatePanel
      v-if="loadError && !stmt"
      state="error"
      action-label="重试"
      @action="fetchData"
    />

    <div v-else-if="stmt" v-loading="loading">
      <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
        <el-descriptions :column="2">
          <el-descriptions-item label="客户">{{ stmt.customer_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <StatusTag :status="stmt.status_view || stmt.status" size="sm" />
          </el-descriptions-item>
          <el-descriptions-item label="期间">{{ formatDate(stmt.start_date) }} ~ {{ formatDate(stmt.end_date) }}</el-descriptions-item>
          <el-descriptions-item label="确认时间">{{ formatDateTimeFull(stmt.confirmed_at) || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
        <template #header><span>金额汇总</span></template>
        <el-row :gutter="24">
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">订单金额</div>
              <div class="stat-value">{{ formatMoney(stmt.total_order_amount) }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">已收金额</div>
              <div class="stat-value text-success">{{ formatMoney(stmt.total_paid_amount) }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">未收金额</div>
              <div class="stat-value text-danger">{{ formatMoney(stmt.total_unpaid_amount) }}</div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
        <template #header><span>订单明细</span></template>
        <el-table :data="stmt.orders || []" stripe size="small">
          <el-table-column prop="order_no" label="订单编号" width="180" />
          <el-table-column prop="project_name" label="项目名称" min-width="200" />
          <el-table-column label="订单金额" width="120">
            <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
          </el-table-column>
          <el-table-column label="已收" width="120">
            <template #default="{ row }">{{ formatMoney(row.paid_amount) }}</template>
          </el-table-column>
          <el-table-column label="未收" width="120">
            <template #default="{ row }">
              <span :class="row.unpaid_amount > 0 ? 'text-danger' : 'text-success'">{{ formatMoney(row.unpaid_amount) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="info-card">
        <template #header><span>收款记录</span></template>
        <el-table :data="stmt.payments || []" stripe size="small">
          <el-table-column prop="payment_no" label="收款编号" width="180" />
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="payment_method" label="方式" width="100" />
          <el-table-column label="收款日期" width="120">
            <template #default="{ row }">{{ formatDate(row.paid_at) || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <StatusTag :status="row.status_view || (row.is_voided ? 'voided' : 'active')" size="sm" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </AppPage>
</template>

<script setup lang="ts">
import { formatDate, formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { Printer } from '@element-plus/icons-vue'
import { usePrint } from '@/composables/usePrint'
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getStatement, confirmStatement } from '@/api/payments'
import type { StatementDetailResponse } from '@/types/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, PageHeader, StatePanel, StatusTag } from '@/components/ui'

const route = useRoute()
const loading = ref(false)
const stmt = ref<StatementDetailResponse | null>(null)
const loadError = ref(false)

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    stmt.value = await getStatement(route.params.id as string)
  } catch {
    loadError.value = true
  } finally { loading.value = false }
}

async function handleConfirm() {
  await ElMessageBox.confirm('确认后对账单将锁定不可修改，确定确认？', '确认对账单', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  try {
    await confirmStatement(route.params.id as string)
    ElMessage.success('对账单已确认')
    fetchData()
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}


const { handlePrintBySelector } = usePrint()
function handlePrintView() {
  handlePrintBySelector('.page')
}
onMounted(fetchData)
</script>

<style scoped>
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.stat-item { text-align: center; padding: 16px 0; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: bold; color: var(--ad-text); }
</style>
