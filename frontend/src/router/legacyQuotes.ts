import { ElMessage } from 'element-plus'
import type { RouteRecordRaw } from 'vue-router'
import { ApiRequestError } from '@/api/requestContract'

/** Old bookmarks resolve existing orders without recreating historical business. */
export const legacyQuoteRoutes: RouteRecordRaw[] = [
  { path: 'quotes', redirect: '/orders' },
  { path: 'quotes/new', redirect: '/orders/new' },
  { path: 'cdr/quotes', redirect: '/orders' },
  { path: 'cdr/quotes/new', redirect: '/orders/new' },
  {
    path: 'quotes/:id/edit',
    alias: ['/quotes/:id', '/cdr/quotes/:id', '/cdr/quotes/:id/edit'],
    name: 'LegacyQuoteOrder',
    component: { render: () => null },
    async beforeEnter(to) {
      // Import after the router is initialized: the API client also imports it.
      const { getOrderForHistoricalQuote } = await import('@/api/orders')
      try {
        const { order_id } = await getOrderForHistoricalQuote(String(to.params.id))
        if (order_id) return { path: `/orders/${order_id}`, replace: true }
        ElMessage.info('报价功能已停用，该历史记录没有可打开的订单。')
      } catch (error) {
        // HTTP failures are displayed by the shared API client.
        if (error instanceof ApiRequestError && error.status === 401) {
          return { path: '/login', replace: true }
        }
        if (error instanceof ApiRequestError && error.status === 403) {
          return { name: 'Forbidden', query: { from: to.fullPath }, replace: true }
        }
      }
      return { path: '/orders', replace: true }
    },
  },
]
