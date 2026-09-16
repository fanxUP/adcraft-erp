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
            <span class="label">部门/科室</span>
            <span class="value" :title="order.department || undefined">{{ order.department || '-' }}</span>
          </div>
          <div class="order-info-item">
            <span class="label">状态</span>
            <StatusTag :status="order.status_view || order.status" size="sm" />
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
      <el-table-column label="供应商" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.supplier_name || row.payee_company_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="payment_amount" label="支付金额" width="140" align="right" sortable>
        <template #default="{ row }">¥ {{ getCostPaymentAmount(row as ProjectCostResponse).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="debt_amount" label="欠款金额" width="140" align="right" sortable>
        <template #default="{ row }">
          <span :class="{ 'cost-debt-value': Number(row.debt_amount || 0) > 0 }">
            ¥ {{ Number(row.debt_amount || 0).toFixed(2) }}
          </span>
          <div v-if="row.status_view" class="cost-status-inline">
            <StatusTag :status="row.status_view" size="sm" />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.category || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="付款方式" width="120">
        <template #default="{ row }">{{ row.payment_method || '-' }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="支出总额" width="140" align="right" sortable>
        <template #default="{ row }">¥ {{ Number(row.amount || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="说明" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '-' }}</template>
      </el-table-column>
      <el-table-column label="凭证" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.attachment_count > 0" size="small" type="success">{{ row.attachment_count }}</el-tag>
          <span v-else></span>
        </template>
      </el-table-column>
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
    <el-dialog v-model="showDialog" :title="isEditing ? '编辑成本' : '登记成本'" width="min(96vw, 1360px)" class="cost-dialog" :close-on-click-modal="false" @closed="discardQueuedCostAttachments">
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
        <el-form-item v-if="canUseSupplier" label="供应商">
          <el-select
            v-model="form.supplier_id"
            clearable
            filterable
            placeholder="选择供应商（可选）"
            style="width: 100%"
          >
            <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
          </el-select>
          <div class="form-tip">选择后将这笔成本关联到供应商；不选择时按无供应商支出记录。</div>
        </el-form-item>
        <el-form-item label="支付金额" required>
          <el-input-number v-model="form.payment_amount" :min="0" :precision="2" style="width: 100%" placeholder="已实际支付的金额" />
        </el-form-item>
        <el-form-item label="欠款金额">
          <el-input-number v-model="form.debt_amount" :min="0" :precision="2" style="width: 100%" placeholder="0 表示无欠款" />
          <div class="form-tip">大于 0 时进入应付管理。</div>
        </el-form-item>
        <el-form-item label="分类" required>
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
        <el-form-item label="支出总额" required>
          <div class="cost-form-total">¥ {{ formTotalAmount.toFixed(2) }}</div>
          <div class="form-tip">支出总额 = 支付金额 + 欠款金额，此项自动计算。</div>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="填写这笔支出的说明…" />
        </el-form-item>
        <el-form-item label="凭证">
          <div
            class="cost-attachment-dropzone"
            :class="{ 'is-disabled': !isEditing, 'is-dragover': costAttachmentDragActive }"
            role="button"
            tabindex="0"
            @click="openCostAttachmentPicker"
            @keydown.enter.prevent="openCostAttachmentPicker"
            @keydown.space.prevent="openCostAttachmentPicker"
            @dragenter.prevent="handleCostAttachmentDragEnter"
            @dragover.prevent="handleCostAttachmentDragOver"
            @dragleave.prevent="handleCostAttachmentDragLeave"
            @drop.prevent="handleCostAttachmentDrop"
          >
            <input
              ref="costAttachmentInput"
              class="cost-attachment-input"
              type="file"
              multiple
              :accept="PROJECT_COST_ATTACHMENT_ACCEPT"
              :disabled="!isEditing"
              @click.stop
              @change="handleCostAttachmentInputChange"
            />
            <el-icon class="cost-attachment-drop-icon"><UploadFilled /></el-icon>
            <div class="cost-attachment-drop-title">将凭证拖到这里上传</div>
            <div class="cost-attachment-drop-subtitle">或点击选择文件，支持批量上传</div>
            <div class="cost-attachment-drop-hint">支持 JPG、PNG、WEBP、PDF；请先保存成本记录后上传凭证</div>
          </div>

          <div v-if="attachmentUploadQueue.length" class="cost-attachment-upload-queue">
            <div v-for="item in attachmentUploadQueue" :key="item.id" class="cost-attachment-upload-row">
              <span class="cost-attachment-upload-name" :title="item.name">{{ item.name }}</span>
              <el-tag v-if="item.status === 'queued'" size="small" type="info">等待上传</el-tag>
              <el-tag v-else-if="item.status === 'uploading'" size="small" type="warning">上传中</el-tag>
              <template v-else>
                <el-tag size="small" type="danger">{{ item.error || '上传失败' }}</el-tag>
                <el-button text type="primary" size="small" @click="retryCostAttachment(item)">重试</el-button>
              </template>
            </div>
          </div>

          <div v-if="dialogAttachments.length" class="cost-attachment-grid">
            <div v-for="att in dialogAttachments" :key="att.id" class="cost-attachment-item">
              <el-image
                v-if="getProjectCostAttachmentKind(att) === 'image'"
                class="cost-attachment-image"
                :src="getProjectCostAttachmentUrl(att.file_path)"
                :alt="att.filename"
                fit="cover"
                lazy
                :preview-src-list="imageAttachmentUrls"
                :initial-index="imagePreviewIndex(att.id)"
                :zoom-rate="PROJECT_COST_ATTACHMENT_PREVIEW_ZOOM_RATE"
                preview-teleported
              />
              <button
                v-else
                type="button"
                class="cost-attachment-file"
                :title="`打开 ${att.filename || '凭证'}`"
                @click="previewCostAttachment(att)"
              >
                <span class="cost-attachment-file-ext">{{ costAttachmentExtension(att.filename) }}</span>
                <span class="cost-attachment-file-name">{{ att.filename || '凭证文件' }}</span>
              </button>
              <div class="cost-attachment-name" :title="att.filename">{{ att.filename || '未命名凭证' }}</div>
              <el-button
                class="cost-attachment-delete"
                :icon="Delete"
                size="small"
                circle
                @click="handleDeleteAtt(att)"
              />
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" :disabled="uploadingAtt" @click="handleSave" type="primary">
          {{ isEditing ? '保存' : '登记' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="showImport" title="导入Excel" width="480px" :close-on-click-modal="false">
      <p style="margin-bottom: 12px; color: var(--ad-text-secondary)">
        Excel 需包含以下列：<br />
        <b>日期、供应商、支付金额、欠款金额、分类、付款方式、支出总额、说明</b>
      </p>
      <p style="margin-bottom: 12px; color: var(--ad-text-secondary); font-size: 13px">
        导入的成本将自动关联到 <b>{{ isQuote ? (order?.quote_no || '报价单') : (order?.order_no || '订单') }}</b>
        ，凭证请在成本记录保存后通过拖拽上传。
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
import { getSuppliers } from '@/api/suppliers'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { ArrowLeft, Delete, Download, UploadFilled } from '@element-plus/icons-vue'
import type { ProjectCostResponse, ProjectCostImportResponse, OrderDetailResponse, QuoteDetailResponse, AttachmentResponse, ProjectCostItemSummaryResponse, SupplierResponse } from '@/types/api'
import { StatusTag } from '@/components/ui'
import { buildProjectCostScopeOptions, getProjectCostScopeIds, type ProjectCostScopeOption } from '@/utils/projectCostScope'
import { getProjectCostPaymentAmount, normalizeProjectCostAmounts } from '@/utils/projectCostAmount'
import {
  PROJECT_COST_ATTACHMENT_ACCEPT,
  PROJECT_COST_ATTACHMENT_PREVIEW_ZOOM_RATE,
  getProjectCostAttachmentKind,
  getProjectCostAttachmentUrl,
  validateProjectCostAttachment,
} from '@/utils/projectCostAttachment'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const canUseSupplier = computed(() => authStore.can('supplier:read'))

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
const suppliers = ref<SupplierResponse[]>([])
const selectedFile = ref<File | null>(null)
const importResult = ref<ProjectCostImportResponse | null>(null)
const dialogAttachments = ref<AttachmentResponse[]>([])
const uploadingAtt = ref(false)
const costAttachmentInput = ref<HTMLInputElement | null>(null)
const costAttachmentDragActive = ref(false)
const attachmentUploadQueue = ref<CostAttachmentUploadItem[]>([])

interface CostAttachmentUploadItem {
  id: string
  costId: string
  file: File
  name: string
  status: 'queued' | 'uploading' | 'error'
  error?: string
}

const REFRESH_INTERVAL_MS = 15000
let refreshTimer: ReturnType<typeof setInterval> | null = null
let orderRequestId = 0
let dataRequestId = 0
let costAttachmentDragDepth = 0
let costAttachmentQueueRunning = false
let costAttachmentSequence = 0
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
const imageAttachments = computed(() => dialogAttachments.value.filter(att => getProjectCostAttachmentKind(att) === 'image'))
const imageAttachmentUrls = computed(() => imageAttachments.value.map(att => getProjectCostAttachmentUrl(att.file_path)))
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
  payment_amount: 0,
  payment_method: '',
  supplier_id: '',
  debt_amount: 0,
  cost_date: '',
  remark: '',
  group_name: '',
  order_item_id: '',
  order_item_ids: [] as string[],
  quote_item_id: '',
})

