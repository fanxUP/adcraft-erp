import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getOrderForHistoricalQuote } from '@/api/orders'
import { ApiRequestError } from '@/api/requestContract'
import { canAccessRoute } from '@/config/access'
import { legacyQuoteRoutes } from './legacyQuotes'

vi.mock('@/api/orders', () => ({ getOrderForHistoricalQuote: vi.fn() }))
vi.mock('element-plus', () => ({ ElMessage: { info: vi.fn() } }))

const quoteId = '11111111-1111-1111-1111-111111111111'
const orderId = '22222222-2222-2222-2222-222222222222'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', children: legacyQuoteRoutes },
      { path: '/orders', component: {} },
      { path: '/orders/new', component: {} },
      { path: '/orders/:id', component: {} },
      { path: '/login', component: {} },
      { path: '/forbidden', name: 'Forbidden', component: {} },
    ],
  })
}

beforeEach(() => vi.resetAllMocks())

describe('retired quotation URLs', () => {
  it.each([
    `/quotes/${quoteId}`, `/quotes/${quoteId}/edit`,
    `/cdr/quotes/${quoteId}`, `/cdr/quotes/${quoteId}/edit`,
  ])('opens an existing order from %s', async (path) => {
    vi.mocked(getOrderForHistoricalQuote).mockResolvedValue({ order_id: orderId })
    const router = makeRouter()
    await router.push(path)
    expect(router.currentRoute.value.path).toBe(`/orders/${orderId}`)
    expect(getOrderForHistoricalQuote).toHaveBeenCalledExactlyOnceWith(quoteId)
    expect(ElMessage.info).not.toHaveBeenCalled()
  })

  it.each([
    ['/quotes', '/orders'], ['/cdr/quotes', '/orders'],
    ['/quotes/new', '/orders/new'], ['/cdr/quotes/new', '/orders/new'],
  ])('redirects %s to %s without looking up history', async (path, destination) => {
    const router = makeRouter()
    await router.push(path)
    expect(router.currentRoute.value.path).toBe(destination)
    expect(getOrderForHistoricalQuote).not.toHaveBeenCalled()
  })

  it('explains a missing order and returns to order management', async () => {
    vi.mocked(getOrderForHistoricalQuote).mockResolvedValue({ order_id: null })
    const router = makeRouter()
    await router.push(`/quotes/${quoteId}/edit`)
    expect(router.currentRoute.value.path).toBe('/orders')
    expect(ElMessage.info).toHaveBeenCalledWith('报价功能已停用，该历史记录没有可打开的订单。')
  })

  it.each([[401, '/login'], [403, '/forbidden'], [500, '/orders']] as const)(
    'handles HTTP %s without reporting that an order is missing', async (status, destination) => {
      vi.mocked(getOrderForHistoricalQuote).mockRejectedValue(new ApiRequestError('请求失败', { status }))
      const router = makeRouter()
      await router.push(`/quotes/${quoteId}/edit`)
      expect(router.currentRoute.value.path).toBe(destination)
      expect(ElMessage.info).not.toHaveBeenCalled()
    },
  )

  it('requires order read permission rather than retired quotation permissions', () => {
    expect(canAccessRoute('LegacyQuoteOrder', ['custom'], [], ['order:read'])).toBe(true)
    expect(canAccessRoute('LegacyQuoteOrder', ['custom'], [], ['quote:read'])).toBe(false)
  })
})
