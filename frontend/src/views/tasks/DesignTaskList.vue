<template>
  <div class="page">
    <div class="page-header">
      <h2>设计任务</h2>
    </div>

    <div class="search-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="fetchData">
        <el-option label="待分配" value="pending" />
        <el-option label="设计中" value="designing" />
        <el-option label="待确认" value="pending_review" />
        <el-option label="需修改" value="revision" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

          <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
        <el-table-column prop="design_no" label="业务单号" width="180" />
        <el-table-column prop="source" label="来源" width="80" />
        <el-table-column prop="order_no" label="关联编号" width="180" />
        <el-table-column prop="customer_name" label="客户" min-width="160" />
        <el-table-column prop="department" label="部门/科室" width="120" />
        <el-table-column prop="project_name" label="项目名称" min-width="200" />
        <el-table-column label="金额" width="100">
          <template #default="{ row }">{{ row.total_amount ? '¥' + row.total_amount.toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="designStatusColor(row.status)" size="small">{{ designStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="派发" width="90">
          <template #default="{ row }">{{ row.assigned_to_name || row.assigned_to || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="100">
          <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button text type="primary" @click="$router.push('/design-tasks/' + row.id)">详情</el-button>
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
import { getDesignTasks } from '@/api/tasks'
import { DesignTaskResponse } from '@/types/api'

const loading = ref(false)
const list = ref<DesignTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')

function designStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '初始/待分配', pending_review: '待确认', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function designStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', pending_review: 'warning', completed: 'success', cancelled: 'info' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getDesignTasks({ page: page.value, page_size: pageSize.value, status: filterStatus.value || undefined })
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
