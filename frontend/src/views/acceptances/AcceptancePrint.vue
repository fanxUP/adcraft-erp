<template>
  <el-dialog
    :model-value="visible"
    title=""
    width="960px"
    :close-on-click-modal="true"
    @close="$emit('close')"
  >
    <div v-if="loading" v-loading="true" style="height: 200px" />
    <div v-else-if="form" class="print-area">
      <!-- 标题 -->
      <h2 class="preview-title">{{ form.project_name || '' }} 验收单</h2>

      <!-- 基本信息 -->
      <div class="preview-info">
        <div class="info-row">
          <span>订单编号: {{ form.order_no || '-' }}</span>
          <span>客户名称: {{ form.customer_name || '-' }}</span>
          <span>联系电话: {{ form.customer_phone || '-' }}</span>
        </div>
        <div class="info-row">
          <span>联 系 人: {{ form.contact_person || '-' }}</span>
          <span>客户地址: {{ form.customer_address || '-' }}</span>
          <span>下单日期: {{ form.order_date?.slice(0, 10) || '-' }}</span>
        </div>
      </div>

      <!-- 验收明细表格 -->
      <table class="preview-table">
        <thead>
          <tr>
            <th style="width: 40px">序号</th>
            <th><div class="wrap-text">项目内容</div></th>
            <th><div class="wrap-text">材质工艺</div></th>
            <th><div class="wrap-text">规格</div></th>
            <th>面积</th>
            <th>数量</th>
            <th>单位</th>
            <th>单价</th>
            <th>小计</th>
            <th>样图</th>
            <th><div class="wrap-text">备注</div></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(row, idx) in displayRows" :key="idx">
            <!-- 分组标题行 -->
            <tr v-if="row.type === 'group-header'" class="group-header-row">
              <td colspan="11" style="font-weight: 600; background: #f5f7fa; border-bottom: 2px solid #409eff; padding: 6px 8px;">
                分项：{{ row.groupName }}
              </td>
            </tr>
            <!-- 分组合计行 -->
            <tr v-else-if="row.type === 'group-total'" class="group-total-row">
              <td colspan="8" style="text-align: right; font-weight: 600; background: #fafafa; border-top: 1px solid #dcdfe6; padding: 6px 8px;">分项合计</td>
              <td style="text-align: right; font-weight: 600; background: #fafafa; border-top: 1px solid #dcdfe6; padding: 6px 8px;">¥ {{ row.total.toFixed(2) }}</td>
              <td style="background: #fafafa; border-top: 1px solid #dcdfe6;"></td>
              <td style="background: #fafafa; border-top: 1px solid #dcdfe6;"></td>
            </tr>
            <!-- 明细行 -->
            <tr v-else>
              <td style="text-align: center">{{ row.idx }}</td>
              <td><div class="wrap-text">{{ row.item.item_name }}</div></td>
              <td><div class="wrap-text">{{ row.item.material_process || '-' }}</div></td>
              <td><div class="wrap-text">{{ row.item.specification || '-' }}</div></td>
              <td style="text-align: right">{{ row.item.area != null ? row.item.area.toFixed(2) : '-' }}</td>
              <td style="text-align: right">{{ row.item.quantity }}</td>
              <td style="text-align: center">{{ row.item.unit || '-' }}</td>
              <td style="text-align: right">{{ row.item.unit_price != null ? row.item.unit_price.toFixed(2) : '-' }}</td>
              <td style="text-align: right">{{ row.item.subtotal != null ? row.item.subtotal.toFixed(2) : '-' }}</td>
              <td style="text-align: center; padding: 4px;">
                <img v-if="row.item.image_url" :src="row.item.image_url" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" />
                <span v-else style="color: #999;">-</span>
              </td>
              <td><div class="wrap-text">{{ row.item.remark || '' }}</div></td>
            </tr>
          </template>
          <tr v-if="!form.items || form.items.length === 0">
            <td colspan="11" style="text-align: center; color: #999;">暂无验收明细</td>
          </tr>

          <!-- 金额汇总 -->
          <tr>
            <td colspan="8" style="text-align: right; font-weight: 600;">本页合计：</td>
            <td style="text-align: right; font-weight: 600;">¥ {{ itemsTotal.toFixed(2) }}</td>
            <td></td>
            <td></td>
          </tr>
          <tr>
            <td colspan="2" style="text-align: right;">金额（大写）：</td>
            <td colspan="5">{{ toChineseAmount(itemsTotal) }}</td>
            <td style="text-align: right;">金额（小写）：</td>
            <td style="text-align: right;">¥ {{ itemsTotal.toFixed(2) }}</td>
            <td></td>
            <td></td>
          </tr>
          <tr>
            <td colspan="11" style="padding: 8px 12px;">
              <div style="display: flex; justify-content: space-between;">
                <span>总金额：<strong>¥ {{ itemsTotal.toFixed(2) }}</strong></span>
                <span>优惠金额：<strong>¥ {{ (form.discount_amount || 0).toFixed(2) }}</strong></span>
                <span>预付金额：<strong>¥ {{ (form.advance_amount || 0).toFixed(2) }}</strong></span>
                <span>应付金额：<strong style="font-size: 14px;">¥ {{ payableAmount.toFixed(2) }}</strong></span>
              </div>
            </td>
          </tr>
        <tr>
          <td style="text-align: right; vertical-align: top; padding-top: 14px;">备注说明：</td>
          <td colspan="10" style="height: 60px; vertical-align: top; padding-top: 14px;">{{ form.remark || '' }}</td>
        </tr>
        </tbody>
      </table>

      <!-- 签字栏 -->
      <div class="preview-signatures">
        <div class="signature-block">
          <div class="signature-label">客户验收签字（盖章）：</div>
          <div style="height: 50px;"></div>
          <div class="signature-date">日期：________年____月____日</div>
        </div>
        <div class="signature-block">
          <div class="signature-label">验收人电话：</div>
        </div>
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
import { getAcceptance } from '@/api/acceptances'

