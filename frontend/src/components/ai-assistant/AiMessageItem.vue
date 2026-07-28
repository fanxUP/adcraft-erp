<template>
  <div class="ai-message" :class="[`role-${msg.role}`]">
    <!-- User message: right-aligned bubble -->
    <div v-if="msg.role === 'user'" class="ai-msg-user">
      <div class="ai-msg-bubble ai-bubble-user">
        <div class="ai-msg-content">{{ msg.content }}</div>
      </div>
      <div class="ai-msg-avatar ai-avatar-user">
        <el-icon :size="15"><UserFilled /></el-icon>
      </div>
    </div>

    <!-- Assistant message: left-aligned with avatar -->
    <div v-else-if="msg.role === 'assistant'" class="ai-msg-assistant">
      <div class="ai-msg-avatar ai-avatar-ai">
        <el-icon :size="15"><MagicStick /></el-icon>
      </div>
      <div class="ai-msg-body">
        <div class="ai-msg-bubble ai-bubble-assistant">
          <div class="ai-msg-content markdown-body" v-html="renderedContent" />
        </div>
        <!-- Tool results inline -->
        <div v-if="hasToolResults" class="ai-msg-tools">
          <AiToolResultCard
            v-for="(tr, idx) in toolResults"
            :key="idx"
            :data="tr"
          />
        </div>
      </div>
    </div>

    <!-- Tool message: minimized inline -->
    <div v-else-if="msg.role === 'tool'" class="ai-msg-tool-row">
      <AiToolResultCard :data="parseToolResult" />
    </div>

    <!-- System/error message: centered -->
    <div v-else class="ai-msg-system">
      <div class="ai-system-inner" :class="systemClass">
        <el-icon :size="13"><WarningFilled v-if="isError" /><InfoFilled v-else /></el-icon>
        <span>{{ msg.content }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import AiToolResultCard from './AiToolResultCard.vue'
import type { AiMessage, AiToolCallResult } from '@/types/aiAssistant'

const props = defineProps<{
  msg: AiMessage
}>()

const store = useAiAssistantStore()

const toolResults = computed(() => store.toolResults)

const hasToolResults = computed(() => toolResults.value.length > 0)

const isError = computed(() => {
  const c = props.msg.content || ''
  return c.includes('错误') || c.includes('失败') || c.includes('抱歉')
})

const systemClass = computed(() => isError.value ? 'is-error' : 'is-info')

const parseToolResult = computed((): AiToolCallResult => {
  try {
    const parsed = props.msg.content ? JSON.parse(props.msg.content) : {}
    return parsed as AiToolCallResult
  } catch {
    return {
      status: 'info',
      result: null,
      error_message: props.msg.content,
    }
  }
})

// Simple markdown-like rendering (no external dep)
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderMarkdown(text: string | null): string {
  if (!text) return ''
  let html = escapeHtml(text)
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // Inline code
  html = html.replace(/`(.+?)`/g, '<code>$1</code>')
  // Lists: - item
  html = html.replace(/^- (.+)$/gm, '• $1')
  // Newlines
  html = html.replace(/\n/g, '<br>')
  return html
}

const renderedContent = computed(() => renderMarkdown(props.msg.content))
</script>

<style scoped>
.ai-message {
  padding: 3px 18px;
  animation: msgFadeIn 0.2s ease;
}
@keyframes msgFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Avatar ── */
.ai-msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 4px;
}
.ai-avatar-user {
  background: linear-gradient(135deg, #f56c6c, #d03050);
  color: #fff;
  box-shadow: 0 2px 6px rgba(245,108,108,0.25);
  margin-left: 8px;
}
.ai-avatar-ai {
  background: linear-gradient(135deg, #67c23a, #4a9e2d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(103,194,58,0.25);
}

/* ── User message ── */
.ai-msg-user {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  margin-bottom: 6px;
}
.ai-bubble-user {
  background: linear-gradient(135deg, #f56c6c, #d03050);
  color: #fff;
  border-radius: 14px 4px 14px 14px;
  box-shadow: 0 2px 8px rgba(245,108,108,0.15);
}
.ai-bubble-user .ai-msg-content {
  color: #fff;
}

/* ── Assistant message ── */
.ai-msg-assistant {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  align-items: flex-start;
}
.ai-msg-body {
  flex: 1;
  min-width: 0;
}
.ai-bubble-assistant {
  background: var(--ai-surface, #1c1c34);
  color: var(--ai-text, #e8e8f0);
  border-radius: 4px 14px 14px 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
  border: 1px solid rgba(255,255,255,0.04);
}

/* ── Bubble base ── */
.ai-msg-bubble {
  padding: 10px 14px;
  display: inline-block;
  max-width: 100%;
  word-wrap: break-word;
}
.ai-msg-content {
  font-size: 13px;
  line-height: 1.65;
}
.markdown-body :deep(code) {
  background: rgba(0,0,0,0.3);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  color: #e6a23c;
}
.markdown-body :deep(strong) {
  font-weight: 600;
  color: var(--ai-text);
}
.markdown-body :deep(em) {
  font-style: italic;
}

/* ── Tool results ── */
.ai-msg-tools {
  margin-top: 6px;
}

/* ── Tool role message ── */
.ai-msg-tool-row {
  padding-left: 38px;
  margin-bottom: 4px;
}

/* ── System ── */
.ai-msg-system {
  padding: 4px 0;
  display: flex;
  justify-content: center;
}
.ai-system-inner {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  max-width: 90%;
}
.ai-system-inner.is-info {
  background: rgba(144,147,153,0.08);
  color: var(--ai-text-muted, #666688);
}
.ai-system-inner.is-error {
  background: rgba(245,108,108,0.08);
  color: var(--ai-accent, #f56c6c);
}
</style>
