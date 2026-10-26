<template>
  <div class="page" v-loading="loading">
    <div class="history-header"><h2>历史报价档案</h2><el-button @click="router.push('/orders')">返回订单管理</el-button></div>
    <el-alert type="info" :closable="false" title="历史记录仅供查询；新业务请直接创建订单。已有来源订单的记录不会重复创建。" style="margin-bottom: 18px" />
    <template v-if="selected">
      <el-descriptions border :column="2"><el-descriptions-item label="历史编号">{{ selected.quote_no || selected.doc_no }}</el-descriptions-item><el-descriptions-item label="项目">{{ selected.project_name }}</el-descriptions-item><el-descriptions-item label="客户">{{ selected.customer_name }}</el-descriptions-item><el-descriptions-item label="金额">¥{{ Number(selected.total_amount || 0).toFixed(2) }}</el-descriptions-item></el-descriptions>
      <el-table :data="selected.items || selected.latest_version?.lines || []" border style="margin-top: 16px"><el-table-column prop="item_name" label="项目内容" min-width="220" /><el-table-column prop="material_process" label="产品/材质/工艺" min-width="180" /><el-table-column prop="quantity" label="数量" width="100" /><el-table-column prop="unit_price" label="单价" width="120" /></el-table>
      <el-button v-if="auth.can('order:create') && selected.status !== 'cancelled'" type="primary" style="margin-top: 18px" @click="continueOrder(selected.id)">继续处理为订单 / 打开已有订单</el-button>
    </template>
    <template v-else>
      <el-table :data="rows" border><el-table-column prop="quote_no" label="历史编号" min-width="180" /><el-table-column prop="project_name" label="项目" min-width="220" /><el-table-column prop="customer_name" label="客户" min-width="180" /><el-table-column prop="status" label="历史状态" width="140" /><el-table-column label="操作" width="120"><template #default="{ row }"><el-button text type="primary" @click="router.push(`${basePath}/${row.id}/edit`)">查看档案</el-button></template></el-table-column></el-table>
      <el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="total, prev, pager, next" style="margin-top: 18px" @current-change="load" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { get, post } from '@/api/index'
import { useAuthStore } from '@/stores/auth'
interface HistoryRow { id: string; quote_no?: string; doc_no?: string; project_name: string; customer_name?: string; status: string; total_amount?: number; items?: unknown[]; latest_version?: { lines?: unknown[] } }
const route = useRoute(), router = useRouter(), auth = useAuthStore()
const page = ref(1), total = ref(0), rows = ref<HistoryRow[]>([]), selected = ref<HistoryRow | null>(null), loading = ref(false)
const isCdr = computed(() => route.path.startsWith('/cdr/'))
const basePath = computed(() => isCdr.value ? '/cdr/quotes' : '/quotes')
async function load() {
  loading.value = true
  try {
    if (route.params.id) selected.value = await get<HistoryRow>(`${basePath.value}/${route.params.id}`)
    else { selected.value = null; const data = await get<{ items: HistoryRow[]; total: number }>(isCdr.value ? '/cdr/quotes' : '/quotes/', { params: { page: page.value, page_size: 20 } }); rows.value = data.items; total.value = data.total }
  } finally { loading.value = false }
}
async function continueOrder(id: string) {
  try {
    await ElMessageBox.confirm('将历史明细继续处理为待确认订单；已有订单会直接打开，历史来源保留。有关联归属冲突时会提示核对。', '继续处理', { type: 'info' })
    const order = await post<{ id: string }>(`/orders/from-history/${id}`)
    await router.push(`/orders/${order.id}`)
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '处理失败') }
}
watch(() => route.fullPath, load, { immediate: true })
</script>

<style scoped>.history-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }</style>
