<template>
  <el-dialog
    :title="isEdit ? '编辑供应商' : '新增供应商'"
    v-model="visible"
    width="640px"
    :close-on-click-modal="false"
    @close="emit('close')"
  >
    <el-steps :active="step" finish-status="success" simple style="margin-bottom: 24px">
      <el-step title="基础信息" />
      <el-step title="连接配置" />
      <el-step title="完成" />
    </el-steps>

    <!-- Step 1: Basic Info -->
    <el-form v-if="step === 0" ref="formRef" :model="form" label-width="100px" :rules="rules">
      <el-form-item label="供应商名称" prop="provider_name">
        <el-input v-model="form.provider_name" placeholder="如：DeepSeek官方" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="供应商代码" prop="provider_code">
        <el-input v-model="form.provider_code" placeholder="如：deepseek-main (唯一英文代码)" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="供应商类型">
        <el-select v-model="form.provider_type" style="width: 100%">
          <el-option label="官方 API" value="official" />
          <el-option label="兼容接口" value="compatible" />
          <el-option label="本地模型" value="local" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      <el-form-item label="API 协议">
        <el-select v-model="form.protocol" style="width: 100%">
          <el-option label="OpenAI Chat Completions（推荐，兼容DeepSeek/千问等）" value="openai_chat_completions" />
          <el-option label="Anthropic Messages" value="anthropic_messages" />
          <el-option label="Gemini" value="gemini_generate_content" />
          <el-option label="Ollama" value="ollama_chat" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级">
        <el-input-number v-model="form.priority" :min="1" :max="9999" style="width: 120px" />
        <span style="color:#909399;font-size:12px;margin-left:8px">数字越小优先级越高</span>
      </el-form-item>
    </el-form>

    <!-- Step 2: Connection -->
    <el-form v-if="step === 1" label-width="120px">
      <el-form-item label="Base URL" prop="base_url">
        <el-input v-model="form.base_url" placeholder="https://api.deepseek.com" />
      </el-form-item>
      <el-form-item label="Full URL Mode">
        <el-switch v-model="form.full_url_mode" />
        <span style="color:#909399;font-size:12px;margin-left:8px">用于非标准路径的 API</span>
      </el-form-item>
      <el-form-item v-if="form.full_url_mode" label="完整 Endpoint">
        <el-input v-model="form.endpoint_url" placeholder="https://api.example.com/custom/chat" />
      </el-form-item>
      <el-form-item label="API Key" prop="api_key">
        <el-input
          v-model="form.api_key"
          type="password"
          show-password
          :placeholder="isEdit ? '留空保持现有密钥' : '必填'"
        />
        <div style="color:#909399;font-size:12px;margin-top:4px">密钥加密存储，不会在页面中明文显示</div>
      </el-form-item>
      <el-form-item label="超时（秒）">
        <el-input-number v-model="form.timeout_seconds" :min="5" :max="300" style="width: 120px" />
      </el-form-item>
      <el-form-item label="重试次数">
        <el-input-number v-model="form.retry_count" :min="0" :max="10" style="width: 120px" />
      </el-form-item>
      <el-form-item label="TLS 校验">
        <el-switch v-model="form.tls_verify" />
      </el-form-item>
    </el-form>

    <!-- Step 3: Confirm -->
    <div v-if="step === 2" class="confirm-step">
      <el-icon color="#67c23a" :size="48"><SuccessFilled /></el-icon>
      <h3>配置确认</h3>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="名称">{{ form.provider_name }}</el-descriptions-item>
        <el-descriptions-item label="代码">{{ form.provider_code }}</el-descriptions-item>
        <el-descriptions-item label="协议">{{ form.protocol }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ form.provider_type }}</el-descriptions-item>
        <el-descriptions-item label="Base URL">{{ form.base_url }}</el-descriptions-item>
        <el-descriptions-item label="API Key">{{ form.api_key ? '已配置' : '未配置' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <template #footer>
      <el-button v-if="step > 0" @click="step--">上一步</el-button>
      <el-button v-if="step < 2" type="primary" @click="nextStep">下一步</el-button>
      <el-button v-if="step === 2" type="primary" :loading="submitting" @click="submit">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
      <el-button @click="emit('close')">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { SuccessFilled } from '@element-plus/icons-vue'
import {
  createProvider,
  updateProvider,
  type AIProviderItem,
  type ProviderCreateData,
} from '@/api/ai-admin'

const props = defineProps<{ provider?: AIProviderItem | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const isEdit = computed(() => !!props.provider)
const visible = ref(true)
const step = ref(0)
const submitting = ref(false)
const formRef = ref()

const form = reactive<ProviderCreateData>({
  provider_code: '',
  provider_name: '',
  provider_type: 'compatible',
  protocol: 'openai_chat_completions',
  base_url: '',
  full_url_mode: false,
  endpoint_url: '',
  api_key: '',
  timeout_seconds: 60,
  retry_count: 2,
  tls_verify: true,
  enabled: false,
  priority: 100,
})

const rules = {
  provider_name: [{ required: true, message: '请输入供应商名称' }],
  provider_code: [{ required: true, message: '请输入供应商代码' }],
  api_key: [{ required: !isEdit.value, message: '请输入 API Key' }],
}

onMounted(() => {
  if (props.provider) {
    form.provider_code = props.provider.provider_code
    form.provider_name = props.provider.provider_name
    form.provider_type = props.provider.provider_type
    form.protocol = props.provider.protocol
    form.base_url = props.provider.base_url || ''
    form.full_url_mode = props.provider.full_url_mode
    form.endpoint_url = props.provider.endpoint_url || ''
    form.timeout_seconds = props.provider.timeout_seconds
    form.retry_count = props.provider.retry_count
    form.tls_verify = props.provider.tls_verify
    form.enabled = props.provider.enabled
    form.priority = props.provider.priority
  }
})

async function nextStep() {
  if (step.value === 0) {
    if (!formRef.value) return
    try {
      await formRef.value.validate()
    } catch {
      return
    }
  }
  step.value++
}

async function submit() {
  submitting.value = true
  try {
    if (isEdit.value && props.provider) {
      const updateData: Record<string, unknown> = {}
      if (form.api_key) updateData.api_key = form.api_key
      updateData.base_url = form.base_url
      updateData.timeout_seconds = form.timeout_seconds
      updateData.retry_count = form.retry_count
      updateData.tls_verify = form.tls_verify
      updateData.enabled = form.enabled
      updateData.priority = form.priority
      await updateProvider(props.provider.id, updateData)
      ElMessage.success('已更新')
    } else {
      await createProvider({ ...form })
      ElMessage.success('供应商已创建')
    }
    emit('saved')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.confirm-step { text-align: center; padding: 20px 0; }
.confirm-step h3 { margin: 12px 0 20px; }
</style>
