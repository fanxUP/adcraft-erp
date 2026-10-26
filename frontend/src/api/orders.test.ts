import { describe, expect, it, vi } from 'vitest'
const { get } = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('./index', () => ({ get, post: vi.fn(), put: vi.fn(), del: vi.fn(), patch: vi.fn(), apiClient: {} }))
import { getProjectQueueOrders, getProjectQueuePage } from './orders'

describe('project order queue pagination', () => {
  it('requests both queue statuses in one server-paginated query', async () => {
    get.mockResolvedValueOnce({ items: [], total: 0 })
    await getProjectQueuePage(3, 20)
    expect(get).toHaveBeenLastCalledWith('/orders/', { params: { page: 3, page_size: 20, status: 'pending_confirm,confirmed' } })
  })
  it('compatibility loader includes orders beyond 200 without duplicates', async () => {
    const rows = Array.from({ length: 205 }, (_, index) => ({ id: String(index), status: 'confirmed', created_at: String(index) }))
    get.mockImplementation(async (_url, { params }) => ({ items: rows.slice((params.page - 1) * 200, params.page * 200), total: 205 }))
    const result = await getProjectQueueOrders()
    expect(result).toHaveLength(205)
    expect(new Set(result.map(row => row.id)).size).toBe(205)
    expect(result.some(row => row.id === '204')).toBe(true)
  })
})
