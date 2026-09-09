import { describe, expect, it } from 'vitest'
import { normalizeProgress, progressTone, resolveStatusPresentation } from './uiPresentation'

describe('normalizeProgress', () => {
  it('将无效值和负数安全归一为 0', () => {
    expect(normalizeProgress(undefined)).toBe(0)
    expect(normalizeProgress(Number.NaN)).toBe(0)
    expect(normalizeProgress(-12)).toBe(0)
  })

  it('将进度限制在 0 到 100 并保持整数展示', () => {
    expect(normalizeProgress(42.6)).toBe(43)
    expect(normalizeProgress(130)).toBe(100)
  })
})

describe('resolveStatusPresentation', () => {
  it('为常见状态提供统一展示语义', () => {
    expect(resolveStatusPresentation('in_installation')).toEqual({
      code: 'in_installation',
      label: '安装中',
      tone: 'info',
      terminal: false,
    })
    expect(resolveStatusPresentation('completed').terminal).toBe(true)
  })

  it('优先使用服务端或调用方传入的展示字段，不改变业务状态', () => {
    expect(resolveStatusPresentation('blocked', '外协任务进行中', 'warning', false)).toEqual({
      code: 'blocked',
      label: '外协任务进行中',
      tone: 'warning',
      terminal: false,
    })
  })

  it('直接消费服务端 canonical status view', () => {
    expect(resolveStatusPresentation({
      code: 'in_production',
      label: '制作中',
      tone: 'info',
      terminal: false,
    })).toEqual({
      code: 'in_production',
      label: '制作中',
      tone: 'info',
      terminal: false,
    })
  })

  it('未知状态保留原始编码并使用中性色', () => {
    expect(resolveStatusPresentation('custom_status')).toMatchObject({
      code: 'custom_status',
      label: 'custom_status',
      tone: 'neutral',
      terminal: false,
    })
  })
})

describe('progressTone', () => {
  it('只有未显式指定颜色时才根据进度提供展示默认色', () => {
    expect(progressTone(undefined, 100)).toBe('success')
    expect(progressTone(undefined, 60)).toBe('brand')
    expect(progressTone('warning', 100)).toBe('warning')
  })
})
