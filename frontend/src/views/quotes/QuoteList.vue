<template>
  <AppPage>
    <template #header>
      <PageHeader title="报价管理" description="统一管理报价状态、金额和转订单流程。">
        <template #actions>
          <el-button v-if="authStore.isAdmin" @click="$router.push('/orders/recycle')" type="warning">
            <el-icon><Delete /></el-icon> 订单回收站
          </el-button>
          <el-button @click="$router.push('/quotes/new')" type="danger">新建常规报价</el-button>
        </template>
      </PageHeader>
    </template>

    <template #toolbar>
      <PageToolbar aria-label="报价筛选">
      <el-form :model="filters" inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="编号/项目名称" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已转订单" value="converted" />
            <el-option label="已作废" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建日期">
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
          <el-button @click="handleSearch" type="primary">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      </PageToolbar>
    </template>

    <DataTableShell :state="tableState" aria-label="报价列表">
      <template #error>
        <StatePanel state="error" action-label="重试" @action="fetchData" />
      </template>
      <el-table :data="list" stripe>
      <el-table-column prop="quote_no" label="报价编号" width="180" />
      <el-table-column prop="customer_name" label="客户名称" width="160" />
      <el-table-column prop="department" label="部门/科室" width="120" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusTag :status="row.status_view || row.status" size="sm" />
        </template>
      </el-table-column>
      <el-table-column label="总金额" width="120">
        <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column label="有效期" width="120">
        <template #default="{ row }">{{ row.valid_until || '-' }}</template>
      </el-table-column>
      <el-table-column label="报价日期" width="120">
        <template #default="{ row }">{{ row.quote_date || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/quotes/${row.id}/edit`)">编辑</el-button>
          <el-button text type="primary" @click="handlePreview(row)">打印预览</el-button>
          <el-button v-if="row.status === 'draft' || row.status === 'confirmed'" text type="warning" @click="handleCancel(row as QuoteListResponse)">作废</el-button>
          <el-button v-if="row.status === 'cancelled'" text @click="handleRevert(row as QuoteListResponse)">转草稿</el-button>
          <el-button text type="danger" @click="handleDelete(row as QuoteListResponse)">删除</el-button>
        </template>
      </el-table-column>
      </el-table>
      <template #footer>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </template>
    </DataTableShell>

    <el-dialog v-model="deleteDialogVisible" title="确认硬删除报价" width="460px" :close-on-click-modal="false">
      <div class="delete-confirm-content">
        <p>确定彻底删除报价「{{ pendingDeleteQuote?.quote_no }}」吗？</p>
        <p class="delete-confirm-warning">报价及其关联数据删除后不可恢复。</p>
        <div v-if="deleteAssociations.length" class="delete-associations">
          <div class="delete-associations-title">将一并删除以下有效关联数据：</div>
          <div v-for="item in deleteAssociations" :key="item.label" class="delete-association-row">
            <span>{{ item.label }}</span><strong>{{ item.count }} 条</strong>
          </div>
        </div>
        <p v-else class="delete-confirm-safe">未发现有效关联数据（已软删除数据不计入）。</p>
      </div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button :loading="deleting" @click="confirmDelete" type="danger">确认删除</el-button>
      </template>
    </el-dialog>

    <QuotePreview :visible="previewVisible" :quote-id="previewQuoteId" @close="previewVisible = false" />

  </AppPage>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { ref, reactive, computed, onActivated, onDeactivated, onMounted, onUnmounted } from 'vue'
import { getQuotes, deleteQuote, previewDeleteQuote, cancelQuote, revertQuoteToDraft } from '@/api/quotes'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { QuoteListResponse } from '@/types/api'
import QuotePreview from './QuotePreview.vue'
import { getErrorMessage } from '@/utils/error'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel, StatusTag } from '@/components/ui'

const authStore = useAuthStore()

const loading = ref(false)
const list = ref<QuoteListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loadError = ref(false)

const filters = reactive({ keyword: '', status: '' })
const dateRange = ref<[string, string] | null>(null)

