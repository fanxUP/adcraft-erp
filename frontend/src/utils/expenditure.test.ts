import { describe, expect, it } from 'vitest'
import { expenditureSourceTarget, expenditureDateLabel, expenditureCategoryLabel, latestRequest } from './expenditure'

describe('expenditure display contracts', () => {
  it('uses the actual document kind, including incurred quote-stage costs', () => {
    expect(expenditureSourceTarget({ source_kind: 'project_cost', document_id: 'order-1', document_type: 'order' })).toEqual({ name: 'ProjectCostDetail', params: { orderId: 'order-1' } })
    expect(expenditureSourceTarget({ source_kind: 'project_cost', document_id: 'quote-1', document_type: 'quote' })).toEqual({ name: 'QuoteCostDetail', params: { quoteId: 'quote-1' } })
    expect(expenditureSourceTarget({ source_kind: 'project_cost', document_id: null })).toBeNull()
  })
  it('never uses a creation/cost date as a payment date', () => {
    expect(expenditureDateLabel(null)).toBe('付款日期待核实')
    expect(expenditureDateLabel('2026-10-08')).toBe('2026-10-08')
  })
  it('localizes external capabilities without rewriting ordinary categories', () => {
    expect(expenditureCategoryLabel('outsource', 'production')).toBe('制作')
    expect(expenditureCategoryLabel('expense', 'production')).toBe('production')
    expect(expenditureCategoryLabel('project_cost', null)).toBe('—')
  })
  it('only allows the latest async response to update a view', () => {
    const request = latestRequest()
    const first = request.begin()
    const second = request.begin()
    expect(request.isCurrent(first)).toBe(false)
    expect(request.isCurrent(second)).toBe(true)
    request.begin()
    expect(request.isCurrent(second)).toBe(false)
  })
  it('links external records without constructing an unauthorized CRUD action', () => {
    expect(expenditureSourceTarget({ source_kind: 'outsource_task', source_id: 'task-1' })).toEqual({ name: 'OutsourceTaskList' })
    expect(expenditureSourceTarget({ source_kind: 'outsource_task', document_id: 'order-1', document_type: 'order' })).toEqual({ name: 'OutsourceTaskList', query: { order_id: 'order-1' } })
    expect(expenditureSourceTarget({ source_kind: 'outsource_payment', source_id: 'payment-1' })).toEqual({ name: 'OutsourcePaymentList' })
  })
})
