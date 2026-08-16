<template>
  <div class="ai-chat-window">
    <!-- Welcome / suggested prompts when no messages -->
    <div v-if="!store.hasMessages" class="ai-chat-welcome">
      <div class="ai-welcome-glow" />
      <div class="ai-welcome-icon">
        <el-icon :size="32"><MagicStick /></el-icon>
      </div>
      <div class="ai-welcome-text">你好！我是 ERP AI 助手</div>
      <div class="ai-welcome-hint">
        <template v-if="store.pageContext.page_purpose">
          你正在使用“{{ store.pageContext.page_title }}”。<br>
          {{ store.pageContext.page_purpose }}
        </template>
        <template v-else>
          我可以帮你查询客户、订单、欠款信息，<br>生成报价草稿和安装任务草稿。
        </template>
      </div>
      <div class="ai-welcome-divider" />
      <AiSuggestedPrompts />
    </div>

    <!-- Message list when there are messages -->
    <AiMessageList v-else />
  </div>
</template>

<script setup lang="ts">
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import AiMessageList from './AiMessageList.vue'
import AiSuggestedPrompts from './AiSuggestedPrompts.vue'

const store = useAiAssistantStore()
</script>

<style scoped>
.ai-chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.ai-chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 20px;
  overflow-y: auto;
  position: relative;
}
.ai-welcome-glow {
  position: absolute;
  top: 10%;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(103, 194, 58, 0.06) 0%, transparent 70%);
  pointer-events: none;
}
.ai-welcome-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.12), rgba(103, 194, 58, 0.06));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-color-success);
  margin-bottom: 16px;
  box-shadow: 0 0 20px rgba(103, 194, 58, 0.1);
  position: relative;
}
.ai-welcome-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--ai-text, #e8e8f0);
  margin-bottom: 8px;
  letter-spacing: 0.3px;
}
.ai-welcome-hint {
  font-size: 13px;
  color: var(--ai-text-muted, #666688);
  text-align: center;
  line-height: 1.7;
  margin-bottom: 4px;
}
.ai-welcome-divider {
  width: 40px;
  height: 2px;
  border-radius: 1px;
  background: var(--ai-border, #2a2a4a);
  margin: 12px 0 4px;
}
</style>
