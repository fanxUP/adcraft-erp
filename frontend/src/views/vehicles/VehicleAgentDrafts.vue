<template>
  <div class="agent-drafts-page">
    <!-- Header + Test Input -->
    <el-card class="test-card">
      <template #header>
        <div class="card-header">
          <span>消息识别测试</span>
          <el-tag type="info" size="small">规则引擎</el-tag>
        </div>
      </template>
      <div class="test-input-row">
        <el-input
          v-model="testContent"
          placeholder="输入消息内容测试识别效果，如：明天安装需要一辆车，去万达广场"
          clearable
          @keyup.enter="handleTestAnalyze"
        />
        <el-button type="primary" :loading="analyzing" @click="handleTestAnalyze">
          识别
        </el-button>
      </div>
      <div v-if="analyzeResult" class="analyze-result">
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="识别意图">
            <el-tag :type="intentTagType(analyzeResult.intent)">{{ intentLabel(analyzeResult.intent) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            <el-progress :percentage="Math.round(analyzeResult.confidence * 100)" :stroke-width="10" style="width: 100px" />
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskTagType(analyzeResult.risk_level)">{{ analyzeResult.risk_level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag type="info">{{ analyzeResult.status }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="analyzeResult.extracted_data && Object.keys(analyzeResult.extracted_data).length" class="extracted-data">
          <span class="label">提取数据：</span>
          <el-tag v-for="(v, k) in analyzeResult.extracted_data" :key="k" size="small" class="data-tag">
            {{ k }}: {{ v }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <!-- Draft List -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>识别草稿</span>
          <div class="filters">
            <el-select v-model="filters.status" placeholder="状态" clearable size="small" style="width: 100px" @change="fetchDrafts">
              <el-option label="待确认" value="pending" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
            <el-select v-model="filters.intent" placeholder="意图" clearable size="small" style="width: 130px" @change="fetchDrafts">
              <el-option v-for="i in intentOptions" :key="i.value" :label="i.label" :value="i.value" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="drafts" v-loading="loading" stripe>
        <el-table-column prop="created_at" label="时间" width="160" :formatter="formatTime" />
        <el-table-column prop="sender_name" label="发送者" width="90" />
        <el-table-column prop="original_content" label="原始消息" min-width="200" show-overflow-tooltip />
        <el-table-column prop="intent" label="识别意图" width="120">
          <template #default="{ row }">
            <el-tag :type="intentTagType(row.intent)" size="small">{{ intentLabel(row.intent) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="90">
          <template #default="{ row }">
            {{ Math.round(row.confidence * 100) }}%
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险" width="70">
          <template #default="{ row }">
            <el-tag :type="riskTagType(row.risk_level)" size="small">{{ row.risk_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" type="success" size="small" @click="handleConfirm(row)">
              确认
            </el-button>
            <el-button v-if="row.status === 'pending'" type="danger" size="small" @click="handleReject(row)">
              驳回
            </el-button>
            <el-button size="small" @click="handleDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end;"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- Detail Drawer -->
    <el-drawer v-model="drawerVisible" title="草稿详情" size="450px">
      <template v-if="currentDraft">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="消息来源">{{ currentDraft.platform }}</el-descriptions-item>
          <el-descriptions-item label="发送者">{{ currentDraft.sender_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="原始消息">{{ currentDraft.original_content }}</el-descriptions-item>
          <el-descriptions-item label="识别意图">
            <el-tag :type="intentTagType(currentDraft.intent)">{{ intentLabel(currentDraft.intent) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ Math.round(currentDraft.confidence * 100) }}%</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskTagType(currentDraft.risk_level)">{{ currentDraft.risk_level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(currentDraft.status)">{{ statusLabel(currentDraft.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="建议操作">{{ currentDraft.suggested_action || '-' }}</el-descriptions-item>
          <el-descriptions-item label="需要确认">{{ currentDraft.requires_confirmation ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="需要财务审核">{{ currentDraft.requires_finance_review ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(null, null, currentDraft.created_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentDraft.confirmed_by_name" label="确认人">{{ currentDraft.confirmed_by_name }}</el-descriptions-item>
          <el-descriptions-item v-if="currentDraft.confirmed_at" label="确认时间">{{ formatTime(null, null, currentDraft.confirmed_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentDraft.reject_reason" label="驳回原因">{{ currentDraft.reject_reason }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="currentDraft.extracted_data && Object.keys(currentDraft.extracted_data).length" class="detail-extracted">
          <h4>提取的结构化数据</h4>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item v-for="(v, k) in currentDraft.extracted_data" :key="k" :label="String(k)">
              {{ v }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div v-if="currentDraft.status === 'pending'" class="drawer-actions">
          <el-button type="success" @click="handleConfirm(currentDraft)">确认创建</el-button>
          <el-button type="danger" @click="handleReject(currentDraft)">驳回</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Reject Dialog -->
    <el-dialog v-model="rejectDialogVisible" title="驳回草稿" width="400px">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="驳回原因（可选）" />
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  analyzeAgentMessage, getAgentDrafts, confirmAgentDraft, rejectAgentDraft,
  type AgentDraftResponse,
} from '@/api/vehicles'

const testContent = ref('')
const analyzing = ref(false)
const analyzeResult = ref<AgentDraftResponse | null>(null)

const loading = ref(false)
const drafts = ref<AgentDraftResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filters = reactive({ status: '', intent: '' })

const drawerVisible = ref(false)
const currentDraft = ref<AgentDraftResponse | null>(null)

const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const rejecting = ref(false)
let rejectingId = ''

const intentOptions = [
  { value: 'vehicle_use_request', label: '用车申请' },
  { value: 'vehicle_dispatch', label: '派车安排' },
  { value: 'vehicle_start', label: '出车' },
  { value: 'vehicle_arrival', label: '到达' },
  { value: 'vehicle_return', label: '收车' },
  { value: 'fuel_expense', label: '油费' },
  { value: 'vehicle_issue', label: '车辆异常' },
  { value: 'maintenance_request', label: '维修保养' },
  { value: 'vehicle_query', label: '车辆查询' },
]

const intentMap: Record<string, string> = Object.fromEntries(intentOptions.map(i => [i.value, i.label]))

function intentLabel(intent: string) { return intentMap[intent] || intent }
function intentTagType(intent: string) {
  const map: Record<string, string> = {
    fuel_expense: 'warning', vehicle_issue: 'danger', maintenance_request: 'warning',
    vehicle_use_request: '', vehicle_dispatch: 'success', vehicle_start: 'success',
    vehicle_arrival: 'success', vehicle_return: 'success', vehicle_query: 'info',
  }
  return map[intent] || 'info'
}
function riskTagType(risk: string) {
  return risk === 'high' ? 'danger' : risk === 'medium' ? 'warning' : 'success'
}
function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待确认', confirmed: '已确认', rejected: '已驳回', expired: '已过期' }
  return map[s] || s
}
function statusTagType(s: string) {
  const map: Record<string, string> = { pending: 'warning', confirmed: 'success', rejected: 'danger', expired: 'info' }
  return map[s] || 'info'
}
function formatTime(_r: unknown, _c: unknown, val: string) {
  if (!val) return '-'
  return val.replace('T', ' ').substring(0, 19)
}

async function fetchDrafts() {
  loading.value = true
  try {
    const res = await getAgentDrafts({
      page: page.value,
      page_size: pageSize,
      status: filters.status || undefined,
      intent: filters.intent || undefined,
    })
    drafts.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

function handlePageChange(p: number) {
  page.value = p
  fetchDrafts()
}

async function handleTestAnalyze() {
  if (!testContent.value.trim()) return
  analyzing.value = true
  analyzeResult.value = null
  try {
    const res = await analyzeAgentMessage({ content: testContent.value.trim(), platform: 'manual' })
    analyzeResult.value = res.data
    ElMessage.success('识别完成')
    fetchDrafts()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '识别失败')
  } finally {
    analyzing.value = false
  }
}

function handleDetail(row: AgentDraftResponse) {
  currentDraft.value = row
  drawerVisible.value = true
}

async function handleConfirm(row: AgentDraftResponse) {
  try {
    await ElMessageBox.confirm(
      `确认将此草稿创建为正式记录？\n\n原始消息：${row.original_content}`,
      '确认草稿',
      { type: 'warning' }
    )
    const res = await confirmAgentDraft(row.id)
    ElMessage.success('已确认并创建正式记录')
    fetchDrafts()
    if (drawerVisible.value && currentDraft.value?.id === row.id) {
      currentDraft.value = res.data
    }
  } catch (e: unknown) {
    if (e !== 'cancel') ElMessage.error(e instanceof Error ? e.message : '确认失败')
  }
}

function handleReject(row: AgentDraftResponse) {
  rejectingId = row.id
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  rejecting.value = true
  try {
    await rejectAgentDraft(rejectingId, rejectReason.value || undefined)
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    fetchDrafts()
    if (drawerVisible.value && currentDraft.value?.id === rejectingId) {
      drawerVisible.value = false
    }
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '驳回失败')
  } finally {
    rejecting.value = false
  }
}

onMounted(() => fetchDrafts())
</script>

<style scoped>
.agent-drafts-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.test-input-row {
  display: flex;
  gap: 8px;
}

.analyze-result {
  margin-top: 12px;
}

.extracted-data {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.extracted-data .label {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.data-tag {
  margin: 0;
}

.filters {
  display: flex;
  gap: 8px;
}

.detail-extracted {
  margin-top: 16px;
}

.detail-extracted h4 {
  margin-bottom: 8px;
  font-size: 14px;
}

.drawer-actions {
  margin-top: 20px;
  display: flex;
  gap: 8px;
}
</style>
