<template>
  <div class="page">
    <h2 style="margin-bottom: 16px; color: var(--ad-text)">操作日志</h2>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="对象类型">
          <el-select v-model="filters.object_type" clearable placeholder="全部" style="width: 140px">
            <el-option label="客户" value="customer" />
            <el-option label="报价" value="quote" />
            <el-option label="订单" value="order" />
            <el-option label="收款" value="payment" />
            <el-option label="支出" value="expense" />
            <el-option label="外协商" value="outsource_vendor" />
            <el-option label="外协任务" value="outsource_task" />
            <el-option label="外协付款" value="outsource_payment" />
            <el-option label="库存" value="inventory" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-select v-model="filters.action" clearable placeholder="全部" style="width: 120px">
            <el-option label="创建" value="create" />
            <el-option label="修改" value="update" />
            <el-option label="删除" value="delete" />
            <el-option label="状态变更" value="status_change" />
            <el-option label="入库" value="stock_in" />
            <el-option label="出库" value="stock_out" />
            <el-option label="作废" value="void" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
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

    <el-card shadow="never" class="table-card" style="margin-top: 16px">
      <el-table :data="logs" stripe size="small" v-loading="loading" empty-text="暂无操作日志">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column prop="user_name" label="操作人" width="100" />
        <el-table-column label="对象" width="100">
          <template #default="{ row }">{{ objectTypeLabel(row.object_type) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            <span v-if="row.action === 'create' && row.after_data?.name">{{ row.after_data.name }}</span>
            <span v-else-if="row.action === 'status_change' && row.after_data?.status">
              状态: {{ row.after_data.status }}
              <span v-if="row.after_data?.reason">({{ row.after_data.reason }})</span>
            </span>
            <span v-else-if="row.after_data?.amount">金额: ¥{{ row.after_data.amount }}</span>
            <span v-else-if="row.after_data?.quantity">
              {{ row.after_data.record_type === 'in' ? '入库' : '出库' }}: {{ row.after_data.quantity }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="140" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="showDetail(row as OperationLogResponse)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" title="日志详情" size="500px">
      <template v-if="currentLog">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="时间">{{ currentLog.created_at }}</el-descriptions-item>
          <el-descriptions-item label="操作人">{{ currentLog.user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="对象类型">{{ objectTypeLabel(currentLog.object_type) }}</el-descriptions-item>
          <el-descriptions-item label="操作">{{ actionLabel(currentLog.action) }}</el-descriptions-item>
          <el-descriptions-item label="IP 地址">{{ currentLog.ip_address || '-' }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 16px 0 8px; color: var(--ad-text)">修改前数据</h4>
        <el-input
          type="textarea"
          :rows="6"
          :model-value="currentLog.before_data ? JSON.stringify(currentLog.before_data, null, 2) : '无'"
          readonly
        />

        <h4 style="margin: 16px 0 8px; color: var(--ad-text)">修改后数据</h4>
        <el-input
          type="textarea"
          :rows="6"
          :model-value="currentLog.after_data ? JSON.stringify(currentLog.after_data, null, 2) : '无'"
          readonly
        />
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getOperationLogs } from '@/api/operation_logs'
import type { OperationLogResponse } from '@/types/api'

const loading = ref(false)
const logs = ref<OperationLogResponse[]>([])
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const drawerVisible = ref(false)
const currentLog = ref<OperationLogResponse | null>(null)

const filters = reactive({
  object_type: '',
  action: '',
})
const dateRange = ref<[string, string] | null>(null)

function objectTypeLabel(t: string | null | undefined) {
  const map: Record<string, string> = {
    customer: '客户', quote: '报价', order: '订单',
    payment: '收款', expense: '支出',
    outsource_vendor: '外协商', outsource_task: '外协任务', outsource_payment: '外协付款',
    inventory: '库存', production_task: '制作任务', design_task: '设计任务', installation_task: '安装任务',
  }
  return map[t || ''] || t || '-'
}

function actionLabel(a: string) {
  const map: Record<string, string> = {
    create: '创建', update: '修改', delete: '删除',
    status_change: '状态变更', stock_in: '入库', stock_out: '出库',
    void: '作废', confirm: '确认', convert: '转订单',
  }
  return map[a] || a
}

function actionTagType(a: string) {
  const map: Record<string, string> = {
    create: 'success', update: 'warning', delete: 'danger',
    stock_in: '', stock_out: 'warning', void: 'danger',
    status_change: 'info',
  }
  return (map[a] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function showDetail(row: OperationLogResponse) {
  currentLog.value = row
  drawerVisible.value = true
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filters.object_type ? { object_type: filters.object_type } : {}),
      ...(filters.action ? { action: filters.action } : {}),
      ...(dateRange.value ? { date_from: dateRange.value[0], date_to: dateRange.value[1] } : {}),
    }
    const res = await getOperationLogs(params)
    logs.value = res.items
    total.value = res.total
  } catch {
    // API error handled by interceptor
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchLogs()
}

function handleReset() {
  filters.object_type = ''
  filters.action = ''
  dateRange.value = null
  page.value = 1
  fetchLogs()
}

onMounted(fetchLogs)
</script>

<style scoped>
.page { padding: 0; }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.table-card { background: var(--ad-card); border: 1px solid var(--ad-border); }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
