<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="stmt" v-loading="loading">
      <div style="display: flex; justify-content: space-between; align-items: center; margin: 16px 0">
        <h2 style="margin: 0; color: var(--ad-text)">对账单 {{ stmt.statement_no }}</h2>
        <el-button v-if="stmt.status === 'draft'" type="success" @click="handleConfirm">确认对账单</el-button>
      </div>

      <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
        <el-descriptions :column="2">
          <el-descriptions-item label="客户">{{ stmt.customer_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="stmt.status === 'confirmed' ? 'success' : 'info'">{{ stmt.status === 'confirmed' ? '已确认' : '草稿' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="期间">{{ stmt.start_date?.slice(0, 10) }} ~ {{ stmt.end_date?.slice(0, 10) }}</el-descriptions-item>
          <el-descriptions-item label="确认时间">{{ stmt.confirmed_at?.slice(0, 19).replace('T', ' ') || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-bottom: 16px">
        <template #header><span>金额汇总</span></template>
        <el-row :gutter="24">
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">订单金额</div>
              <div class="stat-value">¥ {{ stmt.total_order_amount?.toFixed(2) }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">已收金额</div>
              <div class="stat-value" style="color: #22c55e">¥ {{ stmt.total_paid_amount?.toFixed(2) }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">未收金额</div>
              <div class="stat-value" style="color: #e63946">¥ {{ stmt.total_unpaid_amount?.toFixed(2) }}</div>
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
            <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="已收" width="120">
            <template #default="{ row }">¥ {{ row.paid_amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="未收" width="120">
            <template #default="{ row }">
              <span :style="{ color: row.unpaid_amount > 0 ? '#e63946' : '#22c55e' }">¥ {{ row.unpaid_amount?.toFixed(2) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="info-card">
        <template #header><span>收款记录</span></template>
        <el-table :data="stmt.payments || []" stripe size="small">
          <el-table-column prop="payment_no" label="收款编号" width="180" />
          <el-table-column label="金额" width="120">
            <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="payment_method" label="方式" width="100" />
          <el-table-column label="收款日期" width="120">
            <template #default="{ row }">{{ row.paid_at?.slice(0, 10) || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_voided ? 'danger' : 'success'" size="small">{{ row.is_voided ? '作废' : '有效' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getStatement, confirmStatement } from '@/api/payments'
import type { StatementDetailResponse } from '@/types/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const stmt = ref<StatementDetailResponse | null>(null)

async function fetchData() {
  loading.value = true
  try {
    stmt.value = await getStatement(route.params.id as string)
  } catch {
    // API error handled by interceptor
  } finally { loading.value = false }
}

async function handleConfirm() {
  try {
    await confirmStatement(route.params.id as string)
    ElMessage.success('对账单已确认')
    fetchData()
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.stat-item { text-align: center; padding: 16px 0; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.stat-value { font-size: 22px; font-weight: bold; color: var(--ad-text); }
</style>
