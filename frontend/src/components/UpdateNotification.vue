<template>
  <Transition name="slide-down">
    <div v-if="hasUpdate" class="update-bar">
      <span class="update-icon">🔄</span>
      <span class="update-text">系统已更新，请刷新页面以加载最新版本</span>
      <button class="update-btn" @click="refreshPage">立即刷新</button>
      <button class="close-btn" @click="dismissUpdate">✕</button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useVersionCheck } from '@/composables/useVersionCheck'

const { hasUpdate, dismissUpdate, refreshPage } = useVersionCheck()
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
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-size: 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
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
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.update-btn:hover {
  background: rgba(255, 255, 255, 0.35);
}

.close-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
  line-height: 1;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
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
