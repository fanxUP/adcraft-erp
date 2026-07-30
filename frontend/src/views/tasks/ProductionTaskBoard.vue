<template>
  <div class="page">
    <div class="page-header">
      <h2>项目看板</h2>
    </div>

    <div class="board" v-loading="loading">
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
import { ref, onMounted } from 'vue'
import { getOrders } from '@/api/orders'
import { getDesignTasks, getProductionTasks, getInstallationTasks } from '@/api/tasks'
import { getAcceptances } from '@/api/acceptances'
import type { OrderListResponse } from '@/types/api'

const loading = ref(false)
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

async function fetchData() {
  loading.value = true
  try {
    const data = await getOrders({ page_size: 100 })
    allProjects.value = data.items
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

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.board { display: flex; gap: 12px; overflow-x: auto; min-height: 60vh; }
.board-column { flex: 1; min-width: 200px; background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 6px; display: flex; flex-direction: column; }
.column-header { padding: 12px; font-weight: bold; font-size: 16px; color: var(--ad-text); border-bottom: 1px solid var(--ad-border); display: flex; justify-content: center; gap: 8px; align-items: center; }
.column-body { padding: 8px; flex: 1; overflow-y: auto; }
.board-card { margin-bottom: 8px; cursor: pointer; background: var(--ad-card); border: 1px solid var(--ad-border); }
.board-card:hover { border-color: #e63946; }
.card-no { font-size: 12px; color: #888; }
.card-name { font-weight: bold; font-size: 16px; color: var(--ad-text); margin: 4px 0; }
.card-meta { display: flex; justify-content: center; gap: 8px; align-items: center; margin-top: 8px; font-size: 12px; color: #888; }
</style>
