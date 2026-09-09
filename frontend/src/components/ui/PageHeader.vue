<template>
  <header class="ui-page-header">
    <div class="ui-page-header__main">
      <div v-if="eyebrow" class="ui-page-header__eyebrow">{{ eyebrow }}</div>
      <h1 class="ui-page-header__title">{{ title }}</h1>
      <p v-if="description" class="ui-page-header__description">{{ description }}</p>
    </div>
    <div v-if="$slots.meta || $slots.actions" class="ui-page-header__side">
      <div v-if="$slots.meta" class="ui-page-header__meta">
        <slot name="meta" />
      </div>
      <div v-if="$slots.actions" class="ui-page-header__actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  eyebrow?: string
}>()
</script>

<style scoped>
.ui-page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ui-space-5);
  margin-bottom: var(--ui-space-4);
}

.ui-page-header__main {
  min-width: 0;
}

.ui-page-header__eyebrow {
  margin-bottom: var(--ui-space-1);
  color: var(--ui-text-secondary);
  font-size: var(--ui-font-size-caption);
  font-weight: var(--ui-font-weight-semibold);
  letter-spacing: 0.04em;
}

.ui-page-header__title {
  margin: 0;
  color: var(--ui-text);
  font-size: var(--ui-font-size-title);
  font-weight: var(--ui-font-weight-bold);
  line-height: 1.35;
}

.ui-page-header__description {
  max-width: 720px;
  margin: var(--ui-space-2) 0 0;
  color: var(--ui-text-secondary);
  line-height: 1.6;
}

.ui-page-header__side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--ui-space-4);
  flex-shrink: 0;
}

.ui-page-header__meta,
.ui-page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--ui-space-2);
}

@media (max-width: 768px) {
  .ui-page-header {
    flex-direction: column;
    gap: var(--ui-space-3);
  }

  .ui-page-header__side {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }
}
</style>
