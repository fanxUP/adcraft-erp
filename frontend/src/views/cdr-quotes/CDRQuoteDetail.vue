<template>
  <div class="page">
    <div class="page-header">
      <h2>报价详情 #{{ quote?.quote_no || '' }}</h2>
      <div>
        <el-button @click="$router.push('/cdr/quotes')">返回列表</el-button>
        <el-button type="primary" @click="handleEdit">编辑</el-button>
        <el-button :type="'warning'" @click="handleRequestApproval" v-if="version?.status === 'draft'">提交审批</el-button>
        <el-button type="danger" @click="handleConvertToOrder" v-if="canConvert">转订单</el-button>
      </div>
    </div>

    <!-- 基本信息 -->
    <el-card shadow="never" class="section-card">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="报价单号">{{ quote?.quote_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ quote?.customer_name || quote?.customer?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(version?.status)">{{ statusLabel(version?.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="项目">{{ quote?.project_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="税率">{{ (quote?.tax_rate || 0) * 100 }}%</el-descriptions-item>
        <el-descriptions-item label="版本">{{ version?.version_no || 1 }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 报价明细 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <template #header><span>报价明细</span></template>
      <el-table :data="version?.lines || []" stripe>
        <el-table-column label="#" type="index" width="50" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="width_mm" label="宽(mm)" width="80" />
        <el-table-column prop="height_mm" label="高(mm)" width="80" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="unit_price" label="单价" width="100">
          <template #default="{ row }">¥{{ Number(row.unit_price || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120">
          <template #default="{ row }">¥{{ Number(row.amount || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="80">
          <template #default="{ row }">
            <el-tag :type="row.source === 'manual' ? 'warning' : 'info'" size="small">
              {{ row.source === 'manual' ? '手工' : '自动' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 汇总 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px">
      <el-row :gutter="20">
        <el-col :span="6"><div class="summary-item"><span class="label">小计</span><span class="value">¥{{ Number(version?.subtotal_amount || 0).toFixed(2) }}</span></div></el-col>
        <el-col :span="6"><div class="summary-item"><span class="label">预估成本</span><span class="value cost">¥{{ Number(version?.estimated_cost || 0).toFixed(2) }}</span></div></el-col>
        <el-col :span="6"><div class="summary-item"><span class="label">预估毛利</span><span class="value" :class="profitClass">{{ Number(version?.estimated_profit || 0).toFixed(2) }}</span></div></el-col>
        <el-col :span="6"><div class="summary-item highlight"><span class="label">合计</span><span class="value">¥{{ Number(version?.total_amount || 0).toFixed(2) }}</span></div></el-col>
      </el-row>
    </el-card>

    <!-- 审批记录 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px" v-if="approvals.length">
      <template #header><span>审批记录</span></template>
      <el-table :data="approvals" stripe>
        <el-table-column prop="approval_type" label="审批类型" width="140">
          <template #default="{ row }">{{ approvalTypeLabel(row.approval_type) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'">
              {{ { pending: '待审批', approved: '已批准', rejected: '已驳回' }[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="200" />
        <el-table-column prop="decision_comment" label="审批意见" min-width="200" />
        <el-table-column prop="created_at" label="申请时间" width="170" />
      </el-table>
    </el-card>

    <!-- 版本历史 -->
    <el-card shadow="never" class="section-card" style="margin-top: 16px" v-if="versions.length > 1">
      <template #header><span>版本历史</span></template>
      <el-timeline>
        <el-timeline-item v-for="v in versions" :key="v.id" :timestamp="v.created_at">
          <p>版本 {{ v.version_no }} — ¥{{ Number(v.total_amount || 0).toFixed(2) }}</p>
          <p v-if="v.notes" class="trace-detail">{{ v.notes }}</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { getCDRQuote, getLatestVersion, listVersions, listAuditLogs, requestApproval, convertToOrder } from '@/api/cdrQuote'

const route = useRoute()
const router = useRouter()
const quote = ref<any>(null)
const version = ref<any>(null)
const versions = ref<any[]>([])
const approvals = ref<any[]>([])

function statusType(s: string): string {
  return { draft: 'info', review: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info'
}
function statusLabel(s: string): string {
  return { draft: '草稿', review: '复核中', approved: '已批准', rejected: '已驳回' }[s] || s
}
function approvalTypeLabel(t: string): string {
  return { low_margin: '低毛利', over_discount: '超折扣', price_override: '手工改价', high_value: '高金额' }[t] || t
}

const canConvert = computed(() => {
  return version.value?.status && !['rejected', 'converted'].includes(version.value.status)
})

const profitClass = computed(() => {
  const p = Number(version.value?.estimated_profit || 0)
  return p >= 0 ? 'profit-positive' : 'profit-negative'
})

async function fetchData() {
  const quoteId = route.params.id as string
  try {
    quote.value = await getCDRQuote(quoteId)
    version.value = await getLatestVersion(quoteId)
    versions.value = await listVersions(quoteId)
    approvals.value = await api.get(`/cdr/quotes/${quoteId}/approvals`).catch(() => [])
  } catch { /* ignore */ }
}

function handleEdit() {
  router.push(`/cdr/quotes/${route.params.id}/edit`)
}

async function handleRequestApproval() {
  try {
    await ElMessageBox.prompt('请输入审批原因', '提交审批', { inputType: 'textarea' })
    const { value: reason } = await ElMessageBox.prompt('请输入审批原因', '提交审批', {
      inputType: 'textarea', inputPlaceholder: '如：客户急需、超折扣等',
    })
    await requestApproval(route.params.id as string, {
      approval_type: 'price_override',
      reason: reason || '',
    })
    ElMessage.success('已提交审批')
    await fetchData()
  } catch { /* cancelled */ }
}

async function handleConvertToOrder() {
  try {
    await ElMessageBox.confirm(
      '确认将当前报价转为销售订单？转换后报价状态变为"已转换"，并创建新订单。',
      '转订单', { type: 'warning', confirmButtonText: '确认转订单', cancelButtonText: '取消' },
    )
    const order = await convertToOrder(route.params.id as string)
    ElMessage.success(`订单 ${order.doc_no} 创建成功`)
    router.push(`/orders/${order.id}`)
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e?.message || '转订单失败')
    }
  }
}

onMounted(fetchData)
</script>

<style scoped>
.section-card { margin-bottom: 0; }
.summary-item { text-align: center; padding: 12px; }
.summary-item .label { display: block; font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 4px; }
.summary-item .value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.summary-item .value.cost { color: var(--el-color-warning); }
.summary-item .value.profit-positive { color: var(--el-color-success); }
.summary-item .value.profit-negative { color: var(--el-color-danger); }
.summary-item.highlight .value { color: var(--ad-red); }
.trace-detail { font-size: 12px; color: var(--ad-text-secondary); }
</style>
