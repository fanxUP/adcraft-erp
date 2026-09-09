import { describe, expect, it } from 'vitest'
import { isTaskVisible, taskProgress } from './task-board'

describe('统一任务看板进度', () => {
  it('所有看板对任务进度使用同一套 0-100 规范化', () => {
    expect(taskProgress({ progress_pct: -10 })).toBe(0)
    expect(taskProgress({ progress_pct: 45 })).toBe(45)
    expect(taskProgress({ progress_pct: 120 })).toBe(100)
  })

  it('所有看板都隐藏完成、取消和 100% 任务', () => {
    expect(isTaskVisible({ status: 'in_progress', progress_pct: 50 })).toBe(true)
    expect(isTaskVisible({ status: 'completed', progress_pct: 50 })).toBe(false)
    expect(isTaskVisible({ status: 'confirmed', progress_pct: 99 })).toBe(false)
    expect(isTaskVisible({ status: 'cancelled', progress_pct: 20 })).toBe(false)
    expect(isTaskVisible({ status: 'in_progress', progress_pct: 100 })).toBe(false)
  })

  it('服务端终态优先于页面自己的旧状态判断', () => {
    expect(isTaskVisible({
      status: 'in_progress',
      progress_pct: 60,
      status_view: { code: 'completed', label: '已完成', tone: 'success', terminal: true },
    })).toBe(false)
    expect(isTaskVisible({
      status: 'completed',
      progress_pct: 60,
      status_view: { code: 'reopened', label: '已重新打开', tone: 'info', terminal: false },
    })).toBe(true)
  })
})
