<template>
  <AppPage>
    <template #header>
      <PageHeader title="报价管理" description="统一管理报价状态、金额和转订单流程。">
        <template #actions>
          <el-button v-if="authStore.isAdmin" @click="$router.push('/orders/recycle')" type="warning">
            <el-icon><Delete /></el-icon> 订单回收站
          </el-button>
          <el-button type="primary" @click="openSchoolImport">批量导入学校清单</el-button>
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

    <el-dialog v-model="schoolImportVisible" title="批量导入学校清单" width="920px" :close-on-click-modal="false" destroy-on-close>
      <el-alert
        title="系统会先生成预览，确认后才会创建报价草稿。每所学校生成一张报价。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <el-form :model="schoolImportForm" label-width="90px" inline>
        <el-form-item label="客户名称" required>
          <el-input v-model="schoolImportForm.customerName" readonly style="width: 310px" />
        </el-form-item>
        <el-form-item label="项目名称" required>
          <el-input v-model="schoolImportForm.projectName" readonly style="width: 430px" />
        </el-form-item>
      </el-form>

      <div class="school-import-upload">
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept=".xlsx"
          :on-change="handleSchoolFileChange"
        >
          <el-button :disabled="schoolPreviewing || schoolImporting">选择学校清单 Excel</el-button>
        </el-upload>
        <span class="school-import-file">{{ schoolFile?.name || '尚未选择文件' }}</span>
        <el-button type="primary" :loading="schoolPreviewing" :disabled="!schoolFile || schoolImporting" @click="handleSchoolPreview">
          生成预览
        </el-button>
      </div>

      <template v-if="schoolPreview">
        <div class="school-import-summary">
          <span>学校：<strong>{{ schoolPreview.school_count }}</strong> 所</span>
          <span>明细：<strong>{{ schoolPreview.item_count }}</strong> 条</span>
          <span>合计：<strong>{{ formatMoney(schoolPreview.total_amount) }}</strong></span>
          <span v-if="schoolPreview.skipped_rows.length">跳过：{{ schoolPreview.skipped_rows.length }} 行</span>
        </div>
        <el-alert v-if="schoolPreview.errors.length" title="预览存在错误，请修正原文件后重新上传" type="error" :closable="false" show-icon>
          <div v-for="error in schoolPreview.errors" :key="`${error.row}-${error.message}`">第 {{ error.row }} 行：{{ error.message }}</div>
        </el-alert>
        <el-alert v-else-if="schoolPreview.warnings.length" title="部分原始小计与数量×单价存在差异，系统将按数量×单价重算" type="warning" :closable="false" show-icon>
          共 {{ schoolPreview.warnings.length }} 行，详见预览结果
        </el-alert>
        <el-table v-if="schoolPreview.schools.length" :data="schoolPreview.schools" stripe border max-height="360" style="margin-top: 14px">
          <el-table-column prop="department" label="部门/科室" min-width="280" />
          <el-table-column prop="item_count" label="明细数量" width="100" align="right" />
          <el-table-column prop="area_item_count" label="面积明细" width="100" align="right" />
          <el-table-column label="报价金额" width="150" align="right">
            <template #default="{ row }">{{ formatMoney(row.subtotal_amount) }}</template>
          </el-table-column>
          <el-table-column label="单位类型" min-width="220">
            <template #default="{ row }">
              <span v-for="(count, unit) in row.unit_counts" :key="unit" class="unit-count">{{ unit }} {{ count }}条</span>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <template #footer>
        <el-button @click="schoolImportVisible = false" :disabled="schoolImporting">取消</el-button>
        <el-button
          type="primary"
          :loading="schoolImporting"
          :disabled="!schoolPreview?.valid || schoolPreviewing"
          @click="handleSchoolImport"
        >
          确认导入 {{ schoolPreview?.school_count || 0 }} 张报价
        </el-button>
      </template>
    </el-dialog>

    <QuotePreview :visible="previewVisible" :quote-id="previewQuoteId" @close="previewVisible = false" />

  </AppPage>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { ref, reactive, computed, onActivated, onDeactivated, onMounted, onUnmounted } from 'vue'
import { getQuotes, deleteQuote, previewDeleteQuote, cancelQuote, revertQuoteToDraft, previewSchoolQuoteImport, commitSchoolQuoteImport } from '@/api/quotes'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { QuoteListResponse, SchoolQuoteImportPreview } from '@/types/api'
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

const schoolImportVisible = ref(false)
const schoolPreviewing = ref(false)
const schoolImporting = ref(false)
const schoolFile = ref<File | null>(null)
const schoolPreview = ref<SchoolQuoteImportPreview | null>(null)
const schoolImportForm = reactive({
  customerName: '新疆知味居经营管理有限公司',
  projectName: '喀什市思政教育一体化项目-教育教学文化阵地建设项目',
})

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

function openSchoolImport() {
  schoolFile.value = null
  schoolPreview.value = null
  schoolImportVisible.value = true
}

function handleSchoolFileChange(uploadFile: { raw?: File }) {
  schoolFile.value = uploadFile.raw || null
  schoolPreview.value = null
}

async function handleSchoolPreview() {
  if (!schoolFile.value) return
  schoolPreviewing.value = true
  try {
    schoolPreview.value = await previewSchoolQuoteImport(
      schoolFile.value,
      schoolImportForm.customerName,
      schoolImportForm.projectName,
    )
    if (!schoolPreview.value.valid) ElMessage.warning('清单预览存在错误，请检查后再提交')
    else ElMessage.success(`预览完成：${schoolPreview.value.school_count} 所学校，${schoolPreview.value.item_count} 条明细`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '清单预览失败'))
  } finally {
    schoolPreviewing.value = false
  }
}

async function handleSchoolImport() {
  if (!schoolFile.value || !schoolPreview.value?.valid) return
  try {
    await ElMessageBox.confirm(
      `确认创建 ${schoolPreview.value.school_count} 张报价草稿吗？共 ${schoolPreview.value.item_count} 条明细，合计 ${formatMoney(schoolPreview.value.total_amount)}。已有相同客户、项目和学校的报价时，本次不会写入。`,
      '确认批量导入',
      { confirmButtonText: '确认导入', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  schoolImporting.value = true
  try {
    const result = await commitSchoolQuoteImport(
      schoolFile.value,
      schoolImportForm.customerName,
      schoolImportForm.projectName,
      schoolPreview.value.preview_id,
    )
    ElMessage.success(`导入完成：已创建 ${result.school_count} 张报价草稿`)
    schoolImportVisible.value = false
    await fetchData()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '批量导入失败，未完成写入'))
  } finally {
    schoolImporting.value = false
  }
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
.school-import-upload { display: flex; align-items: center; gap: 12px; margin: 4px 0 16px; }
.school-import-file { flex: 1; color: var(--ad-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.school-import-summary { display: flex; gap: 24px; flex-wrap: wrap; margin: 12px 0; color: var(--ad-text-secondary); }
.school-import-summary strong { color: var(--ad-text); }
.unit-count { display: inline-block; margin-right: 12px; color: var(--ad-text-secondary); }
</style>
