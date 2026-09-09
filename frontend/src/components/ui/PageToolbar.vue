<template>
  <div class="ui-page-toolbar" role="toolbar" :aria-label="ariaLabel">
    <div class="ui-page-toolbar__main">
      <div class="ui-page-toolbar__filters">
        <slot />
      </div>
      <div v-if="$slots.actions" class="ui-page-toolbar__actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  ariaLabel?: string
}>(), {
  ariaLabel: '页面工具栏',
})
</script>

<style scoped>
.ui-page-toolbar {
  margin-bottom: var(--ui-space-4);
  padding: var(--ui-space-3) var(--ui-space-4);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface);
  box-shadow: var(--ui-shadow-sm);
}

.ui-page-toolbar__main,
.ui-page-toolbar__filters,
.ui-page-toolbar__actions {
  display: flex;
  align-items: center;
  gap: var(--ui-space-2);
}

.ui-page-toolbar__main {
  justify-content: space-between;
  gap: var(--ui-space-4);
}

.ui-page-toolbar__filters {
  min-width: 0;
  flex: 1;
  flex-wrap: wrap;
}

.ui-page-toolbar__actions {
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .ui-page-toolbar__main {
    align-items: stretch;
    flex-direction: column;
  }

  .ui-page-toolbar__actions {
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}
</style>
