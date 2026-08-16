<template>
  <el-card
    data-ai-target="installation-draft"
    shadow="never"
    class="installation-draft-card"
  >
    <template #header>
      <div class="draft-header">
        <div>
          <span class="eyebrow">AI 操作草稿</span>
          <h3>{{ draft.title }}</h3>
        </div>
        <el-tag type="warning" effect="plain">待核对</el-tag>
      </div>
    </template>

    <p class="draft-notice">
      以下内容只会填入当前表单，不会自动保存。请核对后再点击页面“保存”。
    </p>
    <dl>
      <div v-for="field in draft.fields" :key="field.key" class="draft-row">
        <dt>
          {{ field.label }}
          <el-tag size="small" effect="plain">{{ sourceLabel(field.source) }}</el-tag>
        </dt>
        <dd>
          <span class="current-value">当前：{{ currentValues[field.key] || '未填写' }}</span>
          <strong>草稿：{{ displayValue(field.value) }}</strong>
          <small>{{ field.hint }}</small>
        </dd>
      </div>
    </dl>

    <div class="draft-footer">
      <span v-if="!hasApplicableFields">暂无可自动填入项，请按提示手动完善。</span>
      <el-button
        v-else
        type="primary"
        plain
        @click="$emit('apply')"
      >
        应用可用建议到表单
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { formatDateTime } from '@/utils/datetime'
import { computed } from 'vue'
import type {
  AiFormDraft,
  AiFormDraftFieldSource,
} from '@/types/aiAssistant'

const props = defineProps<{
  draft: AiFormDraft
  currentValues: Record<string, string>
}>()

defineEmits<{
  apply: []
}>()

const hasApplicableFields = computed(() =>
  props.draft.fields.some(field => Boolean(field.value?.trim())),
)

function sourceLabel(source: AiFormDraftFieldSource) {
  return source === 'order' ? '订单信息' : '需手动填写'
}

function displayValue(value: string | null) {
  if (!value) return '等待手动填写'
  return formatDateTime(value)
}
</script>

<style scoped>
.installation-draft-card {
  margin-top: 16px;
  border-color: var(--el-color-warning-light-5);
  background: var(--ad-card);
  color: var(--ad-text);
}
.draft-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.eyebrow {
  color: var(--el-color-warning);
  font-size: 12px;
}
h3 {
  margin: 2px 0 0;
  font-size: 16px;
}
.draft-notice {
  margin: 0 0 12px;
  color: var(--ad-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}
dl {
  display: grid;
  gap: 10px;
  margin: 0;
}
.draft-row {
  display: grid;
  grid-template-columns: minmax(110px, 0.35fr) minmax(0, 1fr);
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid var(--ad-border);
}
dt {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
dd {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
  margin: 0;
}
dd strong {
  overflow-wrap: anywhere;
}
dd small,
.current-value,
.draft-footer span {
  color: var(--ad-text-secondary);
  font-size: 12px;
}
.draft-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
@media (max-width: 640px) {
  .draft-row {
    grid-template-columns: 1fr;
    gap: 5px;
  }
}
</style>
