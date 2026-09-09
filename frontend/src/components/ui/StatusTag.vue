<template>
  <span
    class="ui-status-tag"
    :class="[`ui-status-tag--${presentation.tone}`, `ui-status-tag--${size}`, { 'is-terminal': presentation.terminal }]"
    :data-status="presentation.code"
    :aria-label="presentation.label"
  >
    <span v-if="dot" class="ui-status-tag__dot" aria-hidden="true" />
    {{ presentation.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StatusView as ApiStatusView } from '@/types/api'
import { resolveStatusPresentation, type UiTone } from '@/utils/uiPresentation'

const props = withDefaults(defineProps<{
  status?: string | ApiStatusView | null
  label?: string | null
  tone?: UiTone
  terminal?: boolean
  size?: 'sm' | 'md'
  dot?: boolean
}>(), {
  status: 'unknown',
  label: '',
  tone: undefined,
  terminal: undefined,
  size: 'sm',
  dot: true,
})

const presentation = computed(() => resolveStatusPresentation(
  props.status,
  props.label,
  props.tone,
  props.terminal,
))
</script>

<style scoped>
.ui-status-tag {
  --ui-status-color: var(--ui-neutral);
  --ui-status-background: var(--ui-neutral-soft);
  --ui-status-border: var(--ui-neutral-border);
  display: inline-flex;
  align-items: center;
  gap: var(--ui-space-1);
  max-width: 100%;
  border: 1px solid var(--ui-status-border);
  border-radius: 999px;
  background: var(--ui-status-background);
  color: var(--ui-status-color);
  font-weight: var(--ui-font-weight-medium);
  line-height: 1;
  white-space: nowrap;
}

.ui-status-tag--sm {
  min-height: 24px;
  padding: 0 var(--ui-space-2);
  font-size: var(--ui-font-size-caption);
}

.ui-status-tag--md {
  min-height: 28px;
  padding: 0 var(--ui-space-3);
  font-size: var(--ui-font-size-base);
}

.ui-status-tag--brand,
.ui-status-tag--info {
  --ui-status-color: var(--ui-info);
  --ui-status-background: var(--ui-info-soft);
  --ui-status-border: var(--ui-info-border);
}

.ui-status-tag--success {
  --ui-status-color: var(--ui-success);
  --ui-status-background: var(--ui-success-soft);
  --ui-status-border: var(--ui-success-border);
}

.ui-status-tag--warning {
  --ui-status-color: var(--ui-warning);
  --ui-status-background: var(--ui-warning-soft);
  --ui-status-border: var(--ui-warning-border);
}

.ui-status-tag--danger {
  --ui-status-color: var(--ui-danger);
  --ui-status-background: var(--ui-danger-soft);
  --ui-status-border: var(--ui-danger-border);
}

.ui-status-tag__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
