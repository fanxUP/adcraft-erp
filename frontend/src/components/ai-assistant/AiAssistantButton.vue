<template>
  <div class="ai-float-btn" @click="store.toggleDrawer()" :class="{ 'is-active': store.visible }">
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="ai-badge">
      <div class="ai-btn-inner">
        <el-icon :size="24">
          <ChatDotRound v-if="!store.visible" />
          <Close v-else />
        </el-icon>
      </div>
    </el-badge>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'

const store = useAiAssistantStore()
const unreadCount = computed(() => 0)
</script>

<style scoped>
.ai-float-btn {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 2002;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.ai-float-btn:hover {
  transform: scale(1.12) rotate(-5deg);
}
.ai-float-btn.is-active {
  transform: scale(1.05);
}
.ai-btn-inner {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f56c6c 0%, #e04040 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 20px rgba(245, 108, 108, 0.45),
              0 0 0 1px rgba(245, 108, 108, 0.15);
  transition: all 0.3s ease;
}
.ai-float-btn:hover .ai-btn-inner {
  box-shadow: 0 6px 28px rgba(245, 108, 108, 0.55),
              0 0 0 2px rgba(245, 108, 108, 0.2);
}
.ai-float-btn.is-active .ai-btn-inner {
  background: linear-gradient(135deg, #555 0%, #444 100%);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
  transform: rotate(90deg);
}
.ai-badge :deep(.el-badge__content) {
  border: 2px solid var(--ad-card, #1e1e30);
  background: #f56c6c;
}
</style>
