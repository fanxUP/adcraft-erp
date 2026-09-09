<template>
  <section
    class="ui-state-panel"
    :class="`ui-state-panel--${state}`"
    :aria-busy="state === 'loading'"
    aria-live="polite"
  >
    <div class="ui-state-panel__icon" aria-hidden="true">
      <slot name="icon">{{ stateContent.icon }}</slot>
    </div>
    <h3 class="ui-state-panel__title">{{ title || stateContent.title }}</h3>
    <p v-if="description || stateContent.description" class="ui-state-panel__description">
      {{ description || stateContent.description }}
    </p>
    <div v-if="$slots.actions || actionLabel" class="ui-state-panel__actions">
      <slot name="actions">
        <button v-if="actionLabel" type="button" class="ui-state-panel__action" @click="emit('action')">
          {{ actionLabel }}
        </button>
      </slot>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type UiState = 'loading' | 'empty' | 'error' | 'permission' | 'conflict'

const props = withDefaults(defineProps<{
  state?: UiState
  title?: string
  description?: string
  actionLabel?: string
}>(), {
  state: 'empty',
  title: '',
  description: '',
  actionLabel: '',
})

const emit = defineEmits<{
  action: []
}>()

const stateContent = computed(() => ({
  loading: { icon: '…', title: '正在加载', description: '请稍候，数据加载完成后会自动显示。' },
  empty: { icon: '○', title: '暂无数据', description: '当前条件下暂时没有可展示的内容。' },
  error: { icon: '!', title: '加载失败', description: '数据没有成功加载，请稍后重试。' },
  permission: { icon: '⊘', title: '暂无权限', description: '你没有访问或操作该内容的权限。' },
  conflict: { icon: '↻', title: '内容已变化', description: '页面数据已经更新，请刷新后再继续操作。' },
}[props.state]))
</script>

<style scoped>
.ui-state-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 180px;
  padding: var(--ui-space-7) var(--ui-space-5);
  color: var(--ui-text-secondary);
  text-align: center;
}

.ui-state-panel__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: var(--ui-space-3);
  border-radius: 50%;
  background: var(--ui-neutral-soft);
  color: var(--ui-neutral);
  font-size: 22px;
  font-weight: var(--ui-font-weight-semibold);
}

.ui-state-panel--loading .ui-state-panel__icon {
  animation: ui-state-pulse 1.2s var(--ui-ease-standard) infinite;
}

.ui-state-panel--error .ui-state-panel__icon,
.ui-state-panel--conflict .ui-state-panel__icon {
  background: var(--ui-warning-soft);
  color: var(--ui-warning);
}

.ui-state-panel--permission .ui-state-panel__icon {
  background: var(--ui-danger-soft);
  color: var(--ui-danger);
}

.ui-state-panel__title {
  margin: 0;
  color: var(--ui-text);
  font-size: 16px;
  font-weight: var(--ui-font-weight-semibold);
}

.ui-state-panel__description {
  max-width: 480px;
  margin: var(--ui-space-2) 0 0;
  line-height: 1.6;
}

.ui-state-panel__actions {
  margin-top: var(--ui-space-4);
}

.ui-state-panel__action {
  min-height: var(--ui-control-height);
  padding: 0 var(--ui-space-4);
  border: 1px solid var(--ui-brand);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-brand);
  color: var(--ui-on-brand);
  cursor: pointer;
  font: inherit;
  font-weight: var(--ui-font-weight-medium);
}

.ui-state-panel__action:hover {
  background: var(--ui-brand-hover);
}

@keyframes ui-state-pulse {
  0%,
  100% { opacity: 0.55; }
  50% { opacity: 1; }
}
</style>
