<template>
  <div class="page">
    <div class="page-header">
      <h2>安装任务</h2>
    </div>

    <div class="search-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="fetchData">
        <el-option label="待分配" value="pending" />
        <el-option label="已分配" value="assigned" />
        <el-option label="安装中" value="in_progress" />
        <el-option label="待验收" value="pending_acceptance" />
        <el-option label="已完成" value="completed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="installation_no" label="任务编号" width="180" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="instStatusColor(row.status)" size="small">{{ instStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="contact_name" label="联系人" width="100" />
      <el-table-column prop="contact_phone" label="电话" width="130" />
      <el-table-column label="计划时间" width="120">
        <template #default="{ row }">{{ row.scheduled_at?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/installation-tasks/${row.id}`)">详情</el-button>
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
import { getInstallationTasks } from '@/api/tasks'
import { InstallationTaskResponse } from '@/types/api'

const loading = ref(false)
const list = ref<InstallationTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')

function instStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function instStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success', cancelled: 'info' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getInstallationTasks({ page: page.value, page_size: pageSize.value, status: filterStatus.value || undefined })
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
