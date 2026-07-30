<template>
  <div class="page">
    <div class="page-header">
      <h2>制作任务</h2>
    </div>

    <div class="search-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="fetchData">
        <el-option label="待制作" value="pending" />
        <el-option label="排队中" value="queued" />
        <el-option label="制作中" value="in_progress" />
        <el-option label="待质检" value="qc_check" />
        <el-option label="返工" value="rework" />
        <el-option label="已完成" value="completed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="production_no" label="任务编号" width="180" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="prodStatusColor(row.status)" size="small">{{ prodStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="数量" width="80">
        <template #default="{ row }">{{ row.quantity }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/production-tasks/${row.id}`)">详情</el-button>
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
import { ref, onMounted } from 'vue'
import { getProductionTasks } from '@/api/tasks'
import { ProductionTaskResponse } from '@/types/api'

const loading = ref(false)
const list = ref<ProductionTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')

function prodStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function prodStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success', cancelled: 'info' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getProductionTasks({ page: page.value, page_size: pageSize.value, status: filterStatus.value || undefined })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

onMounted(() => { fetchData() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
