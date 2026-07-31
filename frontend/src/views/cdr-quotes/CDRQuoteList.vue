<template>
  <div class="page">
    <div class="page-header">
      <h2>智能报价</h2>
      <div>
        <el-button type="danger" @click="handleNewQuote">新建报价</el-button>
      </div>
    </div>

    <el-table :data="quotes" v-loading="loading" stripe>
      <el-table-column prop="quote_no" label="报价单号" width="180" />
      <el-table-column label="客户" min-width="160">
        <template #default="{ row }">{{ row.customer_name || row.customer?.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column prop="total_amount" label="总金额" width="120">
        <template #default="{ row }">¥{{ Number(row.total_amount || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="viewDetail(row)">详情</el-button>
          <el-button text type="primary" @click="editQuote(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listCDRQuotes, type CDRQuote } from '@/api/cdrQuote'

const router = useRouter()
const loading = ref(false)
const quotes = ref<CDRQuote[]>([])

function statusType(s: string): string {
  return { draft: 'info', confirmed: 'success', cancelled: 'danger', converted: 'warning' }[s] || 'info'
}

function statusLabel(s: string): string {
  return { draft: '草稿', confirmed: '已确认', cancelled: '已取消', converted: '已转订单' }[s] || s
}

async function fetchData() {
  loading.value = true
  try {
    const res = await listCDRQuotes({ page: 1, page_size: 100 })
    quotes.value = res.items || []
  } finally {
    loading.value = false
  }
}

function handleNewQuote() {
  router.push('/cdr/quotes/new')
}

function viewDetail(row: CDRQuote) {
  router.push(`/cdr/quotes/${row.id}`)
}

function editQuote(row: CDRQuote) {
  router.push(`/cdr/quotes/${row.id}/edit`)
}

onMounted(fetchData)
</script>
