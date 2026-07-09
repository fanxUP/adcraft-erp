<template>
  <div class="page">
    <div class="page-header">
      <h2>项目成本</h2>
    </div>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="订单成本" name="order">
        <el-card shadow="never" class="filter-card">
          <el-form :model="orderFilters" inline>
            <el-form-item label="关键词">
              <el-input v-model="orderFilters.keyword" placeholder="订单编号/项目名称" clearable style="width: 220px" @keyup.enter="handleSearch" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="orderFilters.status" clearable placeholder="全部" style="width: 120px">
                <el-option label="待确认" value="pending_confirm" />
                <el-option label="已确认" value="confirmed" />
                <el-option label="进行中" value="in_progress" />
                <el-option label="生产中" value="in_production" />
                <el-option label="安装中" value="in_installation" />
                <el-option label="已完成" value="completed" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">搜索</el-button>
              <el-button @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-table :data="orderList" v-loading="orderLoading" stripe style="margin-top: 16px">
          <el-table-column prop="order_no" label="订单编号" width="180" />
          <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="客户" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.customer_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="订单金额" width="120" align="right">
            <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="项目成本" width="120" align="right">
            <template #default="{ row }">
              <span :style="{ color: (costMap[row.id] || 0) > 0 ? '#e6a23c' : '' }">
                ¥ {{ (costMap[row.id] || 0).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="110">
            <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="$router.push(`/project-costs/${row.id}`)">登记成本</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="orderPage"
          v-model:page-size="orderPageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="orderTotal"
          layout="total, sizes, prev, pager, next"
          style="margin-top: 16px; justify-content: flex-end"
          @change="fetchOrders"
        />
      </el-tab-pane>

      <el-tab-pane label="报价单成本" name="quote">
        <el-card shadow="never" class="filter-card">
          <el-form :model="quoteFilters" inline>
            <el-form-item label="关键词">
              <el-input v-model="quoteFilters.keyword" placeholder="报价单编号/项目名称" clearable style="width: 220px" @keyup.enter="handleSearch" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">搜索</el-button>
              <el-button @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-table :data="quoteList" v-loading="quoteLoading" stripe style="margin-top: 16px">
          <el-table-column prop="quote_no" label="报价单编号" width="180" />
          <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="客户" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.customer_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="报价金额" width="120" align="right">
            <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="项目成本" width="120" align="right">
            <template #default="{ row }">
              <span :style="{ color: (row.cost_amount || 0) > 0 ? '#e6a23c' : '' }">
                ¥ {{ (row.cost_amount || 0).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="$router.push(`/quote-costs/${row.id}`)">登记成本</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="quotePage"
          v-model:page-size="quotePageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="quoteTotal"
          layout="total, sizes, prev, pager, next"
          style="margin-top: 16px; justify-content: flex-end"
          @change="fetchQuotes"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getOrders } from '@/api/orders'
import { getProjectCostSummary, getQuotesForCost } from '@/api/payments'
import type { OrderListResponse, QuoteCostResponse } from '@/types/api'

const activeTab = ref('order')

// ── Orders ──
const orderLoading = ref(false)
const orderList = ref<OrderListResponse[]>([])
const orderTotal = ref(0)
const orderPage = ref(1)
const orderPageSize = ref(20)
const costMap = ref<Record<string, number>>({})
const orderFilters = reactive({ keyword: '', status: '' })

// ── Quotes ──
const quoteLoading = ref(false)
const quoteList = ref<QuoteCostResponse[]>([])
const quoteTotal = ref(0)
const quotePage = ref(1)
const quotePageSize = ref(20)
const quoteFilters = reactive({ keyword: '' })

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchOrders() {
  orderLoading.value = true
  try {
    const params: Record<string, unknown> = { page: orderPage.value, page_size: orderPageSize.value }
    if (orderFilters.keyword) params.keyword = orderFilters.keyword
    if (orderFilters.status) params.status = orderFilters.status
    const data = await getOrders(params)
    orderList.value = data.items
    orderTotal.value = data.total
    if (data.items.length > 0) {
      const ids = data.items.map((o: OrderListResponse) => o.id)
      try {
        const summary = await getProjectCostSummary(ids)
        costMap.value = summary.costs
      } catch { /* ignore */ }
    }
  } finally { orderLoading.value = false }
}

async function fetchQuotes() {
  quoteLoading.value = true
  try {
    const params: Record<string, unknown> = { page: quotePage.value, page_size: quotePageSize.value }
    if (quoteFilters.keyword) params.keyword = quoteFilters.keyword
    const data = await getQuotesForCost(params)
    quoteList.value = data.items
    quoteTotal.value = data.total
  } finally { quoteLoading.value = false }
}

function handleSearch() {
  if (activeTab.value === 'order') {
    orderPage.value = 1
    fetchOrders()
  } else {
    quotePage.value = 1
    fetchQuotes()
  }
}

function handleReset() {
  if (activeTab.value === 'order') {
    orderFilters.keyword = ''
    orderFilters.status = ''
    orderPage.value = 1
    fetchOrders()
  } else {
    quoteFilters.keyword = ''
    quotePage.value = 1
    fetchQuotes()
  }
}

function handleTabChange() {
  if (activeTab.value === 'quote' && quoteList.value.length === 0) {
    fetchQuotes()
  }
}

onMounted(fetchOrders)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
</style>