const previewVisible = ref(false)
const previewQuoteId = ref<string | null>(null)
const deleteDialogVisible = ref(false)
const pendingDeleteQuote = ref<QuoteListResponse | null>(null)
const deleting = ref(false)
const deleteAssociations = ref<Array<{ label: string; count: number }>>([])

const REFRESH_INTERVAL_MS = 15000
let refreshTimer: ReturnType<typeof setInterval> | null = null
let fetchRequestId = 0

const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return list.value.length ? 'ready' : 'empty'
})

function handlePreview(row: QuoteListResponse) {
  previewQuoteId.value = row.id
  previewVisible.value = true
}


async function fetchData() {
  const requestId = ++fetchRequestId
  loading.value = true
  loadError.value = false
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filters.keyword ? { keyword: filters.keyword } : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(dateRange.value ? { date_from: dateRange.value[0], date_to: dateRange.value[1] } : {}),
    }
    const data = await getQuotes(params)
    if (requestId === fetchRequestId) {
      list.value = data.items
      total.value = data.total
    }
  } catch {
    if (requestId === fetchRequestId) loadError.value = true
  } finally {
    if (requestId === fetchRequestId) loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  dateRange.value = null
  page.value = 1
  fetchData()
}

async function handleCancel(row: QuoteListResponse) {
  await ElMessageBox.confirm(`确定作废报价「${row.quote_no}」？作废后可从列表筛选查看。`, '作废报价', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await cancelQuote(row.id)
  ElMessage.success('报价已作废')
  fetchData()
}

async function handleRevert(row: QuoteListResponse) {
  await ElMessageBox.confirm(`确定将报价「${row.quote_no}」转回草稿？转回后可重新编辑。`, '转草稿', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await revertQuoteToDraft(row.id)
  ElMessage.success('已转回草稿')
  fetchData()
}

function handleDelete(row: QuoteListResponse) {
  pendingDeleteQuote.value = row
  deleteAssociations.value = []
  deleteDialogVisible.value = true
  previewDeleteQuote(row.id).then((preview) => {
    deleteAssociations.value = preview.associations
  }).catch((error) => {
    deleteDialogVisible.value = false
    ElMessage.error(getErrorMessage(error, '无法读取关联数据，已取消删除'))
  })
}

async function confirmDelete() {
  if (!pendingDeleteQuote.value) return
  deleting.value = true
  try {
    await deleteQuote(pendingDeleteQuote.value.id)
    ElMessage.success('报价已删除')
    deleteDialogVisible.value = false
    pendingDeleteQuote.value = null
    deleteAssociations.value = []
    await fetchData()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '报价删除失败'))
  } finally {
    deleting.value = false
  }
}

function refreshIfVisible() {
  if (!document.hidden && !loading.value) void fetchData()
}

function handleVisibilityChange() {
  if (!document.hidden) void fetchData()
}

function startAutoRefresh() {
  if (refreshTimer) return
  refreshTimer = setInterval(refreshIfVisible, REFRESH_INTERVAL_MS)
  document.addEventListener('visibilitychange', handleVisibilityChange)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
}

onMounted(() => {
  void fetchData()
  startAutoRefresh()
})
onActivated(startAutoRefresh)
onDeactivated(stopAutoRefresh)
onUnmounted(stopAutoRefresh)
</script>

<style scoped>
.quote-actions { display: flex; gap: 8px; }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
.delete-confirm-content p { margin: 0; line-height: 1.7; }
.delete-confirm-warning { margin-top: 8px !important; color: var(--el-color-danger); font-size: 13px; }
.delete-confirm-safe { margin-top: 12px !important; color: var(--el-color-success); font-size: 13px; }
.delete-associations { margin-top: 16px; padding: 12px; background: var(--ad-darker); border: 1px solid var(--ad-border); border-radius: 6px; }
.delete-associations-title { margin-bottom: 8px; font-weight: 600; }
.delete-association-row { display: flex; justify-content: space-between; padding: 4px 0; }
</style>
