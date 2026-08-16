<template>
  <div class="ai-input-box">
    <div class="ai-input-row">
      <div class="ai-input-field">
        <el-input
          v-model="store.inputText"
          type="textarea"
          :rows="1"
          placeholder="输入消息，Enter 发送..."
          :disabled="store.loading"
          resize="none"
          class="ai-textarea"
          @keydown.enter.prevent="handleKeydown"
        />
      </div>
      <el-button
        type="primary"
        class="ai-send-btn"
        :disabled="!store.inputText.trim() || store.loading"
        :loading="store.loading"
        @click="doSend"
      >
        <el-icon :size="16"><ArrowRight /></el-icon>
      </el-button>
    </div>
    <div class="ai-input-hint">
      <span>Enter 发送 · Shift+Enter 换行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAiAssistantStore } from '@/stores/aiAssistantStore'

const store = useAiAssistantStore()

function handleKeydown(e: Event) {
  const ke = e as KeyboardEvent
  if (!ke.shiftKey) {
    e.preventDefault()
    doSend()
  }
}

function doSend() {
  const text = store.inputText.trim()
  if (!text || store.loading) return
  store.sendMessageStream(text)
}
</script>

<style scoped>
.ai-input-box {
  padding: 10px 14px 8px;
  background: #1a1a2e;
  border-top: 1px solid var(--ai-border, #2a2a4a);
}
.ai-input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.ai-input-field {
  flex: 1;
}
.ai-textarea :deep(.el-textarea__inner) {
  background: #252548;
  border-color: #3a3a5a;
  color: #f0f0f8;
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 13px;
  line-height: 1.5;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.ai-textarea :deep(.el-textarea__inner:focus) {
  border-color: var(--el-color-danger);
  box-shadow: 0 0 0 2px rgba(245,108,108,0.12);
}
.ai-textarea :deep(.el-textarea__inner::placeholder) {
  color: #6a6a8a;
}
.ai-send-btn {
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 10px;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--el-color-danger) 0%, #d03050 100%);
  border: none;
}
.ai-send-btn:hover {
  background: linear-gradient(135deg, var(--el-color-danger) 0%, #c02840 100%);
  box-shadow: 0 2px 8px rgba(245,108,108,0.25);
}
.ai-send-btn:disabled {
  background: #252548;
  border: 1px solid #3a3a5a;
}
.ai-input-hint {
  display: flex;
  justify-content: flex-end;
  margin-top: 5px;
  font-size: 11px;
  color: #6a6a8a;
}
</style>
