<template>
  <div class="page">
    <div class="page-header">
      <h2>安装任务</h2>
      <el-button type="danger" @click="dialogVisible = true">创建安装任务</el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="fetchData">
        <el-option label="待分配" value="pending" />
        <el-option label="已分配" value="assigned" />
        <el-option label="安装中" value="in_progress" />
        <el-option label="待验收" value="pending_acceptance" />
        <el-option label="已完成" value="completed" />
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

    <el-dialog v-model="dialogVisible" title="创建安装任务" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="订单">
          <el-select v-model="form.order_id" placeholder="选择订单" filterable style="width: 100%">
            <el-option v-for="o in orderOptions" :key="o.id" :label="`${o.order_no} ${o.project_name}`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称">
          <el-input v-model="form.project_name" />
        </el-form-item>
        <el-form-item label="安装地址">
          <el-input v-model="form.address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" />
        </el-form-item>
        <el-form-item label="计划时间">
          <el-date-picker v-model="form.scheduled_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
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
import { getInstallationTasks, createInstallationTask } from '@/api/tasks'
import { getOrders } from '@/api/orders'
import { getUsers } from '@/api/users'
import { ElMessage } from 'element-plus'
import { InstallationTaskResponse, OrderListResponse, UserResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<InstallationTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const dialogVisible = ref(false)
const orderOptions = ref<OrderListResponse[]>([])
const userOptions = ref<UserResponse[]>([])
const form = reactive({ order_id: '', customer_id: '', project_name: '', assigned_to: '', address: '', contact_name: '', contact_phone: '', scheduled_at: '' })

function instStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成' }
  return map[s] || s
}
function instStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success' }
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

async function loadOptions() {
  const [ordersRes, usersRes] = await Promise.all([getOrders({ page_size: 200 }), getUsers({ page_size: 200 })])
  orderOptions.value = ordersRes.items
  userOptions.value = usersRes.items
}

async function handleCreate() {
  saving.value = true
  try {
    const selOrder = orderOptions.value.find(o => o.id === form.order_id)
    await createInstallationTask({ ...form, customer_id: selOrder?.customer_id || '' })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    Object.assign(form, { order_id: '', customer_id: '', project_name: '', assigned_to: '', address: '', contact_name: '', contact_phone: '', scheduled_at: '' })
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
