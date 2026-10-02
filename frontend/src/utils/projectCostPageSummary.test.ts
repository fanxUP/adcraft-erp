import { describe, expect, it } from 'vitest'
import { sumCurrentPageProjectCosts } from './projectCostPageSummary'

describe('sumCurrentPageProjectCosts', () => {
  it('adds order and quote costs for only the rows on the current page', () => {
    const rows = [
      { id: 'order-1', _type: 'order' as const },
      { id: 'quote-1', _type: 'quote' as const, cost_amount: 23.4 },
      { id: 'order-2', _type: 'order' as const },
    ]

    expect(sumCurrentPageProjectCosts(rows, {
      'order-1': 101.2,
      'order-2': 0.7,
      'quote-1': 900,
      'order-not-on-page': 700,
    })).toBe(125.3)
  })

  it('treats missing or non-finite amounts as zero and returns zero for an empty page', () => {
    expect(sumCurrentPageProjectCosts([
      { id: 'order-missing', _type: 'order' as const },
      { id: 'quote-invalid', _type: 'quote' as const, cost_amount: Number.NaN },
    ], {})).toBe(0)
    expect(sumCurrentPageProjectCosts([], {})).toBe(0)
  })

  it('sums monetary values in cents to avoid floating-point drift', () => {
    expect(sumCurrentPageProjectCosts([
      { id: 'quote-1', _type: 'quote' as const, cost_amount: 10.1 },
      { id: 'quote-2', _type: 'quote' as const, cost_amount: 0.2 },
    ], {})).toBe(10.3)
  })
})
