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
      { path: 'profile', name: 'ProfileCenter', component: () => import('@/views/profile/ProfileCenter.vue') },
      { path: 'customers', name: 'CustomerList', component: () => import('@/views/customers/CustomerList.vue') },
      { path: 'customers/:id', name: 'CustomerDetail', component: () => import('@/views/customers/CustomerDetail.vue') },
      { path: 'products', name: 'ProductManage', component: () => import('@/views/products/ProductManage.vue') },
      { path: 'quotes', name: 'QuoteList', component: () => import('@/views/quotes/QuoteList.vue') },
      { path: 'quotes/new', name: 'QuoteCreate', component: () => import('@/views/quotes/QuoteEditor.vue') },
      { path: 'quotes/:id/edit', name: 'QuoteEdit', component: () => import('@/views/quotes/QuoteEditor.vue') },
      { path: 'contracts', name: 'ContractList', component: () => import('@/views/contracts/ContractList.vue') },
      { path: 'contracts/:id', name: 'ContractDetail', component: () => import('@/views/contracts/ContractDetail.vue') },
      { path: 'orders', name: 'OrderList', component: () => import('@/views/orders/OrderList.vue') },
      { path: 'orders/recycle', name: 'OrderRecycle', meta: { roles: ['admin'] }, component: () => import('@/views/orders/OrderRecycle.vue') },
      { path: 'orders/:id', name: 'OrderDetail', component: () => import('@/views/orders/OrderDetail.vue') },
      { path: 'acceptances', name: 'AcceptanceList', component: () => import('@/views/acceptances/AcceptanceList.vue') },
      { path: 'acceptances/:id', name: 'AcceptanceDetail', component: () => import('@/views/acceptances/AcceptanceDetail.vue') },
      { path: 'design-tasks', name: 'DesignTaskList', component: () => import('@/views/tasks/DesignTaskList.vue') },
      { path: 'design-tasks/:id', name: 'DesignTaskDetail', component: () => import('@/views/tasks/DesignTaskDetail.vue') },
      { path: 'production-tasks', name: 'ProductionTaskList', component: () => import('@/views/tasks/ProductionTaskList.vue') },
      { path: 'projects/board', name: 'ProjectKanbanBoard', component: () => import('@/views/tasks/ProductionTaskBoard.vue') },
      { path: 'production-tasks/board', redirect: '/projects/board' },
      { path: 'production-tasks/:id', name: 'ProductionTaskDetail', component: () => import('@/views/tasks/ProductionTaskDetail.vue') },
      { path: 'installation-tasks', name: 'InstallationTaskList', component: () => import('@/views/tasks/InstallationTaskList.vue') },
      { path: 'installation-tasks/:id', name: 'InstallationTaskDetail', component: () => import('@/views/tasks/InstallationTaskDetail.vue') },
      { path: 'receivables', name: 'ReceivablesView', component: () => import('@/views/payments/ReceivablesView.vue') },
      { path: 'payments', redirect: '/receivables' },
      { path: 'customer-debts', redirect: '/receivables' },
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
      { path: 'admin/ai/providers', name: 'AIProviderList', meta: { roles: ['admin'] },
            component: () => import('@/views/ai-model-center/ProviderList.vue') },
            { path: "employees", name: "EmployeeList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/EmployeeList.vue") },
            { path: "departments", name: "DepartmentList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/DepartmentList.vue") },
            { path: "salaries", name: "SalaryList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/SalaryList.vue") },
            { path: "salary-report", name: "SalaryReport", meta: { roles: ["admin"] }, component: () => import("@/views/employee/SalaryReport.vue") },
            { path: "salary-rules", name: "SalaryRuleList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/SalaryRuleList.vue") },
            { path: "employment-histories", name: "EmploymentHistoryList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/EmploymentHistoryList.vue") },
            { path: "leaves", name: "LeaveRequestList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/LeaveRequestList.vue") },
      { path: "attendance/records", name: "AttendanceRecordList", meta: { roles: ["admin"] }, component: () => import("@/views/attendance/AttendanceRecordList.vue") },
      { path: "attendance/rules", name: "AttendanceRuleList", meta: { roles: ["admin"] }, component: () => import("@/views/attendance/AttendanceRuleList.vue") },
      { path: 'admin/ai/knowledge-health', name: 'AIKnowledgeHealth', meta: { roles: ['admin'] },
            component: () => import('@/views/admin/AiKnowledgeHealth.vue') },
      { path: 'vehicle-dashboard', name: 'VehicleDashboard', component: () => import('@/views/vehicles/VehicleDashboard.vue') },
      { path: 'vehicles', name: 'VehicleList', component: () => import('@/views/vehicles/VehicleList.vue') },
      { path: 'vehicle-drivers', name: 'DriverList', component: () => import('@/views/vehicles/DriverList.vue') },
      { path: 'vehicle-use-requests', name: 'VehicleUseRequestList', component: () => import('@/views/vehicles/VehicleUseRequestList.vue') },
      { path: 'vehicle-agent-drafts', name: 'VehicleAgentDrafts', component: () => import('@/views/vehicles/VehicleAgentDrafts.vue') },
      { path: 'vehicle-dispatches', name: 'VehicleDispatchList', component: () => import('@/views/vehicles/VehicleDispatchList.vue') },
      { path: 'vehicle-trip-records', name: 'VehicleTripRecordList', component: () => import('@/views/vehicles/VehicleTripRecordList.vue') },
      { path: 'vehicle-expenses', name: 'VehicleExpenseList', component: () => import('@/views/vehicles/VehicleExpenseList.vue') },
      { path: 'vehicle-incidents', name: 'VehicleIncidentList', component: () => import('@/views/vehicles/VehicleIncidentList.vue') },
      { path: 'vehicle-reports', name: 'VehicleReports', component: () => import('@/views/vehicles/VehicleReports.vue') },
      { path: 'aerial-dashboard', name: 'AerialDashboard', component: () => import('@/views/aerial/AerialDashboard.vue') },
      { path: 'aerial-ledgers', name: 'AerialLedgerList', component: () => import('@/views/aerial/AerialLedgerList.vue') },
      { path: 'aerial-personnel-expenses', name: 'AerialPersonnelExpenseList', component: () => import('@/views/aerial/AerialPersonnelExpenseList.vue') },
      { path: 'aerial-personnel-wages', name: 'AerialPersonnelWageList', component: () => import('@/views/aerial/AerialPersonnelWageList.vue') },
      { path: 'aerial-vehicle-costs', name: 'AerialVehicleCostList', component: () => import('@/views/aerial/AerialVehicleCostList.vue') },
      { path: 'aerial-safety-checks', name: 'AerialSafetyCheckList', component: () => import('@/views/aerial/AerialSafetyCheckList.vue') },
      { path: 'aerial-reports', name: 'AerialReports', component: () => import('@/views/aerial/AerialReports.vue') },
      { path: 'aerial-vehicles', name: 'AerialVehicleList', component: () => import('@/views/aerial/AerialVehicleList.vue') },
      { path: 'aerial-personnel', name: 'AerialPersonnelList', component: () => import('@/views/aerial/AerialPersonnelList.vue') },
      { path: 'aerial-agent-drafts', name: 'AerialAgentDraftList', component: () => import('@/views/aerial/AerialAgentDraftList.vue') },
      { path: 'aerial-attendance', name: 'AerialAttendanceList', component: () => import('@/views/aerial/AerialAttendanceList.vue') },
      { path: 'ai/anomalies', name: 'AnomalyDashboard', component: () => import('@/views/ai/AnomalyDashboard.vue') },
      { path: 'ai/quotes', name: 'AIQuoteAssistant', component: () => import('@/views/ai/AIQuoteAssistant.vue') },
      { path: 'ai/knowledge', name: 'QuoteKnowledgeBase', component: () => import('@/views/ai/QuoteKnowledgeBase.vue') },
      { path: 'ai/reports', name: 'BusinessNarrativeReport', component: () => import('@/views/ai/BusinessNarrativeReport.vue') },
      { path: 'ai/site-photos', name: 'SitePhotoRecognition', component: () => import('@/views/ai/SitePhotoRecognition.vue') },
      { path: 'ai/payment-ocr', name: 'PaymentOCR', component: () => import('@/views/ai/PaymentOCR.vue') },

      // CDR 智能报价
      { path: 'cdr/quotes', name: 'CDRQuoteList', component: () => import('@/views/cdr-quotes/CDRQuoteList.vue') },
      { path: 'cdr/quotes/new', name: 'CDRQuoteCreate', component: () => import('@/views/cdr-quotes/CDRQuoteEditor.vue') },
      { path: 'cdr/quotes/:id', name: 'CDRQuoteDetail', component: () => import('@/views/cdr-quotes/CDRQuoteDetail.vue') },
      { path: 'cdr/quotes/:id/edit', name: 'CDRQuoteEdit', component: () => import('@/views/cdr-quotes/CDRQuoteEditor.vue') },
      { path: 'cdr/price-rules', name: 'PriceRuleList', component: () => import('@/views/cdr-quotes/PriceRuleList.vue') },
    ],
  },
  {
    path: '/mobile',
    component: () => import('@/layouts/MobileLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'MobileHome', component: () => import('@/views/mobile/MobileHome.vue') },
      { path: 'installation', name: 'MobileInstallation', component: () => import('@/views/tasks/MobileInstallation.vue') },
      { path: 'profile', name: 'MobileProfile', component: () => import('@/views/mobile/MobileProfile.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/** Quick mobile user-agent detection */
function isMobileDevice(): boolean {
  if (typeof navigator === 'undefined') return false
  return /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
}

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Restore user profile if token exists but user not loaded (page refresh)
  if (authStore.isLoggedIn && !authStore.user) {
    await authStore.fetchProfile(true)
  }

  // Auth guard
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
    return
  }

  // If logged in and on login page, redirect
  if (to.path === '/login' && authStore.isLoggedIn) {
    // Redirect mobile users to mobile home, desktop users to desktop home
    const pref = localStorage.getItem('prefer_mobile')
    if (pref === 'true' || (pref === null && isMobileDevice())) {
      next('/mobile')
    } else {
      next('/')
    }
    return
  }

  // Role-based guard
  if (to.meta.roles && authStore.user) {
    const userRoles: string[] = authStore.user.roles || []
    const required: string[] = to.meta.roles as string[]
    const hasAccess = required.some(r => userRoles.includes(r))
    if (!hasAccess) {
      next('/')
      return
    }
  }

  // Mobile auto-detect on first visit to desktop home
  if (to.path === '/' && authStore.isLoggedIn) {
    const pref = localStorage.getItem('prefer_mobile')
    if (pref === 'true' || (pref === null && isMobileDevice())) {
      next('/mobile')
      return
    }
  }

  next()
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
    }
    if (!storedVersion) {
      localStorage.setItem(VERSION_KEY, currentVersion)
    }
  } catch {
    // ignore
  }
})

export default router
