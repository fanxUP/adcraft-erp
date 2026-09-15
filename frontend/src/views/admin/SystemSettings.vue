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
        <el-divider content-position="left">品牌设置</el-divider>
        <el-form-item label="系统名称">
          <el-input v-model="form.APP_NAME" maxlength="120" show-word-limit />
          <div class="form-tip">保存后会同步更新侧边栏、登录页、浏览器标题和移动端个人中心。</div>
        </el-form-item>
        <el-form-item label="系统 Logo">
          <div class="branding-editor">
            <div class="branding-preview" :title="brandingStore.appName">
              <BrandLogo :size="72" />
            </div>
            <div class="branding-actions">
              <div class="branding-action-row">
                <el-upload
                  :show-file-list="false"
                  :auto-upload="false"
                  accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                  :on-change="handleLogoChange"
                  :disabled="logoUploading"
                >
                  <el-button type="primary" :loading="logoUploading">
                    {{ logoUploading ? '上传中…' : '选择并上传 Logo' }}
                  </el-button>
                </el-upload>
                <el-button
                  v-if="form.BRANDING?.has_custom_logo"
                  :loading="logoRestoring"
                  @click="handleRestoreLogo"
                >恢复默认</el-button>
              </div>
              <div class="form-tip">仅支持 JPG、PNG、WEBP，大小不超过 2MB。</div>
              <div v-if="form.BRANDING?.logo_filename" class="form-tip">
                当前文件：{{ form.BRANDING.logo_filename }}（{{ formatFileSize(form.BRANDING.logo_size) }}）
              </div>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">基本设置</el-divider>
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
import type { UploadFile } from 'element-plus'
import {
  getSystemSettings,
  updateSystemSettings,
  uploadSystemLogo,
  restoreDefaultSystemLogo,
  type BrandingMetadata,
  type SystemSettings,
} from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, PageHeader } from '@/components/ui'
import BrandLogo from '@/components/BrandLogo.vue'
import { useBrandingStore } from '@/stores/branding'

const loading = ref(false)
const saving = ref(false)
const bumping = ref(false)
const logoUploading = ref(false)
const logoRestoring = ref(false)
const settings = ref<SystemSettings | null>(null)
const brandingStore = useBrandingStore()

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
  BRANDING: null as BrandingMetadata | null,
})

function fallbackBranding(appName: string): BrandingMetadata {
  return {
    app_name: appName,
    logo_url: null,
    logo_version: 0,
    has_custom_logo: false,
  }
}

function syncBranding(data: SystemSettings) {
  const branding = data.BRANDING || fallbackBranding(data.APP_NAME)
  form.BRANDING = branding
  brandingStore.setBranding(branding)
}

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
      BRANDING: data.BRANDING || null,
    })
    syncBranding(data)
  } finally { loading.value = false }
}

function formatFileSize(size: number | null | undefined): string {
  if (!size) return '未知大小'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

async function handleLogoChange(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file || logoUploading.value) return
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!['.jpg', '.jpeg', '.png', '.webp'].includes(extension)) {
    ElMessage.warning('Logo 仅支持 JPG、PNG、WEBP 格式')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('Logo 文件不能超过 2MB')
    return
  }

  logoUploading.value = true
  try {
    const result = await uploadSystemLogo(file)
    form.BRANDING = result.branding
    brandingStore.setBranding(result.branding)
    ElMessage.success(result.message || 'Logo 已更新')
  } catch {
    // handled by the shared API interceptor
  } finally {
    logoUploading.value = false
  }
}

async function handleRestoreLogo() {
  try {
    await ElMessageBox.confirm(
      '恢复默认 Logo 后，系统将使用内置的字母标志。确定继续吗？',
      '恢复默认 Logo',
      { confirmButtonText: '恢复默认', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }

  logoRestoring.value = true
  try {
    const result = await restoreDefaultSystemLogo()
    form.BRANDING = result.branding
    brandingStore.setBranding(result.branding)
    ElMessage.success(result.message || 'Logo 已恢复默认')
  } catch {
    // handled by the shared API interceptor
  } finally {
    logoRestoring.value = false
  }
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
    await fetchSettings()
  } catch { /* handled */ } finally { saving.value = false }
}

onMounted(fetchSettings)
</script>

<style scoped>
.form-tip {
  margin-top: 4px;
  color: var(--ad-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.branding-editor {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.branding-preview {
  display: flex;
  width: 96px;
  height: 96px;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: 1px solid var(--ui-border);
  border-radius: 12px;
  background: var(--ui-surface-subtle);
}

.branding-actions {
  min-width: 0;
  padding-top: 4px;
}

.branding-action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 600px) {
  .branding-editor {
    align-items: center;
    flex-direction: column;
  }

  .branding-actions {
    width: 100%;
    padding-top: 0;
  }
}
</style>
