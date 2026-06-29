<template>
  <div class="anomaly-dashboard">
    <div class="page-header">
      <h2>智能异常提醒</h2>
      <el-tag type="success">规则引擎 — 无需 AI Key</el-tag>
    </div>

    <!-- Summary cards -->
    <el-row :gutter="16" class="summary-row">
      <el-col :span="8">
        <el-card shadow="hover" class="summary-card critical">
          <div class="summary-count">{{ summary.critical }}</div>
          <div class="summary-label">严重异常</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="summary-card warning">
          <div class="summary-count">{{ summary.warning }}</div>
          <div class="summary-label">警告</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="summary-card info">
          <div class="summary-count">{{ summary.info }}</div>
          <div class="summary-label">提示</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Filter bar -->
    <el-card class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="6">
          <el-select v-model="filterSeverity" placeholder="严重程度" clearable style="width: 100%">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="提示" value="info" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterType" placeholder="异常类型" clearable style="width: 100%">
            <el-option label="报价低于成本" value="quote_underpriced" />
            <el-option label="订单逾期" value="order_overdue" />
            <el-option label="安装未收款" value="install_unpaid" />
            <el-option label="欠款超账期" value="customer_credit_exceeded" />
            <el-option label="外协延迟" value="outsource_delayed" />
            <el-option label="库存不足" value="inventory_low" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button type="primary" :loading="loading" @click="fetchData">
            <el-icon><Refresh /></el-icon> 扫描
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- Alert list -->
    <el-card class="list-card">
      <template #header>
        <span>异常列表（{{ filteredAlerts.length }} 条）</span>
      </template>
      <el-table v-loading="loading" :data="filteredAlerts" stripe empty-text="未发现异常">
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="severityTag(row.severity)" size="small">
              {{ severityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="140">
          <template #default="{ row }">
            {{ typeText(row.type) }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="detail" label="详情" min-width="300" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="goToSource(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { scanAnomalies } from '@/api/ai'
import type { AnomalyAlert, AnomalySummary } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const alerts = ref<AnomalyAlert[]>([])
const summary = ref<AnomalySummary>({ critical: 0, warning: 0, info: 0 })
const filterSeverity = ref('')
const filterType = ref('')

const filteredAlerts = computed(() => {
  let list = alerts.value
  if (filterSeverity.value) {
    list = list.filter(a => a.severity === filterSeverity.value)
  }
  if (filterType.value) {
    list = list.filter(a => a.type === filterType.value)
  }
  return list
})

function severityTag(s: string) {
  const map: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[s] || 'info'
}

function severityText(s: string) {
  const map: Record<string, string> = { critical: '严重', warning: '警告', info: '提示' }
  return map[s] || s
}

function typeText(t: string) {
  const map: Record<string, string> = {
    quote_underpriced: '报价低于成本',
    order_overdue: '订单逾期',
    install_unpaid: '安装未收款',
    customer_credit_exceeded: '欠款超账期',
    outsource_delayed: '外协延迟',
    inventory_low: '库存不足',
  }
  return map[t] || t
}

function goToSource(row: AnomalyAlert) {
  const routes: Record<string, string> = {
    quote: `/quotes/${row.object_id}/edit`,
    order: `/orders/${row.object_id}`,
    outsource_task: `/outsource/tasks`,
    inventory_item: `/inventory`,
  }
  const path = routes[row.object_type]
  if (path) {
    router.push(path)
  }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await scanAnomalies()
    alerts.value = res.alerts || []
    summary.value = res.summary || { critical: 0, warning: 0, info: 0 }
  } catch {
    ElMessage.error('获取异常数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.anomaly-dashboard { padding: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; color: var(--ad-text); }

.summary-row { margin-bottom: 16px; }

.summary-card { text-align: center; }
.summary-card.critical { border-top: 3px solid var(--ad-red, #e63946); }
.summary-card.warning { border-top: 3px solid var(--ad-orange, #e6a817); }
.summary-card.info { border-top: 3px solid var(--ad-blue, #409eff); }

.summary-count { font-size: 36px; font-weight: 700; color: var(--ad-text); }
.summary-label { font-size: 14px; color: var(--ad-text-muted); margin-top: 4px; }

.filter-card { margin-bottom: 16px; }
.list-card { margin-bottom: 16px; }
</style>
