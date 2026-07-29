import { describe, expect, it } from 'vitest'
import {
  getPageGuideCalloutPosition,
  hasPageActionCompleted,
  isSameWorkflowPath,
} from './pageActionGuide'
import type { AiPageActionGuide, AiWorkflowGuidance } from '@/types/aiAssistant'

const guide: AiPageActionGuide = {
  label: '进入生产阶段',
  target_path: '/orders/33333333-3333-3333-3333-333333333333',
  target_key: 'order-status-in_production',
  target_status: 'in_production',
}

function guidance(overrides: Partial<AiWorkflowGuidance> = {}): AiWorkflowGuidance {
  return {
    business_type: 'order',
    business_id: '33333333-3333-3333-3333-333333333333',
    current_status: 'designing',
    current_step: '设计阶段',
    blockers: [],
    next_action: {
      label: guide.label,
      target_page: '订单详情',
      target_path: guide.target_path,
      target_key: guide.target_key,
      target_status: guide.target_status,
    },
    completion_signal: '订单状态变为“生产中”',
    allowed_next_statuses: ['in_production'],
    ...overrides,
  }
}

describe('page action guidance helpers', () => {
  it('detects completion when the target status is reached', () => {
    expect(hasPageActionCompleted(guide, guidance({
      current_status: 'in_production',
    }))).toBe(true)
  })

  it('keeps guiding while the same exact action remains next', () => {
    expect(hasPageActionCompleted(guide, guidance())).toBe(false)
  })

  it('detects completion when workflow advances to another control', () => {
    expect(hasPageActionCompleted(guide, guidance({
      next_action: {
        label: '开始制作',
        target_page: '制作任务详情',
        target_path: '/production-tasks/22222222-2222-2222-2222-222222222222',
        target_key: 'task-status-in_progress',
      },
    }))).toBe(true)
    expect(hasPageActionCompleted(guide, guidance({ next_action: null }))).toBe(true)
  })

  it('compares workflow paths without being affected by trailing slashes', () => {
    expect(isSameWorkflowPath('/orders/1/', '/orders/1')).toBe(true)
    expect(isSameWorkflowPath('/orders/1', '/orders/2')).toBe(false)
  })

  it('keeps the callout inside a narrow viewport', () => {
    const position = getPageGuideCalloutPosition(
      { top: 1600, bottom: 1680, left: 240 },
      { width: 320, height: 800 },
    )

    expect(position).toEqual({
      left: 12,
      top: 688,
      width: 296,
    })
  })
})
