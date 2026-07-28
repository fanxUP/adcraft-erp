<template>
  <div class="ai-suggested">
    <div class="ai-suggested-title">快速操作</div>
    <div class="ai-suggested-grid">
      <TransitionGroup name="chip">
        <div
          v-for="(item, idx) in prompts"
          :key="idx"
          class="ai-suggested-chip"
          :style="{ transitionDelay: `${idx * 0.05}s` }"
          @click="handleClick(item.prompt)"
        >
          <span class="ai-chip-text">{{ item.label }}</span>
        </div>
      </TransitionGroup>
    </div>
    <div v-if="prompts.length === 0" class="ai-suggested-empty">
      <el-icon :size="28"><ChatDotRound /></el-icon>
      <span>在当前页面发送消息开始对话</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { PAGE_QUICK_ACTIONS } from '@/types/aiAssistant'

const store = useAiAssistantStore()

const prompts = computed(() => {
  const page = store.pageContext.page || ''
  return PAGE_QUICK_ACTIONS[page] || PAGE_QUICK_ACTIONS[''] || []
})

function handleClick(prompt: string) {
  store.inputText = prompt
  store.sendMessageStream(prompt)
}
</script>

<style scoped>
.ai-suggested {
  width: 100%;
  padding: 12px 8px;
}
.ai-suggested-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ai-text-secondary, #8888aa);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.ai-suggested-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ai-suggested-chip {
  padding: 7px 16px;
  border-radius: 18px;
  border: 1px solid var(--ai-border, #2a2a4a);
  cursor: pointer;
  font-size: 13px;
  color: var(--ai-text, #e8e8f0);
  transition: all 0.2s ease;
  white-space: nowrap;
  background: rgba(255,255,255,0.02);
  user-select: none;
}
.ai-suggested-chip:hover {
  border-color: var(--ai-accent, #f56c6c);
  color: var(--ai-accent, #f56c6c);
  background: var(--ai-accent-bg, rgba(245, 108, 108, 0.08));
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(245, 108, 108, 0.08);
}
.ai-suggested-chip:active {
  transform: translateY(0);
}
.ai-suggested-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 0;
  color: var(--ai-text-muted, #666688);
  font-size: 13px;
}

.chip-enter-active {
  transition: all 0.3s ease;
}
.chip-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
</style>
