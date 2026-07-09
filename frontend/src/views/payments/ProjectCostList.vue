<template>
  <div class="page">
    <div class="page-header">
      <h2>项目成本</h2>
    </div>

    <!-- Unified filter -->
    <el-card shadow="never" class="filter-card">
      <el-form inline>
        <el-form-item label="类型">
          <el-select v-model="filterType" clearable placeholder="全部" style="width: 120px" @change="handleSearch">
            <el-option label="订单" value="order" />
            <el-option label="报价单" value="quote" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="keyword" placeholder="编号/项目名称" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item v-if="filterType !== 'quote'" label="状态">
          <el-select v-model="statusFilter" clearable placeholder="全部" style="width: 120px" @change="handleSearch">
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

    <!-- Unified table -->
    <el-table :data="combinedList" v-loading="loading" stripe style="margin-top: 16px" row-key="id">
      <el-table-column label="类型" width="90" fixed>
        <template #default="{ row }">
          <el-tag v-if="row._type === 'order'" type="primary" size="small">订单</el-tag>
          <el-tag v-else type="success" size="small">报价单</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="编号" width="180">
        <template #default="{ row }">{{ row._type === 'order' ? row.order_no : row.quote_no }}</template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
      <el-table-column label="客户" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.customer_name || '-' }}</template>
      </el-table-column>
      <el-table-column v-if="filterType !== 'quote'" label="状态" width="110">
        <template #default="{ row }">
          <el-tag v-if="row._type === 'order'" :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="120" align="right">
        <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="项目成本" width="120" align="right">
        <template #default="{ row }">
          <span v-if="row._type === 'order'" :style="{ color: (costMap[row.id] || 0) > 0 ? '#e6a23c' : '' }">
            ¥ {{ (costMap[row.id] || 0).toFixed(2) }}
          </span>
          <span v-else :style="{ color: (row.cost_amount || 0) > 0 ? '#e6a23c' : '' }">
            ¥ {{ (row.cost_amount || 0).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="110">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" size="small" @click="$router.push(row._type === 'order' ? `/project-costs/${row.id}` : `/quote-costs/${row.id}`)">
            登记成本
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="totalCount"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getOrders } from '@/api/orders'
import { getProjectCostSummary, getQuotesForCost } from '@/api/payments'
import type { OrderListResponse, QuoteCostResponse } from '@/types/api'

const loading = ref(false)
const keyword = ref('')
const filterType = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(20)

// Internal storage
type CombinedRow = (OrderListResponse | QuoteCostResponse) & {
  _type: 'order' | 'quote'
  _sortKey: string
}

const allRows = ref<CombinedRow[]>([])

// Cost summary map for orders
const costMap = ref<Record<string, number>>({})

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

// Total count for pagination (client-side filtered)
const totalCount = computed(() => {
  let list = allRows.value
  if (filterType.value) {
    list = list.filter(r => r._type === filterType.value)
  }
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(r => {
      const no = r._type === 'order' ? (r as unknown as Record<string, unknown>).order_no : (r as unknown as Record<string, unknown>).quote_no
      return (no?.toLowerCase().includes(kw)) || (r.project_name?.toLowerCase().includes(kw))
    })
  }
  if (statusFilter.value) {
    list = list.filter(r => r._type === 'order' && (r as unknown as Record<string, unknown>).status === statusFilter.value)
  }
  return list.length
})

// Client-side paginated & filtered view
const combinedList = computed(() => {
  let list = allRows.value

  // Client-side type filter
  if (filterType.value) {
    list = list.filter(r => r._type === filterType.value)
  }
  // Keyword filter
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(r => {
      const no = r._type === 'order' ? (r as unknown as Record<string, unknown>).order_no : (r as unknown as Record<string, unknown>).quote_no
      return (no?.toLowerCase().includes(kw)) || (r.project_name?.toLowerCase().includes(kw))
    })
  }
  // Status filter (only for orders)
  if (statusFilter.value) {
    list = list.filter(r => r._type === 'order' && (r as unknown as Record<string, unknown>).status === statusFilter.value)
  }

  // Sort by _sortKey (created_at) descending
  const sorted = [...list].sort((a, b) => b._sortKey.localeCompare(a._sortKey))

  // Paginate
  const start = (page.value - 1) * pageSize.value
  return sorted.slice(start, start + pageSize.value)
})

async function fetchData() {
  loading.value = true
  try {
    const orderParams: Record<string, unknown> = { page: 1, page_size: 100 }
    const quoteParams: Record<string, unknown> = { page: 1, page_size: 100 }

    // Fetch both
    const [orderData, quoteData] = await Promise.all([
      getOrders(orderParams),
      getQuotesForCost(quoteParams),
    ])

    // Build order rows
    const orders: CombinedRow[] = (orderData.items || []).map((o: OrderListResponse) => ({
      ...o,
      _type: 'order' as const,
      _sortKey: o.created_at || '',
    }))

    // Build quote rows
    const quotes: CombinedRow[] = (quoteData.items || []).map((q: QuoteCostResponse) => ({
      ...q,
      _type: 'quote' as const,
      _sortKey: q.created_at || '',
    }))

    allRows.value = [...orders, ...quotes]

    // Fetch cost summaries for orders
    if (orders.length > 0) {
      const ids = orders.map(o => o.id)
      try {
        const summary = await getProjectCostSummary(ids)
        costMap.value = summary.costs
      } catch { /* ignore */ }
    } else {
      costMap.value = {}
    }
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  // For client-side filtering, just re-compute
}

function handleReset() {
  keyword.value = ''
  filterType.value = ''
  statusFilter.value = ''
  page.value = 1
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
</style>
