<template>
  <div class="page">
    <div class="page-header">
      <h2>设计任务</h2>
      <el-button type="danger" @click="dialogVisible = true">创建设计任务</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="fetchData">
        <el-option label="待分配" value="pending" />
        <el-option label="设计中" value="designing" />
        <el-option label="待确认" value="pending_review" />
        <el-option label="需修改" value="revision" />
        <el-option label="已确认" value="confirmed" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="design_no" label="任务编号" width="180" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="designStatusColor(row.status)" size="small">{{ designStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/design-tasks/${row.id}`)">详情</el-button>
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

    <el-dialog v-model="dialogVisible" title="创建设计任务" width="500px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="订单">
          <el-select v-model="form.order_id" placeholder="选择订单" filterable style="width: 100%">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} ${o.project_name}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="form.project_name" />
        </el-form-item>
        <el-form-item label="设计师">
          <el-select v-model="form.assigned_to" placeholder="选择设计师" clearable style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="设计说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getDesignTasks, createDesignTask } from '@/api/tasks'
import { getOrders } from '@/api/orders'
import { getUsers } from '@/api/users'
import { ElMessage } from 'element-plus'
import { DesignTaskResponse, OrderListResponse, UserResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<DesignTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const dialogVisible = ref(false)
const orderOptions = ref<OrderListResponse[]>([])
const userOptions = ref<UserResponse[]>([])
const form = reactive({ order_id: '', customer_id: '', project_name: '', assigned_to: '', description: '' })

function designStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已确认' }
  return map[s] || s
}
function designStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', designing: '', pending_review: 'warning', revision: 'danger', confirmed: 'success' }
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

async function loadOptions() {
  const [ordersRes, usersRes] = await Promise.all([getOrders({ page_size: 100 }), getUsers({ page_size: 100 })])
  orderOptions.value = ordersRes.items
  userOptions.value = usersRes.items
}

async function handleCreate() {
  saving.value = true
  try {
    const selOrder = orderOptions.value.find(o => o.id === form.order_id)
    await createDesignTask({ ...form, customer_id: selOrder?.customer_id || '' })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    Object.assign(form, { order_id: '', customer_id: '', project_name: '', assigned_to: '', description: '' })
    fetchData()
  } catch { /* handled by interceptor */ } finally { saving.value = false }
}

onMounted(() => { fetchData(); loadOptions() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
