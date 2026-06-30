<template>
  <div class="payment-ocr">
    <div class="page-header">
      <h2>收款截图识别</h2>
      <el-tag type="success">规则引擎 — 无需 AI Key</el-tag>
    </div>

    <el-row :gutter="16">
      <!-- Upload section -->
      <el-col :span="12">
        <el-card class="upload-card">
          <template #header>上传收款截图</template>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept="image/*"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            drag
          >
            <el-icon :size="48"><UploadFilled /></el-icon>
            <div class="upload-text">将微信/支付宝/银行转账截图拖到此处</div>
            <template #tip>
              <div class="upload-tip">支持 JPG/PNG，确保截图清晰显示金额和时间</div>
            </template>
          </el-upload>

          <el-form style="margin-top: 16px">
            <el-form-item label="关联订单">
              <el-input v-model="orderId" placeholder="可选：输入订单ID" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" :disabled="!selectedFile" @click="doRecognize">
                <el-icon><Search /></el-icon> 识别截图
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Preview section -->
      <el-col :span="12">
        <el-card v-if="previewUrl" class="preview-card">
          <template #header>截图预览</template>
          <el-image :src="previewUrl" fit="contain" style="width: 100%; max-height: 400px" />
        </el-card>
        <el-card v-else class="preview-card">
          <template #header>截图预览</template>
          <div class="empty-preview">
            <el-icon :size="48"><Picture /></el-icon>
            <p>上传截图后此处显示预览</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Results -->
    <el-card v-if="result" class="results-card" style="margin-top: 16px">
      <template #header>
        <span>
          识别结果
          <el-tag v-if="result.mode === 'ai_enhanced'" size="small" type="success" style="margin-left: 8px">AI 增强</el-tag>
          <el-tag :type="confidenceTag" size="small" style="margin-left: 8px">
            置信度：{{ confidenceText }}
          </el-tag>
        </span>
      </template>

      <!-- Order context -->
      <el-alert
        v-if="result.order_context"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      >
        <template #title>
          关联订单：{{ result.order_context.order_no }} |
          客户：{{ result.order_context.customer_name }} |
          未收金额：¥{{ formatMoney(result.order_context.unpaid_amount as number | undefined) }}
        </template>
      </el-alert>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="识别金额">
          <span class="amount-value">
            {{ result.extracted.amount ? `¥${formatMoney(result.extracted.amount)}` : '未识别' }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="付款时间">
          {{ result.extracted.paid_at || '未识别' }}
        </el-descriptions-item>
        <el-descriptions-item label="付款方">
          {{ result.extracted.payer_name || '未识别' }}
        </el-descriptions-item>
        <el-descriptions-item label="付款方式">
          {{ paymentMethodText(result.extracted.payment_method) }}
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">
          {{ result.extracted.remark || '无' }}
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="result.extracted.amount && result.extracted.paid_at" style="margin-top: 16px; text-align: right">
        <el-button type="success" @click="goToPayment">前往登记收款</el-button>
      </div>
    </el-card>

    <div v-if="!result && !loading" class="empty-state">
      <el-icon :size="64"><Picture /></el-icon>
      <p>上传收款截图，系统将自动识别金额、时间、付款方等信息</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, Search, Picture } from '@element-plus/icons-vue'
import { recognizePaymentScreenshot } from '@/api/ai'
import type { OCRRecognizeResponse } from '@/types/api'
import type { UploadFile } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const orderId = ref('')
const result = ref<OCRRecognizeResponse | null>(null)

const confidenceTag = computed(() => {
  const map: Record<string, 'success' | 'warning' | 'info'> = {
    high: 'success',
    medium: 'warning',
    low: 'info',
    none: 'info',
  }
  return map[result.value?.confidence || 'none'] || 'info'
})

const confidenceText = computed(() => {
  const map: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低',
    none: '无',
  }
  return map[result.value?.confidence || 'none'] || '无'
})

function paymentMethodText(method: string | undefined): string {
  const map: Record<string, string> = {
    wechat: '微信',
    alipay: '支付宝',
    bank_transfer: '银行转账',
    cash: '现金',
    other: '其他',
  }
  return map[method || ''] || method || '未识别'
}

function formatMoney(val: number | undefined | null): string {
  if (val == null) return '0'
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function handleFileChange(file: UploadFile) {
  if (file.raw) {
    selectedFile.value = file.raw
    previewUrl.value = URL.createObjectURL(file.raw)
  }
}

function handleFileRemove() {
  selectedFile.value = null
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
  result.value = null
}

async function doRecognize() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择截图')
    return
  }
  loading.value = true
  try {
    result.value = await recognizePaymentScreenshot(
      selectedFile.value,
      orderId.value || undefined,
    )
    ElMessage.success('识别完成')
  } catch {
    ElMessage.error('识别失败')
    result.value = null
  } finally {
    loading.value = false
  }
}

function goToPayment() {
  if (orderId.value) {
    router.push(`/orders/${orderId.value}`)
  } else {
    router.push('/payments')
  }
}
</script>

<style scoped>
.payment-ocr { padding: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; color: var(--ad-text); }

.upload-card { margin-bottom: 16px; }

.upload-text { color: var(--ad-text-muted); margin-top: 8px; }
.upload-tip { color: var(--ad-text-muted); font-size: 12px; margin-top: 4px; }

.preview-card { margin-bottom: 16px; min-height: 300px; }

.empty-preview {
  text-align: center;
  padding: 60px 20px;
  color: var(--ad-text-muted);
}

.results-card { margin-bottom: 16px; }

.amount-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--ad-red, #e63946);
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--ad-text-muted);
}
</style>
