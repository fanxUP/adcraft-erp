<template>
  <el-dialog
    :model-value="visible"
    title="验收单预览"
    width="800px"
    :close-on-click-modal="true"
    @close="$emit('close')"
  >
    <div v-if="loading" v-loading="true" style="height: 200px" />
    <div v-else-if="form" class="print-area">
      <!-- 表头 -->
      <div class="preview-header">
        <div class="company-logo">LOGO</div>
        <div class="company-info">
          <div class="company-name">广告制作公司</div>
          <div class="company-detail">地址: __________  电话: __________</div>
        </div>
      </div>

      <!-- 标题 -->
      <h2 class="preview-title">验 收 单</h2>

      <!-- 基本信息 -->
      <div class="preview-meta">
        <div class="meta-row">
          <span>验收单号: {{ form.acceptance_no }}</span>
          <span>日　　期: {{ form.created_at?.slice(0, 10) || '-' }}</span>
        </div>
        <div class="meta-row">
          <span>状　　态: {{ statusLabel(form.status) }}</span>
          <span>验收日期: {{ form.accepted_at?.slice(0, 10) || '-' }}</span>
        </div>
      </div>

      <div class="preview-parties">
        <div class="party-row">
          <span>订单编号: {{ form.order_no || '-' }}</span>
          <span>客户名称: {{ form.customer_name || '-' }}</span>
        </div>
        <div class="party-row">
          <span>项目名称: {{ form.project_name || '-' }}</span>
          <span>客户验收人: {{ form.accepted_by || '-' }}</span>
        </div>
        <div class="party-row">
          <span>我方验收人: {{ form.our_acceptor_name || '-' }}</span>
          <span></span>
        </div>
      </div>

      <!-- 验收明细表格 -->
      <table class="preview-table">
        <thead>
          <tr>
            <th style="width: 50px">序号</th>
            <th><div class="wrap-text">项目名称</div></th>
            <th><div class="wrap-text">规格说明</div></th>
            <th>数量</th>
            <th>单位</th>
            <th>验收状态</th>
            <th><div class="wrap-text">备注</div></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in form.items" :key="item.id || idx">
            <td style="text-align: center">{{ idx + 1 }}</td>
            <td><div class="wrap-text">{{ item.item_name }}</div></td>
            <td><div class="wrap-text">{{ item.specification || '-' }}</div></td>
            <td style="text-align: right">{{ item.quantity }}</td>
            <td style="text-align: center">{{ item.unit || '-' }}</td>
            <td style="text-align: center">{{ itemStatusLabel(item.item_status) }}</td>
            <td><div class="wrap-text">{{ item.remark || '' }}</div></td>
          </tr>
          <tr v-if="!form.items || form.items.length === 0">
            <td colspan="7" style="text-align: center; color: #999;">暂无验收明细</td>
          </tr>
        </tbody>
      </table>

      <!-- 验收结论 -->
      <div class="preview-conclusion">
        <div class="conclusion-row">
          <span class="label">验收结论:</span>
          <span class="value" :class="form.status">
            {{ statusLabel(form.status) }}
          </span>
        </div>
        <div v-if="form.remark" class="conclusion-row">
          <span class="label">备　　注:</span>
          <span class="value">{{ form.remark }}</span>
        </div>
        <div v-if="form.reject_reason" class="conclusion-row">
          <span class="label">驳回原因:</span>
          <span class="value reject">{{ form.reject_reason }}</span>
        </div>
      </div>

      <!-- 签字栏 -->
      <div class="preview-signatures">
        <div class="signature-block">
          <div class="signature-label">客户签字（盖章）:</div>
          <div class="signature-line"></div>
          <div class="signature-date">日期: ________年____月____日</div>
        </div>
        <div class="signature-block">
          <div class="signature-label">供方签字（盖章）:</div>
          <div class="signature-line"></div>
          <div class="signature-date">日期: ________年____月____日</div>
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
import { ref, watch } from 'vue'
import { getAcceptance } from '@/api/acceptances'

interface AcceptancePrintItem {
  id?: string
  item_name: string
  specification?: string
  quantity: number
  unit?: string
  item_status: string
  remark?: string
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
  project_name?: string
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
      project_name: data.project_name,
      items: (data.items || []).map(item => ({
        id: item.id,
        item_name: item.item_name,
        specification: item.specification,
        quantity: item.quantity,
        unit: item.unit,
        item_status: item.item_status,
        remark: item.remark,
      })),
    }
  } finally {
    loading.value = false
  }
})

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: '草稿',
    pending: '待验收',
    accepted: '已验收',
    rejected: '已驳回',
  }
  return map[s] || s
}

function itemStatusLabel(s: string) {
  const map: Record<string, string> = {
    pending: '待验收',
    accepted: '合格',
    rejected: '不合格',
    conditional: '有条件通过',
  }
  return map[s] || s
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
  font-size: 13px;
  table-layout: auto;
}
.preview-table th,
.preview-table td {
  border: 1px solid #333;
  padding: 8px 10px;
  white-space: nowrap;
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
  border-bottom: 1px solid #333;
  height: 50px;
  margin-bottom: 8px;
}
.signature-date {
  font-size: 13px;
  color: #666;
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
