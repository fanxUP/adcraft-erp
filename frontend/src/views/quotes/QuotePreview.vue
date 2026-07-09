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
      <!-- A4 打印内容容器 — 屏幕预览样式与打印一致 -->
      <div class="print-a4-wrapper" style="padding: 0;">
        <!-- 表头 -->
        <div class="print-header">
          <div class="print-logo">LOGO</div>
          <div class="print-company">
            <div class="print-company-name">广告制作公司</div>
            <div class="print-company-detail">地址: __________  电话: __________</div>
          </div>
        </div>

        <div class="print-title">报 价 单</div>

        <!-- 基本信息 -->
        <div class="print-info">
          <div class="print-info-row">
            <span><strong>报价单号:</strong> {{ quote.quote_no }}</span>
            <span><strong>日　　期:</strong> {{ quote.created_at?.slice(0, 10) }}</span>
          </div>
          <div class="print-info-row">
            <span><strong>有效期至:</strong> {{ quote.valid_until || '-' }}</span>
            <span><strong>状　　态:</strong> {{ statusLabel(quote.status) }}</span>
          </div>
        </div>

        <div class="print-info">
          <div class="print-info-row">
            <span><strong>客户名称:</strong> {{ quote.customer_name || '-' }}</span>
            <span><strong>联系电话:</strong> {{ customerPhone }}</span>
          </div>
          <div class="print-info-row">
            <span><strong>项目名称:</strong> {{ quote.project_name || '-' }}</span>
            <span><strong>业 务 员:</strong> {{ salesName }}</span>
          </div>
          <div v-if="quote.department" class="print-info-row">
            <span><strong>部门/科室:</strong> {{ quote.department }}</span>
            <span></span>
          </div>
        </div>

        <!-- 明细表格 -->
        <table class="print-table">
          <colgroup>
            <col style="width: 5%" />
            <col style="width: 16%" />
            <col style="width: 14%" />
            <col style="width: 14%" />
            <col style="width: 7%" />
            <col style="width: 6%" />
            <col style="width: 10%" />
            <col style="width: 11%" />
            <col style="width: 10%" />
          </colgroup>
          <thead>
            <tr>
              <th class="center">序号</th>
              <th>项目内容</th>
              <th>材质工艺</th>
              <th>规格</th>
              <th class="numeric">数量</th>
              <th class="center">单位</th>
              <th class="numeric">单价</th>
              <th class="numeric">小计</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in previewDisplayRows" :key="row.key">
              <tr v-if="row.type === 'group-header'" class="print-group-header">
                <td colspan="9"><strong>分项：</strong>{{ row.groupName }}</td>
              </tr>
              <tr v-else-if="row.type === 'group-total'" class="print-group-total">
                <td colspan="7" style="text-align: right;">分项合计</td>
                <td class="numeric">{{ row.total.toFixed(2) }}</td>
                <td></td>
              </tr>
              <tr v-else>
                <td class="center">{{ row.idx }}</td>
                <td>{{ row.item.item_name }}</td>
                <td>{{ row.item.material_process || '-' }}</td>
                <td>{{ formatSpec(row.item) }}</td>
                <td class="numeric">{{ row.item.quantity }}</td>
                <td class="center">{{ row.item.use_area ? '㎡' : (row.item.unit || '-') }}</td>
                <td class="numeric">{{ row.item.unit_price?.toFixed(2) }}</td>
                <td class="numeric">{{ row.item.subtotal_amount?.toFixed(2) }}</td>
                <td>{{ row.item.remark || '' }}</td>
              </tr>
            </template>
          </tbody>
        </table>

        <!-- 汇总 -->
        <div class="print-summary">
          <div class="print-summary-row">
            <span>小　　计: ¥{{ quote.subtotal_amount?.toFixed(2) }}</span>
            <span>优　　惠: ¥{{ quote.discount_amount?.toFixed(2) }}</span>
            <span>税　　率: {{ quote.tax_rate }}%</span>
          </div>
          <div class="print-summary-row">
            <span>税　　额: ¥{{ quote.tax_amount?.toFixed(2) }}</span>
            <span class="print-summary-total">合　　计: ¥{{ quote.total_amount?.toFixed(2) }}</span>
          </div>
        </div>

        <!-- 备注 -->
        <div v-if="quote.remark" class="print-remark">
          <div class="print-remark-label">备注:</div>
          <div class="print-remark-content">{{ quote.remark }}</div>
        </div>

        <!-- 条款 -->
        <div class="print-terms">
          <div class="print-terms-label">条款说明:</div>
          <ol>
            <li>本报价有效期见上方日期</li>
            <li>付款方式: 预付50%，完工付余款</li>
            <li>本报价不含税，如需发票另加税点</li>
          </ol>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
      <el-button type="primary" @click="handlePrintBySelector('.print-area')">打印</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getQuote } from '@/api/quotes'
import { getCustomer } from '@/api/customers'
import { usePrint } from '@/composables/usePrint'
import { QuoteDetailResponse, QuoteItemResponse } from '@/types/api'

const props = defineProps<{
  visible: boolean
  quoteId?: string
  currentItems?: QuoteItemResponse[]
}>()

const { handlePrintBySelector } = usePrint()

const loading = ref(false)
const quote = ref<QuoteDetailResponse | null>(null)
const customerPhone = ref('-')
const salesName = ref('-')

interface PreviewRow {
  type: 'group-header' | 'group-total' | 'item'
  groupName?: string
  item?: QuoteItemResponse
  idx?: number
  total?: number
  key: string
}

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
  if (!val) return
  loading.value = true
  try {
    if (props.quoteId) {
      quote.value = await getQuote(props.quoteId)
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
    } else if (props.currentItems) {
      quote.value = {
        id: '', quote_no: '（新建）', customer_name: '', project_name: '',
        status: 'draft', subtotal_amount: 0, discount_amount: 0,
        tax_rate: 0, tax_amount: 0, total_amount: 0,
        items: props.currentItems, created_at: undefined,
        department: undefined, sales_user_id: undefined, remark: undefined,
      }
    }
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
</script>

<style>
/* 屏幕预览样式 — 保持与打印一致 */
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

/* 打印样式由全局 print.scss 统一控制，
   此文件仅保留屏幕预览所需的最小样式 */
</style>
