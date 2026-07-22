<template>
  <div class="page">
    <div class="page-header">
      <h2>验收管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">新建验收单</el-button>
    </div>

    <el-card class="filter-card">
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="验收单号" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="草稿" value="draft" />
            <el-option label="待验收" value="pending" />
            <el-option label="已验收" value="accepted" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="acceptance_no" label="验收单号" min-width="140" />
        <el-table-column label="来源" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.order_id" type="primary" size="small">订单</el-tag>
            <el-tag v-else-if="row.quote_id" type="success" size="small">报价</el-tag>
            <el-tag v-else type="info" size="small">独立</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联编号" min-width="150">
          <template #default="{ row }">
            {{ row.order_no || row.quote_no || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户" min-width="120" />
        <el-table-column prop="department" label="部门/科室" min-width="120" />
        <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusColor(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="accepted_by" label="验收人" width="100" />
        <el-table-column label="验收日期" width="120">
          <template #default="{ row }">{{ row.accepted_at?.slice(0, 10) || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="120">
          <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="$router.push(`/acceptances/${row.id}`)">查看</el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'rejected'"
              text type="primary" size="small"
              @click="$router.push(`/acceptances/${row.id}?edit=1`)"
            >编辑</el-button>
            <el-button
              v-if="row.status === 'draft'"
              text type="danger" size="small"
              @click="handleDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @change="fetchData"
      />
    </el-card>

    <!-- 新建验收单 → 选择订单/报价单（合并列表） -->
    <el-dialog v-model="showCreateDialog" title="选择订单或报价单创建验收单" width="900px" :close-on-click-modal="false">
      <el-table :data="availableItems" v-loading="loadingItems" border stripe highlight-current-row @row-dblclick="handleCreateFromItem">
        <el-table-column label="来源" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.order_no" type="primary" size="small">订单</el-tag>
            <el-tag v-else type="success" size="small">报价</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="编号" min-width="140">
          <template #default="{ row }">{{ row.order_no || row.quote_no }}</template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户" min-width="120" />
        <el-table-column prop="department" label="科室/部门" min-width="100" />
        <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="total_amount" label="金额" width="130" align="right">
          <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleCreateFromItem(row)">选择</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!availableItems.length && !loadingItems" style="text-align:center;color:#999;padding:32px 0;">
        暂无可用的订单或报价
      </div>
      <template #footer>
        <el-button type="primary" @click="handleCreateBlank">创建空白验收单</el-button>
        <el-button @click="showCreateDialog = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAcceptances, deleteAcceptance, getAvailableOrders, getAvailableQuotes, createAcceptance } from '@/api/acceptances'
import type { AvailableOrder } from '@/api/acceptances'
import type { AcceptanceListResponse } from '@/types/api'

const router = useRouter()

const loading = ref(false)
const list = ref<AcceptanceListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', status: '' })

// 新建验收单弹窗（统一合并订单+报价单）
const showCreateDialog = ref(false)
const availableItems = ref<AvailableOrder[]>([])
const loadingItems = ref(false)

async function loadAvailableItems() {
  loadingItems.value = true
  try {
    const [orders, quotes] = await Promise.all([getAvailableOrders(), getAvailableQuotes()])
    availableItems.value = [...orders, ...quotes]
  } catch { /* ignore */ }
  finally { loadingItems.value = false }
}

async function handleCreateFromItem(row: AvailableOrder) {
  try {
    const payload = row.order_no ? { order_id: row.id } : { quote_id: row.id }
    const data = await createAcceptance(payload)
    ElMessage.success('验收单创建成功')
    showCreateDialog.value = false
    router.push(`/acceptances/${data.id}`)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

async function handleCreateBlank() {
  try {
    const data = await createAcceptance({})
    ElMessage.success('空白验收单已创建')
    showCreateDialog.value = false
    router.push(`/acceptances/${data.id}`)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

const statusLabel = (s: string) => {
  const map: Record<string, string> = {
    draft: '草稿', pending: '待验收', accepted: '已验收', rejected: '已驳回'
  }
  return map[s] || s
}

const statusColor = (s: string): '' | 'success' | 'warning' | 'info' | 'danger' => {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    draft: 'info', pending: 'warning', accepted: 'success', rejected: 'danger'
  }
  return map[s] || ''
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getAcceptances({ page: page.value, page_size: pageSize.value, ...filters })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  page.value = 1
  fetchData()
}

async function handleDelete(row: AcceptanceListResponse) {
  await ElMessageBox.confirm('确定删除该验收单？', '提示', { type: 'warning' })
  await deleteAcceptance(row.id)
  ElMessage.success('已删除')
  fetchData()
}

watch(showCreateDialog, (v) => {
  if (v) loadAvailableItems()
})

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { margin-bottom: 16px; }
</style>
