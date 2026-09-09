<template>
  <div class="ui-page-shell" :class="{ 'ui-page-shell--compact': compact, 'ui-page-shell--flush': flush }">
    <slot name="header" />
    <slot name="toolbar" />
    <div class="ui-page-shell__content">
      <slot />
    </div>
    <slot name="footer" />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  compact?: boolean
  flush?: boolean
}>(), {
  compact: false,
  flush: false,
})
</script>

<style scoped>
.ui-page-shell {
  width: 100%;
  max-width: var(--ui-page-max-width);
  margin: 0 auto;
  padding: var(--ui-space-5);
  box-sizing: border-box;
}

.ui-page-shell--compact {
  padding: var(--ui-space-4);
}

.ui-page-shell--flush {
  padding-left: 0;
  padding-right: 0;
}

.ui-page-shell__content {
  min-width: 0;
}

@media (max-width: 768px) {
  .ui-page-shell,
  .ui-page-shell--compact {
    padding: var(--ui-space-4) var(--ui-space-3);
  }
}
</style>
