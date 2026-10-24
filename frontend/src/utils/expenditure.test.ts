import { describe, expect, it } from 'vitest'
import { expenditureSourceTarget, expenditureDateLabel, expenditureLastPaymentDateLabel, expenditureCategoryLabel, expenditureDimensionCategoryLabel, expenditureDimensionShare, expenditureDefaultDateRange, latestRequest } from './expenditure'

describe('expenditure display contracts', () => {
  it('uses the actual document kind, including incurred quote-stage costs', () => {
    expect(expenditureSourceTarget({ source_kind: 'project_cost', document_id: 'order-1', document_type: 'order' })).toEqual({ name: 'ProjectCostDetail', params: { orderId: 'order-1' } })
    expect(expenditureSourceTarget({ source_kind: 'project_cost', document_id: 'quote-1', document_type: 'quote' })).toEqual({ name: 'QuoteCostDetail', params: { quoteId: 'quote-1' } })
    expect(expenditureSourceTarget({ source_kind: 'project_cost', document_id: null })).toBeNull()
  })
  it('keeps missing disbursement dates unverified instead of guessing', () => {
    expect(expenditureDateLabel(null)).toBe('付款日期待核实')
    expect(expenditureDateLabel('2026-10-08')).toBe('2026-10-08')
  })
  it('labels latest payment dates and distinguishes unverified paid amounts from unpaid records', () => {
    expect(expenditureLastPaymentDateLabel('2026-10-08T00:30:00', 500)).toBe('2026-10-08')
    expect(expenditureLastPaymentDateLabel(null, 500)).toBe('日期待核实')
    expect(expenditureLastPaymentDateLabel(null, 0)).toBe('未付款')
  })
  it('localizes external capabilities without rewriting ordinary categories', () => {
    expect(expenditureCategoryLabel('outsource', 'production')).toBe('制作')
    expect(expenditureCategoryLabel('expense', 'production')).toBe('production')
    expect(expenditureCategoryLabel('project_cost', null)).toBe('—')
  })
  it('keeps dimension categories distinct by source and computes safe percentage shares', () => {
    expect(expenditureDimensionCategoryLabel('outsource', 'production')).toBe('制作（外协）')
    expect(expenditureDimensionCategoryLabel('project_cost', '材料')).toBe('材料（项目实际费用）')
    expect(expenditureDimensionShare(25, 100)).toBe(25)
    expect(expenditureDimensionShare(1, 0)).toBe(0)
    expect(expenditureDimensionShare(-1, 100)).toBe(0)
  })
  it('uses Shanghai calendar dates for the default summary period', () => {
    expect(expenditureDefaultDateRange(new Date('2026-10-23T16:30:00Z'))).toEqual(['2026-10-01', '2026-10-24'])
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
