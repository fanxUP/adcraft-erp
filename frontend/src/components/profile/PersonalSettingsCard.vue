<template>
  <el-card class="personal-settings-card" shadow="never">
    <template #header>
      <div class="settings-header">
        <div>
          <div class="settings-title">我的设置</div>
          <div class="settings-subtitle">只影响当前账号，可在不同设备保持一致</div>
        </div>
        <el-tag v-if="dirty" type="warning" size="small">未保存</el-tag>
        <el-tag v-else type="success" size="small">已保存</el-tag>
      </div>
    </template>

    <div class="settings-section">
      <div class="section-title">界面风格</div>
      <div class="theme-grid" role="radiogroup" aria-label="界面风格">
        <button
          v-for="theme in themes"
          :key="theme.name"
          type="button"
          class="theme-card"
          :class="{ active: draft.theme === theme.name }"
          :aria-checked="draft.theme === theme.name"
          role="radio"
          @click="draft.theme = theme.name"
        >
          <span class="theme-preview" aria-hidden="true">
            <span class="preview-bg" :style="{ background: theme.colors[1] }">
              <span
                class="preview-card"
                :style="{
                  background: theme.colors[2],
                  borderColor: theme.colors[2] === '#ffffff' ? '#e0e0e0' : 'transparent',
                }"
              >
                <span class="preview-accent" :style="{ background: theme.colors[0] }" />
                <span class="preview-line" :style="{ background: theme.colors[0], opacity: 0.3 }" />
                <span class="preview-line short" :style="{ background: theme.colors[0], opacity: 0.15 }" />
              </span>
            </span>
          </span>
          <span class="theme-info">
            <span class="theme-name">{{ theme.label }}</span>
            <span class="theme-desc">{{ theme.desc }}</span>
          </span>
        </button>
      </div>
    </div>

    <div class="settings-section">
      <div class="section-title">文字大小</div>
      <el-radio-group v-model="draft.font_size" class="font-size-options" aria-label="文字大小">
        <el-radio
          v-for="size in fontSizes"
          :key="size"
          :value="size"
          border
          size="small"
        >
          {{ size }}px
        </el-radio>
      </el-radio-group>
      <div class="font-preview" :style="fontPreviewStyle">
        示例文字：项目进度、任务明细和工作台数据
      </div>
    </div>

    <el-collapse class="advanced-settings">
      <el-collapse-item title="高级设置：文字粗细" name="font-weight">
        <el-select v-model="draft.font_weight" aria-label="文字粗细" style="max-width: 260px; width: 100%">
          <el-option
            v-for="option in fontWeights"
            :key="option.value"
            :label="`${option.label} (${option.value})`"
            :value="option.value"
          />
        </el-select>
      </el-collapse-item>
    </el-collapse>

    <div class="settings-actions">
      <el-button @click="restoreDefaults" :disabled="saving">恢复默认</el-button>
      <el-button type="primary" :loading="saving" :disabled="!dirty" @click="saveSettings">
        保存设置
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateUserPreferences } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import {
  DEFAULT_USER_PREFERENCES,
  FONT_SIZE_OPTIONS,
  FONT_WEIGHT_OPTIONS,
  normalizeUserPreferences,
  THEME_LIST,
} from '@/config/userPreferences'
import type { UserPreferences } from '@/types/api'
import { getErrorMessage } from '@/utils/error'

const authStore = useAuthStore()
const appStore = useAppStore()
const themes = THEME_LIST
const fontSizes = FONT_SIZE_OPTIONS
const fontWeights = FONT_WEIGHT_OPTIONS
const saving = ref(false)
const serverPreferences = ref<UserPreferences>(normalizeUserPreferences(authStore.user?.preferences))
const draft = reactive<UserPreferences>({ ...serverPreferences.value })

const dirty = computed(() => (
  draft.theme !== serverPreferences.value.theme
  || draft.font_size !== serverPreferences.value.font_size
  || draft.font_weight !== serverPreferences.value.font_weight
))

const fontPreviewStyle = computed(() => ({
  fontSize: `${draft.font_size}px`,
  fontWeight: String(draft.font_weight),
}))

