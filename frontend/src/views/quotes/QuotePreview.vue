<template>
  <el-dialog
    :model-value="visible"
    title="报价单预览"
    width="800px"
    :close-on-click-modal="true"
    @close="$emit('close')"
  >
    <div v-if="loading" v-loading="true" style="height: 200px" />
    <div v-else-if="quote" class="print-area">
      <div class="preview-header">
        <div class="company-logo">LOGO</div>
        <div class="company-info">
          <div class="company-name">广告制作公司</div>
          <div class="company-detail">地址: __________  电话: __________</div>
        </div>
      </div>

      <h2 class="preview-title">报 价 单</h2>

      <div class="preview-meta">
        <div class="meta-row">
          <span>报价单号: {{ quote.quote_no }}</span>
          <span>日　　期: {{ quote.created_at?.slice(0, 10) }}</span>
        </div>
        <div class="meta-row">
          <span>有效期至: {{ quote.valid_until || '-' }}</span>
          <span>状　　态: {{ statusLabel(quote.status) }}</span>
        </div>
      </div>

      <div class="preview-parties">
        <div class="party-row">
          <span>客户名称: {{ quote.customer_name || '-' }}</span>
          <span>联系电话: {{ customerPhone }}</span>
        </div>
        <div class="party-row">
          <span>项目名称: {{ quote.project_name || '-' }}</span>
          <span>业 务 员: {{ salesName }}</span>
        </div>
        <div v-if="quote.department" class="party-row">
          <span>部门/科室: {{ quote.department }}</span>
          <span></span>
        </div>
      </div>

      <table class="preview-table">
        <colgroup>
          <col style="width: 5%" />
          <col style="width: 14%" />
          <col style="width: 13%" />
          <col style="width: 13%" />
          <col style="width: 6%" />
          <col style="width: 6%" />
          <col style="width: 9%" />
          <col style="width: 10%" />
          <col style="width: 9%" />
        </colgroup>
        <thead>
          <tr>
            <th>序号</th>
            <th>项目内容</th>
            <th>材质工艺</th>
            <th>规格</th>
            <th>数量</th>
            <th>单位</th>
            <th>单价</th>
            <th>小计</th>
            <th>备注</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="row in previewDisplayRows" :key="row.key">
            <tr v-if="row.type === 'group-header'" class="group-header">
              <td colspan="9">分项：{{ row.groupName }}</td>
            </tr>
            <tr v-else-if="row.type === 'group-total'" class="group-total">
              <td colspan="7" style="text-align: right;">分项合计</td>
              <td>{{ row.total.toFixed(2) }}</td>
              <td></td>
            </tr>
            <tr v-else>
              <td style="text-align: center">{{ row.idx }}</td>
              <td>{{ row.item.item_name }}</td>
              <td>{{ row.item.material_process || '-' }}</td>
              <td>{{ formatSpec(row.item) }}</td>
              <td style="text-align: right">{{ row.item.quantity }}</td>
              <td style="text-align: center">{{ row.item.use_area ? '㎡' : (row.item.unit || '-') }}</td>
              <td style="text-align: right">{{ row.item.unit_price?.toFixed(2) }}</td>
              <td style="text-align: right">{{ row.item.subtotal_amount?.toFixed(2) }}</td>
              <td>{{ row.item.remark || '' }}</td>
            </tr>
          </template>
        </tbody>
      </table>

      <div class="preview-summary">
        <div class="summary-row">
          <span>小　　计: ¥{{ quote.subtotal_amount?.toFixed(2) }}</span>
          <span>优　　惠: ¥{{ quote.discount_amount?.toFixed(2) }}</span>
          <span>税　　率: {{ quote.tax_rate }}%</span>
        </div>
        <div class="summary-row">
          <span>税　　额: ¥{{ quote.tax_amount?.toFixed(2) }}</span>
          <span class="total">合　　计: ¥{{ quote.total_amount?.toFixed(2) }}</span>
        </div>
      </div>

      <div v-if="quote.remark" class="preview-remark">
        <div class="remark-label">备注:</div>
        <div class="remark-content">{{ quote.remark }}</div>
      </div>

      <div class="preview-terms">
        <div class="terms-label">条款说明:</div>
        <ol>
          <li>本报价有效期见上方日期</li>
          <li>付款方式: 预付50%，完工付余款</li>
          <li>本报价不含税，如需发票另加税点</li>
        </ol>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
      <el-button type="primary" @click="handlePrint">打印</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getQuote } from '@/api/quotes'
import { getCustomer } from '@/api/customers'
import { QuoteDetailResponse, QuoteItemResponse } from '@/types/api'

const props = defineProps<{
  visible: boolean
  quoteId: string | null
  currentItems?: QuoteItemResponse[]
}>()

defineEmits<{
  close: []
}>()

const loading = ref(false)
const quote = ref<QuoteDetailResponse | null>(null)
const customerPhone = ref('-')
const salesName = ref('-')

