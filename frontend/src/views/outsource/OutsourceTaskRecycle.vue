<template>
  <div class="page">
    <div class="page-header">
      <h2>
        <el-button text @click="$router.push('/outsource/tasks')">
          <el-icon><ArrowLeft /></el-icon> 返回外协任务
        </el-button>
        外协任务回收站
      </h2>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px" empty-text="回收站暂无内容">
      <el-table-column prop="task_no" label="任务编号" width="140" />
      <el-table-column prop="vendor_name" label="外协商" width="140" />
      <el-table-column label="关联任务" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.related_project_name">{{ row.related_project_name }}</span>
          <span v-else style="color: #999">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
      <el-table-column prop="total_amount" label="总金额" width="110" align="right">
        <template #default="{ row }">¥{{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="原状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="deleted_at" label="删除时间" width="170">
        <template #default="{ row }">{{ row.deleted_at?.replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button text type="success" @click="handleRestore(row)">恢复</el-button>
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
import { getDeletedOutsourceTasks, restoreOutsourceTask } from '@/api/outsource'
import type { OutsourceTaskResponse } from '@/types/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const list = ref<OutsourceTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

function statusLabel(val: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消' }
  return map[val] || val
}

function statusTagType(val: string) {
  const map: Record<string, string> = { pending: 'warning', in_progress: '', completed: 'success', settled: 'info', cancelled: 'danger' }
  return (map[val] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getDeletedOutsourceTasks({ page: page.value, page_size: pageSize.value })
    list.value = data.items as OutsourceTaskResponse[]
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleRestore(row: OutsourceTaskResponse) {
  await ElMessageBox.confirm(`确定恢复外协任务「${row.task_no}」？恢复后状态为已取消。`, '恢复任务', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await restoreOutsourceTask(row.id)
  ElMessage.success('外协任务已恢复')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); display: flex; align-items: center; gap: 8px; }
</style>
