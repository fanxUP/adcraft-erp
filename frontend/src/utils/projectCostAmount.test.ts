import { describe, expect, it } from 'vitest'
import {
  getProjectCostPaymentAmount,
  normalizeProjectCostAmounts,
} from './projectCostAmount'

describe('项目成本金额归一化', () => {
  it('按支付金额加欠款金额计算支出总额', () => {
    expect(normalizeProjectCostAmounts(100, 30)).toEqual({
      paymentAmount: 100,
      debtAmount: 30,
      totalAmount: 130,
    })
  })

  it('以分为单位计算，避免浮点误差', () => {
    expect(normalizeProjectCostAmounts(0.1, 0.2).totalAmount).toBe(0.3)
  })

  it('允许其中一项为零，但总额不能为零', () => {
    expect(normalizeProjectCostAmounts(100, 0).totalAmount).toBe(100)
    expect(normalizeProjectCostAmounts(0, 100).totalAmount).toBe(100)
    expect(() => normalizeProjectCostAmounts(0, 0)).toThrow('支出总额必须大于0')
  })

  it('拒绝负金额和无效金额', () => {
    expect(() => normalizeProjectCostAmounts(-1, 0)).toThrow('支付金额不能小于0')
    expect(() => normalizeProjectCostAmounts(0, -1)).toThrow('欠款金额不能小于0')
    expect(() => normalizeProjectCostAmounts(Number.NaN, 0)).toThrow('支付金额必须是有效数字')
  })

  it('可以从历史总额和欠款反算登记时支付金额', () => {
    expect(getProjectCostPaymentAmount(130, 30)).toBe(100)
    expect(getProjectCostPaymentAmount(100, 0)).toBe(100)
    expect(getProjectCostPaymentAmount(100, 130)).toBe(0)
  })
})
