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
          <span>客户地址: {{ form.customer_address || '-' }}</span>
        </div>
        <div class="info-row">
          <span>部门/科室: {{ form.department || '-' }}</span>
          <span>联 系 人: {{ form.contact_person || '-' }}</span>
          <span>联系电话: {{ form.customer_phone || '-' }}</span>
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
              <td style="text-align: right; font-weight: 600; background: #fafafa; border-top: 1px solid #dcdfe6; padding: 6px 8px; white-space: nowrap;">¥ {{ row.total.toFixed(2) }}</td>
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
            <td style="text-align: right; font-weight: 600; white-space: nowrap;">¥ {{ itemsTotal.toFixed(2) }}</td>
            <td></td>
            <td></td>
          </tr>
          <tr>
            <td colspan="2" style="text-align: right; border-right: none;">金额（大写）：</td>
            <td colspan="5" style="border-left: none; border-right: none; font-weight: bold;">{{ toChineseAmount(itemsTotal) }}</td>
            <td style="text-align: right; border-left: none; border-right: none; font-weight: bold;">金额（小写）：</td>
            <td style="text-align: right; white-space: nowrap; border-left: none; font-weight: bold;">¥ {{ itemsTotal.toFixed(2) }}</td>
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
          <td colspan="11" style="height: 60px; vertical-align: top; padding-top: 14px;"><strong>备注说明：</strong>{{ form.remark || '' }}</td>
        </tr>
        <tr>
          <td colspan="11" style="padding: 8px 12px;">负责人/联系电话：{{ form.contact_person || '' }} / {{ form.customer_phone || '' }}</td>
        </tr>
        </tbody>
      </table>

      <!-- 签字栏 -->
      <div class="preview-signatures">
        <div class="signature-block">
          <div class="signature-label">甲方：{{ form.customer_name || '客户' }}（盖章）</div>
          <div style="height: 50px;"></div>
          <div class="signature-label">验收签字：</div>
          <div style="height: 50px;"></div>
          <div class="signature-label">联系电话：</div>
          <div style="height: 30px;"></div>
          <div class="signature-date">日期：________年____月____日</div>
        </div>
        <div class="signature-block">
          <div class="signature-label">乙方：{{ companyName || '制作安装方' }}（盖章）</div>
          <div style="height: 50px;"></div>
          <div class="signature-label">签字：</div>
          <div style="height: 50px;"></div>
          <div class="signature-label">联系电话：</div>
          <div style="height: 30px;"></div>
          <div class="signature-date">日期：________年____月____日</div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
      <el-button @click="handleExportImage">导出图片</el-button>
      <el-button @click="handleExportPDF">导出 PDF</el-button>
      <el-button type="primary" @click="handlePrint">打印</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { getAcceptance } from '@/api/acceptances'
import { getSystemSettings } from '@/api/admin'
import { downloadBlob } from '@/utils/download'

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
  department?: string
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
const companyName = ref('')

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
    const [data, settings] = await Promise.all([
      getAcceptance(props.acceptanceId),
      getSystemSettings().catch(() => null),
    ])
    companyName.value = settings?.COMPANY_NAME || ''
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
      department: data.department,
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

async function getCanvas(): Promise<HTMLCanvasElement | null> {
  const el = document.querySelector('.print-area') as HTMLElement | null
  if (!el) return null
  return html2canvas(el, { scale: 2, useCORS: true, backgroundColor: '#ffffff' })
}

async function handleExportImage() {
  const canvas = await getCanvas()
  if (!canvas) return
  canvas.toBlob(blob => {
    if (!blob) return
    downloadBlob(blob, `验收单_${form.value?.acceptance_no || 'export'}.png`)
  }, 'image/png')
}

