<template>
  <div class="page">
    <div class="page-header">
      <h2>制作任务</h2>
      <el-button type="danger" @click="dialogVisible = true">创建制作任务</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="fetchData">
        <el-option label="待制作" value="pending" />
        <el-option label="排队中" value="queued" />
        <el-option label="制作中" value="in_progress" />
        <el-option label="待质检" value="qc_check" />
        <el-option label="返工" value="rework" />
        <el-option label="已完成" value="completed" />
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

    <el-dialog v-model="dialogVisible" title="创建制作任务" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="订单">
          <el-select v-model="form.order_id" placeholder="选择订单" filterable style="width: 100%">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} ${o.project_name}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="form.project_name" />
        </el-form-item>
        <el-form-item label="长(m)">
          <el-input-number v-model="form.length" :precision="3" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="宽(m)">
          <el-input-number v-model="form.width" :precision="3" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="form.quantity" :precision="3" :min="0.001" style="width: 100%" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="form.assigned_to" placeholder="选择负责人" clearable style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
          </el-select>
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
import { getProductionTasks, createProductionTask } from '@/api/tasks'
import { getOrders } from '@/api/orders'
import { getUsers } from '@/api/users'
import { ElMessage } from 'element-plus'
import { ProductionTaskResponse, OrderListResponse, UserResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<ProductionTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const dialogVisible = ref(false)
const orderOptions = ref<OrderListResponse[]>([])
const userOptions = ref<UserResponse[]>([])
const form = reactive({ order_id: '', customer_id: '', project_name: '', assigned_to: '', length: undefined as number | undefined, width: undefined as number | undefined, height: undefined as number | undefined, quantity: 1 })

function prodStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成' }
  return map[s] || s
}
function prodStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success' }
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

async function loadOptions() {
  const [ordersRes, usersRes] = await Promise.all([getOrders({ page_size: 100 }), getUsers({ page_size: 100 })])
  orderOptions.value = ordersRes.items
  userOptions.value = usersRes.items
}

async function handleCreate() {
  saving.value = true
  try {
    const selOrder = orderOptions.value.find(o => o.id === form.order_id)
    await createProductionTask({ ...form, customer_id: selOrder?.customer_id || '' })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    Object.assign(form, { order_id: '', customer_id: '', project_name: '', assigned_to: '', length: undefined, width: undefined, height: undefined, quantity: 1 })
    fetchData()
  } catch { /* handled */ } finally { saving.value = false }
}

onMounted(() => { fetchData(); loadOptions() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
