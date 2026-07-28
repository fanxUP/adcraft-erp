<template>
  <div class="provider-list">
    <div class="page-header">
      <h2>AI 模型中心</h2>
      <div class="header-actions">
        <el-input
          v-model="searchText"
          placeholder="搜索供应商..."
          clearable
          style="width: 240px"
          @input="onSearch"
        />
        <el-button type="primary" @click="showCreate = true">
          <el-icon><Plus /></el-icon>新增供应商
        </el-button>
      </div>
    </div>

    <!-- Stats bar -->
    <el-row :gutter="16" class="stats-bar">
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-item">
            <div class="stat-value">{{ providers.length }}</div>
            <div class="stat-label">供应商总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-item">
            <div class="stat-value success">{{ enabledCount }}</div>
            <div class="stat-label">已启用</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-item">
            <div class="stat-value warning">{{ degradedCount }}</div>
            <div class="stat-label">异常</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-item">
            <div class="stat-value">{{ totalModels }}</div>
            <div class="stat-label">模型总数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Provider cards -->
    <div v-loading="loading" class="card-grid">
      <el-empty v-if="!loading && providers.length === 0" description="暂无供应商，点击右上角新增" />

      <el-card
        v-for="p in filteredProviders"
        :key="p.id"
        shadow="hover"
        class="provider-card"
        :class="{ 'card-disabled': !p.enabled }"
      >
        <div class="card-header">
          <div class="card-title-row">
            <div class="provider-icon" :class="p.enabled ? 'icon-enabled' : 'icon-disabled'">
              <el-icon :size="24"><Connection /></el-icon>
            </div>
            <div>
              <div class="provider-name">{{ p.provider_name }}</div>
              <div class="provider-code">{{ p.provider_code }}</div>
            </div>
          </div>
          <div class="card-status">
            <el-tag
              :type="healthTagType(p.health_status)"
              size="small"
              effect="plain"
            >
              {{ healthLabel(p.health_status) }}
            </el-tag>
          </div>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">协议</span>
            <span class="value">{{ protocolLabel(p.protocol) }}</span>
          </div>
          <div class="info-row">
            <span class="label">地址</span>
            <span class="value url">{{ p.base_url || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="label">模型</span>
            <span class="value">{{ p.model_count }} 个</span>
          </div>
          <div class="info-row">
            <span class="label">API Key</span>
            <span class="value">{{ p.has_api_key ? (p.api_key_display || '已配置') : '未配置' }}</span>
          </div>
          <div class="info-row">
            <span class="label">优先级</span>
            <span class="value">{{ p.priority }}</span>
          </div>
        </div>

        <div class="card-footer">
          <el-switch
            :model-value="p.enabled"
            size="small"
            @change="(v: any) => toggleProvider(p.id, Boolean(v))"
          />
          <span class="enable-label">{{ p.enabled ? '已启用' : '已禁用' }}</span>

          <div class="card-actions">
            <el-button text size="small" @click="editProvider(p)">编辑</el-button>
            <el-button text size="small" @click="manageModels(p)">模型</el-button>
            <el-button text size="small" @click="testConnection(p)">测试</el-button>
            <el-popconfirm title="确认删除该供应商？" @confirm="removeProvider(p.id)">
              <template #reference>
                <el-button text size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Create/Edit dialog -->
    <ProviderForm
      v-if="showCreate || editingProvider"
      :provider="editingProvider"
      @close="closeForm"
      @saved="onSaved"
    />

    <!-- Models dialog -->
    <ModelList
      v-if="showModels"
      :provider="selectedProvider!"
      @close="showModels = false"
    />

    <!-- Test result dialog -->
    <el-dialog v-model="showTestResult" title="测试结果" width="480px">
      <div v-if="testResult" class="test-result">
        <div class="test-status">
          <el-icon v-if="testResult.success" color="#67c23a" :size="48"><SuccessFilled /></el-icon>
          <el-icon v-else color="#f56c6c" :size="48"><WarningFilled /></el-icon>
          <div :class="testResult.success ? 'success-text' : 'fail-text'">
            {{ testResult.success ? '连接成功' : '连接失败' }}
          </div>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="状态码">{{ testResult.status_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="延迟">{{ testResult.latency_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="输入 Token">{{ testResult.input_tokens ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="输出 Token">{{ testResult.output_tokens ?? '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="testResult.output_text" class="test-output">
          <div class="label">模型回复：</div>
          <pre>{{ testResult.output_text }}</pre>
        </div>
        <div v-if="testResult.error_message" class="test-error">
          <div class="label">错误信息：</div>
          <pre>{{ testResult.error_message }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Connection, SuccessFilled, WarningFilled } from '@element-plus/icons-vue'
import ProviderForm from './ProviderForm.vue'
import ModelList from './ModelList.vue'
import {
  getProviders,
  enableProvider,
  disableProvider,
  deleteProvider,
  testProvider,
  type AIProviderItem,
  type TestResult,
} from '@/api/ai-admin'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const providers = ref<AIProviderItem[]>([])
const searchText = ref('')
const showCreate = ref(false)
const editingProvider = ref<AIProviderItem | null>(null)
const showModels = ref(false)
const selectedProvider = ref<AIProviderItem | null>(null)
const showTestResult = ref(false)
const testResult = ref<TestResult | null>(null)

const enabledCount = computed(() => providers.value.filter(p => p.enabled).length)
const degradedCount = computed(() => providers.value.filter(p => p.health_status === 'degraded' || p.health_status === 'down').length)
const totalModels = computed(() => providers.value.reduce((s, p) => s + p.model_count, 0))

const filteredProviders = computed(() => {
  if (!searchText.value) return providers.value
  const q = searchText.value.toLowerCase()
  return providers.value.filter(p =>
    p.provider_name.toLowerCase().includes(q) ||
    p.provider_code.toLowerCase().includes(q) ||
    (p.base_url || '').toLowerCase().includes(q)
  )
})

function healthTagType(status: string) {
  if (status === 'healthy') return 'success'
  if (status === 'degraded') return 'warning'
  if (status === 'down') return 'danger'
  if (status === 'disabled') return 'info'
  return 'info'
}

function healthLabel(status: string) {
  const labels: Record<string, string> = {
    healthy: '健康', degraded: '降级', down: '不可用',
    unknown: '未知', disabled: '已禁用',
  }
  return labels[status] || status
}

function protocolLabel(p: string) {
  const labels: Record<string, string> = {
    openai_chat_completions: 'OpenAI Chat',
    openai_responses: 'OpenAI Responses',
    anthropic_messages: 'Anthropic',
    gemini_generate_content: 'Gemini',
    ollama_chat: 'Ollama',
    custom_http: '自定义',
  }
  return labels[p] || p
}

async function loadProviders() {
  loading.value = true
  try {
    const res = await getProviders({ page_size: 100 })
    providers.value = res.items || []
  } catch {
    ElMessage.error('加载供应商列表失败')
  } finally {
    loading.value = false
  }
}

async function toggleProvider(id: string, enable: boolean) {
  try {
    if (enable) {
      await enableProvider(id)
    } else {
      await disableProvider(id)
    }
    await loadProviders()
    ElMessage.success(enable ? '已启用' : '已禁用')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function removeProvider(id: string) {
  try {
    await deleteProvider(id)
    await loadProviders()
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

function editProvider(p: AIProviderItem) {
  editingProvider.value = p
}

function manageModels(p: AIProviderItem) {
  selectedProvider.value = p
  showModels.value = true
}

async function testConnection(p: AIProviderItem) {
  testResult.value = null
  showTestResult.value = true
  try {
    const res = await testProvider(p.id)
    testResult.value = res
  } catch (error: unknown) {
    testResult.value = { success: false, status_code: null, latency_ms: null,
      first_token_latency_ms: null, input_tokens: null, output_tokens: null,
      output_text: null, error_code: 'CLIENT_ERROR', error_message: getErrorMessage(error, '请求失败') }
  }
}

function closeForm() {
  showCreate.value = false
  editingProvider.value = null
}

async function onSaved() {
  closeForm()
  await loadProviders()
}

function onSearch() {
  // Filter is computed
}

onMounted(loadProviders)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; }
.header-actions { display: flex; gap: 12px; }

.stats-bar { margin-bottom: 20px; }
.stat-item { text-align: center; padding: 8px 0; }
.stat-value { font-size: 28px; font-weight: 700; color: #409eff; }
.stat-value.success { color: #67c23a; }
.stat-value.warning { color: #e6a23c; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.provider-card { border-radius: 8px; }
.provider-card.card-disabled { opacity: 0.7; }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.card-title-row { display: flex; align-items: center; gap: 12px; }
.provider-icon { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.icon-enabled { background: #ecf5ff; color: #409eff; }
.icon-disabled { background: #f4f4f5; color: #c0c4cc; }
.provider-name { font-size: 16px; font-weight: 600; }
.provider-code { font-size: 12px; color: #909399; margin-top: 2px; }

.card-body { margin-bottom: 12px; }
.info-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }
.info-row .label { color: #909399; }
.info-row .value.url { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.card-footer { display: flex; align-items: center; gap: 8px; padding-top: 12px; border-top: 1px solid #ebeef5; }
.enable-label { font-size: 12px; color: #909399; }
.card-actions { margin-left: auto; display: flex; gap: 4px; }

.test-result .test-status { text-align: center; margin-bottom: 20px; }
.test-result .test-status .success-text { font-size: 18px; color: #67c23a; margin-top: 8px; }
.test-result .test-status .fail-text { font-size: 18px; color: #f56c6c; margin-top: 8px; }
.test-output, .test-error { margin-top: 16px; }
.test-output pre, .test-error pre { background: #f5f7fa; padding: 12px; border-radius: 4px; font-size: 13px; max-height: 200px; overflow: auto; white-space: pre-wrap; }
.label { font-size: 13px; color: #909399; margin-bottom: 4px; }
</style>
