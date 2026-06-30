<template>
  <div class="page">
    <div class="page-header">
      <h2>报价管理</h2>
      <el-button type="danger" @click="$router.push('/quotes/new')">新建报价</el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="编号/项目名称" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已转订单" value="converted" />
            <el-option label="已作废" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="quote_no" label="报价编号" width="180" />
      <el-table-column prop="customer_name" label="客户名称" width="160" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="总金额" width="140">
        <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="有效期" width="120">
        <template #default="{ row }">{{ row.valid_until || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/quotes/${row.id}/edit`)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row as QuoteListResponse)">删除</el-button>
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
import { getQuotes, deleteQuote } from '@/api/quotes'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuoteListResponse } from '@/types/api'

const loading = ref(false)
const list = ref<QuoteListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({ keyword: '', status: '' })
const dateRange = ref<[string, string] | null>(null)

function statusLabel(s: string) {
  const map: Record<string, string> = { draft: '草稿', confirmed: '已确认', converted: '已转订单', cancelled: '已作废' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { draft: 'info', confirmed: 'success', converted: '', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filters.keyword ? { keyword: filters.keyword } : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(dateRange.value ? { date_from: dateRange.value[0], date_to: dateRange.value[1] } : {}),
    }
    const data = await getQuotes(params)
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
  dateRange.value = null
  page.value = 1
  fetchData()
}

async function handleDelete(row: QuoteListResponse) {
  await ElMessageBox.confirm(`确认删除报价 "${row.quote_no}"？`, '确认', { type: 'warning' })
  await deleteQuote(row.id)
  ElMessage.success('已删除')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
</style>
