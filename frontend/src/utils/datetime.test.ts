import { describe, expect, it } from 'vitest'
import { businessToday } from './datetime'

describe('付款默认日期使用北京时间', () => {
  it.each([
    ['2026-10-30T00:00:00+08:00', '2026-10-30'],
    ['2026-10-30T07:59:59+08:00', '2026-10-30'],
    ['2026-10-30T08:00:00+08:00', '2026-10-30'],
    ['2026-11-01T00:00:00+08:00', '2026-11-01'],
    ['2027-01-01T00:00:00+08:00', '2027-01-01'],
    ['2026-10-30T23:59:59+08:00', '2026-10-30'],
  ])('%s → %s', (instant, expected) => {
    expect(businessToday(new Date(instant))).toBe(expected)
  })
})
