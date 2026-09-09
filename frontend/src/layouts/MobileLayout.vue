<template>
  <div class="mobile-layout">
    <!-- Page content area -->
    <div class="mobile-content" :class="{ 'has-bottom-tabs': showTabs }">
      <router-view />
    </div>

    <!-- Bottom tab bar -->
    <nav v-if="showTabs" class="bottom-tabs" aria-label="移动端主导航">
      <button
        v-for="tab in tabs"
        :key="tab.path"
        type="button"
        class="tab-item"
        :class="{ active: currentTab === tab.path }"
        :aria-current="currentTab === tab.path ? 'page' : undefined"
        :aria-label="`前往${tab.label}`"
        @click="switchTab(tab.path)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

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
  background: var(--ui-bg);
  color: var(--ui-text);
  display: flex;
  flex-direction: column;
  position: relative;
}

.mobile-content {
  flex: 1;
}

.mobile-content.has-bottom-tabs {
  padding-bottom: 64px;
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
  background: var(--ui-surface-subtle);
  border-top: 1px solid var(--ui-border);
  z-index: 100;
  padding: 6px 0 env(safe-area-inset-bottom, 6px) 0;
  box-shadow: 0 -2px 12px rgb(15 23 42 / 18%);
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
  outline: none;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
}

.tab-item:active {
  opacity: 0.7;
}

.tab-item:focus-visible {
  box-shadow: var(--ui-focus-ring);
}

.tab-icon {
  font-size: 22px;
  line-height: 1;
}

.tab-label {
  font-size: 11px;
  color: var(--ui-text-muted);
  font-weight: 500;
  transition: color 0.15s;
}

.tab-item.active .tab-label {
  color: var(--ui-brand);
}

.tab-item.active .tab-icon {
  transform: scale(1.05);
}

/* Safe area for notched devices */
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .mobile-content.has-bottom-tabs {
    padding-bottom: calc(64px + env(safe-area-inset-bottom));
  }
}
</style>
