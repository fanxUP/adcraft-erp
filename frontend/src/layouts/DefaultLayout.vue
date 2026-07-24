<template>
  <div class="default-layout">
    <el-container>
      <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo">
          <span v-if="!sidebarCollapsed" class="logo-text">AdCraft ERP</span>
          <span v-else class="logo-short">A</span>
        </div>
        <div class="sidebar-menu-wrap">
        <el-menu
          :default-active="route.path"
          router
          :collapse="sidebarCollapsed"
        >
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>首页驾驶舱</span>
          </el-menu-item>
          <el-menu-item index="/notifications">
            <el-icon><Bell /></el-icon>
            <span>消息中心</span>
          </el-menu-item>
          <el-menu-item index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <span>即时通讯</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/customers">
            <el-icon><User /></el-icon>
            <span>客户管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/quotes">
            <el-icon><Document /></el-icon>
            <span>报价管理</span>
          </el-menu-item>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/contracts-group">
            <template #title>
              <el-icon><DocumentChecked /></el-icon>
              <span>合同管理</span>
            </template>
            <el-menu-item index="/contracts">常规合同</el-menu-item>
            <el-menu-item index="/framework-contracts">框架合同</el-menu-item>
          </el-sub-menu>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/orders">
            <el-icon><Tickets /></el-icon>
            <span>订单管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/acceptances">
            <el-icon><Stamp /></el-icon>
            <span>验收管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'designer', 'production'])" index="/products">
            <el-icon><Goods /></el-icon>
            <span>产品管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'designer', 'production'])" index="/material-process">
            <el-icon><Box /></el-icon>
            <span>材质工艺</span>
          </el-menu-item>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'production'])" index="/outsource">
            <template #title>
              <el-icon><Connection /></el-icon>
              <span>外协管理</span>
            </template>
            <el-menu-item index="/outsource/vendors">外协商</el-menu-item>
            <el-menu-item index="/outsource/tasks">外协任务</el-menu-item>
            <el-menu-item index="/outsource/payments">外协付款</el-menu-item>
          </el-sub-menu>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production'])" index="/inventory">
            <el-icon><Box /></el-icon>
            <span>库存管理</span>
          </el-menu-item>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'designer', 'production', 'installer'])" index="/tasks">
            <template #title>
              <el-icon><List /></el-icon>
              <span>任务管理</span>
            </template>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'designer'])" index="/design-tasks">设计任务</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production'])" index="/production-tasks">制作任务</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production'])" index="/production-tasks/board">制作看板</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'installer'])" index="/installation-tasks">安装任务</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'finance'])" index="/finance">
            <template #title>
              <el-icon><Money /></el-icon>
              <span>财务管理</span>
            </template>
            <el-menu-item index="/receivables">应收管理</el-menu-item>
            <el-menu-item index="/expenses">支出管理</el-menu-item>
            <el-menu-item index="/project-costs">项目成本</el-menu-item>
            <el-menu-item index="/cost-debts">成本欠款</el-menu-item>
            <el-menu-item index="/statements">对账单</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="/vehicles-group">
            <template #title>
              <el-icon><Van /></el-icon>
              <span>车辆管理</span>
            </template>
            <el-menu-item index="/vehicle-dashboard">车辆看板</el-menu-item>
            <el-menu-item index="/vehicle-use-requests">用车申请</el-menu-item>
            <el-menu-item index="/vehicle-agent-drafts">消息识别</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production', 'installer'])" index="/vehicle-dispatches">派车管理</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production', 'installer'])" index="/vehicle-trip-records">出车收车台账</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production', 'installer', 'finance'])" index="/vehicle-expenses">车辆费用</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance'])" index="/vehicle-insurance">保险年检</el-menu-item>
            <el-menu-item index="/vehicle-incidents">违章事故</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance', 'production'])" index="/vehicle-reports">车辆报表</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production', 'installer'])" index="/vehicles">车辆档案</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production', 'installer'])" index="/vehicle-drivers">司机管理</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="/aerial-group">
            <template #title>
              <el-icon><Platform /></el-icon>
              <span>高空作业车</span>
            </template>
            <el-menu-item index="/aerial-dashboard">高空车看板</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance', 'production'])" index="/aerial-agent-drafts">Agent草稿</el-menu-item>
            <el-menu-item index="/aerial-ledgers">出车台账</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance', 'production'])" index="/aerial-personnel-expenses">垫付/报销</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance'])" index="/aerial-personnel-wages">人员工资</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance', 'production'])" index="/aerial-vehicle-costs">车辆费用</el-menu-item>
            <el-menu-item index="/aerial-safety-checks">安全检查</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'finance', 'production'])" index="/aerial-reports">统计报表</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production'])" index="/aerial-vehicles">高空车档案</el-menu-item>
            <el-menu-item v-if="authStore.hasAnyRole(['admin', 'production'])" index="/aerial-personnel">人员管理</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'sales', 'finance'])" index="/reports">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>报表中心</span>
            </template>
            <el-menu-item index="/reports/daily">销售日报</el-menu-item>
            <el-menu-item index="/reports/monthly">销售月报</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="authStore.isAdmin" index="/admin">
            <template #title>
              <el-icon><Tools /></el-icon>
              <span>后台管理</span>
            </template>
            <el-menu-item index="/admin/users">用户管理</el-menu-item>
            <el-menu-item index="/admin/roles">角色权限</el-menu-item>
            <el-menu-item index="/admin/settings">系统设置</el-menu-item>
            <el-menu-item index="/operation-logs">操作日志</el-menu-item>
            <el-menu-item index="/backups">备份管理</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'sales', 'finance'])" index="/ai">
            <template #title>
              <el-icon><MagicStick /></el-icon>
              <span>智能助手</span>
            </template>
            <el-menu-item index="/ai/quotes">AI报价助手</el-menu-item>
            <el-menu-item index="/ai/anomalies">智能异常提醒</el-menu-item>
            <el-menu-item index="/ai/knowledge">报价知识库</el-menu-item>
            <el-menu-item index="/ai/reports">智能经营报告</el-menu-item>
            <el-menu-item index="/ai/site-photos">现场照片识别</el-menu-item>
            <el-menu-item index="/ai/payment-ocr">收款截图识别</el-menu-item>
          </el-sub-menu>
        </el-menu>
        </div>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-button text @click="appStore.toggleSidebar()">
              <el-icon :size="20"><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
            </el-button>
          </div>
          <div class="header-right">
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useChatStore } from '@/stores/chat'
import NotificationBell from '@/components/NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const chatStore = useChatStore()

const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)

function handleLogout() {
  chatStore.disconnectWebSocket()
  authStore.logout()
}

onMounted(() => {
  // 连接聊天 WebSocket
  if (authStore.token) {
    chatStore.connectWebSocket(authStore.token)
    chatStore.fetchConversations()
  }
})

onUnmounted(() => {
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

/* 侧边栏滚动条样式 */
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

.main-content {
  padding: 20px;
  min-height: calc(100vh - 60px);
}
</style>

<!-- 非 scoped：子菜单弹出层在 body 上，需要全局覆盖 -->
<style>
.el-menu--popup {
  --el-menu-bg-color: var(--ad-card) !important;
  --el-menu-text-color: var(--ad-text-secondary) !important;
  --el-menu-hover-bg-color: var(--ad-darker) !important;
  --el-menu-active-color: var(--ad-red) !important;
}
</style>
