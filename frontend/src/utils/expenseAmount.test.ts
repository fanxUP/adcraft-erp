import { describe, expect, it } from 'vitest'

import { normalizeExpenseAmounts } from './expenseAmount'

describe('normalizeExpenseAmounts', () => {
  it('uses the payable amount as the total when total is empty', () => {
    expect(normalizeExpenseAmounts(0, 800)).toEqual({
      amount: 800,
      payable_amount: 800,
    })
  })

  it('keeps an explicitly entered total and payable amount', () => {
    expect(normalizeExpenseAmounts(1000, 600)).toEqual({
      amount: 1000,
      payable_amount: 600,
    })
  })

  it('rejects an empty total and empty payable amount', () => {
    expect(() => normalizeExpenseAmounts(0, 0)).toThrow('请填写支出金额或待付款金额')
  })

  it('rejects a payable amount above the total', () => {
    expect(() => normalizeExpenseAmounts(100, 120)).toThrow('待付款金额不能大于支出总额且不能小于0')
  })
})
