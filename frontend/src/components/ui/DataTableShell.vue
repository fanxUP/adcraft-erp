<template>
  <section class="ui-data-table-shell" :aria-label="ariaLabel">
    <div v-if="state !== 'ready'" class="ui-data-table-shell__state">
      <slot :name="state">
        <StatePanel :state="state" />
      </slot>
    </div>
    <div v-else class="ui-data-table-shell__table">
      <slot />
    </div>
    <div v-if="$slots.footer" class="ui-data-table-shell__footer">
      <slot name="footer" />
    </div>
  </section>
</template>

<script setup lang="ts">
import StatePanel, { type UiState } from './StatePanel.vue'

withDefaults(defineProps<{
  state?: UiState | 'ready'
  ariaLabel?: string
}>(), {
  state: 'ready',
  ariaLabel: '数据列表',
})
</script>

<style scoped>
.ui-data-table-shell {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface);
  box-shadow: var(--ui-shadow-sm);
}

.ui-data-table-shell__table {
  min-width: 0;
  overflow-x: auto;
}

.ui-data-table-shell__state {
  min-height: 180px;
}

.ui-data-table-shell__footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--ui-space-3) var(--ui-space-4);
  border-top: 1px solid var(--ui-border);
}
</style>
