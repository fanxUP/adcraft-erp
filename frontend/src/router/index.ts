import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: () => import('@/layouts/BlankLayout.vue'),
    children: [{ path: '', name: 'Login', component: () => import('@/views/login/LoginView.vue') }],
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Home', component: () => import('@/views/home/DashboardView.vue') },
      { path: 'customers', name: 'CustomerList', component: () => import('@/views/customers/CustomerList.vue') },
      { path: 'customers/:id', name: 'CustomerDetail', component: () => import('@/views/customers/CustomerDetail.vue') },
      { path: 'basic', name: 'MasterData', component: () => import('@/views/basic/MasterData.vue') },
      { path: 'quotes', name: 'QuoteList', component: () => import('@/views/quotes/QuoteList.vue') },
      { path: 'quotes/new', name: 'QuoteCreate', component: () => import('@/views/quotes/QuoteEditor.vue') },
      { path: 'quotes/:id/edit', name: 'QuoteEdit', component: () => import('@/views/quotes/QuoteEditor.vue') },
      { path: 'contracts', name: 'ContractList', component: () => import('@/views/contracts/ContractList.vue') },
      { path: 'orders', name: 'OrderList', component: () => import('@/views/orders/OrderList.vue') },
      { path: 'orders/recycle', name: 'OrderRecycle', meta: { roles: ['admin'] }, component: () => import('@/views/orders/OrderRecycle.vue') },
      { path: 'orders/:id', name: 'OrderDetail', component: () => import('@/views/orders/OrderDetail.vue') },
      { path: 'acceptances', name: 'AcceptanceList', component: () => import('@/views/acceptances/AcceptanceList.vue') },
      { path: 'acceptances/:id', name: 'AcceptanceDetail', component: () => import('@/views/acceptances/AcceptanceDetail.vue') },
      { path: 'design-tasks', name: 'DesignTaskList', component: () => import('@/views/tasks/DesignTaskList.vue') },
      { path: 'design-tasks/:id', name: 'DesignTaskDetail', component: () => import('@/views/tasks/DesignTaskDetail.vue') },
      { path: 'production-tasks', name: 'ProductionTaskList', component: () => import('@/views/tasks/ProductionTaskList.vue') },
      { path: 'production-tasks/board', name: 'ProductionTaskBoard', component: () => import('@/views/tasks/ProductionTaskBoard.vue') },
      { path: 'production-tasks/:id', name: 'ProductionTaskDetail', component: () => import('@/views/tasks/ProductionTaskDetail.vue') },
      { path: 'installation-tasks', name: 'InstallationTaskList', component: () => import('@/views/tasks/InstallationTaskList.vue') },
      { path: 'installation-tasks/:id', name: 'InstallationTaskDetail', component: () => import('@/views/tasks/InstallationTaskDetail.vue') },
      { path: 'payments', name: 'PaymentList', component: () => import('@/views/payments/PaymentList.vue') },
      { path: 'customer-debts', name: 'CustomerDebtList', component: () => import('@/views/payments/CustomerDebtList.vue') },
      { path: 'expenses', name: 'ExpenseList', component: () => import('@/views/payments/ExpenseList.vue') },
      { path: 'statements', name: 'StatementList', component: () => import('@/views/payments/StatementList.vue') },
      { path: 'statements/:id', name: 'StatementDetail', component: () => import('@/views/payments/StatementDetail.vue') },
      { path: 'project-costs', name: 'ProjectCostList', component: () => import('@/views/payments/ProjectCostList.vue') },
      { path: 'project-costs/:orderId', name: 'ProjectCostDetail', component: () => import('@/views/payments/ProjectCostDetail.vue') },
      { path: 'quote-costs/:quoteId', name: 'QuoteCostDetail', component: () => import('@/views/payments/ProjectCostDetail.vue') },
      { path: 'cost-debts', name: 'CostDebtList', component: () => import('@/views/payments/CostDebtList.vue') },
      { path: 'reports/daily', name: 'DailyReport', component: () => import('@/views/reports/DailyReport.vue') },
      { path: 'reports/monthly', name: 'MonthlyReport', component: () => import('@/views/reports/MonthlyReport.vue') },
      { path: 'outsource/vendors', name: 'OutsourceVendorList', component: () => import('@/views/outsource/OutsourceVendorList.vue') },
      { path: 'outsource/tasks', name: 'OutsourceTaskList', component: () => import('@/views/outsource/OutsourceTaskList.vue') },
      { path: 'outsource/tasks/recycle', name: 'OutsourceTaskRecycle', meta: { roles: ['admin'] }, component: () => import('@/views/outsource/OutsourceTaskRecycle.vue') },
      { path: 'outsource/payments', name: 'OutsourcePaymentList', component: () => import('@/views/outsource/OutsourcePaymentList.vue') },
      { path: 'inventory', name: 'InventoryList', component: () => import('@/views/inventory/InventoryList.vue') },
      { path: 'operation-logs', name: 'OperationLogList', meta: { roles: ['admin'] }, component: () => import('@/views/system/OperationLogList.vue') },
      { path: 'backups', name: 'BackupManage', meta: { roles: ['admin'] }, component: () => import('@/views/system/BackupManage.vue') },
      { path: 'notifications', name: 'NotificationList', component: () => import('@/views/system/NotificationList.vue') },
      { path: 'chat', name: 'Chat', component: () => import('@/views/chat/ChatLayout.vue') },
      { path: 'admin/users', name: 'AdminUserManage', meta: { roles: ['admin'] }, component: () => import('@/views/admin/UserManage.vue') },
      { path: 'admin/roles', name: 'AdminRoleManage', meta: { roles: ['admin'] }, component: () => import('@/views/admin/RoleManage.vue') },
      { path: 'admin/settings', name: 'AdminSettings', meta: { roles: ['admin'] }, component: () => import('@/views/admin/SystemSettings.vue') },
      { path: 'ai/anomalies', name: 'AnomalyDashboard', component: () => import('@/views/ai/AnomalyDashboard.vue') },
      { path: 'ai/quotes', name: 'AIQuoteAssistant', component: () => import('@/views/ai/AIQuoteAssistant.vue') },
      { path: 'ai/knowledge', name: 'QuoteKnowledgeBase', component: () => import('@/views/ai/QuoteKnowledgeBase.vue') },
      { path: 'ai/reports', name: 'BusinessNarrativeReport', component: () => import('@/views/ai/BusinessNarrativeReport.vue') },
      { path: 'ai/site-photos', name: 'SitePhotoRecognition', component: () => import('@/views/ai/SitePhotoRecognition.vue') },
      { path: 'ai/payment-ocr', name: 'PaymentOCR', component: () => import('@/views/ai/PaymentOCR.vue') },
    ],
  },
  {
    path: '/mobile',
    component: () => import('@/layouts/MobileLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: 'installation', name: 'MobileInstallation', component: () => import('@/views/tasks/MobileInstallation.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Restore user profile if token exists but user not loaded (page refresh)
  if (authStore.isLoggedIn && !authStore.user) {
    await authStore.fetchProfile(true)
  }

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && authStore.isLoggedIn) {
    next('/')
  } else if (to.meta.roles && authStore.user) {
    const userRoles: string[] = authStore.user.roles || []
    const required: string[] = to.meta.roles as string[]
    const hasAccess = required.some(r => userRoles.includes(r))
    if (!hasAccess) {
      next('/')
    } else {
      next()
    }
  } else {
    next()
  }
})

// 每次路由切换时检查是否有版本更新
const VERSION_KEY = 'app_version'
router.afterEach(async () => {
  try {
    const res = await fetch(`/version.json?t=${Date.now()}`)
    if (!res.ok) return
    const data = await res.json()
    const currentVersion = data.version || ''
    if (!currentVersion) return
    const storedVersion = localStorage.getItem(VERSION_KEY)
    if (storedVersion && storedVersion !== currentVersion) {
      // 版本已变化，标记为有更新（UpdateNotification 会显示提示条）
      // 如果 localStorage 里还没有版本号，存一下
    }
    if (!storedVersion) {
      localStorage.setItem(VERSION_KEY, currentVersion)
    }
  } catch {
    // ignore
  }
})

export default router
