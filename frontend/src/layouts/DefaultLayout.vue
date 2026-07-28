<template>
  <div class="default-layout">
    <el-container>
      <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo">
          <span v-if="!sidebarCollapsed" class="logo-text">AdCraft ERP</span>
          <span v-else class="logo-short">A</span>
        </div>
        <div class="sidebar-menu-wrap">
        <AppSidebarMenu
          :active-path="route.path"
          :collapsed="sidebarCollapsed"
          :roles="authStore.roles"
        />
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
            <el-dropdown @command="handleSmartTool">
              <el-button text>
                <el-icon :size="18"><MagicStick /></el-icon>
                <span v-if="!sidebarCollapsed">智能工具</span>
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
import { computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useChatStore } from '@/stores/chat'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import NotificationBell from '@/components/NotificationBell.vue'
import AiAssistantButton from '@/components/ai-assistant/AiAssistantButton.vue'
import AiAssistantDrawer from '@/components/ai-assistant/AiAssistantDrawer.vue'
import AppSidebarMenu from '@/components/navigation/AppSidebarMenu.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const chatStore = useChatStore()
const aiStore = useAiAssistantStore()

const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)

// Update AI assistant page context on route changes
watch(
  () => route.path,
  (_path) => {
    const name = route.name as string || ''
    const params = route.params as Record<string, string>

    // Comprehensive route name → page info mapping (covers ALL routes)
    const pageLabels: Record<string, { page: string; business_type?: string }> = {
      // --- Dashboard ---
      'Home': { page: 'dashboard' },

      // --- Customer ---
      'CustomerList': { page: 'customer_list', business_type: 'customer' },
      'CustomerDetail': { page: 'customer_detail', business_type: 'customer' },

      // --- Orders ---
      'OrderList': { page: 'order_list', business_type: 'order' },
      'OrderRecycle': { page: 'order_recycle', business_type: 'order' },
      'OrderDetail': { page: 'order_detail', business_type: 'order' },

      // --- Regular Quotes ---
      'QuoteList': { page: 'quote_list', business_type: 'quote' },
      'QuoteCreate': { page: 'quote_create', business_type: 'quote' },
      'QuoteEdit': { page: 'quote_edit', business_type: 'quote' },

      // --- CDR Quotes (智能报价) ---
      'CDRQuoteList': { page: 'cdr_quote_list', business_type: 'quote' },
      'CDRQuoteCreate': { page: 'cdr_quote_create', business_type: 'quote' },
      'CDRQuoteDetail': { page: 'cdr_quote_detail', business_type: 'quote' },
      'CDRQuoteEdit': { page: 'cdr_quote_edit', business_type: 'quote' },

      // --- Price Center ---
      'PriceRuleList': { page: 'price_rules', business_type: 'price' },
      'CustomerAgreementList': { page: 'customer_agreements', business_type: 'price' },

      // --- Contracts ---
      'ContractList': { page: 'contract_list', business_type: 'contract' },
      'FrameworkContractList': { page: 'framework_contract_list', business_type: 'contract' },
      'FrameworkContractDetail': { page: 'framework_contract_detail', business_type: 'contract' },

      // --- Acceptances ---
      'AcceptanceList': { page: 'acceptance_list', business_type: 'acceptance' },
      'AcceptanceDetail': { page: 'acceptance_detail', business_type: 'acceptance' },

      // --- Design Tasks ---
      'DesignTaskList': { page: 'design_task_list', business_type: 'design_task' },
      'DesignTaskDetail': { page: 'design_task_detail', business_type: 'design_task' },

      // --- Production Tasks ---
      'ProductionTaskList': { page: 'production_task_list', business_type: 'production_task' },
      'ProductionTaskBoard': { page: 'production_task_board', business_type: 'production_task' },
      'ProductionTaskDetail': { page: 'production_task_detail', business_type: 'production_task' },

      // --- Installation Tasks ---
      'InstallationTaskList': { page: 'installation_task_list', business_type: 'installation_task' },
      'InstallationTaskDetail': { page: 'installation_task_detail', business_type: 'installation_task' },

      // --- Products & Materials ---
      'ProductManage': { page: 'product_manage', business_type: 'product' },
      'MaterialProcessManage': { page: 'material_process', business_type: 'product' },

      // --- Finance ---
      'ReceivablesView': { page: 'receivables', business_type: 'finance' },
      'ExpenseList': { page: 'expenses', business_type: 'finance' },
      'StatementList': { page: 'statement_list', business_type: 'finance' },
      'StatementDetail': { page: 'statement_detail', business_type: 'finance' },
      'ProjectCostList': { page: 'project_cost_list', business_type: 'finance' },
      'ProjectCostDetail': { page: 'project_cost_detail', business_type: 'finance' },
      'QuoteCostDetail': { page: 'quote_cost_detail', business_type: 'finance' },
      'CostDebtList': { page: 'cost_debt_list', business_type: 'finance' },

      // --- Outsource ---
      'OutsourceVendorList': { page: 'outsource_vendors', business_type: 'outsource' },
      'OutsourceTaskList': { page: 'outsource_tasks', business_type: 'outsource' },
      'OutsourceTaskRecycle': { page: 'outsource_task_recycle', business_type: 'outsource' },
      'OutsourcePaymentList': { page: 'outsource_payments', business_type: 'outsource' },

      // --- Inventory ---
      'InventoryList': { page: 'inventory' },

      // --- Reports ---
      'DailyReport': { page: 'daily_report', business_type: 'report' },
      'MonthlyReport': { page: 'monthly_report', business_type: 'report' },

      // --- Admin ---
      'AdminUserManage': { page: 'admin_users', business_type: 'admin' },
      'AdminRoleManage': { page: 'admin_roles', business_type: 'admin' },
      'AdminSettings': { page: 'admin_settings', business_type: 'admin' },
      'AIProviderList': { page: 'ai_providers', business_type: 'admin' },
      'OperationLogList': { page: 'operation_logs', business_type: 'admin' },
      'BackupManage': { page: 'backups', business_type: 'admin' },

      // --- System ---
      'NotificationList': { page: 'notifications' },
      'Chat': { page: 'chat' },

      // --- Vehicle ---
      'VehicleDashboard': { page: 'vehicle_dashboard', business_type: 'vehicle' },
      'VehicleList': { page: 'vehicle_list', business_type: 'vehicle' },
      'DriverList': { page: 'driver_list', business_type: 'vehicle' },
      'VehicleUseRequestList': { page: 'vehicle_use_requests', business_type: 'vehicle' },
      'VehicleAgentDrafts': { page: 'vehicle_agent_drafts', business_type: 'vehicle' },
      'VehicleDispatchList': { page: 'vehicle_dispatches', business_type: 'vehicle' },
      'VehicleTripRecordList': { page: 'vehicle_trip_records', business_type: 'vehicle' },
      'VehicleExpenseList': { page: 'vehicle_expenses', business_type: 'vehicle' },
      'VehicleInsuranceInspection': { page: 'vehicle_insurance', business_type: 'vehicle' },
      'VehicleIncidentList': { page: 'vehicle_incidents', business_type: 'vehicle' },
      'VehicleReports': { page: 'vehicle_reports', business_type: 'vehicle' },

      // --- Aerial ---
      'AerialDashboard': { page: 'aerial_dashboard', business_type: 'aerial' },
      'AerialLedgerList': { page: 'aerial_ledgers', business_type: 'aerial' },
      'AerialPersonnelExpenseList': { page: 'aerial_personnel_expenses', business_type: 'aerial' },
      'AerialPersonnelWageList': { page: 'aerial_personnel_wages', business_type: 'aerial' },
      'AerialVehicleCostList': { page: 'aerial_vehicle_costs', business_type: 'aerial' },
      'AerialSafetyCheckList': { page: 'aerial_safety_checks', business_type: 'aerial' },
      'AerialReports': { page: 'aerial_reports', business_type: 'aerial' },
      'AerialVehicleList': { page: 'aerial_vehicles', business_type: 'aerial' },
      'AerialPersonnelList': { page: 'aerial_personnel', business_type: 'aerial' },
      'AerialAgentDraftList': { page: 'aerial_agent_drafts', business_type: 'aerial' },

      // --- AI Features ---
      'AnomalyDashboard': { page: 'anomaly_dashboard', business_type: 'ai' },
      'AIQuoteAssistant': { page: 'ai_quote_assistant', business_type: 'ai' },
      'QuoteKnowledgeBase': { page: 'quote_knowledge_base', business_type: 'ai' },
      'BusinessNarrativeReport': { page: 'business_narrative_report', business_type: 'ai' },
      'SitePhotoRecognition': { page: 'site_photo_recognition', business_type: 'ai' },
      'PaymentOCR': { page: 'payment_ocr', business_type: 'ai' },
    }

    const info = pageLabels[name] || {}
    const ctx: Record<string, string> = { ...info }

    // Extract business IDs from all possible param names
    if (params.id) ctx.business_id = params.id
    if (params.orderId) ctx.business_id = params.orderId
    if (params.quoteId) ctx.business_id = params.quoteId

    aiStore.resetPageContext(ctx)
  },
  { immediate: true }
)

function handleLogout() {
  chatStore.disconnectWebSocket()
  authStore.logout()
}

function handleSmartTool(path: string) {
  router.push(path)
}

onMounted(() => {
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

<style>
.el-menu--popup {
  --el-menu-bg-color: var(--ad-card) !important;
  --el-menu-text-color: var(--ad-text-secondary) !important;
  --el-menu-hover-bg-color: var(--ad-darker) !important;
  --el-menu-active-color: var(--ad-red) !important;
}
</style>
