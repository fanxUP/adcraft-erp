<template>
  <div class="draft-list-page">
    <div class="page-header">
      <h2>Agent 草稿中心</h2>
      <el-button type="primary" @click="showIngestDialog = true">
        <el-icon><ChatDotRound /></el-icon>模拟消息
      </el-button>
    </div>

    <!-- 筛选 -->
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="filters">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="待确认" value="pending" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadDrafts">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 草稿列表 -->
    <el-table :data="drafts" v-loading="loading" stripe style="width: 100%"
      :row-class-name="({ row }) => row.status === 'pending' ? 'row-pending' : ''">
      <el-table-column prop="created_at" label="时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="sender_name" label="发送人" width="100" />
      <el-table-column prop="platform" label="平台" width="90">
        <template #default="{ row }">
          <el-tag size="small">{{ platformLabel(row.platform) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="raw_message" label="原始消息" min-width="200" show-overflow-tooltip />
      <el-table-column prop="intent" label="识别意图" width="160">
        <template #default="{ row }">
          <el-tag :type="intentTagType(row.intent)" size="small">{{ intentLabel(row.intent) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="confidence" label="置信度" width="80">
        <template #default="{ row }">
          {{ (row.confidence * 100).toFixed(0) }}%
        </template>
      </el-table-column>
      <el-table-column prop="risk_level" label="风险" width="70">
        <template #default="{ row }">
          <el-tag :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'success'" size="small">
            {{ row.risk_level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="showDetail(row)">详情</el-button>
          <template v-if="row.status === 'pending'">
            <el-button link type="success" @click="handleConfirm(row)">确认</el-button>
            <el-button link type="danger" @click="handleReject(row)">拒绝</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadDrafts"
        @size-change="loadDrafts"
      />
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="showDetailDialog" title="草稿详情" width="700px">
      <template v-if="detailDraft">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="发送人">{{ detailDraft.sender_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ platformLabel(detailDraft.platform) }}</el-descriptions-item>
          <el-descriptions-item label="意图">
            <el-tag :type="intentTagType(detailDraft.intent)" size="small">{{ intentLabel(detailDraft.intent) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ (detailDraft.confidence * 100).toFixed(0) }}%</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="detailDraft.risk_level === 'high' ? 'danger' : detailDraft.risk_level === 'medium' ? 'warning' : 'success'" size="small">
              {{ detailDraft.risk_level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(detailDraft.status) }}</el-descriptions-item>
          <el-descriptions-item label="原始消息" :span="2">
            <div style="white-space: pre-wrap;">{{ detailDraft.raw_message }}</div>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 提取的字段 -->
        <div v-if="detailDraft.extracted && Object.keys(detailDraft.extracted).length > 0" style="margin-top: 16px;">
          <h4>识别提取数据</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item v-for="(val, key) in detailDraft.extracted" :key="key" :label="extractedLabel(key)">
              <template v-if="Array.isArray(val)">
                <div v-for="(item, idx) in val" :key="idx">
                  {{ typeof item === 'object' ? JSON.stringify(item) : item }}
                </div>
              </template>
              <template v-else>{{ val }}</template>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 执行结果 -->
        <div v-if="detailDraft.status === 'confirmed' && (detailDraft.created_ledger_id || detailDraft.created_expense_id)" style="margin-top: 16px;">
          <h4>执行结果</h4>
          <p v-if="detailDraft.created_ledger_id">已创建台账: {{ detailDraft.created_ledger_id }}</p>
          <p v-if="detailDraft.created_expense_id">已创建费用: {{ detailDraft.created_expense_id }}</p>
        </div>

        <div v-if="detailDraft.reject_reason" style="margin-top: 16px;">
          <h4>拒绝原因</h4>
          <p>{{ detailDraft.reject_reason }}</p>
        </div>
      </template>
    </el-dialog>

    <!-- 模拟消息弹窗 -->
    <el-dialog v-model="showIngestDialog" title="模拟 Agent 消息" width="600px">
      <el-form :model="ingestForm" label-width="80px">
        <el-form-item label="发送人">
          <el-input v-model="ingestForm.sender_name" placeholder="如：王师傅" />
        </el-form-item>
        <el-form-item label="消息内容">
          <el-input v-model="ingestForm.content" type="textarea" :rows="4"
            placeholder="如：今天去万达广场装门头，高空车收800，油费我垫了120，停车20。" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="ingestForm.platform">
            <el-option label="微信" value="wechat" />
            <el-option label="WorkBuddy" value="workbuddy" />
            <el-option label="飞书" value="feishu" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showIngestDialog = false">取消</el-button>
        <el-button type="primary" @click="handleIngest" :loading="ingesting">发送识别</el-button>
      </template>
    </el-dialog>

    <!-- 确认弹窗 -->
    <el-dialog v-model="showConfirmDialog" title="确认草稿" width="500px">
      <p>确认此草稿将写入正式台账/费用记录。</p>
      <p v-if="confirmDraft?.risk_level === 'high'" style="color: #e6a23c;">
        ⚠️ 此草稿风险等级为高，请仔细核对。
      </p>
      <el-form v-if="confirmDraft?.extracted" label-width="80px" style="margin-top: 12px;">
        <template v-for="(val, key) in confirmDraft.extracted" :key="key">
          <el-form-item :label="extractedLabel(key)" v-if="key !== 'personnel_expenses'">
            <el-input v-model="confirmDraft.extracted[key]" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showConfirmDialog = false">取消</el-button>
        <el-button type="success" @click="doConfirm" :loading="confirming">确认执行</el-button>
      </template>
    </el-dialog>

    <!-- 拒绝弹窗 -->
    <el-dialog v-model="showRejectDialog" title="拒绝草稿" width="400px">
      <el-form label-width="80px">
        <el-form-item label="拒绝原因">
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRejectDialog = false">取消</el-button>
        <el-button type="danger" @click="doReject" :loading="rejecting">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound } from '@element-plus/icons-vue'
import {
  getAerialAgentDrafts,
  getAerialAgentDraft,
  confirmAerialAgentDraft,
  rejectAerialAgentDraft,
  ingestAerialAgentMessage,
  type AerialAgentDraft,
} from '@/api/aerial'

const loading = ref(false)
const drafts = ref<AerialAgentDraft[]>([])
const filters = reactive({ status: 'pending' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const showDetailDialog = ref(false)
const detailDraft = ref<AerialAgentDraft | null>(null)

const showIngestDialog = ref(false)
const ingestForm = reactive({ sender_name: '', content: '', platform: 'wechat' })
const ingesting = ref(false)

const showConfirmDialog = ref(false)
const confirmDraft = ref<AerialAgentDraft | null>(null)
const confirming = ref(false)

const showRejectDialog = ref(false)
const rejectDraftId = ref('')
const rejectReason = ref('')
const rejecting = ref(false)

const loadDrafts = async () => {
  loading.value = true
  try {
    const res = await getAerialAgentDrafts({
      status: filters.status || undefined,
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    drafts.value = res.data?.items || []
    pagination.total = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

const showDetail = async (row: AerialAgentDraft) => {
  try {
    const res = await getAerialAgentDraft(row.id)
    detailDraft.value = res.data
    showDetailDialog.value = true
  } catch {
    detailDraft.value = row
    showDetailDialog.value = true
  }
}

const handleConfirm = (row: AerialAgentDraft) => {
  confirmDraft.value = { ...row, extracted: { ...row.extracted } }
  showConfirmDialog.value = true
}

const doConfirm = async () => {
  if (!confirmDraft.value) return
  confirming.value = true
  try {
    const res = await confirmAerialAgentDraft(confirmDraft.value.id, confirmDraft.value.extracted)
    if (res.data?.success) {
      ElMessage.success('草稿已确认，已写入正式台账')
      showConfirmDialog.value = false
      loadDrafts()
    } else {
      ElMessage.error(res.data?.error || '确认失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '确认失败')
  } finally {
    confirming.value = false
  }
}

const handleReject = (row: AerialAgentDraft) => {
  rejectDraftId.value = row.id
  rejectReason.value = ''
  showRejectDialog.value = true
}

const doReject = async () => {
  rejecting.value = true
  try {
    await rejectAerialAgentDraft(rejectDraftId.value, rejectReason.value)
    ElMessage.success('草稿已拒绝')
    showRejectDialog.value = false
    loadDrafts()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '拒绝失败')
  } finally {
    rejecting.value = false
  }
}

const handleIngest = async () => {
  if (!ingestForm.content.trim()) {
    ElMessage.warning('请输入消息内容')
    return
  }
  ingesting.value = true
  try {
    const res = await ingestAerialAgentMessage({
      platform: ingestForm.platform,
      sender_name: ingestForm.sender_name || undefined,
      content: ingestForm.content,
    })
    const data = res.data
    if (data?.intent && data.intent !== 'normal_chat') {
      ElMessage.success(`识别成功：${intentLabel(data.intent)}，置信度 ${(data.confidence * 100).toFixed(0)}%`)
    } else {
      ElMessage.info('未识别为高空车相关消息')
    }
    showIngestDialog.value = false
    ingestForm.content = ''
    loadDrafts()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    ingesting.value = false
  }
}

// ── 工具函数 ──────────────────────────────────────────────────────────────

const platformLabel = (p: string) => {
  const map: Record<string, string> = { wechat: '微信', workbuddy: 'WorkBuddy', feishu: '飞书', erp: 'ERP' }
  return map[p] || p
}

const intentLabel = (i: string) => {
  const map: Record<string, string> = {
    aerial_work_ledger: '出车台账',
    aerial_personnel_expense: '人员垫付',
    aerial_payment_claim: '付款声称',
    aerial_vehicle_issue: '车辆异常',
    aerial_query_report: '查询统计',
    aerial_reimbursement_claim: '报销确认',
    normal_chat: '普通消息',
  }
  return map[i] || i
}

const intentTagType = (i: string) => {
  const map: Record<string, string> = {
    aerial_work_ledger: 'primary',
    aerial_personnel_expense: 'warning',
    aerial_payment_claim: 'danger',
    aerial_vehicle_issue: 'danger',
    aerial_query_report: 'info',
    aerial_reimbursement_claim: 'warning',
    normal_chat: 'info',
  }
  return map[i] || 'info'
}

const statusLabel = (s: string) => {
  const map: Record<string, string> = { pending: '待确认', confirmed: '已确认', rejected: '已拒绝', expired: '已过期' }
  return map[s] || s
}

const statusTagType = (s: string) => {
  const map: Record<string, string> = { pending: 'warning', confirmed: 'success', rejected: 'danger', expired: 'info' }
  return map[s] || 'info'
}

const extractedLabel = (key: string) => {
  const map: Record<string, string> = {
    work_date: '作业日期',
    work_location: '作业地点',
    work_content: '作业内容',
    receivable_amount: '应收金额',
    name: '人员',
    name_hint: '发送人',
    personnel_id: '人员ID',
    vehicle_id: '车辆ID',
    customer_name: '客户',
    personnel_expenses: '垫付费用',
    issue_description: '问题描述',
    plate_number: '车牌号',
    claim_text: '付款声明',
    query_text: '查询内容',
    query_month: '查询月份',
  }
  return map[key] || key
}

const formatTime = (t?: string) => {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 19)
}

onMounted(loadDrafts)
</script>

<style scoped>
.draft-list-page {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
}
.filter-card {
  margin-bottom: 16px;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
:deep(.row-pending) {
  background-color: #fdf6ec !important;
}
</style>
