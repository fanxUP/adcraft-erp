<template>
  <div class="page">
    <div class="page-header">
      <h2>报价管理</h2>
      <div>
        <el-button @click="importDialogVisible = true">导入</el-button>
        <el-button type="danger" @click="$router.push('/quotes/new')">新建报价</el-button>
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
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/quotes/${row.id}/edit`)">编辑</el-button>
          <el-button text type="success" @click="handlePreview(row)">预览</el-button>
          <el-button text type="danger" @click="handleDelete(row as QuoteListResponse)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

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

    <!-- Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="导入报价单" width="620px">
      <div style="margin-bottom: 16px; font-size: 13px; color: var(--ad-text-secondary)">
        <p>支持 .xlsx / .xls 格式，每行对应一条报价明细。相同"客户名称+项目名称"的行归为同一报价单。</p>
        <p>列说明（<span style="color: #f56c6c">*</span>为必填）：</p>
        <el-table :data="templateColumns" border size="small" style="margin: 8px 0" max-height="280px">
          <el-table-column prop="name" label="列名" width="140" />
          <el-table-column prop="desc" label="说明" />
          <el-table-column label="必填" width="60">
            <template #default="{ row }">
              <span v-if="row.required" style="color: #f56c6c">*</span>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin: 12px 0">
          <el-button size="small" @click="downloadQuoteTemplate">📥 下载导入模版</el-button>
        </div>

        <p>示例数据（分项用法）：</p>
        <el-table :data="sampleData" border size="small" style="margin: 8px 0">
          <el-table-column prop="customer_name" label="客户名称" width="100" />
          <el-table-column prop="project_name" label="项目名称" width="120" />
          <el-table-column prop="group_name" label="明细分组" width="80" />
          <el-table-column prop="item_name" label="项目(明细)" width="120" />
          <el-table-column prop="unit" label="单位" width="50" />
          <el-table-column prop="quantity" label="数量" width="60" />
          <el-table-column prop="unit_price" label="单价" width="70" />
        </el-table>
      </div>

      <el-upload
        ref="uploadRef"
        accept=".xlsx,.xls"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="() => ElMessage.warning('只能上传一个文件')"
      >
        <template #trigger>
          <el-button type="primary">选择文件</el-button>
        </template>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx / .xls 文件</div>
        </template>
      </el-upload>

      <div v-if="importResult" style="margin-top: 16px">
        <el-alert
          :title="`导入完成：共 ${importResult.succeeded} 份报价单，成功 ${importResult.succeeded} 条，失败 ${importResult.failed} 条`"
          :type="importResult.failed > 0 ? 'warning' : 'success'"
          show-icon
        />
        <el-table v-if="importResult.errors?.length" :data="importResult.errors" border size="small" style="margin-top: 8px" max-height="200px">
          <el-table-column prop="row" label="行号" width="60" />
          <el-table-column prop="message" label="错误信息" />
        </el-table>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="danger" :loading="importing" :disabled="!importFile" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getQuotes, deleteQuote, importQuotes, downloadQuoteTemplate } from '@/api/quotes'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import type { QuoteListResponse, ImportResponse } from '@/types/api'
import { getErrorMessage } from '@/utils/error'
import QuotePreview from './QuotePreview.vue'

const loading = ref(false)
const list = ref<QuoteListResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({ keyword: '', status: '' })
const dateRange = ref<[string, string] | null>(null)

const previewVisible = ref(false)
const previewQuoteId = ref<string | null>(null)

function handlePreview(row: QuoteListResponse) {
  previewQuoteId.value = row.id
  previewVisible.value = true
}

// Import state
const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)
const importResult = ref<ImportResponse | null>(null)

const templateColumns = [
  { name: '客户名称', desc: '客户全称', required: true },
  { name: '项目名称', desc: '项目名称', required: true },
  { name: '部门/科室', desc: '所属部门', required: false },
  { name: '有效期', desc: 'YYYY-MM-DD 格式', required: false },
  { name: '税率', desc: '如 0.13 表示 13%', required: false },
  { name: '优惠金额', desc: '优惠抵扣金额', required: false },
  { name: '备注', desc: '报价单备注', required: false },
  { name: '明细分组', desc: '分项名称，相同名称归入同一分项', required: false },
  { name: '项目名称(明细)', desc: '明细行名称', required: true },
  { name: '材质工艺', desc: '材质/工艺描述', required: false },
  { name: '数量', desc: '数量值', required: true },
  { name: '单位', desc: '如 个、套、㎡', required: false },
  { name: '单价', desc: '单价金额', required: false },
  { name: '长', desc: '长度数值', required: false },
  { name: '长单位', desc: 'm / cm / mm', required: false },
  { name: '宽', desc: '宽度数值', required: false },
  { name: '宽单位', desc: 'm / cm / mm', required: false },
  { name: '高', desc: '高度数值', required: false },
  { name: '高单位', desc: 'm / cm / mm', required: false },
  { name: '件数', desc: '件数，默认 1', required: false },
  { name: '加工费', desc: '加工费用', required: false },
  { name: '安装费', desc: '安装费用', required: false },
  { name: '设计费', desc: '设计费用', required: false },
  { name: '运输费', desc: '运输费用', required: false },
  { name: '其他费用', desc: '其他费用', required: false },
  { name: '明细备注', desc: '明细行备注', required: false },
]

const sampleData = [
  { customer_name: '示例公司', project_name: 'XX广告牌', group_name: '分项1', item_name: '不锈钢烤漆字', unit: '个', quantity: 2, unit_price: 350 },
  { customer_name: '示例公司', project_name: 'XX广告牌', group_name: '分项2', item_name: '安装人工费', unit: '项', quantity: 1, unit_price: 2000 },
]

function handleFileChange(uploadFile: UploadFile) {
  importFile.value = uploadFile.raw || null
  importResult.value = null
}

async function handleImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const data = await importQuotes(importFile.value)
    importResult.value = data
    ElMessage.success(`导入完成：成功 ${data.succeeded} 份报价单${data.failed > 0 ? `，失败 ${data.failed} 条` : ''}`)
    fetchData()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导入失败'))
  } finally {
    importing.value = false
  }
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

async function handleDelete(row: QuoteListResponse) {
  await ElMessageBox.confirm(`确认删除报价 "${row.quote_no}"？`, '确认', { type: 'warning' })
  await deleteQuote(row.id)
  ElMessage.success('已删除')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
</style>
