<template>
  <div class="default-layout">
    <el-container>
      <el-aside :width="navigationCollapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo" :title="brandingStore.appName">
          <BrandLogo :size="32" />
          <span v-if="!navigationCollapsed" class="logo-text">{{ brandingStore.appName }}</span>
        </div>
        <div class="sidebar-menu-wrap">
          <AppSidebarMenu
            :active-path="route.path"
            :collapsed="navigationCollapsed"
            :roles="authStore.roles"
            :permissions="authStore.permissions"
          />
        </div>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-button text aria-label="切换侧栏" @click="appStore.toggleSidebar()">
              <el-icon :size="20"><Fold v-if="!navigationCollapsed" /><Expand v-else /></el-icon>
            </el-button>
            <span class="header-page-title">{{ currentPageTitle }}</span>
          </div>
          <div class="header-right">
            <el-dropdown v-if="smartTools.length" @command="handleSmartTool">
              <el-button text>
                <el-icon :size="18"><MagicStick /></el-icon>
                <span v-if="!narrowViewport">智能工具</span>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="tool in smartTools"
                    :key="tool.path"
                    :command="tool.path"
                  >
                    {{ tool.label }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-badge :value="chatStore.totalUnreadCount" :hidden="chatStore.totalUnreadCount === 0" :max="99">
              <el-button text @click="router.push('/chat')">
                <el-icon :size="20"><ChatDotRound /></el-icon>
              </el-button>
            </el-badge>
            <NotificationBell />
            <el-dropdown>
              <span class="user-info">
                {{ authStore.user?.real_name || authStore.user?.username }}
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
                  <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>

    <!-- AI Assistant -->
    <AiAssistantButton />
    <AiAssistantDrawer />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useChatStore } from '@/stores/chat'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import NotificationBell from '@/components/NotificationBell.vue'
import AiAssistantButton from '@/components/ai-assistant/AiAssistantButton.vue'
import AiAssistantDrawer from '@/components/ai-assistant/AiAssistantDrawer.vue'
import BrandLogo from '@/components/BrandLogo.vue'
import AppSidebarMenu from '@/components/navigation/AppSidebarMenu.vue'
import { filterSmartTools, getRouteTitle } from '@/config/access'
import { resolvePageContext } from '@/config/pageContext'
import { useBrandingStore } from '@/stores/branding'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const chatStore = useChatStore()
const aiStore = useAiAssistantStore()
const brandingStore = useBrandingStore()

const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)
const narrowViewport = ref(false)
const navigationCollapsed = computed(() =>
  sidebarCollapsed.value || narrowViewport.value,
)
const currentPageTitle = computed(() => getRouteTitle(route.name))
const smartTools = computed(() => filterSmartTools(authStore.roles, authStore.permissions))

function updateViewportState() {
  narrowViewport.value = window.innerWidth <= 600
}

// Keep the AI assistant scoped to the current business page.
watch(
  () => [route.name, route.params] as const,
  ([name, params]) => {
    aiStore.resetPageContext(
      resolvePageContext(String(name || ''), params as Record<string, string | string[]>),
    )
  },
  { immediate: true },
)

watch(
  () => authStore.user?.id,
  userId => {
    if (userId) aiStore.restorePageActionGuide(userId)
  },
  { immediate: true },
)

function handleLogout() {
  chatStore.disconnectWebSocket()
  authStore.logout()
}

function handleSmartTool(path: string) {
  router.push(path)
}

onMounted(() => {
  updateViewportState()
  window.addEventListener('resize', updateViewportState)
  if (authStore.token) {
    chatStore.connectWebSocket(authStore.token)
    chatStore.fetchConversations()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', updateViewportState)
  chatStore.disconnectWebSocket()
})
</script>

<style scoped>
.default-layout {
  min-height: 100vh;
  background: var(--ui-bg);
}

.sidebar {
  background-color: var(--ui-surface-subtle);
  border-right: 1px solid var(--ui-border);
  transition: width var(--ui-duration-normal) var(--ui-ease-standard);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100vh;

  :deep(.el-menu) {
    --el-menu-bg-color: var(--ui-surface-subtle);
    --el-menu-text-color: var(--ui-text-secondary);
    --el-menu-active-color: var(--ui-brand);
    --el-menu-hover-bg-color: var(--ui-surface);
    border-right: none;

    .el-menu-item,
    .el-sub-menu__title {
      font-size: calc(var(--ad-font-size-base) + 1px);
      font-weight: 600;
    }

    .el-menu-item.is-active {
      background: var(--ui-brand-soft);
      position: relative;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 18px;
        border-radius: 0 2px 2px 0;
        background: var(--ui-brand);
      }
    }
  }
}

.sidebar-menu-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu-wrap::-webkit-scrollbar {
  width: 4px;
}
.sidebar-menu-wrap::-webkit-scrollbar-track {
  background: transparent;
}
.sidebar-menu-wrap::-webkit-scrollbar-thumb {
  background: var(--ui-border);
  border-radius: 2px;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  color: var(--ui-text);
  font-weight: 700;
  border-bottom: 1px solid var(--ui-border);
}

.logo-text {
  font-size: calc(var(--ad-font-size-base) + 2px);
  white-space: nowrap;
  overflow: hidden;
}

.header {
  background: var(--ui-surface-subtle);
  border-bottom: 1px solid var(--ui-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--ui-space-2);
  min-width: 0;
}

.header-page-title {
  overflow: hidden;
  color: var(--ui-text);
  font-size: var(--ui-font-size-base);
  font-weight: var(--ui-font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  color: var(--ui-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

@media (max-width: 600px) {
  .header {
    padding: 0 8px;
  }

  .header-right {
    gap: 4px;
  }
}

.main-content {
  padding: 20px;
  min-height: calc(100vh - 60px);
  background: var(--ui-bg);
}
</style>

<style>
.el-menu--popup {
  --el-menu-bg-color: var(--ui-surface) !important;
  --el-menu-text-color: var(--ui-text-secondary) !important;
  --el-menu-hover-bg-color: var(--ui-surface-subtle) !important;
  --el-menu-active-color: var(--ui-brand) !important;
}
</style>
