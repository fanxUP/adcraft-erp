<template>
  <div class="page">
    <div class="page-header">
      <h2>制作看板</h2>
    </div>

    <div class="board" v-loading="loading">
      <div v-for="col in columns" :key="col.key" class="board-column">
        <div class="column-header">
          <span>{{ col.label }}</span>
          <el-tag size="small" type="info">{{ colCards(col.key).length }}</el-tag>
        </div>
        <div class="column-body">
          <el-card
            v-for="card in colCards(col.key)"
            :key="card.id"
            shadow="hover"
            class="board-card"
            @click="$router.push(`/production-tasks/${card.id}`)"
          >
            <div class="card-no">{{ card.production_no }}</div>
            <div class="card-name">{{ card.project_name }}</div>
            <div class="card-meta">
              <span>数量: {{ card.quantity }}</span>
              <el-tag :type="prodStatusColor(card.status)" size="small">{{ prodStatusLabel(card.status) }}</el-tag>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getProductionTasks } from '@/api/tasks'
import type { ProductionTaskResponse } from '@/types/api'

const loading = ref(false)
const allTasks = ref<ProductionTaskResponse[]>([])

const columns = [
  { key: 'pending', label: '待制作' },
  { key: 'queued', label: '排队中' },
  { key: 'in_progress', label: '制作中' },
  { key: 'qc_check', label: '待质检' },
  { key: 'rework', label: '返工' },
  { key: 'completed', label: '已完成' },
]

function prodStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成' }
  return map[s] || s
}
function prodStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

function colCards(key: string) { return allTasks.value.filter(t => t.status === key) }

async function fetchData() {
  loading.value = true
  try {
    const data = await getProductionTasks({ page_size: 200 })
    allTasks.value = data.items
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.board { display: flex; gap: 12px; overflow-x: auto; min-height: 60vh; }
.board-column { flex: 1; min-width: 200px; background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 6px; display: flex; flex-direction: column; }
.column-header { padding: 12px; font-weight: bold; color: var(--ad-text); border-bottom: 1px solid var(--ad-border); display: flex; justify-content: space-between; align-items: center; }
.column-body { padding: 8px; flex: 1; overflow-y: auto; }
.board-card { margin-bottom: 8px; cursor: pointer; background: #252540; border: 1px solid var(--ad-border); }
.board-card:hover { border-color: #e63946; }
.card-no { font-size: 12px; color: #888; }
.card-name { font-weight: bold; color: var(--ad-text); margin: 4px 0; }
.card-meta { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 12px; color: #888; }
</style>
