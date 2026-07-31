<template>
  <div class="page" v-loading="loading">
    <h1 style="margin: 0 0 24px; color: var(--ad-text)">经营驾驶舱</h1>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日订单金额</div>
          <div class="stat-value">¥ {{ data.today_order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日收款金额</div>
          <div class="stat-value" style="color: #22c55e">¥ {{ data.today_payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月订单金额</div>
          <div class="stat-value">¥ {{ data.month_order_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月收款金额</div>
          <div class="stat-value" style="color: #22c55e">¥ {{ data.month_payment_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月未收金额</div>
          <div class="stat-value" style="color: #e63946">¥ {{ data.month_unpaid_amount?.toFixed(2) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card task-card">
          <div class="stat-label">待设计任务</div>
          <div class="stat-value">{{ data.pending_design_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card task-card">
          <div class="stat-label">待制作任务</div>
          <div class="stat-value">{{ data.pending_production_count }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card task-card">
          <div class="stat-label">待安装任务</div>
          <div class="stat-value">{{ data.pending_installation_count }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="info-card">
          <template #header><span>逾期订单</span></template>
          <div style="text-align: center; padding: 20px 0">
            <div style="font-size: 36px; font-weight: bold; font-size: 16px; color: #e63946">{{ data.overdue_order_count }}</div>
            <div style="color: var(--ad-text-secondary); margin-top: 4px">逾期订单数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="info-card">
          <template #header><span>客户欠款排行</span></template>
          <div v-if="!data.customer_debt_ranking?.length" style="text-align: center; padding: 20px; color: var(--ad-text-secondary)">暂无欠款</div>
          <div v-for="(item, idx) in data.customer_debt_ranking" :key="item.customer_id" class="debt-row">
            <span class="debt-rank">{{ idx + 1 }}</span>
            <span class="debt-name">{{ item.customer_name }}</span>
            <span class="debt-amount">¥ {{ item.debt_amount?.toFixed(2) }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>

  <!-- 制作看板 -->
  <div class="page" style="margin-top: 24px">
    <h2 style="margin: 0 0 16px; color: var(--ad-text)">项目看板</h2>
    <div class="board" v-loading="boardLoading">
      <div v-for="col in columns" :key="col.key" class="board-column">
        <div class="column-header">
          <span>{{ col.label }}</span>
          <el-tag size="small" type="danger">{{ colCards(col.key).length }}</el-tag>
        </div>
        <div class="column-body">
          <el-card
            v-for="card in colCards(col.key)"
            :key="card.id"
            shadow="hover"
            class="board-card"
            @click="handleCardClick(card, col.key)"
          >
            <div class="card-no">{{ card.order_no }}</div>
            <div class="card-name">{{ card.project_name }}</div>
            <div class="card-meta">
              <span>{{ card.customer_name || '-' }}</span>
              <span>¥{{ card.total_amount?.toFixed(2) }}</span>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getDashboard } from '@/api/payments'
import { getOrders } from '@/api/orders'
import { getDesignTasks, getProductionTasks, getInstallationTasks } from '@/api/tasks'
import { getAcceptances } from '@/api/acceptances'
import type { CustomerDebtItem, OrderListResponse } from '@/types/api'

const loading = ref(false)
const data = reactive({
  today_order_amount: 0, today_payment_amount: 0,
  month_order_amount: 0, month_payment_amount: 0,
  month_unpaid_amount: 0,
  pending_design_count: 0, pending_production_count: 0, pending_installation_count: 0,
  overdue_order_count: 0,
  customer_debt_ranking: [] as CustomerDebtItem[],
})

const boardLoading = ref(false)
const allProjects = ref<OrderListResponse[]>([])

const columns = [
  { key: 'queue', label: '项目队列', statuses: ['pending_confirm', 'confirmed'] },
  { key: 'designing', label: '设计', statuses: ['designing'] },
  { key: 'production', label: '制作', statuses: ['in_production'] },
  { key: 'installation', label: '安装', statuses: ['in_installation'] },
  { key: 'acceptance', label: '验收', statuses: ['pending_acceptance'] },
]

function colCards(key: string) {
  const col = columns.find(c => c.key === key)
  return allProjects.value.filter(t => col ? col.statuses.includes(t.status) : false)
}

async function fetchBoardData() {
  boardLoading.value = true
  try {
    const r = await getOrders({ page_size: 100 })
    allProjects.value = r.items
  } finally { boardLoading.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const d = await getDashboard()
    Object.assign(data, d)
  } finally { loading.value = false }
}

async function handleCardClick(card: OrderListResponse, colKey: string) {
  if (colKey === 'designing') {
    try {
      const res = await getDesignTasks({ order_id: card.id, page_size: 1 })
      if (res.items.length > 0) {
        return window.location.href = '/design-tasks/' + res.items[0].id
      }
    } catch {}
  } else if (colKey === 'production') {
    try {
      const res = await getProductionTasks({ order_id: card.id, page_size: 1 })
      if (res.items.length > 0) {
        return window.location.href = '/production-tasks/' + res.items[0].id
      }
    } catch {}
  } else if (colKey === 'installation') {
    try {
      const res = await getInstallationTasks({ order_id: card.id, page_size: 1 })
      if (res.items.length > 0) {
        return window.location.href = '/installation-tasks/' + res.items[0].id
      }
    } catch {}
  } else if (colKey === 'acceptance') {
    try {
      const res = await getAcceptances({ order_id: card.id, page_size: 1 })
      if (res.items.length > 0) {
        return window.location.href = '/acceptances/' + res.items[0].id
      }
    } catch {}
  }
  window.location.href = '/orders/' + card.id
}

onMounted(() => {
  fetchData()
  fetchBoardData()
})
</script>

<style scoped>
.page { padding: 0; }
.board { display: flex; gap: 12px; overflow-x: auto; min-height: 40vh; }
.board-column { flex: 1; min-width: 200px; background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 6px; display: flex; flex-direction: column; }
.column-header { padding: 12px; font-weight: bold; font-size: 16px; color: var(--ad-text); border-bottom: 1px solid var(--ad-border); display: flex; justify-content: center; gap: 8px; align-items: center; }
.column-body { padding: 8px; flex: 1; overflow-y: auto; }
.board-card { margin-bottom: 8px; cursor: pointer; background: var(--ad-card); border: 1px solid var(--ad-border); }
.board-card:hover { border-color: #e63946; }
.card-no { font-size: 12px; color: #888; }
.card-name { font-weight: bold; font-size: 16px; color: var(--ad-text); margin: 4px 0; }
.card-meta { display: flex; justify-content: center; gap: 8px; align-items: center; margin-top: 8px; font-size: 12px; color: #888; }
.stat-card { background: var(--ad-card); border: 1px solid var(--ad-border); text-align: center; padding: 12px 0; }
.stat-label { font-size: 13px; color: var(--ad-text-secondary); margin-bottom: 8px; }
.stat-value { font-size: 24px; font-weight: bold; font-size: 16px; color: var(--ad-text); }
.task-card .stat-value { font-size: 32px; margin-top: 4px; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.debt-row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--ad-border); }
.debt-rank { width: 28px; height: 28px; background: #e63946; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; font-size: 16px; margin-right: 12px; }
.debt-name { flex: 1; color: var(--ad-text); }
.debt-amount { font-weight: bold; font-size: 16px; color: #e63946; }
</style>
