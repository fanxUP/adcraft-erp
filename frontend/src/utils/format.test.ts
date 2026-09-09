import { describe, expect, it } from 'vitest'
import { formatMoney, formatNumber, formatPercent } from './format'

describe('统一销售与财务格式', () => {
  it('金额保留两位小数并安全处理空值', () => {
    expect(formatMoney(1234.5)).toBe('¥ 1,234.50')
    expect(formatMoney(null)).toBe('-')
    expect(formatMoney(1234.5, false)).toBe('1,234.50')
  })

  it('数字和百分比不会输出 NaN 或超出范围', () => {
    expect(formatNumber(1234.567)).toBe('1,234.57')
    expect(formatNumber(undefined)).toBe('-')
    expect(formatPercent(125)).toBe('100%')
    expect(formatPercent(-2)).toBe('0%')
  })
})