const formTotalAmount = computed(() => {
  try {
    return normalizeProjectCostAmounts(form.payment_amount, form.debt_amount).totalAmount
  } catch {
    return 0
  }
})

const scopeMode = computed<'document' | 'items'>({
  get: () => form.order_item_ids.length > 0 ? 'items' : 'document',
  set: value => {
    if (value === 'document') form.order_item_ids = []
  },
})

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
  Object.assign(form, { category: '', payment_amount: 0, payment_method: '', supplier_id: '', debt_amount: 0, cost_date: '', remark: '', group_name: '', order_item_id: '', order_item_ids: [], quote_item_id: '' })
  isEditing.value = false
  editingId.value = ''
  editingScopeSnapshots.value = []
  dialogAttachments.value = []
  attachmentUploadQueue.value = []
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
  form.payment_amount = row.payment_amount ?? getProjectCostPaymentAmount(row.amount, row.debt_amount)
  form.payment_method = row.payment_method || ''
  form.supplier_id = row.supplier_id || ''
  form.debt_amount = row.debt_amount || 0
  form.cost_date = formatDate(row.cost_date) || ''
  form.remark = row.remark || ''
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
  attachmentUploadQueue.value = []
  showDialog.value = true
  loadAttachments(row.id)
}

async function fetchSuppliers() {
  if (!canUseSupplier.value) return
  try {
    const data = await getSuppliers({ page: 1, page_size: 200, is_active: true })
    suppliers.value = data.items
  } catch {
    // 供应商为可选字段，目录读取失败不阻断成本表单。
  }
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

function getCostPaymentAmount(row: ProjectCostResponse) {
  return row.payment_amount ?? getProjectCostPaymentAmount(row.amount, row.debt_amount)
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
  const category = form.category.trim()
  if (!category) {
    ElMessage.warning('请选择分类')
    return
  }

  let amounts
  try {
    amounts = normalizeProjectCostAmounts(form.payment_amount, form.debt_amount)
  } catch (error) {
    ElMessage.warning(error instanceof Error ? error.message : '请检查支付金额和欠款金额')
    return
  }

  saving.value = true
  try {
    if (isEditing.value) {
      const payload: Record<string, unknown> = {
        category,
        amount: amounts.totalAmount,
        debt_amount: amounts.debtAmount,
        cost_date: form.cost_date || null,
        payment_method: form.payment_method || null,
        supplier_id: form.supplier_id || null,
        remark: form.remark.trim() || null,
        group_name: form.group_name.trim() || null,
      }
      if (isQuote.value) {
        payload.quote_item_id = form.quote_item_id || null
      } else {
        payload.order_item_ids = [...form.order_item_ids]
      }
      await updateProjectCost(editingId.value, payload)
      ElMessage.success('成本已更新')
    } else {
      if (isQuote.value) {
        await createProjectCost({
          source_type: 'quote',
          quote_id: sourceId.value,
          category,
          amount: amounts.totalAmount,
          debt_amount: amounts.debtAmount,
          cost_date: form.cost_date || undefined,
          remark: form.remark || undefined,
          quote_item_id: form.quote_item_id || undefined,
          group_name: form.group_name || undefined,
          payment_method: form.payment_method || undefined,
          supplier_id: form.supplier_id || undefined,
        })
      } else {
        await createProjectCost({
          source_type: 'order',
          order_id: sourceId.value,
          category,
          amount: amounts.totalAmount,
          debt_amount: amounts.debtAmount,
          cost_date: form.cost_date || undefined,
          remark: form.remark || undefined,
          order_item_ids: form.order_item_ids.length ? [...form.order_item_ids] : undefined,
          group_name: form.group_name || undefined,
          payment_method: form.payment_method || undefined,
          supplier_id: form.supplier_id || undefined,
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

function openCostAttachmentPicker() {
  if (isEditing.value) costAttachmentInput.value?.click()
}

function handleCostAttachmentDragEnter() {
  if (!isEditing.value) return
  costAttachmentDragDepth += 1
  costAttachmentDragActive.value = true
}

function handleCostAttachmentDragOver() {
  if (isEditing.value) costAttachmentDragActive.value = true
}

function handleCostAttachmentDragLeave() {
  costAttachmentDragDepth = Math.max(0, costAttachmentDragDepth - 1)
  if (costAttachmentDragDepth === 0) costAttachmentDragActive.value = false
}

function handleCostAttachmentDrop(event: DragEvent) {
  costAttachmentDragDepth = 0
  costAttachmentDragActive.value = false
  if (!isEditing.value) return
  enqueueCostAttachments(Array.from(event.dataTransfer?.files || []))
}

function handleCostAttachmentInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  enqueueCostAttachments(files)
}

function enqueueCostAttachments(files: File[]) {
  if (!isEditing.value || !editingId.value || !files.length) return

  const accepted: File[] = []
  let rejectedCount = 0
  for (const file of files) {
    if (validateProjectCostAttachment(file)) rejectedCount += 1
    else accepted.push(file)
  }
  if (rejectedCount) {
    ElMessage.warning(`${rejectedCount} 个文件格式不支持，仅可上传 JPG、PNG、WEBP 或 PDF`)
  }
  if (!accepted.length) return

  const costId = editingId.value
  attachmentUploadQueue.value.push(...accepted.map(file => ({
    id: `${costId}-${Date.now()}-${costAttachmentSequence++}`,
    costId,
    file,
    name: file.name,
    status: 'queued' as const,
  })))
  void startCostAttachmentUploadQueue()
}

async function startCostAttachmentUploadQueue() {
  if (costAttachmentQueueRunning) return
  costAttachmentQueueRunning = true
  uploadingAtt.value = true
  try {
    while (true) {
      const next = attachmentUploadQueue.value.find(item => item.status === 'queued')
      if (!next) break
      next.status = 'uploading'
      try {
        const att = await uploadProjectCostAttachment(next.costId, next.file)
        if (showDialog.value && isEditing.value && editingId.value === next.costId) {
          dialogAttachments.value.unshift(att)
        }
        attachmentUploadQueue.value = attachmentUploadQueue.value.filter(item => item.id !== next.id)
        void fetchData()
        ElMessage.success(`${next.name} 上传成功`)
      } catch {
        next.status = 'error'
        next.error = '上传失败，请重试'
      }
    }
  } finally {
    costAttachmentQueueRunning = false
    uploadingAtt.value = false
  }
}

function retryCostAttachment(item: CostAttachmentUploadItem) {
  if (item.status !== 'error' || !isEditing.value || editingId.value !== item.costId) return
  item.status = 'queued'
  item.error = undefined
  void startCostAttachmentUploadQueue()
}

function discardQueuedCostAttachments() {
  costAttachmentDragDepth = 0
  costAttachmentDragActive.value = false
  // Keep the current request alive, but do not upload files that were still
  // waiting after the dialog was closed.
  attachmentUploadQueue.value = attachmentUploadQueue.value.filter(item => item.status === 'uploading')
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

function imagePreviewIndex(attachmentId: string) {
  return imageAttachments.value.findIndex(att => att.id === attachmentId)
}

function costAttachmentExtension(filename?: string | null) {
  const extension = filename?.trim().split('.').pop()
  return extension ? extension.toUpperCase() : '文件'
}

function previewCostAttachment(att: AttachmentResponse) {
  const url = getProjectCostAttachmentUrl(att.file_path)
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
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
  void fetchSuppliers()
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
.cost-form-total {
  min-height: 32px;
  color: var(--el-color-warning);
  font-size: 18px;
  font-weight: 600;
  line-height: 32px;
}
.cost-debt-value {
  color: var(--el-color-danger);
  font-weight: 600;
}
.cost-status-inline {
  margin-top: 4px;
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
.cost-attachment-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 132px;
  box-sizing: border-box;
  padding: 18px 24px;
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
  color: var(--ad-text-secondary, #909399);
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}
.cost-attachment-dropzone:hover,
.cost-attachment-dropzone.is-dragover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.cost-attachment-dropzone.is-disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.cost-attachment-input {
  display: none;
}
.cost-attachment-drop-icon {
  margin-bottom: 8px;
  color: var(--el-color-primary);
  font-size: 30px;
}
.cost-attachment-drop-title {
  color: var(--ad-text, #303133);
  font-size: 14px;
  font-weight: 600;
}
.cost-attachment-drop-subtitle {
  margin-top: 4px;
  color: var(--el-color-primary);
  font-size: 13px;
}
.cost-attachment-drop-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.4;
  text-align: center;
}
.cost-attachment-upload-queue {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  margin-top: 10px;
}
.cost-attachment-upload-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px 8px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  font-size: 12px;
}
.cost-attachment-upload-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--ad-text, #303133);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cost-attachment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
  width: 100%;
  margin-top: 14px;
}
.cost-attachment-item {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--ad-border, #dcdfe6);
  border-radius: 8px;
  background: var(--ad-card, #fff);
}
.cost-attachment-image,
.cost-attachment-file {
  display: flex;
  width: 100%;
  height: 112px;
  box-sizing: border-box;
}
.cost-attachment-image {
  cursor: zoom-in;
}
.cost-attachment-file {
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  border: 0;
  background: var(--el-fill-color-lighter);
  color: var(--ad-text-secondary, #606266);
  cursor: pointer;
  text-align: center;
}
.cost-attachment-file:hover {
  background: var(--el-fill-color-light);
}
.cost-attachment-file-ext {
  color: var(--el-color-primary);
  font-size: 18px;
  font-weight: 700;
}
.cost-attachment-file-name,
.cost-attachment-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cost-attachment-file-name {
  width: 100%;
  font-size: 12px;
}
.cost-attachment-name {
  padding: 7px 34px 7px 8px;
  color: var(--ad-text-secondary, #606266);
  font-size: 12px;
}
.cost-attachment-delete {
  position: absolute;
  top: 2px;
  right: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}
.cost-attachment-item:hover .cost-attachment-delete,
.cost-attachment-delete:focus-visible {
  opacity: 1;
}

@media (max-width: 760px) {
  .cost-attachment-dropzone {
    padding: 16px;
  }
  .cost-attachment-grid {
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  }
}

</style>
