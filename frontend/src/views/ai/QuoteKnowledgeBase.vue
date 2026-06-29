<template>
  <div class="quote-knowledge-base">
    <div class="page-header">
      <h2>报价知识库</h2>
      <el-tag type="success">规则引擎 — 无需 AI Key</el-tag>
    </div>

    <!-- Search form -->
    <el-card class="search-card">
      <el-form :inline="true" @submit.prevent="doSearch">
        <el-form-item label="关键词">
          <el-input
            v-model="searchKeyword"
            placeholder="例如：党建文化墙 PVC 亚克力"
            style="width: 360px"
            clearable
            @keyup.enter="doSearch"
          />
        </el-form-item>
        <el-form-item label="面积范围(㎡)">
          <el-input-number v-model="searchMinArea" :min="0" :step="0.1" placeholder="最小" controls-position="right" style="width: 120px" />
          <span style="margin: 0 8px">—</span>
          <el-input-number v-model="searchMaxArea" :min="0" :step="0.1" placeholder="最大" controls-position="right" style="width: 120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="doSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="description" style="margin-top: 12px">
        <el-input
          v-model="description"
          type="textarea"
          :rows="2"
          placeholder="或者输入完整需求描述：客户要做一面 6米×2米的党建文化墙，材质要求 PVC + 亚克力，含设计和安装"
        />
        <el-button type="default" :loading="loading" style="margin-top: 8px" @click="doSearchByDesc">
          <el-icon><MagicStick /></el-icon> 智能提取关键词搜索
        </el-button>
      </div>
    </el-card>

    <!-- Pricing summary -->
    <el-row v-if="pricingSummary.avg_price > 0" :gutter="16" class="pricing-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">¥{{ formatMoney(pricingSummary.price_range[0]) }} — ¥{{ formatMoney(pricingSummary.price_range[1]) }}</div>
          <div class="stat-label">价格区间</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">¥{{ formatMoney(pricingSummary.avg_price) }}</div>
          <div class="stat-label">平均成交价</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ (pricingSummary.avg_margin * 100).toFixed(1) }}%</div>
          <div class="stat-label">平均毛利率</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card recommended">
          <div class="stat-value">¥{{ formatMoney(pricingSummary.recommended_price) }}</div>
          <div class="stat-label">推荐报价</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Results table -->
    <el-card class="results-card">
      <template #header>
        <span>相似历史报价（{{ results.length }} 条）</span>
      </template>
      <el-table v-loading="loading" :data="results" stripe empty-text="输入关键词搜索历史报价">
        <el-table-column prop="quote_no" label="报价编号" width="160" />
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="面积(㎡)" width="100">
          <template #default="{ row }">{{ row.total_area?.toFixed(1) || '-' }}</template>
        </el-table-column>
        <el-table-column prop="items_summary" label="物料概览" min-width="200" show-overflow-tooltip />
        <el-table-column label="成交金额" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="毛利" width="100">
          <template #default="{ row }">¥{{ formatMoney(row.gross_profit) }}</template>
        </el-table-column>
        <el-table-column label="毛利率" width="90">
          <template #default="{ row }">
            <el-tag :type="row.profit_margin > 0.3 ? 'success' : row.profit_margin > 0.15 ? 'warning' : 'danger'" size="small">
              {{ ((row.profit_margin || 0) * 100).toFixed(1) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="日期" width="100">
          <template #default="{ row }">{{ row.created_at?.slice(0, 10) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/quotes/${row.quote_id}/edit`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, MagicStick } from '@element-plus/icons-vue'
import { findSimilarQuotes, searchByDescription } from '@/api/ai'
import type { SimilarQuoteResult, PricingSummary } from '@/types/api'

const loading = ref(false)
const searchKeyword = ref('')
const searchMinArea = ref<number | undefined>(undefined)
const searchMaxArea = ref<number | undefined>(undefined)
const description = ref('')
const results = ref<SimilarQuoteResult[]>([])
const pricingSummary = ref<PricingSummary>({
  price_range: [],
  avg_price: 0,
  avg_margin: 0,
  recommended_price: 0,
})

function formatMoney(val: number | undefined): string {
  if (val === undefined || val === null) return '0'
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

async function doSearch() {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  loading.value = true
  try {
    const res = await findSimilarQuotes({
      keyword: searchKeyword.value,
      min_area: searchMinArea.value,
      max_area: searchMaxArea.value,
      limit: 10,
    })
    results.value = res.items || []
    pricingSummary.value = res.pricing_summary || pricingSummary.value
  } catch {
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

async function doSearchByDesc() {
  if (!description.value.trim()) {
    ElMessage.warning('请输入需求描述')
    return
  }
  loading.value = true
  try {
    const res = await searchByDescription(description.value, 10)
    results.value = res.items || []
    if (res.pricing_summary) {
      pricingSummary.value = res.pricing_summary
    }
  } catch {
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.quote-knowledge-base { padding: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; color: var(--ad-text); }

.search-card { margin-bottom: 16px; }

.pricing-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-card.recommended { border: 2px solid var(--ad-red, #e63946); }
.stat-value { font-size: 22px; font-weight: 700; color: var(--ad-text); }
.stat-label { font-size: 13px; color: var(--ad-text-muted); margin-top: 4px; }

.results-card { margin-bottom: 16px; }
</style>
