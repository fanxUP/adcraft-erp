<template>
  <section class="workflow-checklist" aria-label="AI任务清单">
    <header>
      <span>{{ checklist.title }}</span>
      <strong>{{ checklist.completed_items }}/{{ checklist.total_items }}</strong>
    </header>

    <ol>
      <li
        v-for="item in checklist.items"
        :key="item.key"
        :class="`is-${item.state}`"
      >
        <el-icon aria-hidden="true">
          <CircleCheckFilled v-if="item.state === 'completed'" />
          <Clock v-else />
        </el-icon>
        <span class="item-copy">
          <strong>{{ item.label }}</strong>
          <small>{{ item.detail }}</small>
        </span>
        <button
          v-if="item.action"
          type="button"
          @click="$emit('action', item.action)"
        >
          处理
        </button>
      </li>
    </ol>

    <button
      v-if="checklist.draft_action"
      type="button"
      class="draft-action"
      @click="$emit('action', checklist.draft_action)"
    >
      <el-icon><Document /></el-icon>
      {{ checklist.draft_action.label }}
      <el-icon><Right /></el-icon>
    </button>
  </section>
</template>

<script setup lang="ts">
import type {
  AiWorkflowAction,
  AiWorkflowChecklist,
} from '@/types/aiAssistant'

defineProps<{
  checklist: AiWorkflowChecklist
}>()

defineEmits<{
  action: [action: AiWorkflowAction]
}>()
</script>

<style scoped>
.workflow-checklist {
  display: grid;
  gap: 7px;
  margin-top: 10px;
  padding: 9px;
  border: 1px solid var(--ai-border, #2a2a4a);
  border-radius: 6px;
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--ai-text-secondary, #8888aa);
  font-size: 11px;
}
header strong {
  color: var(--ai-text, #e8e8f0);
  font-variant-numeric: tabular-nums;
}
ol {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
li {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) auto;
  align-items: start;
  gap: 6px;
  color: var(--el-color-warning);
}
li.is-completed {
  color: var(--el-color-success);
}
.item-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.item-copy strong {
  color: var(--ai-text, #e8e8f0);
  font-size: 11px;
  line-height: 1.4;
}
.item-copy small {
  color: var(--ai-text-muted, #666688);
  font-size: 10px;
  line-height: 1.4;
}
li button,
.draft-action {
  border: 0;
  background: transparent;
  color: var(--ai-accent, #f56c6c);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}
li button {
  padding: 0;
  font-size: 10px;
}
.draft-action {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
  font-size: 11px;
}
button:hover,
button:focus-visible {
  text-decoration: underline;
}
button:focus-visible {
  border-radius: 2px;
  outline: 2px solid var(--ai-accent, #f56c6c);
  outline-offset: 2px;
}
</style>
