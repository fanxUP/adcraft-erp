<template>
  <div class="page">
    <div class="page-header">
      <h2>报价管理</h2>
      <div class="quote-actions">
        <el-button @click="$router.push('/cdr/quotes')">智能报价记录</el-button>
        <el-button type="primary" @click="$router.push('/cdr/quotes/new')">新建智能报价</el-button>
        <el-button type="danger" @click="$router.push('/quotes/new')">新建常规报价</el-button>
      </div>
    </div>

    <el-card shadow="never" class="filter-card">
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
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="quote_no" label="报价编号" width="180" />
      <el-table-column prop="customer_name" label="客户名称" width="160" />
      <el-table-column prop="department" label="部门/科室" width="120" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusColor(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="总金额" width="140">
        <template #default="{ row }">¥ {{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="有效期" width="120">
        <template #default="{ row }">{{ row.valid_until || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ row.created_at?.slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/quotes/${row.id}/edit`)">编辑</el-button>
          <el-button text type="success" @click="handlePreview(row)">预览</el-button>
          <el-button v-if="row.status === 'draft' || row.status === 'confirmed'" text type="warning" @click="handleCancel(row as QuoteListResponse)">作废</el-button>
          <el-button v-if="row.status === 'cancelled'" text @click="handleRevert(row as QuoteListResponse)">转草稿</el-button>
          <el-button text type="danger" @click="handleDelete(row as QuoteListResponse)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

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
        <el-button type="danger" :loading="deleting" @click="confirmDelete">确认删除</el-button>
      </template>
    </el-dialog>

    <QuotePreview :visible="previewVisible" :quote-id="previewQuoteId" @close="previewVisible = false" />

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
import { ref, reactive, onMounted } from 'vue'
import { getQuotes, deleteQuote, previewDeleteQuote, cancelQuote, revertQuoteToDraft } from '@/api/quotes'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { QuoteListResponse } from '@/types/api'
import QuotePreview from './QuotePreview.vue'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const list = ref<QuoteListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({ keyword: '', status: '' })
const dateRange = ref<[string, string] | null>(null)

const previewVisible = ref(false)
const previewQuoteId = ref<string | null>(null)
const deleteDialogVisible = ref(false)
const pendingDeleteQuote = ref<QuoteListResponse | null>(null)
const deleting = ref(false)
const deleteAssociations = ref<Array<{ label: string; count: number }>>([])

function handlePreview(row: QuoteListResponse) {
  previewQuoteId.value = row.id
  previewVisible.value = true
}


function statusLabel(s: string) {
  const map: Record<string, string> = { draft: '草稿', confirmed: '已确认', converted: '已转订单', cancelled: '已作废' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { draft: 'info', confirmed: 'success', converted: '', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filters.keyword ? { keyword: filters.keyword } : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(dateRange.value ? { date_from: dateRange.value[0], date_to: dateRange.value[1] } : {}),
    }
    const data = await getQuotes(params)
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
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

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.quote-actions { display: flex; gap: 8px; }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
.delete-confirm-content p { margin: 0; line-height: 1.7; }
.delete-confirm-warning { margin-top: 8px !important; color: var(--el-color-danger); font-size: 13px; }
.delete-confirm-safe { margin-top: 12px !important; color: var(--el-color-success); font-size: 13px; }
.delete-associations { margin-top: 16px; padding: 12px; background: var(--ad-darker); border: 1px solid var(--ad-border); border-radius: 6px; }
.delete-associations-title { margin-bottom: 8px; font-weight: 600; }
.delete-association-row { display: flex; justify-content: space-between; padding: 4px 0; }
</style>