async function handleExportPDF() {
  const canvas = await getCanvas()
  if (!canvas) return

  const imgData = canvas.toDataURL('image/png')

  // A4 尺寸 (mm)，8mm 边距
  const pdfWidth = 210
  const margin = 8
  const maxWidth = pdfWidth - margin * 2

  // canvas 是 scale:2 渲染的，实际像素 /2 后换算为 mm（96dpi: 1px = 25.4/96 mm）
  const pxToMm = 25.4 / 96
  const imgWmm = (canvas.width / 2) * pxToMm
  const imgHmm = (canvas.height / 2) * pxToMm

  // 按 A4 内容宽度等比缩放
  const ratio = maxWidth / imgWmm
  const finalW = maxWidth
  const finalH = imgHmm * ratio

  const pdf = new jsPDF('portrait', 'mm', 'a4')
  pdf.addImage(imgData, 'PNG', margin, margin, finalW, finalH)
  pdf.save(`验收单_${form.value?.acceptance_no || 'export'}.pdf`)
}

function handlePrint() {
  const printArea = document.querySelector('.print-area')
  if (!printArea) return

  // 创建独立的打印容器（不受 Element Plus teleport 结构影响）
  const container = document.createElement('div')
  container.id = '__print_container__'
  container.innerHTML = printArea.outerHTML
  document.body.appendChild(container)

  window.print()

  // 打印对话框关闭后清理
  setTimeout(() => {
    const el = document.getElementById('__print_container__')
    if (el) el.remove()
  }, 500)
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
  line-height: normal;
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
  @page { size: A4; margin: 8mm; }

  html, body { background: white !important; }

  body > * { display: none !important; }

  #__print_container__ {
    display: block !important;
    position: static !important;
    background: white !important;
    padding: 0 !important;
    margin: 0 auto !important;
    width: 185mm;
    max-width: 185mm;
    box-sizing: border-box;
  }

  #__print_container__ .preview-table {
    table-layout: fixed;
    width: 100%;
  }

  /* 列宽按比例分配（总宽100%，基于原始px比例换算）*/
  #__print_container__ .preview-table thead th:nth-child(1) { width: 3.7%; }
  #__print_container__ .preview-table thead th:nth-child(2) { width: 14%; }
  #__print_container__ .preview-table thead th:nth-child(3) { width: 14%; }
  #__print_container__ .preview-table thead th:nth-child(4) { width: 12%; }
  #__print_container__ .preview-table thead th:nth-child(5) { width: 6.5%; }
  #__print_container__ .preview-table thead th:nth-child(6) { width: 5%; }
  #__print_container__ .preview-table thead th:nth-child(7) { width: 4.5%; }
  #__print_container__ .preview-table thead th:nth-child(8) { width: 9.5%; }
  #__print_container__ .preview-table thead th:nth-child(9) { width: 10.5%; }
  #__print_container__ .preview-table thead th:nth-child(10) { width: 6.5%; }
  #__print_container__ .preview-table thead th:nth-child(11) { width: 14%; }

  #__print_container__ .preview-table th,
  #__print_container__ .preview-table td {
    font-size: 9px;
    padding: 2px 3px;
    box-sizing: border-box;
  }

  #__print_container__ .preview-table td:nth-child(1),
  #__print_container__ .preview-table td:nth-child(5),
  #__print_container__ .preview-table td:nth-child(6),
  #__print_container__ .preview-table td:nth-child(7),
  #__print_container__ .preview-table td:nth-child(8),
  #__print_container__ .preview-table td:nth-child(9),
  #__print_container__ .preview-table td:nth-child(10) {
    white-space: nowrap;
  }

  /* 内容列允许折行 */
  #__print_container__ .preview-table td:nth-child(2),
  #__print_container__ .preview-table td:nth-child(3),
  #__print_container__ .preview-table td:nth-child(4),
  #__print_container__ .preview-table td:nth-child(11) {
    word-break: break-all;
  }

  #__print_container__ .preview-table td:nth-child(2) .wrap-text,
  #__print_container__ .preview-table td:nth-child(3) .wrap-text,
  #__print_container__ .preview-table td:nth-child(4) .wrap-text,
  #__print_container__ .preview-table td:nth-child(11) .wrap-text {
    max-width: none;
  }

    /* 信息行与表格等宽 */
  #__print_container__ .preview-info {
    width: 100%;
    box-sizing: border-box;
  }

  #__print_container__ .preview-signatures {
    page-break-inside: avoid;
    margin-top: 20px;
  }
}
</style>
