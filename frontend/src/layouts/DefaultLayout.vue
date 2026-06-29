<template>
  <div class="default-layout">
    <el-container>
      <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo">
          <span v-if="!sidebarCollapsed" class="logo-text">AdCraft ERP</span>
          <span v-else class="logo-short">A</span>
        </div>
        <el-menu
          :default-active="route.path"
          router
          :collapse="sidebarCollapsed"
          background-color="#1a1a2e"
          text-color="#a0a0b0"
          active-text-color="#e63946"
        >
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>首页驾驶舱</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/customers">
            <el-icon><User /></el-icon>
            <span>客户管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/quotes">
            <el-icon><Document /></el-icon>
            <span>报价管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'sales'])" index="/orders">
            <el-icon><Tickets /></el-icon>
            <span>订单管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'designer', 'production'])" index="/products">
            <el-icon><Goods /></el-icon>
            <span>产品管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'designer', 'production'])" index="/materials">
            <el-icon><Box /></el-icon>
            <span>材质管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.hasAnyRole(['admin', 'designer', 'production'])" index="/processes">
            <el-icon><Setting /></el-icon>
            <span>工艺管理</span>
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
            <el-menu-item index="/payments">收款记录</el-menu-item>
            <el-menu-item index="/expenses">支出管理</el-menu-item>
            <el-menu-item index="/customer-debts">客户欠款</el-menu-item>
            <el-menu-item index="/statements">对账单</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="authStore.hasAnyRole(['admin', 'sales', 'finance'])" index="/reports">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>报表中心</span>
            </template>
            <el-menu-item index="/reports/daily">销售日报</el-menu-item>
            <el-menu-item index="/reports/monthly">销售月报</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="authStore.isAdmin" index="/system">
            <template #title>
              <el-icon><Tools /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/operation-logs">操作日志</el-menu-item>
            <el-menu-item index="/backups">备份管理</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-button text @click="appStore.toggleSidebar()">
              <el-icon :size="20"><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
            </el-button>
          </div>
          <div class="header-right">
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)

function handleLogout() {
  authStore.logout()
}
</script>

<style scoped>
.default-layout {
  min-height: 100vh;
  background: var(--ad-dark);
}

.sidebar {
  background-color: #1a1a2e;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e63946;
  font-size: 20px;
  font-weight: bold;
  border-bottom: 1px solid var(--ad-border);
}

.logo-short {
  font-size: 24px;
}

.header {
  background: #1a1a2e;
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
