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
      { path: 'products', name: 'ProductManage', component: () => import('@/views/products/ProductManage.vue') },
      { path: 'materials', name: 'MaterialManage', component: () => import('@/views/materials/MaterialManage.vue') },
      { path: 'processes', name: 'ProcessManage', component: () => import('@/views/processes/ProcessManage.vue') },
      { path: 'quotes', name: 'QuoteList', component: () => import('@/views/quotes/QuoteList.vue') },
      { path: 'quotes/new', name: 'QuoteCreate', component: () => import('@/views/quotes/QuoteEditor.vue') },
      { path: 'quotes/:id/edit', name: 'QuoteEdit', component: () => import('@/views/quotes/QuoteEditor.vue') },
      { path: 'orders', name: 'OrderList', component: () => import('@/views/orders/OrderList.vue') },
      { path: 'orders/:id', name: 'OrderDetail', component: () => import('@/views/orders/OrderDetail.vue') },
      { path: 'design-tasks', name: 'DesignTaskList', component: () => import('@/views/tasks/DesignTaskList.vue') },
      { path: 'design-tasks/:id', name: 'DesignTaskDetail', component: () => import('@/views/tasks/DesignTaskDetail.vue') },
      { path: 'production-tasks', name: 'ProductionTaskList', component: () => import('@/views/tasks/ProductionTaskList.vue') },
      { path: 'production-tasks/board', name: 'ProductionTaskBoard', component: () => import('@/views/tasks/ProductionTaskBoard.vue') },
      { path: 'production-tasks/:id', name: 'ProductionTaskDetail', component: () => import('@/views/tasks/ProductionTaskDetail.vue') },
      { path: 'installation-tasks', name: 'InstallationTaskList', component: () => import('@/views/tasks/InstallationTaskList.vue') },
      { path: 'installation-tasks/:id', name: 'InstallationTaskDetail', component: () => import('@/views/tasks/InstallationTaskDetail.vue') },
      { path: 'mobile/installation', name: 'MobileInstallation', component: () => import('@/views/tasks/MobileInstallation.vue') },
      { path: 'payments', name: 'PaymentList', component: () => import('@/views/payments/PaymentList.vue') },
      { path: 'customer-debts', name: 'CustomerDebtList', component: () => import('@/views/payments/CustomerDebtList.vue') },
      { path: 'statements', name: 'StatementList', component: () => import('@/views/payments/StatementList.vue') },
      { path: 'statements/:id', name: 'StatementDetail', component: () => import('@/views/payments/StatementDetail.vue') },
      { path: 'reports/daily', name: 'DailyReport', component: () => import('@/views/reports/DailyReport.vue') },
      { path: 'reports/monthly', name: 'MonthlyReport', component: () => import('@/views/reports/MonthlyReport.vue') },
      { path: 'outsource/vendors', name: 'OutsourceVendorList', component: () => import('@/views/outsource/OutsourceVendorList.vue') },
      { path: 'outsource/tasks', name: 'OutsourceTaskList', component: () => import('@/views/outsource/OutsourceTaskList.vue') },
      { path: 'outsource/payments', name: 'OutsourcePaymentList', component: () => import('@/views/outsource/OutsourcePaymentList.vue') },
      { path: 'inventory', name: 'InventoryList', component: () => import('@/views/inventory/InventoryList.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && authStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
