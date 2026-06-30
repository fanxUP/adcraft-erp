<template>
  <div class="business-narrative-report">
    <div class="page-header">
      <h2>智能经营报告</h2>
      <el-tag type="success">规则引擎 — 无需 AI Key</el-tag>
    </div>

    <!-- Period selector -->
    <el-card class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="4">
          <el-radio-group v-model="period" @change="fetchReport">
            <el-radio-button value="monthly">月报</el-radio-button>
            <el-radio-button value="weekly">周报</el-radio-button>
          </el-radio-group>
        </el-col>
        <el-col :span="4">
          <el-input-number v-model="year" :min="2020" :max="2030" @change="fetchReport" />
        </el-col>
        <el-col :span="4" v-if="period === 'monthly'">
          <el-select v-model="month" @change="fetchReport">
            <el-option v-for="m in 12" :key="m" :label="`${m}月`" :value="m" />
          </el-select>
        </el-col>
        <el-col :span="4" v-if="period === 'weekly'">
          <el-input-number v-model="week" :min="1" :max="53" @change="fetchReport" placeholder="周数" />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" :loading="loading" @click="fetchReport">
            <el-icon><Refresh /></el-icon> 生成报告
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- Stats summary -->
    <el-row v-if="report" :gutter="16" class="stats-row">
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ report.stats.order_count }}</div>
          <div class="stat-label">订单数</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">¥{{ formatMoney(report.stats.order_amount) }}</div>
          <div class="stat-label">订单金额</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">¥{{ formatMoney(report.stats.payment_amount) }}</div>
          <div class="stat-label">收款金额</div>
        </el-card>
      </el-col>
      <el-col v-if="report.stats.unpaid_amount !== undefined" :span="4">
        <el-card shadow="hover" class="stat-card unpaid">
          <div class="stat-value">¥{{ formatMoney(report.stats.unpaid_amount) }}</div>
          <div class="stat-label">未收金额</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ report.stats.overdue_count }}</div>
          <div class="stat-label">逾期订单</div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ ((report.stats.collection_rate || 0) * 100).toFixed(0) }}%</div>
          <div class="stat-label">收款率</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Narrative -->
    <el-card v-if="report" class="narrative-card">
      <template #header>
        <span>
          {{ period === 'monthly' ? `${year}年${month}月` : `第${week}周` }} 经营报告
          <el-tag v-if="report.mode === 'ai_enhanced'" size="small" type="success" style="margin-left: 8px">AI 增强</el-tag>
        </span>
      </template>
      <div class="narrative-content" v-html="renderedNarrative" />
    </el-card>

    <!-- Suggestions -->
    <el-card v-if="report?.suggestions?.length" class="suggestions-card">
      <template #header>改进建议</template>
      <ul class="suggestions-list">
        <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
      </ul>
    </el-card>

    <div v-if="!report && !loading" class="empty-state">
      <el-icon :size="64"><TrendCharts /></el-icon>
      <p>选择报告周期，点击"生成报告"</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, TrendCharts } from '@element-plus/icons-vue'
import { getBusinessNarrative } from '@/api/ai'
import type { BusinessNarrativeResponse } from '@/types/api'

const loading = ref(false)
const period = ref('monthly')
const year = ref(new Date().getFullYear())
const month = ref(new Date().getMonth() + 1)
const week = ref(0)
const report = ref<BusinessNarrativeResponse | null>(null)

const renderedNarrative = computed(() => {
  if (!report.value?.narrative) return ''
  return report.value.narrative
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
})

function formatMoney(val: number | undefined | null): string {
  if (val == null) return '0'
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

async function fetchReport() {
  loading.value = true
  try {
    report.value = await getBusinessNarrative({
      period: period.value,
      year: year.value,
      month: period.value === 'monthly' ? month.value : undefined,
      week: period.value === 'weekly' ? week.value || undefined : undefined,
    })
  } catch {
    ElMessage.error('获取报告失败')
    report.value = null
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.business-narrative-report { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.filter-card { margin-bottom: 16px; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-card.unpaid { border-top: 3px solid var(--ad-orange, #e6a817); }
.stat-value { font-size: 24px; font-weight: 700; color: var(--ad-text); }
.stat-label { font-size: 13px; color: var(--ad-text-muted); margin-top: 4px; }
.narrative-card { margin-bottom: 16px; }
.narrative-content { line-height: 1.8; color: var(--ad-text); }
.suggestions-card { margin-bottom: 16px; }
.suggestions-list { margin: 0; padding-left: 20px; color: var(--ad-text); }
.suggestions-list li { margin-bottom: 8px; }
.empty-state { text-align: center; padding: 80px 20px; color: var(--ad-text-muted); }
</style>
