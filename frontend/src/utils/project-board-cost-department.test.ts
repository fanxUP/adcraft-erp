import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { dedupeProjectQueueOrders, isProjectQueueStatus } from './project-queue'
import type { OrderListResponse } from '@/types/api'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string) {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

function order(overrides: Partial<OrderListResponse> = {}): OrderListResponse {
  return {
    id: 'order-1',
    order_no: 'O20260912-0001',
    customer_id: 'customer-1',
    customer_name: '客户一',
    project_name: '项目一',
    status: 'pending_confirm',
    total_amount: 100,
    paid_amount: 0,
    unpaid_amount: 100,
    created_at: '2026-09-12T10:00:00+08:00',
    ...overrides,
  }
}

describe('项目看板与项目成本的部门/科室展示', () => {
  it('独立项目看板包含项目队列列并使用共享项目队列卡片', () => {
    const source = readSource('views/tasks/ProductionTaskBoard.vue')

    expect(source).toContain("label: '项目队列'")
    expect(source).toContain('getProjectQueueOrders')
    expect(source).toContain('ProjectQueueCard')
    expect(source).toContain('queueCards')
  })

  it('工作台和独立项目看板使用同一项目队列加载方法与卡片', () => {
    const dashboard = readSource('views/home/DashboardView.vue')
    const board = readSource('views/tasks/ProductionTaskBoard.vue')

    expect(dashboard).toContain('getProjectQueueOrders')
    expect(dashboard).toContain('ProjectQueueCard')
    expect(board).toContain('getProjectQueueOrders')
    expect(board).toContain('ProjectQueueCard')
    expect(dashboard).not.toContain('getOrders({ page_size: 100 })')
  })

  it('项目队列只保留待确认和已确认订单，并按订单去重', () => {
    expect(isProjectQueueStatus('pending_confirm')).toBe(true)
    expect(isProjectQueueStatus('confirmed')).toBe(true)
    expect(isProjectQueueStatus('in_progress')).toBe(false)

    const rows = dedupeProjectQueueOrders([
      order({ id: 'order-1', created_at: '2026-09-12T10:00:00+08:00' }),
      order({ id: 'order-1', status: 'confirmed', created_at: '2026-09-12T11:00:00+08:00' }),
      order({ id: 'order-2', order_no: 'O20260912-0002', status: 'confirmed', created_at: '2026-09-12T09:00:00+08:00' }),
      order({ id: 'order-3', order_no: 'O20260912-0003', status: 'in_progress', created_at: '2026-09-12T12:00:00+08:00' }),
    ])

    expect(rows.map(row => row.id)).toEqual(['order-1', 'order-2'])
    expect(rows[0].status).toBe('confirmed')
  })

  it('项目成本列表声明并渲染部门/科室列', () => {
    const source = readSource('views/payments/ProjectCostList.vue')
    const types = readSource('types/api.ts')

    expect(source).toContain('label="部门/科室"')
    expect(source).toContain('row.department || \'-\'')
    expect(types).toContain('export interface QuoteCostResponse')
    expect(types).toMatch(/interface QuoteCostResponse[\s\S]*department\?: string/)
  })

  it('项目成本订单和报价详情均渲染部门/科室', () => {
    const source = readSource('views/payments/ProjectCostDetail.vue')

    expect(source).toContain('<span class="label">部门/科室</span>')
    expect(source).toContain('order.department || \'-\'')
  })
})
