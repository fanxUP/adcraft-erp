<template>
  <AppPage>
    <template #header><PageHeader title="系统设置" description="统一管理安全控制和系统运行参数。界面风格与文字大小请在个人中心修改。" /></template>

    <!-- Force Re-login -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <span>安全控制</span>
      </template>
      <el-form label-width="140px" style="max-width: 600px">
        <el-form-item label="强制重新登录">
          <div>
            <el-button :loading="bumping" @click="handleBumpToken">
              强制所有用户重新登录
            </el-button>
            <div style="font-size: 12px; color: var(--ad-text-secondary); margin-top: 4px">
              发布需要重新登录才能生效的更新后，点击此按钮强制所有已登录用户退出并重新登录
            </div>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <el-form :model="form" label-width="140px" style="max-width: 600px">
        <el-divider content-position="left">基本设置</el-divider>
        <el-form-item label="系统名称">
          <el-input v-model="form.APP_NAME" />
        </el-form-item>
        <el-form-item label="公司名称（乙方）">
          <el-input v-model="form.COMPANY_NAME" placeholder="用于打印验收单等处乙方名称" />
        </el-form-item>
        <el-form-item label="公司联系电话">
          <el-input v-model="form.COMPANY_PHONE" placeholder="用于报价单/订单/验收单打印显示" />
        </el-form-item>
        <el-form-item label="JWT过期时间(分钟)">
          <el-input-number v-model="form.JWT_EXPIRE_MINUTES" :min="60" :max="10080" style="width: 100%" />
        </el-form-item>

        <el-divider content-position="left">AI 功能</el-divider>
        <el-form-item label="启用AI功能">
          <el-switch v-model="form.AI_ENABLED" />
        </el-form-item>
        <template v-if="form.AI_ENABLED">
          <el-form-item label="AI供应商">
            <el-select v-model="form.AI_PROVIDER" style="width: 100%">
              <el-option label="Anthropic" value="anthropic" />
              <el-option label="OpenAI" value="openai" />
            </el-select>
          </el-form-item>
          <el-form-item label="AI模型">
            <el-input v-model="form.AI_MODEL" placeholder="如 claude-sonnet-4-20250514" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.AI_API_KEY" type="password" show-password placeholder="输入新Key覆盖" />
            <div style="font-size: 12px; color: var(--ad-text-secondary); margin-top: 4px">当前: {{ settings?.AI_API_KEY || '未配置' }}</div>
          </el-form-item>
          <el-form-item label="API Base URL">
            <el-input v-model="form.AI_API_BASE_URL" placeholder="留空使用默认" />
          </el-form-item>
        </template>

        <el-divider content-position="left">存储</el-divider>
        <el-form-item label="上传方式">
          <el-tag>{{ form.UPLOAD_STORAGE }}</el-tag>
        </el-form-item>
        <el-form-item label="上传目录">
          <el-tag>{{ form.LOCAL_UPLOAD_DIR }}</el-tag>
        </el-form-item>

        <el-form-item>
          <el-button :loading="saving" @click="handleSave" type="primary">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </AppPage>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getSystemSettings, updateSystemSettings, type SystemSettings } from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, PageHeader } from '@/components/ui'

const loading = ref(false)
const saving = ref(false)
const bumping = ref(false)
const settings = ref<SystemSettings | null>(null)

const form = reactive({
  APP_NAME: '',
  COMPANY_NAME: '',
  COMPANY_PHONE: '',
  JWT_EXPIRE_MINUTES: 1440,
  UPLOAD_STORAGE: '',
  LOCAL_UPLOAD_DIR: '',
  AI_ENABLED: false,
  AI_PROVIDER: 'anthropic',
  AI_MODEL: '',
  AI_API_KEY: '',
  AI_API_BASE_URL: '',
})

async function fetchSettings() {
  loading.value = true
  try {
    const data = await getSystemSettings()
    settings.value = data
    Object.assign(form, {
      APP_NAME: data.APP_NAME,
      COMPANY_NAME: data.COMPANY_NAME || '',
      COMPANY_PHONE: data.COMPANY_PHONE || '',
      JWT_EXPIRE_MINUTES: data.JWT_EXPIRE_MINUTES,
      UPLOAD_STORAGE: data.UPLOAD_STORAGE,
      LOCAL_UPLOAD_DIR: data.LOCAL_UPLOAD_DIR,
      AI_ENABLED: data.AI_ENABLED,
      AI_PROVIDER: data.AI_PROVIDER,
      AI_MODEL: data.AI_MODEL,
      AI_API_KEY: '',
      AI_API_BASE_URL: data.AI_API_BASE_URL,
    })
  } finally { loading.value = false }
}

async function handleBumpToken() {
  try {
    await ElMessageBox.confirm(
      '确定强制所有用户重新登录？当前所有已登录用户将被立即退出，需要重新输入密码。',
      '确认操作',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  bumping.value = true
  try {
    const { forceRelogin } = await import('@/api/admin')
    const res = await forceRelogin()
    ElMessage.success(res.message || '已强制所有用户重新登录')
  } catch { /* handled */ } finally { bumping.value = false }
}

async function handleSave() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      APP_NAME: form.APP_NAME,
      COMPANY_NAME: form.COMPANY_NAME,
      COMPANY_PHONE: form.COMPANY_PHONE,
      JWT_EXPIRE_MINUTES: form.JWT_EXPIRE_MINUTES,
      AI_ENABLED: form.AI_ENABLED,
      AI_PROVIDER: form.AI_PROVIDER,
      AI_MODEL: form.AI_MODEL,
      AI_API_BASE_URL: form.AI_API_BASE_URL,
    }
    // Only send API key if user typed a new one
    if (form.AI_API_KEY) {
      payload.AI_API_KEY = form.AI_API_KEY
    }
    const result = await updateSystemSettings(payload)
    ElMessage.success(result.message || '设置已保存')
    fetchSettings()
  } catch { /* handled */ } finally { saving.value = false }
}

onMounted(fetchSettings)
</script>
