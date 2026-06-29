<template>
  <div class="ai-quote-assistant">
    <div class="page-header">
      <h2>AI 报价助手</h2>
      <el-tag type="success">规则引擎 — 无需 AI Key</el-tag>
    </div>

    <el-row :gutter="20">
      <!-- Input panel -->
      <el-col :span="8">
        <el-card>
          <template #header>需求描述</template>
          <el-form>
            <el-form-item>
              <el-input
                v-model="description"
                type="textarea"
                :rows="8"
                placeholder="请描述客户需求，例如：

  客户要做一面 6米×2米的党建文化墙
  材质要求 PVC + 亚克力面板
  需要含设计、制作和安装
  安装在室内墙面"
              />
            </el-form-item>
            <el-form-item label="关联客户">
              <el-select v-model="customerId" placeholder="可选" clearable filterable style="width: 100%">
                <el-option
                  v-for="c in customers"
                  :key="c.id"
                  :label="c.name"
                  :value="c.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" style="width: 100%" @click="generateDraft">
                <el-icon><MagicStick /></el-icon> 生成报价草稿
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Similar quotes -->
        <el-card v-if="draft && draft.similar_quotes?.length" style="margin-top: 16px">
          <template #header>相似历史报价</template>
          <div v-for="sq in draft.similar_quotes" :key="sq.quote_id" class="similar-item">
            <div class="sim-no">{{ sq.quote_no }}</div>
            <div class="sim-name">{{ sq.project_name }}</div>
            <div class="sim-amount">¥{{ formatMoney(sq.total_amount) }}</div>
          </div>
        </el-card>
      </el-col>

      <!-- Result panel -->
      <el-col :span="16">
        <el-card v-loading="loading">
          <template #header>
            <span>报价草稿</span>
            <el-tag v-if="draft" size="small" style="margin-left: 12px">
              {{ draft.mode === 'ai_enhanced' ? 'AI 增强' : '规则引擎' }}
            </el-tag>
          </template>

          <div v-if="!draft" class="empty-state">
            <el-icon :size="64"><MagicStick /></el-icon>
            <p>输入需求描述，AI 将自动生成报价草稿</p>
          </div>

          <div v-else>
            <!-- AI analysis -->
            <el-alert v-if="draft.ai_analysis" :title="draft.ai_analysis" type="info" :closable="false" style="margin-bottom: 16px" />

            <!-- Risk notes -->
            <el-alert v-for="(risk, i) in draft.risk_notes" :key="i" :title="risk" type="warning" :closable="false" style="margin-bottom: 8px" />

            <!-- Project name -->
            <div class="project-name">
              <span class="label">项目名称：</span>
              <el-input v-model="draft.project_name" style="width: 300px" />
            </div>

            <!-- Items table -->
            <el-table :data="draft.items" stripe style="margin-top: 16px">
              <el-table-column prop="item_name" label="项目" min-width="160" />
              <el-table-column label="规格" width="140">
                <template #default="{ row }">
                  <template v-if="row.length || row.width">
                    {{ row.length || '?' }} × {{ row.width || '?' }}
                    <span v-if="row.height"> × {{ row.height }}</span>
                  </template>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="quantity" label="数量" width="70" />
              <el-table-column label="单价(¥)" width="110">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.unit_price"
                    :min="0"
                    :step="10"
                    size="small"
                    controls-position="right"
                    style="width: 100px"
                  />
                </template>
              </el-table-column>
              <el-table-column label="小计(¥)" width="110">
                <template #default="{ row }">
                  {{ formatMoney((row.length || 0) * (row.width || 0) * (row.quantity || 1) * (row.unit_price || 0)) }}
                </template>
              </el-table-column>
              <el-table-column label="设计费" width="100">
                <template #default="{ row }">
                  <el-input-number v-model="row.design_fee" :min="0" :step="50" size="small" style="width: 90px" />
                </template>
              </el-table-column>
              <el-table-column label="安装费" width="100">
                <template #default="{ row }">
                  <el-input-number v-model="row.installation_fee" :min="0" :step="50" size="small" style="width: 90px" />
                </template>
              </el-table-column>
            </el-table>

            <!-- Total estimate -->
            <div class="total-bar" style="margin-top: 16px; text-align: right; font-size: 18px; font-weight: 700;">
              预估总价：<span style="color: var(--ad-red)">¥{{ formatMoney(computeTotal) }}</span>
            </div>

            <!-- Actions -->
            <div class="actions" style="margin-top: 16px; text-align: right;">
              <el-button @click="draft = null">重新生成</el-button>
              <el-button type="primary" :loading="saving" @click="saveQuote">保存为正式报价</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { assistQuote, saveAssistedQuote } from '@/api/ai'
import { getCustomers } from '@/api/customers'
import type { AIQuoteAssistResponse, CustomerResponse } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const description = ref('')
const customerId = ref('')
const customers = ref<CustomerResponse[]>([])
const draft = ref<AIQuoteAssistResponse | null>(null)

const computeTotal = computed(() => {
  if (!draft.value) return 0
  return draft.value.items.reduce((sum, item) => {
    const area = (item.length || 0) * (item.width || 0) * (item.quantity || 1)
    const subtotal = area * (item.unit_price || 0)
    return sum + subtotal + (item.design_fee || 0) + (item.installation_fee || 0) + (item.process_fee || 0) + (item.transport_fee || 0) + (item.other_fee || 0)
  }, 0)
})

function formatMoney(val: number | undefined): string {
  if (val === undefined || val === null) return '0'
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

async function generateDraft() {
  if (!description.value.trim()) {
    ElMessage.warning('请输入需求描述')
    return
  }
  loading.value = true
  try {
    draft.value = await assistQuote({
      description: description.value,
      customer_id: customerId.value || undefined,
    })
  } catch {
    ElMessage.error('生成报价草稿失败')
  } finally {
    loading.value = false
  }
}

async function saveQuote() {
  if (!draft.value) return
  saving.value = true
  try {
    const quote = await saveAssistedQuote({
      project_name: draft.value.project_name,
      customer_id: customerId.value || undefined,
      items: draft.value.items,
      ai_analysis: draft.value.ai_analysis,
    })
    ElMessage.success('报价已保存为草稿')
    router.push(`/quotes/${(quote as Record<string, unknown>).id}/edit`)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const res = await getCustomers({ page: 1, page_size: 100 })
    customers.value = res.items || []
  } catch { /* ignore */ }
})
</script>

<style scoped>
.ai-quote-assistant { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.empty-state { text-align: center; padding: 80px 20px; color: var(--ad-text-muted); }
.project-name { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.project-name .label { font-weight: 600; white-space: nowrap; }
.similar-item { padding: 8px 0; border-bottom: 1px solid var(--ad-border); }
.similar-item:last-child { border-bottom: none; }
.sim-no { font-size: 12px; color: var(--ad-text-muted); }
.sim-name { font-size: 13px; color: var(--ad-text); }
.sim-amount { font-size: 14px; font-weight: 700; color: var(--ad-red); }
</style>
