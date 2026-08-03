<template>
  <div class="default-layout">
    <el-container>
      <el-aside :width="navigationCollapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo">
          <span v-if="!navigationCollapsed" class="logo-text">AdCraft ERP</span>
          <span v-else class="logo-short">A</span>
        </div>
        <div class="sidebar-menu-wrap">
        <AppSidebarMenu
          :active-path="route.path"
          :collapsed="navigationCollapsed"
          :roles="authStore.roles"
        />
        </div>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-button text @click="appStore.toggleSidebar()">
              <el-icon :size="20"><Fold v-if="!navigationCollapsed" /><Expand v-else /></el-icon>
            </el-button>
          </div>
          <div class="header-right">
            <el-dropdown @command="handleSmartTool">
              <el-button text>
                <el-icon :size="18"><MagicStick /></el-icon>
                <span v-if="!navigationCollapsed">智能工具</span>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="/ai/quotes">AI 报价助手</el-dropdown-item>
                  <el-dropdown-item command="/ai/knowledge">报价知识库</el-dropdown-item>
                  <el-dropdown-item command="/ai/site-photos">现场照片识别</el-dropdown-item>
                  <el-dropdown-item command="/ai/payment-ocr">收款截图识别</el-dropdown-item>
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
import AppSidebarMenu from '@/components/navigation/AppSidebarMenu.vue'
import { resolvePageContext } from '@/config/pageContext'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const chatStore = useChatStore()
const aiStore = useAiAssistantStore()

const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)
const narrowViewport = ref(false)
const navigationCollapsed = computed(() =>
  sidebarCollapsed.value || narrowViewport.value,
)

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
  background: var(--ad-dark);
}

.sidebar {
  background-color: var(--ad-darker);
  transition: width 0.3s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100vh;

  :deep(.el-menu) {
    --el-menu-bg-color: var(--ad-darker);
    --el-menu-text-color: var(--ad-text-secondary);
    --el-menu-active-color: var(--ad-red);
    --el-menu-hover-bg-color: var(--ad-card);
    border-right: none;

    .el-menu-item,
    .el-sub-menu__title {
      font-size: calc(var(--ad-font-size-base) + 1px);
      font-weight: 600;
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
  background: var(--ad-border);
  border-radius: 2px;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ad-red);
  font-size: calc(var(--ad-font-size-base) + 6px);
  font-weight: 700;
  border-bottom: 1px solid var(--ad-border);
}

.logo-short {
  font-size: calc(var(--ad-font-size-base) + 10px);
}

.header {
  background: var(--ad-darker);
  border-bottom: 1px solid var(--ad-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  color: var(--ad-text);
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
}
</style>

<style>
.el-menu--popup {
  --el-menu-bg-color: var(--ad-card) !important;
  --el-menu-text-color: var(--ad-text-secondary) !important;
  --el-menu-hover-bg-color: var(--ad-darker) !important;
  --el-menu-active-color: var(--ad-red) !important;
}
</style>
