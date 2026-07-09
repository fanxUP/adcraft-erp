<template>
  <Transition name="slide-down">
    <div v-if="hasUpdate" class="update-bar">
      <span class="update-icon">🔄</span>
      <span class="update-text">系统已更新，请刷新页面以加载最新版本</span>
      <button class="update-btn" @click="refreshPage">立即刷新</button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useVersionCheck } from '@/composables/useVersionCheck'

const { hasUpdate, refreshPage } = useVersionCheck()
</script>

<style scoped>
.update-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 24px;
  background: linear-gradient(135deg, #e6a23c, #d48806);
  color: #fff;
  font-size: 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

.update-icon {
  font-size: 18px;
  line-height: 1;
}

.update-text {
  flex: 1;
}

.update-btn {
  padding: 5px 16px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.update-btn:hover {
  background: rgba(255, 255, 255, 0.4);
}

/* Transition */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
