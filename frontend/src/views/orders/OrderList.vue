<template>
  <div class="page">
    <div class="page-header">
      <h2>订单管理</h2>
      <el-button v-if="authStore.isAdmin" type="warning" @click="$router.push('/orders/recycle')">
        <el-icon><Delete /></el-icon> 回收站
      </el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="订单编号/项目名称" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="待确认" value="pending_confirm" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="设计中" value="designing" />
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

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="order_no" label="订单编号" width="180" />
      <el-table-column prop="customer_name" label="客户名称" width="160" />
      <el-table-column prop="department" label="部门/科室" width="130" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="总金额" width="120">
        <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="已收" width="110">
        <template #default="{ row }">¥ {{ row.paid_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="未收" width="110">
        <template #default="{ row }">¥ {{ row.unpaid_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="毛利" width="100">
        <template #default="{ row }">
          <span :style="{ color: (row.gross_profit || 0) >= 0 ? '#67c23a' : '#f56c6c' }">
            ¥ {{ row.gross_profit?.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="120">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <div style="display: flex; gap: 8px; justify-content: center;">
            <el-button text type="primary" @click="$router.push(`/orders/${row.id}`)">详情</el-button>
            <el-button v-if="row.status !== 'cancelled'" text type="danger" @click="handleCancel(row as OrderListResponse)">取消</el-button>
            <el-button v-if="row.status === 'cancelled'" text type="warning" @click="handleConvertToQuote(row as OrderListResponse)">转报价</el-button>
          </div>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOrders, changeOrderStatus, convertOrderToQuote } from '@/api/orders'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { OrderListResponse } from '@/types/api'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const list = ref<OrderListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({ keyword: '', status: '' })

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', designing: '设计中',
    in_production: '生产中', in_installation: '安装中', completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', designing: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filters.keyword ? { keyword: filters.keyword } : {}),
      ...(filters.status ? { status: filters.status } : {}),
    }
    const data = await getOrders(params)
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  page.value = 1
  fetchData()
}

async function handleCancel(row: OrderListResponse) {
  await ElMessageBox.confirm(`确定取消订单「${row.order_no}」？订单将移入回收站。`, '取消订单', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await changeOrderStatus(row.id, { to_status: 'cancelled' })
  ElMessage.success('订单已取消，已移入回收站')
  fetchData()
}

async function handleConvertToQuote(row: OrderListResponse) {
  await ElMessageBox.confirm(`确定将订单「${row.order_no}」转为报价单？`, '转报价', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await convertOrderToQuote(row.id)
  ElMessage.success('订单已转为报价单')
  router.push('/quotes')
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
</style>
