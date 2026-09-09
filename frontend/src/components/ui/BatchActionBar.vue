<template>
  <div
    v-if="alwaysVisible || selectedCount > 0"
    class="ui-batch-action-bar"
    role="region"
    aria-live="polite"
    aria-label="批量操作"
  >
    <div class="ui-batch-action-bar__summary">
      <strong>{{ selectedCount }}</strong>
      <span>条已选择</span>
      <span v-if="disabledCount > 0" class="ui-batch-action-bar__disabled">
        {{ disabledCount }} 条不可操作
      </span>
    </div>
    <div class="ui-batch-action-bar__actions">
      <slot name="actions" :selected-count="selectedCount" :busy="busy" />
      <button
        v-if="showClear"
        type="button"
        class="ui-batch-action-bar__clear"
        :disabled="busy"
        @click="emit('clear')"
      >
        清除选择
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  selectedCount?: number
  disabledCount?: number
  busy?: boolean
  alwaysVisible?: boolean
  showClear?: boolean
}>(), {
  selectedCount: 0,
  disabledCount: 0,
  busy: false,
  alwaysVisible: false,
  showClear: true,
})

const emit = defineEmits<{
  clear: []
}>()
</script>

<style scoped>
.ui-batch-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ui-space-4);
  min-height: 48px;
  margin-bottom: var(--ui-space-3);
  padding: var(--ui-space-2) var(--ui-space-3);
  border: 1px solid var(--ui-info-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-info-soft);
  color: var(--ui-text);
}

.ui-batch-action-bar__summary,
.ui-batch-action-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--ui-space-2);
}

.ui-batch-action-bar__summary strong {
  color: var(--ui-info);
  font-variant-numeric: tabular-nums;
}

.ui-batch-action-bar__disabled {
  color: var(--ui-warning);
  font-size: var(--ui-font-size-caption);
}

.ui-batch-action-bar__clear {
  min-height: 28px;
  padding: 0 var(--ui-space-2);
  border: 0;
  background: transparent;
  color: var(--ui-text-secondary);
  cursor: pointer;
  font: inherit;
}

.ui-batch-action-bar__clear:hover:not(:disabled) {
  color: var(--ui-text);
}

.ui-batch-action-bar__clear:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 640px) {
  .ui-batch-action-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .ui-batch-action-bar__actions {
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}
</style>
