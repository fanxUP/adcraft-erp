<template>
  <div v-if="hasContext" class="ai-context-bar">
    <div class="ai-context-dot" />
    <el-icon :size="13"><InfoFilled /></el-icon>
    <span class="ai-context-text">{{ contextText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'

const store = useAiAssistantStore()

const hasContext = computed(() => {
  const ctx = store.pageContext
  return !!(ctx.page || ctx.customer_name || ctx.order_no || ctx.quote_no || ctx.business_type)
})

const contextText = computed(() => {
  const ctx = store.pageContext
  const parts: string[] = []
  if (ctx.page_title) parts.push(ctx.page_title)
  else if (ctx.page) parts.push(ctx.page)
  if (ctx.customer_name) parts.push(`客户: ${ctx.customer_name}`)
  if (ctx.order_no) parts.push(`订单: ${ctx.order_no}`)
  if (ctx.quote_no) parts.push(`报价: ${ctx.quote_no}`)
  if (ctx.project_name) parts.push(`项目: ${ctx.project_name}`)
  return parts.join(' · ') || '当前页面'
})
</script>

<style scoped>
.ai-context-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  background: linear-gradient(90deg, rgba(245,108,108,0.06), rgba(245,108,108,0.02));
  border-bottom: 1px solid var(--ai-border, #2a2a4a);
  font-size: 12px;
  color: var(--ai-text-secondary, #8888aa);
  flex-shrink: 0;
}
.ai-context-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ai-accent, #f56c6c);
  flex-shrink: 0;
}
.ai-context-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