interface AcceptancePrintItem {
  id?: string
  item_name: string
  material_process?: string
  specification?: string
  quantity: number
  unit?: string
  area?: number
  unit_price?: number
  subtotal?: number
  image_url?: string
  item_status: string
  remark?: string
  group_name?: string
}

interface AcceptancePrintData {
  acceptance_no: string
  status: string
  created_at?: string
  accepted_at?: string
  accepted_by?: string
  our_acceptor_name?: string
  remark?: string
  reject_reason?: string
  order_no?: string
  customer_name?: string
  customer_phone?: string
  customer_address?: string
  contact_person?: string
  order_date?: string
  project_name?: string
  discount_amount?: number
  advance_amount?: number
  items: AcceptancePrintItem[]
}

const props = defineProps<{
  visible: boolean
  acceptanceId: string | null
}>()

defineEmits<{
  close: []
}>()

const loading = ref(false)
const form = ref<AcceptancePrintData | null>(null)

type PrintDisplayRow =
  | { type: 'group-header'; groupName: string }
  | { type: 'item'; item: AcceptancePrintItem; groupName: string; idx: number }
  | { type: 'group-total'; groupName: string; total: number }

const displayRows = computed<PrintDisplayRow[]>(() => {
  const items = form.value?.items || []
  const grouped = new Map<string, AcceptancePrintItem[]>()
  const ungrouped: AcceptancePrintItem[] = []
  for (const item of items) {
    if (item.group_name) {
      if (!grouped.has(item.group_name)) grouped.set(item.group_name, [])
      grouped.get(item.group_name)!.push(item)
    } else {
      ungrouped.push(item)
    }
  }
  const rows: PrintDisplayRow[] = []
  let seq = 0
  for (const [groupName, groupItems] of grouped) {
    rows.push({ type: 'group-header', groupName })
    for (const item of groupItems) { seq++; rows.push({ type: 'item', item, groupName, idx: seq }) }
    const total = groupItems.reduce((s, i) => s + (i.subtotal || 0), 0)
    rows.push({ type: 'group-total', groupName, total })
  }
  for (const item of ungrouped) { seq++; rows.push({ type: 'item', item, groupName: '', idx: seq }) }
  return rows
})

const itemsTotal = computed(() => (form.value?.items || []).reduce((s, i) => s + (i.subtotal || 0), 0))
const payableAmount = computed(() => itemsTotal.value - (form.value?.discount_amount || 0) - (form.value?.advance_amount || 0))

