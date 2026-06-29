<template>
  <div class="page">
    <div class="page-header">
      <h2>报价管理</h2>
      <el-button type="danger" @click="$router.push('/quotes/new')">新建报价</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="quote_no" label="报价编号" width="180" />
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
          <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getQuotes, deleteQuote } from '@/api/quotes'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

function statusLabel(s: string) {
  const map: Record<string, string> = { draft: '草稿', confirmed: '已确认', converted: '已转订单', cancelled: '已作废' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { draft: 'info', confirmed: 'success', converted: '', cancelled: 'danger' }
  return map[s] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getQuotes({ page: page.value, page_size: pageSize.value })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

async function handleDelete(row: any) {
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
</style>