watch(
  () => authStore.user?.preferences,
  preferences => {
    if (dirty.value) return
    const normalized = normalizeUserPreferences(preferences)
    serverPreferences.value = normalized
    Object.assign(draft, normalized)
  },
  { deep: true },
)

// Preview changes immediately, but persistence only happens after Save.
watch(
  () => [draft.theme, draft.font_size, draft.font_weight] as const,
  ([theme, fontSize, fontWeight]) => {
    // Avoid a second source of user state: the auth store applies the same
    // normalized values after a successful save or profile load.
    appStore.setTheme(theme)
    appStore.setFontSize(fontSize)
    appStore.setFontWeight(fontWeight)
  },
  { immediate: true },
)

function restoreDefaults() {
  Object.assign(draft, DEFAULT_USER_PREFERENCES)
}

async function saveSettings() {
  if (!dirty.value || !authStore.user) return
  saving.value = true
  try {
    const preferences = await updateUserPreferences({ ...draft })
    const normalized = normalizeUserPreferences(preferences)
    serverPreferences.value = normalized
    authStore.setUserPreferences(normalized)
    Object.assign(draft, normalized)
    ElMessage.success('个人设置已保存')
  } catch (error: unknown) {
    Object.assign(draft, serverPreferences.value)
    ElMessage.error(getErrorMessage(error) || '个人设置保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('个人设置还有未保存的修改，确定离开吗？', '提示', {
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑',
      type: 'warning',
    })
    return true
  } catch {
    return false
  }
})
</script>

<style scoped>
.personal-settings-card {
  margin-bottom: 16px;
}

.settings-header,
.settings-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.settings-title {
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 650;
}

.settings-subtitle {
  margin-top: 4px;
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.settings-section {
  margin-bottom: 20px;
}

.section-title {
  margin-bottom: 10px;
  color: var(--ad-text);
  font-size: 14px;
  font-weight: 600;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.theme-card {
  overflow: hidden;
  padding: 0;
  border: 2px solid var(--ad-border);
  border-radius: 8px;
  background: var(--ad-card);
  color: var(--ad-text);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.theme-card:hover,
.theme-card:focus-visible {
  border-color: var(--ad-text-secondary);
  outline: none;
  transform: translateY(-2px);
}

.theme-card.active {
  border-color: var(--ad-red);
  box-shadow: 0 0 12px var(--ad-accent-glow, rgba(37, 99, 235, 0.2));
}

.theme-preview {
  display: block;
  height: 72px;
  padding: 8px;
}

.preview-bg {
  display: flex;
  height: 100%;
  align-items: stretch;
  padding: 6px;
  border-radius: 4px;
}

.preview-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  border: 1px solid transparent;
  border-radius: 3px;
}

.preview-accent {
  display: block;
  width: 24px;
  height: 4px;
  border-radius: 2px;
}

.preview-line {
  display: block;
  width: 80%;
  height: 3px;
  border-radius: 1px;
}

.preview-line.short { width: 50%; }

.theme-info {
  display: block;
  padding: 8px 10px;
  background: var(--ad-card);
}

.theme-name,
.theme-desc {
  display: block;
}

.theme-name {
  color: var(--ad-text);
  font-size: 13px;
  font-weight: bold;
}

.theme-desc {
  margin-top: 2px;
  color: var(--ad-text-secondary);
  font-size: 11px;
}

.font-size-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.font-size-options :deep(.el-radio) {
  margin-right: 0;
}

.font-preview {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid var(--ad-border);
  border-radius: 8px;
  background: var(--ad-darker);
  color: var(--ad-text);
  line-height: 1.6;
}

.advanced-settings {
  margin-bottom: 20px;
  border-top: 1px solid var(--ad-border);
  border-bottom: 1px solid var(--ad-border);
}

.settings-actions {
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .theme-grid {
    grid-template-columns: 1fr;
  }

  .settings-actions {
    align-items: stretch;
    flex-direction: column-reverse;
  }

  .settings-actions .el-button {
    width: 100%;
    margin-left: 0;
  }
}
</style>