function toChineseAmount(n: number): string {
  const digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const units = ['', '拾', '佰', '仟']
  const bigUnits = ['', '万', '亿']
  if (n === 0) return '零元整'
  const negative = n < 0
  n = Math.abs(n)
  const intPart = Math.floor(n)
  const decPart = Math.round((n - intPart) * 100)
  const jiao = Math.floor(decPart / 10)
  const fen = decPart % 10
  let result = ''
  if (intPart > 0) {
    const str = String(intPart)
    const len = str.length
    let zeroFlag = false
    for (let i = 0; i < len; i++) {
      const d = parseInt(str[i])
      const pos = len - 1 - i
      const unitIdx = pos % 4
      const bigIdx = Math.floor(pos / 4)
      if (d === 0) {
        zeroFlag = true
        if (unitIdx === 0 && bigUnits[bigIdx]) { result += bigUnits[bigIdx]; zeroFlag = false }
      } else {
        if (zeroFlag) { result += '零'; zeroFlag = false }
        result += digits[d] + units[unitIdx]
        if (unitIdx === 0 && bigUnits[bigIdx]) result += bigUnits[bigIdx]
      }
    }
    result += '元'
  }
  if (jiao === 0 && fen === 0) { result += '整' }
  else {
    if (jiao > 0) result += digits[jiao] + '角'
    else if (intPart > 0) result += '零'
    if (fen > 0) result += digits[fen] + '分'
  }
  return (negative ? '负' : '') + result
}

watch(() => props.visible, async (val) => {
  if (!val || !props.acceptanceId) return
  loading.value = true
  try {
    const data = await getAcceptance(props.acceptanceId)
    form.value = {
      acceptance_no: data.acceptance_no,
      status: data.status,
      created_at: data.created_at,
      accepted_at: data.accepted_at,
      accepted_by: data.accepted_by,
      our_acceptor_name: data.our_acceptor_name,
      remark: data.remark,
      reject_reason: data.reject_reason,
      order_no: data.order_no,
      customer_name: data.customer_name,
      customer_phone: data.customer_phone,
      customer_address: data.customer_address,
      contact_person: data.contact_person,
      order_date: data.order_date,
      project_name: data.project_name,
      discount_amount: data.discount_amount,
      advance_amount: data.advance_amount,
      items: (data.items || []).map(item => ({
        id: item.id,
        item_name: item.item_name,
        material_process: item.material_process,
        specification: item.specification,
        quantity: item.quantity,
        unit: item.unit,
        area: item.area,
        unit_price: item.unit_price,
        subtotal: item.subtotal,
        image_url: item.image_url,
        item_status: item.item_status,
        remark: item.remark,
        group_name: item.group_name,
      })),
    }
  } finally {
    loading.value = false
  }
})



function handlePrint() {
  window.print()
}
</script>

<style>
/* 不用 scoped，因为 el-dialog teleport 到 body，scoped 样式无法穿透 */
.preview-title {
  text-align: center;
  font-size: 22px;
  margin: 16px 0;
  letter-spacing: 4px;
  padding-bottom: 12px;
  border-bottom: 2px solid #333;
}
.preview-info {
  margin-bottom: 12px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 14px;
}
.preview-table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
  table-layout: auto;
}
.preview-table th,
.preview-table td {
  border: 1px solid #333;
  padding: 6px 8px;
  white-space: nowrap;
  font-size: 12px;
}
.preview-table th {
  background: #f5f5f5;
  font-weight: bold;
  text-align: center;
}
.preview-table .wrap-text {
  white-space: normal;
  word-break: break-all;
  max-width: 8em;
  min-width: 2em;
}
.preview-conclusion {
  margin: 16px 0;
  padding: 12px;
  border: 1px solid #ddd;
  background: #fafafa;
  font-size: 14px;
}
.conclusion-row {
  display: flex;
  padding: 4px 0;
}
.conclusion-row .label {
  font-weight: bold;
  min-width: 80px;
}
.conclusion-row .value.accepted {
  color: #67c23a;
  font-weight: bold;
}
.conclusion-row .value.rejected {
  color: #f56c6c;
  font-weight: bold;
}
.conclusion-row .value.reject {
  color: #f56c6c;
}
.preview-signatures {
  display: flex;
  justify-content: space-between;
  margin-top: 40px;
  padding-top: 20px;
}
.signature-block {
  width: 45%;
}
.signature-label {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 8px;
}
.signature-line {
  border-bottom: 3px solid #333;
  height: 50px;
  margin-bottom: 8px;
}
.signature-date {
  font-size: 14px;
  font-weight: bold;
  color: #666;
}

.group-header-row td {
  background: #f5f7fa !important;
  border-bottom: 2px solid #409eff !important;
  font-weight: 600;
}
.group-total-row td {
  background: #fafafa !important;
  border-top: 1px solid #dcdfe6 !important;
  font-weight: 600;
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
  .preview-signatures {
    page-break-inside: avoid;
  }
}
</style>
