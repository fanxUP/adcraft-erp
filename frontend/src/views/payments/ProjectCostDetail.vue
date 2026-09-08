<template>
  <div class="page">
    <!-- Order info header -->
    <div class="order-header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
      <el-card v-if="order" shadow="never" class="order-card" style="margin-top: 12px">
        <div class="order-info-row">
          <div class="order-info-item">
            <span class="label">订单编号</span>
            <span class="value">{{ order.order_no }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">项目名称</span>
            <span class="value">{{ order.project_name }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">客户</span>
            <span class="value">{{ order.customer_name || '-' }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">状态</span>
            <el-tag :type="statusColor(order.status)" size="small">{{ statusLabel(order.status) }}</el-tag>
          </div>
          <div class="order-info-item">
            <span class="label">项目成本合计</span>
            <span class="value" style="color: var(--el-color-warning); font-weight: bold; font-size: 18px">
              ¥ {{ totalCost.toFixed(2) }}
            </span>
            <span v-if="!isQuote && costSummary" class="cost-summary-note">
              整单 ¥ {{ orderScopeCost.toFixed(2) }} · 明细归属 ¥ {{ itemScopeCost.toFixed(2) }}
            </span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Actions -->
    <div style="display: flex; gap: 8px; margin: 16px 0">
      <el-button type="danger" @click="openCreate">登记成本</el-button>
      <el-button @click="openImport">导入Excel</el-button>
    </div>

    <!-- Filters -->
    <div class="search-bar">
      <el-select
        v-model="filterCategory"
        placeholder="成本类别"
        clearable
        style="width: 160px"
        @change="fetchData"
      >
        <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px; margin-left: 12px"
        @change="fetchData"
      />
      <el-button style="margin-left: 12px" @click="fetchData" type="primary">搜索</el-button>
    </div>

    <!-- Cost table -->
    <div style="display: flex; gap: 8px; margin: 16px 0; align-items: center;">
      <el-button
        v-if="authStore.isAdmin && selectedIds.length > 0"
        @click="handleBatchDelete" type="danger">
        批量删除（{{ selectedIds.length }}）
      </el-button>
      <span v-if="selectedIds.length > 0" style="font-size: 13px; color: var(--ad-text-secondary)">已选中 {{ selectedIds.length }} 条记录</span>
    </div>
    <el-table
      :data="list"
      v-loading="loading"
      stripe
      style="margin-top: 16px"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="cost_no" label="编号" width="140" sortable />
      <el-table-column label="分项" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.group_name">{{ row.group_name }}</span>
          <span v-else-if="row.order_item_name">{{ row.order_item_name }}</span>
          <span v-else-if="row.quote_item_name">{{ row.quote_item_name }}</span>
          <span v-else></span>
        </template>
      </el-table-column>
      <el-table-column label="成本归属" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <div>{{ costScopeLabel(row as ProjectCostResponse) }}</div>
          <div v-if="!isQuote && (row as ProjectCostResponse).item_scopes?.length > 1" class="scope-tags">
            <el-tag
              v-for="scope in (row as ProjectCostResponse).item_scopes"
              :key="scope.order_item_id"
              size="small"
              effect="plain"
            >
              {{ scope.order_item_name || '未命名明细' }}
            </el-tag>
          </div>
          <el-tag v-if="isHistoricalCost(row as ProjectCostResponse)" type="info" size="small">历史明细</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="cost_date" label="日期" width="120" sortable>
        <template #default="{ row }">
          {{ formatDate(row.cost_date) || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="summary" label="成本摘要" min-width="180" show-overflow-tooltip />
      <el-table-column prop="description" label="产品/材质/工艺" min-width="180" show-overflow-tooltip />
      <el-table-column prop="specification" label="规格尺寸" width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.specification || '-' }}</template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" width="100" align="right" sortable>
        <template #default="{ row }">{{ row.quantity ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="单位" width="80" align="center">
        <template #default="{ row }">{{ row.unit || '-' }}</template>
      </el-table-column>
      <el-table-column prop="unit_price" label="单价" width="120" align="right" sortable>
        <template #default="{ row }">¥ {{ row.unit_price?.toFixed(2) ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="140" align="right" sortable>
        <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="欠款" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_debt && !row.is_settled" type="danger" size="small">欠款</el-tag>
          <el-tag v-else-if="row.is_debt && row.is_settled" type="success" size="small">已结清</el-tag>
          <span v-else></span>
        </template>
      </el-table-column>
      <el-table-column label="成本类别" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.category || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="付款方式" width="120">
        <template #default="{ row }">{{ row.payment_method || '-' }}</template>
      </el-table-column>
      <el-table-column label="收款公司" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.payee_company_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="凭证" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.attachment_count > 0" size="small" type="success">{{ row.attachment_count }}</el-tag>
          <span v-else></span>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row as ProjectCostResponse)">编辑</el-button>
          <el-button
            v-if="authStore.isAdmin"
            text
            type="danger"
            size="small"
            @click="handleDelete(row as ProjectCostResponse)"
          >
            删除
          </el-button>
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

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing ? '编辑成本' : '登记成本'" width="min(96vw, 1360px)" class="cost-dialog" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="isQuote ? '报价单' : '订单'">
          <el-input :value="(isQuote ? (order?.quote_no || '') : (order?.order_no || '')) + ' ' + (order?.project_name || '')" disabled />
        </el-form-item>
        <el-form-item v-if="!isQuote" label="成本归属" required class="cost-scope-form-item">
          <div class="cost-scope-list">
            <div class="cost-scope-mode-row">
              <el-radio v-model="scopeMode" value="document" :disabled="historicalScopes.length > 0">整单成本</el-radio>
              <span>不指定某项订单明细</span>
              <strong>整单已登记 ¥ {{ orderScopeCost.toFixed(2) }}</strong>
            </div>
            <div class="cost-scope-heading">
              <span>订单明细（可多选）</span>
              <span class="cost-scope-count">已选 {{ form.order_item_ids.length }} 项</span>
            </div>
            <div v-if="scopeTableRows.length" class="cost-scope-table-wrap">
              <el-table
                :data="scopeTableRows"
                row-key="id"
                border
                stripe
                size="small"
                class="cost-scope-table"
                :row-class-name="scopeRowClassName"
                @row-click="handleScopeRowClick"
              >
                <el-table-column label="" width="48" align="center">
                  <template #default="{ row }">
                    <el-checkbox
                      :model-value="isScopeSelected(row)"
                      :disabled="row.historical"
                      @change="setOrderItemSelected(row.id, $event)"
                      @click.stop
                    />
                  </template>
                </el-table-column>
                <el-table-column label="项目内容" min-width="150" show-overflow-tooltip>
                  <template #default="{ row }">
                    <div class="scope-project-cell">
                      <span>{{ row.label }}</span>
                      <el-tag v-if="row.historical" type="info" size="small">历史明细</el-tag>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="产品/材质/工艺" min-width="170" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.materialProcess || '-' }}</template>
                </el-table-column>
                <el-table-column label="规格" min-width="150" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.specification || '-' }}</template>
                </el-table-column>
                <el-table-column label="面积" width="85" align="right">
                  <template #default="{ row }">{{ formatScopeArea(row) }}</template>
                </el-table-column>
                <el-table-column label="数量" width="85" align="right">
                  <template #default="{ row }">{{ formatScopeNumber(row.quantity) }}</template>
                </el-table-column>
                <el-table-column label="单位" width="70" align="center">
                  <template #default="{ row }">{{ row.unit || '-' }}</template>
                </el-table-column>
                <el-table-column label="单价" width="105" align="right">
                  <template #default="{ row }">{{ formatScopeMoney(row.unitPrice) }}</template>
                </el-table-column>
                <el-table-column label="小计" width="120" align="right">
                  <template #default="{ row }">{{ formatScopeMoney(row.subtotalAmount) }}</template>
                </el-table-column>
                <el-table-column label="关联成本" width="140" align="right">
                  <template #default="{ row }">
                    <div v-if="row.historical" class="scope-cost-cell">
                      <span class="scope-cost-muted">原归属</span>
                    </div>
                    <div v-else class="scope-cost-cell">
                      <strong>¥ {{ row.registeredAmount.toFixed(2) }}</strong>
                      <span>{{ row.recordCount > 0 ? `${row.recordCount} 笔` : '未登记' }}</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else description="暂无可关联的有效订单明细" :image-size="60" />
            <div class="form-tip">多选仅表示这笔成本同时涉及这些明细；成本总额只入账一次，不做金额分摊或重复扣减。</div>
          </div>
        </el-form-item>
        <el-form-item label="分项">
          <el-input v-model="form.group_name" placeholder="输入分项名称（可选）" clearable />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="form.cost_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="成本摘要">
          <el-input v-model="form.summary" type="textarea" :rows="2" placeholder="成本摘要说明…" />
        </el-form-item>
        <el-form-item label="产品/材质/工艺">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="产品/材质/工艺说明…" />
        </el-form-item>
        <el-form-item label="规格尺寸">
          <el-input v-model="form.specification" placeholder="规格尺寸（如 1200×2400mm）" clearable />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="form.quantity" :min="0" :precision="2" style="width: 100%" placeholder="成本数量" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" placeholder="单位（个/米/平方米/套…）" clearable />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" placeholder="成本单价" />
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="欠款金额">
          <el-input-number v-model="form.debt_amount" :min="0" :precision="2" style="width: 100%" placeholder="0 表示无欠款" />
          <div style="font-size: 12px; color: var(--ad-text-secondary); margin-top: 4px">大于0时自动记为欠款</div>
        </el-form-item>
        <el-form-item label="成本类别" required>
          <el-select
            v-model="form.category"
            placeholder="选择类别"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="form.payment_method" placeholder="选择付款方式" clearable style="width: 100%">
            <el-option v-for="pm in PAYMENT_METHODS" :key="pm" :label="pm" :value="pm" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款公司">
          <el-input v-model="form.payee_company_name" placeholder="输入对方收款公司名称" clearable />
          <div style="font-size: 12px; color: var(--ad-text-secondary); margin-top: 2px">对方收款公司名称（可选）</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="备注…" />
        </el-form-item>
        <el-form-item label="凭证">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*,.pdf"
            multiple
            :on-change="onUploadChange"
          >
            <el-button :loading="uploadingAtt" :disabled="!isEditing">
              <el-icon><Plus /></el-icon> 上传凭证
            </el-button>
            <template #tip>
              <div class="el-upload__tip">支持 jpg/png/pdf，编辑模式下可上传</div>
            </template>
          </el-upload>
          <div v-if="dialogAttachments.length" style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px">
            <div
              v-for="att in dialogAttachments"
              :key="att.id"
              class="att-thumb"
              @click="handlePreviewAtt(att)"
            >
              <img
                v-if="att.file_type?.startsWith('image/')"
                :src="`/uploads/${att.file_path}`"
                class="att-img"
              />
              <div v-else class="att-file">
                <span>{{ att.filename?.split('.').pop()?.toUpperCase() }}</span>
              </div>
              <el-button
                class="att-del"
                :icon="Delete"
                size="small"
                circle
                @click.stop="handleDeleteAtt(att)"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" @click="handleSave" type="primary">
          {{ isEditing ? '保存' : '登记' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="showImport" title="导入Excel" width="480px" :close-on-click-modal="false">
      <p style="margin-bottom: 12px; color: var(--ad-text-secondary)">
        Excel 需包含以下列：<br />
        <b>分项、成本类别、付款方式、收款公司、规格尺寸、数量、单位、单价、金额、欠款金额、成本日期、产品/材质/工艺、成本摘要、备注</b>
      </p>
      <p style="margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 13px">
        导入的成本将自动关联到 <b>{{ isQuote ? (order?.quote_no || '报价单') : (order?.order_no || '订单') }}</b>
      </p>
      <div style="margin-bottom: 12px;">
        <el-button size="small" @click="downloadTemplate">
          <el-icon><Download /></el-icon> 下载导入模板
        </el-button>
      </div>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="onFileChange"
      >
        <el-button>选择Excel文件</el-button>
      </el-upload>
      <div v-if="importResult" style="margin-top: 12px">
        <el-alert
          :type="importResult.errors.length === 0 ? 'success' : 'warning'"
          :closable="false"
        >
          <template #title>
            导入完成：成功 {{ importResult.created }} 条
            <span v-if="importResult.errors.length">，失败 {{ importResult.errors.length }} 条</span>
          </template>
          <ul v-if="importResult.errors.length" style="margin-top: 6px; padding-left: 16px">
            <li v-for="e in importResult.errors" :key="e.row">
              第 {{ e.row }} 行：{{ e.error }}
            </li>
          </ul>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="showImport = false">关闭</el-button>
        <el-button :loading="importing" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- Image Preview Dialog -->
    <el-dialog v-model="previewVisible" title="凭证预览" width="600px" destroy-on-close :close-on-click-modal="false">
      <img :src="previewUrl" style="width: 100%; object-fit: contain" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { ref, reactive, onActivated, onDeactivated, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getProjectCosts, createProjectCost, updateProjectCost, deleteProjectCost, batchDeleteProjectCosts, importProjectCosts,
  getProjectCostAttachments, uploadProjectCostAttachment, deleteProjectCostAttachment, getOrderProjectCostItemSummary,
} from '@/api/payments'
import { getOrder } from '@/api/orders'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { ArrowLeft, Plus, Delete, Download } from '@element-plus/icons-vue'
import type { ProjectCostResponse, ProjectCostImportResponse, OrderDetailResponse, QuoteDetailResponse, AttachmentResponse, ProjectCostItemSummaryResponse } from '@/types/api'
import { buildProjectCostScopeOptions, getProjectCostScopeIds, type ProjectCostScopeOption } from '@/utils/projectCostScope'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const CATEGORIES = ['人工/工时费', '材料费', '租赁费', '运输/物流费', '安装杂费', '办公费', '餐费/交通费', '差旅费', '其他']
const PAYMENT_METHODS = ['现金支付', '微信支付', '支付宝转账', '转账支付', '对公支付', '其它支付']

const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const list = ref<ProjectCostResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterCategory = ref('')
const dateRange = ref<string[] | null>(null)
const showDialog = ref(false)
const showImport = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const order = ref<OrderDetailResponse | QuoteDetailResponse | null>(null)
const costSummary = ref<ProjectCostItemSummaryResponse | null>(null)
const selectedFile = ref<File | null>(null)
const importResult = ref<ProjectCostImportResponse | null>(null)
const dialogAttachments = ref<AttachmentResponse[]>([])
const uploadingAtt = ref(false)
const previewVisible = ref(false)
const previewUrl = ref('')

const REFRESH_INTERVAL_MS = 15000
let refreshTimer: ReturnType<typeof setInterval> | null = null
let orderRequestId = 0
let dataRequestId = 0
const queryCreateOpened = ref(false)
const editingScopeSnapshots = ref<Array<{ id: string; label: string; detail: string }>>([])

type ProjectCostScopeTableRow = ProjectCostScopeOption & { historical: boolean }

// Detect source type: order or quote
const isQuote = computed(() => route.path.includes('/quote-costs/'))
const sourceId = computed(() => {
  if (isQuote.value) return route.params.quoteId as string
  return route.params.orderId as string
})

const totalCost = computed(() => {
  if (!isQuote.value && costSummary.value) return costSummary.value.total_registered
  return list.value.reduce((sum, c) => sum + (c.amount || 0), 0)
})

const orderScopeCost = computed(() => costSummary.value?.order_scope_registered || 0)
const itemScopeCost = computed(() => costSummary.value?.item_scope_registered || 0)
const orderItems = computed(() => {
  if (isQuote.value) return []
  return (order.value as OrderDetailResponse | null)?.items || []
})
const costScopeOptions = computed(() => buildProjectCostScopeOptions(orderItems.value, costSummary.value?.items || []))
const activeOrderItemIds = computed(() => new Set(costScopeOptions.value.map(option => option.id)))
const historicalScopes = computed(() => editingScopeSnapshots.value
  .filter(scope => !activeOrderItemIds.value.has(scope.id))
  .map(scope => {
    const summary = costSummary.value?.items.find(item => item.order_item_id === scope.id)
    return {
      ...scope,
      registeredAmount: summary?.total_registered || 0,
      recordCount: summary?.record_count || 0,
    }
  }))
const scopeTableRows = computed<ProjectCostScopeTableRow[]>(() => [
  ...costScopeOptions.value.map(option => ({ ...option, historical: false })),
  ...historicalScopes.value.map(scope => ({
    id: scope.id,
    label: scope.label,
    detail: scope.detail,
    materialProcess: '',
    specification: scope.detail,
    area: null,
    useArea: false,
    quantity: null,
    unit: '',
    unitPrice: null,
    subtotalAmount: null,
    registeredAmount: scope.registeredAmount,
    recordCount: scope.recordCount,
    historical: true,
  })),
])

const form = reactive({
  category: '',
  quantity: 0,
  specification: '',
  unit: "",
  unit_price: 0,
  amount: 0,
  payment_method: '',
  payee_company_name: '',
  debt_amount: 0,
  cost_date: '',
  description: '',
  remark: '',
  summary: '',
  group_name: '',
  order_item_id: '',
  order_item_ids: [] as string[],
  quote_item_id: '',
})

const scopeMode = computed<'document' | 'items'>({
  get: () => form.order_item_ids.length > 0 ? 'items' : 'document',
  set: value => {
    if (value === 'document') form.order_item_ids = []
  },
})

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending_confirm: '待确认', confirmed: '已确认', in_progress: '进行中',
    in_production: '生产中', in_installation: '安装中',
    completed: '已完成', cancelled: '已取消',
  }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending_confirm: 'warning', confirmed: 'info', in_progress: '', in_production: '', in_installation: '', completed: 'success', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

const selectedIds = ref<string[]>([])

function onSelectionChange(rows: ProjectCostResponse[]) {
  selectedIds.value = rows.map(r => r.id)
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return
  try {
    await ElMessageBox.confirm(`确定批量删除选中的 ${selectedIds.value.length} 条成本记录吗？`, '确认批量删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await batchDeleteProjectCosts(selectedIds.value)
    ElMessage.success(`已删除 ${selectedIds.value.length} 条记录`)
    selectedIds.value = []
    fetchData()
    void fetchCostSummary()
  } catch {
    // cancelled or API error
  }
}

function resetForm() {
  Object.assign(form, { category: '', amount: 0, payment_method: '', payee_company_name: '', debt_amount: 0, cost_date: '', description: '', summary: '', remark: '', group_name: '', order_item_id: '', order_item_ids: [], quote_item_id: '', quantity: 0, specification: '', unit: '', unit_price: 0 })
  isEditing.value = false
  editingId.value = ''
  editingScopeSnapshots.value = []
  dialogAttachments.value = []
}

function openCreate(orderItemId?: string) {
  resetForm()
  const requestedItemId = orderItemId || (typeof route.query.order_item_id === 'string' ? route.query.order_item_id : '')
  if (!isQuote.value && requestedItemId && activeOrderItemIds.value.has(requestedItemId)) {
    form.order_item_ids = [requestedItemId]
  }
  showDialog.value = true
}

function openEdit(row: ProjectCostResponse) {
  isEditing.value = true
  editingId.value = row.id
  form.category = row.category
  form.amount = row.amount
  form.payment_method = row.payment_method || ''
  form.payee_company_name = row.payee_company_name || ''
  form.debt_amount = row.debt_amount || 0
  form.cost_date = formatDate(row.cost_date) || ''
  form.description = row.description || ''
  form.remark = row.remark || ''
  form.summary = row.summary || ''
  form.quantity = row.quantity || 0
  form.specification = row.specification || ''
  form.unit = row.unit || ''
  form.unit_price = row.unit_price || 0
  form.group_name = row.group_name || ''
  form.order_item_id = row.order_item_id || ''
  form.quote_item_id = row.quote_item_id || ''
  const rowItemIds = row.order_item_ids?.length
    ? row.order_item_ids
    : (row.order_item_id ? [row.order_item_id] : [])
  const rowScopeNames = new Map((row.item_scopes || []).map(scope => [scope.order_item_id, scope.order_item_name]))
  form.order_item_ids = [...rowItemIds]
  editingScopeSnapshots.value = rowItemIds.map(itemId => ({
    id: itemId,
    label: rowScopeNames.get(itemId) || row.order_item_name || '未命名明细',
    detail: '该明细已失效，仅保留原成本记录归属',
  }))
  dialogAttachments.value = []
  showDialog.value = true
  loadAttachments(row.id)
}

function openImport() {
  showImport.value = true
  selectedFile.value = null
  importResult.value = null
}

function onFileChange(file: UploadFile) {
  selectedFile.value = file.raw || null
}

function setOrderItemSelected(orderItemId: string, selected: boolean) {
  if (!activeOrderItemIds.value.has(orderItemId)) return
  if (selected) {
    if (!form.order_item_ids.includes(orderItemId)) form.order_item_ids.push(orderItemId)
    return
  }
  form.order_item_ids = form.order_item_ids.filter(id => id !== orderItemId)
}

function toggleOrderItem(orderItemId: string) {
  if (historicalScopes.value.some(scope => scope.id === orderItemId)) return
  setOrderItemSelected(orderItemId, !form.order_item_ids.includes(orderItemId))
}

function isScopeSelected(row: ProjectCostScopeTableRow) {
  return form.order_item_ids.includes(row.id)
}

function handleScopeRowClick(row: ProjectCostScopeTableRow) {
  if (row.historical) return
  toggleOrderItem(row.id)
}

function scopeRowClassName({ row }: { row: ProjectCostScopeTableRow }) {
  if (row.historical) return 'scope-row-historical'
  return isScopeSelected(row) ? 'scope-row-selected' : ''
}

function formatScopeNumber(value: number | null) {
  if (value == null) return '-'
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

function formatScopeArea(row: ProjectCostScopeTableRow) {
  return row.useArea && row.area != null ? row.area.toFixed(2) : '-'
}

function formatScopeMoney(value: number | null) {
  return value == null ? '-' : `¥ ${value.toFixed(2)}`
}

function costScopeLabel(row: ProjectCostResponse) {
  if (isQuote.value) {
    return row.quote_item_id ? `报价明细 · ${row.quote_item_name || '未命名明细'}` : '报价单'
  }
  const itemIds = getProjectCostScopeIds(row)
  if (itemIds.length > 1) {
    const names = (row.item_scopes || [])
      .map(scope => scope.order_item_name)
      .filter((name): name is string => Boolean(name))
    return `订单明细（${itemIds.length}项）${names.length ? ` · ${names.join('、')}` : ''}`
  }
  return itemIds.length ? `订单明细 · ${row.order_item_name || '未命名明细'}` : '整单成本'
}

function isHistoricalCost(row: ProjectCostResponse) {
  if (isQuote.value) return false
  const itemIds = getProjectCostScopeIds(row)
  return itemIds.some(itemId => !activeOrderItemIds.value.has(itemId))
}

function downloadTemplate() {
  const token = localStorage.getItem('token')
  const url = '/api/v1/project-costs/template'
  fetch(url, { headers: { Authorization: 'Bearer ' + token } })
    .then(function(res) {
      if (!res.ok) throw new Error('Download failed')
      return res.blob()
    })
    .then(function(blob) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = '项目成本导入模板.xlsx'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    })
    .catch(function() {
      ElMessage.error('下载模板失败')
    })
}

async function fetchOrder() {
  const requestId = ++orderRequestId
  try {
    if (isQuote.value) {
      const { getQuote } = await import('@/api/quotes')
      const latest = await getQuote(sourceId.value)
      if (requestId === orderRequestId) order.value = latest
    } else {
      const latest = await getOrder(sourceId.value)
      if (requestId === orderRequestId) {
        order.value = latest
        const requestedItemId = typeof route.query.order_item_id === 'string' ? route.query.order_item_id : ''
        if (!queryCreateOpened.value && requestedItemId && latest.items.some(item => item.id === requestedItemId && (item.lifecycle_status == null || item.lifecycle_status === 'active'))) {
          queryCreateOpened.value = true
          openCreate(requestedItemId)
        }
      }
    }
  } catch { /* ignore */ }
}

async function fetchCostSummary() {
  if (isQuote.value) {
    costSummary.value = null
    return
  }
  try {
    costSummary.value = await getOrderProjectCostItemSummary(sourceId.value)
  } catch {
    costSummary.value = null
  }
}

async function fetchData() {
  const requestId = ++dataRequestId
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (isQuote.value) {
      params.quote_id = sourceId.value
      params.source_type = 'quote'
    } else {
      params.order_id = sourceId.value
    }
    if (filterCategory.value) params.category = filterCategory.value
    if (dateRange.value) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const data = await getProjectCosts(params)
    if (requestId === dataRequestId) {
      list.value = data.items
      total.value = data.total
    }
  } finally {
    if (requestId === dataRequestId) loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      const payload: Record<string, unknown> = {}
      if (form.category) payload.category = form.category
      if (form.amount > 0) payload.amount = form.amount
      if (form.payment_method) payload.payment_method = form.payment_method
      if (form.payee_company_name) payload.payee_company_name = form.payee_company_name
      if (form.quantity > 0) payload.quantity = form.quantity
      if (form.specification) payload.specification = form.specification
      if (form.unit) payload.unit = form.unit
      if (form.unit_price > 0) payload.unit_price = form.unit_price
      if (form.debt_amount > 0) payload.debt_amount = form.debt_amount
      else payload.debt_amount = 0
      if (form.cost_date) payload.cost_date = form.cost_date
      if (form.description) payload.description = form.description
      payload.summary = form.summary
      if (form.remark) payload.remark = form.remark
      if (isQuote.value) {
        if (form.quote_item_id) payload.quote_item_id = form.quote_item_id
      } else {
        payload.order_item_ids = [...form.order_item_ids]
      }
      if (form.group_name) payload.group_name = form.group_name
      await updateProjectCost(editingId.value, payload)
      ElMessage.success('成本已更新')
    } else {
      if (isQuote.value) {
        await createProjectCost({
          source_type: 'quote',
          quote_id: sourceId.value,
          category: form.category,
          amount: form.amount,
          cost_date: form.cost_date || undefined,
          description: form.description || undefined,
          summary: form.summary || undefined,
          remark: form.remark || undefined,
          quote_item_id: form.quote_item_id || undefined,
          group_name: form.group_name || undefined,
          payment_method: form.payment_method || undefined,
          payee_company_name: form.payee_company_name || undefined,
          quantity: form.quantity > 0 ? form.quantity : undefined,
          specification: form.specification || undefined,
          unit: form.unit || undefined,
          unit_price: form.unit_price > 0 ? form.unit_price : undefined,
          debt_amount: form.debt_amount > 0 ? form.debt_amount : undefined,
        })
      } else {
        await createProjectCost({
          source_type: 'order',
          order_id: sourceId.value,
          category: form.category,
          amount: form.amount,
          cost_date: form.cost_date || undefined,
          description: form.description || undefined,
          summary: form.summary || undefined,
          remark: form.remark || undefined,
          order_item_ids: form.order_item_ids.length ? [...form.order_item_ids] : undefined,
          group_name: form.group_name || undefined,
          payment_method: form.payment_method || undefined,
          payee_company_name: form.payee_company_name || undefined,
          quantity: form.quantity > 0 ? form.quantity : undefined,
          specification: form.specification || undefined,
          unit: form.unit || undefined,
          unit_price: form.unit_price > 0 ? form.unit_price : undefined,
          debt_amount: form.debt_amount > 0 ? form.debt_amount : undefined,
        })
      }
      ElMessage.success('成本登记成功')
    }
    showDialog.value = false
    resetForm()
    fetchData()
    void fetchCostSummary()
  } catch {
    // API error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: ProjectCostResponse) {
  try {
    await ElMessageBox.confirm(`确定删除成本「${row.cost_no}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProjectCost(row.id)
    ElMessage.success('已删除')
    fetchData()
    void fetchCostSummary()
  } catch {
    // User cancelled or API error
  }
}

function goBack() {
  if (isQuote.value && window.history.length > 1) {
    history.back()
  } else {
    router.push('/project-costs')
  }
}

async function handleImport() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择Excel文件')
    return
  }
  importing.value = true
  try {
    const result = await importProjectCosts(selectedFile.value, isQuote.value ? undefined : sourceId.value, isQuote.value ? sourceId.value : undefined, isQuote.value ? 'quote' : 'order')
    importResult.value = result
    if (result.created > 0) {
      fetchData()
      void fetchCostSummary()
    }
  } catch {
    // API error handled by interceptor
  } finally {
    importing.value = false
  }
}

async function loadAttachments(costId: string) {
  try {
    dialogAttachments.value = await getProjectCostAttachments(costId)
  } catch { /* ignore */ }
}

async function handleUploadAtt(file: File) {
  if (!editingId.value) return
  uploadingAtt.value = true
  try {
    const att = await uploadProjectCostAttachment(editingId.value, file)
    dialogAttachments.value.unshift(att)
    fetchData()
  } catch {
    // handled by interceptor
  } finally {
    uploadingAtt.value = false
  }
}

function onUploadChange(uploadFile: UploadFile) {
  if (uploadFile.raw) handleUploadAtt(uploadFile.raw)
  return false // prevent el-upload auto upload
}

async function handleDeleteAtt(att: AttachmentResponse) {
  try {
    await ElMessageBox.confirm(`确定删除凭证「${att.filename}」吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProjectCostAttachment(att.id)
    dialogAttachments.value = dialogAttachments.value.filter(a => a.id !== att.id)
    ElMessage.success('已删除')
    fetchData()
  } catch { /* cancelled */ }
}

function handlePreviewAtt(att: AttachmentResponse) {
  const url = `/uploads/${att.file_path}`
  if (att.file_type?.startsWith('image/')) {
    previewUrl.value = url
    previewVisible.value = true
  } else {
    window.open(url, '_blank')
  }
}

function refreshIfVisible() {
  if (document.hidden || loading.value) return
  void fetchOrder()
  void fetchData()
  void fetchCostSummary()
}

function handleVisibilityChange() {
  if (!document.hidden) {
    void fetchOrder()
    void fetchData()
    void fetchCostSummary()
  }
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
  void fetchOrder()
  void fetchData()
  void fetchCostSummary()
  startAutoRefresh()
})
onActivated(startAutoRefresh)
onDeactivated(stopAutoRefresh)
onUnmounted(stopAutoRefresh)
</script>

<style scoped>
.page { padding: 0; }
.order-header { margin-bottom: 8px; }
.order-card { background: var(--ad-card); border: 1px solid var(--ad-border); }
.order-info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: center;
}
.order-info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.order-info-item .label {
  font-size: 12px;
  color: var(--ad-text-secondary, #888);
}
.order-info-item .value {
  font-size: 14px;
  color: var(--ad-text);
}
.cost-summary-note {
  font-size: 11px;
  color: var(--ad-text-secondary, #888);
  white-space: nowrap;
}
.search-bar { display: flex; align-items: center; }
.cost-dialog :deep(.el-dialog__body) {
  max-height: min(70vh, 760px);
  overflow-x: hidden;
  overflow-y: auto;
}
.cost-scope-form-item :deep(.el-form-item__content) {
  min-width: 0;
}
.cost-scope-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.cost-scope-mode-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 34px;
  padding: 8px 12px;
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 6px;
  background: var(--el-color-primary-light-9);
  color: var(--ad-text-secondary, #888);
  font-size: 12px;
}
.cost-scope-mode-row strong {
  margin-left: auto;
  color: var(--el-color-warning);
  white-space: nowrap;
}
.cost-scope-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--ad-text, #303133);
  font-size: 13px;
  font-weight: 600;
}
.cost-scope-count {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 400;
}
.cost-scope-table-wrap {
  width: 100%;
  overflow-x: auto;
}
.cost-scope-table {
  width: 100%;
  min-width: 1080px;
}
.scope-project-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.scope-project-cell > span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.scope-cost-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  line-height: 1.25;
}
.scope-cost-cell strong {
  color: var(--el-color-warning);
  white-space: nowrap;
}
.scope-cost-cell span {
  color: var(--ad-text-secondary, #888);
  font-size: 11px;
  white-space: nowrap;
}
.scope-cost-cell .scope-cost-muted {
  color: var(--el-color-info);
}
.cost-scope-table :deep(.scope-row-historical td.el-table__cell) {
  background: var(--el-fill-color-light);
}
.cost-scope-table :deep(.scope-row-selected td.el-table__cell) {
  background: var(--el-color-primary-light-9);
}
.cost-scope-table :deep(.scope-row-historical .cell) {
  color: var(--ad-text-secondary, #888);
}
.scope-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.form-tip {
  margin-top: 6px;
  color: var(--ad-text-secondary, #888);
  font-size: 12px;
  line-height: 1.5;
}
@media (max-width: 760px) {
  .cost-scope-mode-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .cost-scope-mode-row strong {
    width: 100%;
    margin-left: 0;
  }
}
.att-thumb {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--ad-border, #dcdfe6);
  cursor: pointer;
}
.att-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.att-file {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ad-darker);
  font-size: 12px;
  color: var(--ad-text-secondary);
  font-weight: bold;
}
.att-del {
  position: absolute;
  top: 2px;
  right: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}
.att-thumb:hover .att-del {
  opacity: 1;
}

</style>
