<template>
  <div class="mobile-layout">
    <!-- Page content area -->
    <div class="mobile-content">
      <router-view />
    </div>

    <!-- Bottom tab bar -->
    <div class="bottom-tabs" v-if="showTabs">
      <div
        v-for="tab in tabs"
        :key="tab.path"
        class="tab-item"
        :class="{ active: currentTab === tab.path }"
        @click="switchTab(tab.path)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tabs = [
  { path: '/mobile',          icon: '🏠', label: '首页' },
  { path: '/mobile/installation', icon: '📋', label: '任务' },
  { path: '/mobile/profile',  icon: '👤', label: '我的' },
]

const currentTab = computed(() => route.path)

/** Hide tabs on sub-pages (e.g. drawer isn't relevant) */
const showTabs = computed(() => {
  return tabs.some(t => route.path === t.path)
})

function switchTab(path: string) {
  if (route.path !== path) {
    router.push(path)
  }
}
</script>

<style scoped>
.mobile-layout {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: #0f0f1a;
  color: var(--ad-text, #e0e0e0);
  display: flex;
  flex-direction: column;
  position: relative;
}

.mobile-content {
  flex: 1;
  padding-bottom: 64px; /* space for bottom tabs */
}

/* Bottom Tab Bar */
.bottom-tabs {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  display: flex;
  background: #1a1a2e;
  border-top: 1px solid #2a2a3e;
  z-index: 100;
  padding: 6px 0 env(safe-area-inset-bottom, 6px) 0;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.3);
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 0;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.tab-item:active {
  opacity: 0.7;
}

.tab-icon {
  font-size: 22px;
  line-height: 1;
}

.tab-label {
  font-size: 11px;
  color: #888;
  font-weight: 500;
  transition: color 0.15s;
}

.tab-item.active .tab-label {
  color: var(--ad-red, #e63946);
}

.tab-item.active .tab-icon {
  transform: scale(1.05);
}

/* Safe area for notched devices */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .mobile-content {
    padding-bottom: calc(64px + env(safe-area-inset-bottom));
  }
}
</style>