type PreviewRow =
  | { type: 'group-header'; groupName: string; key: string }
  | { type: 'item'; item: QuoteItemResponse; idx: number; key: string }
  | { type: 'group-total'; groupName: string; total: number; key: string }

const previewDisplayRows = computed<PreviewRow[]>(() => {
  if (!quote.value) return []
  const items = quote.value.items || []
  const grouped = new Map<string, QuoteItemResponse[]>()
  const ungrouped: QuoteItemResponse[] = []

  for (const item of items) {
    if (item.group_name) {
      if (!grouped.has(item.group_name)) grouped.set(item.group_name, [])
      grouped.get(item.group_name)!.push(item)
    } else {
      ungrouped.push(item)
    }
  }

  const rows: PreviewRow[] = []
  let idx = 1
  for (const [groupName, groupItems] of grouped) {
    rows.push({ type: 'group-header', groupName, key: `gh-${groupName}` })
    for (const item of groupItems) rows.push({ type: 'item', item, idx: idx++, key: item.id || `i-${idx}` })
    const total = groupItems.reduce((s, i) => s + (i.subtotal_amount || 0), 0)
    rows.push({ type: 'group-total', groupName, total, key: `gt-${groupName}` })
  }
  for (const item of ungrouped) rows.push({ type: 'item', item, idx: idx++, key: item.id || `i-${idx}` })
  return rows
})

watch(() => props.visible, async (val) => {
  if (!val || !props.quoteId) return
  loading.value = true
  try {
    quote.value = await getQuote(props.quoteId)
    // 如果传入了当前编辑的items，使用它们覆盖API返回的items
    if (props.currentItems) {
      quote.value.items = props.currentItems
    }
    if (quote.value.customer_id) {
      try {
        const customer = await getCustomer(quote.value.customer_id)
        customerPhone.value = customer.phone || '-'
      } catch { customerPhone.value = '-' }
    }
    salesName.value = '-'
  } finally {
    loading.value = false
  }
})

function statusLabel(s: string) {
  const map: Record<string, string> = { draft: '草稿', confirmed: '已确认', converted: '已转订单', cancelled: '已作废' }
  return map[s] || s
}

function formatSpec(item: QuoteItemResponse) {
  const parts: string[] = []
  if (item.length) parts.push(`${item.length}${item.length_unit || 'm'}`)
  if (item.width) parts.push(`${item.width}${item.width_unit || 'm'}`)
  if (item.height) parts.push(`${item.height}${item.height_unit || 'm'}`)
  if (item.pieces && item.pieces > 1) parts.push(`${item.pieces}`)
  return parts.length ? parts.join(' × ') : '-'
}

function handlePrint() {
  window.print()
}
</script>

<style>
/* 不用 scoped，因为 el-dialog teleport 到 body，scoped 样式无法穿透 */
.preview-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #333;
}
.company-logo {
  width: 80px;
  height: 80px;
  border: 1px dashed #ccc;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}
.company-name {
  font-size: 20px;
  font-weight: bold;
}
.company-detail {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
.preview-title {
  text-align: center;
  font-size: 22px;
  margin: 16px 0;
  letter-spacing: 8px;
}
.preview-meta,
.preview-parties {
  margin-bottom: 12px;
}
.meta-row,
.party-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 14px;
}
.preview-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 12px;
  table-layout: fixed;
}
.preview-table th,
.preview-table td {
  border: 1px solid #333;
  padding: 6px 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-all;
}
.preview-table th {
  background: #f5f5f5;
  font-weight: bold;
  text-align: center;
}
.preview-table .group-header td {
  background: #e8edf2;
  border-bottom: 2px solid #409eff;
  font-weight: 600;
  padding: 6px 12px;
}
.preview-table .group-total td {
  background: #f5f5f5;
  font-weight: 600;
}
.preview-summary {
  margin: 16px 0;
  padding: 12px;
  border: 1px solid #ddd;
  background: #fafafa;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 14px;
}
.summary-row .total {
  font-weight: bold;
  font-size: 16px;
  color: #e6a23c;
}
.preview-remark {
  margin: 12px 0;
  font-size: 13px;
}
.remark-label {
  font-weight: bold;
  margin-bottom: 4px;
}
.remark-content {
  color: #666;
  white-space: pre-wrap;
}
.preview-terms {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed #ccc;
  font-size: 12px;
  color: #666;
}
.terms-label {
  font-weight: bold;
  margin-bottom: 6px;
  color: #333;
}
.preview-terms ol {
  margin: 0;
  padding-left: 20px;
}
.preview-terms li {
  margin-bottom: 4px;
}

@media print {
  :deep(.el-dialog__header),
  :deep(.el-dialog__footer),
  :deep(.el-overlay) {
    display: none !important;
  }
  .print-area {
    padding: 0;
    margin: 0;
  }
}
</style>
