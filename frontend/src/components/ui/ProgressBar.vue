<template>
  <div class="ui-progress-bar" :class="`ui-progress-bar--${size}`">
    <div class="ui-progress-bar__meta">
      <span v-if="label" class="ui-progress-bar__label">{{ label }}</span>
      <span v-if="showValue" class="ui-progress-bar__value">{{ value }}%</span>
    </div>
    <div
      class="ui-progress-bar__track"
      role="progressbar"
      :aria-label="ariaLabel"
      :aria-valuemin="0"
      :aria-valuemax="100"
      :aria-valuenow="value"
      :aria-valuetext="`${value}%`"
    >
      <span
        class="ui-progress-bar__fill"
        :class="`ui-progress-bar__fill--${resolvedTone}`"
        :style="{ width: `${value}%` }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { normalizeProgress, progressTone, type UiTone } from '@/utils/uiPresentation'

const props = withDefaults(defineProps<{
  percentage?: number | null
  label?: string
  tone?: UiTone
  size?: 'sm' | 'md'
  showValue?: boolean
  ariaLabel?: string
}>(), {
  percentage: 0,
  label: '',
  tone: undefined,
  size: 'md',
  showValue: true,
  ariaLabel: '当前进度',
})

const value = computed(() => normalizeProgress(props.percentage))
const resolvedTone = computed(() => progressTone(props.tone, value.value))
</script>

<style scoped>
.ui-progress-bar {
  min-width: 120px;
}

.ui-progress-bar__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ui-space-2);
  margin-bottom: var(--ui-space-1);
  color: var(--ui-text-secondary);
  font-size: var(--ui-font-size-caption);
}

.ui-progress-bar__value {
  color: var(--ui-text);
  font-variant-numeric: tabular-nums;
  font-weight: var(--ui-font-weight-semibold);
}

.ui-progress-bar__track {
  overflow: hidden;
  width: 100%;
  border-radius: 999px;
  background: var(--ui-neutral-soft);
}

.ui-progress-bar--sm .ui-progress-bar__track {
  height: 6px;
}

.ui-progress-bar--md .ui-progress-bar__track {
  height: 8px;
}

.ui-progress-bar__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  transition: width var(--ui-duration-normal) var(--ui-ease-standard);
}

.ui-progress-bar__fill--brand,
.ui-progress-bar__fill--info {
  background: var(--ui-info);
}

.ui-progress-bar__fill--success {
  background: var(--ui-success);
}

.ui-progress-bar__fill--warning {
  background: var(--ui-warning);
}

.ui-progress-bar__fill--danger {
  background: var(--ui-danger);
}

.ui-progress-bar__fill--neutral {
  background: var(--ui-neutral);
}
</style>
