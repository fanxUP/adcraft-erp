import { describe, expect, it } from 'vitest'
import {
  extractWorkflowGuidance,
  isSafeWorkflowTarget,
} from './workflowGuidance'
import type { AiToolCallResult } from '@/types/aiAssistant'

const guidanceResult: AiToolCallResult = {
  tool_name: 'get_workflow_guidance',
  status: 'success',
  result: {
    business_type: 'order',
    business_id: '33333333-3333-3333-3333-333333333333',
    current_status: 'designing',
    current_step: '设计阶段',
    blockers: ['设计任务待审核确认'],
    next_action: {
      label: '确认设计稿',
      target_page: '设计任务详情',
      target_path: '/design-tasks/22222222-2222-2222-2222-222222222222',
    },
    completion_signal: '设计任务状态变为“已确认”',
    allowed_next_statuses: ['in_production'],
  },
}

describe('workflow guidance helpers', () => {
  it('extracts a successful workflow guidance tool result', () => {
    expect(extractWorkflowGuidance([guidanceResult])).toMatchObject({
      business_type: 'order',
      current_step: '设计阶段',
      next_action: {
        label: '确认设计稿',
      },
    })
  })

  it('ignores malformed or failed tool results', () => {
    expect(extractWorkflowGuidance([
      { ...guidanceResult, status: 'failed' },
      { tool_name: 'get_order_progress', status: 'success', result: {} },
    ])).toBeNull()
  })

  it('allows only known in-app workflow routes', () => {
    expect(isSafeWorkflowTarget('/orders/33333333-3333-3333-3333-333333333333')).toBe(true)
    expect(isSafeWorkflowTarget('/receivables')).toBe(true)
    expect(isSafeWorkflowTarget('https://example.com/orders/1')).toBe(false)
    expect(isSafeWorkflowTarget('//example.com/orders/1')).toBe(false)
    expect(isSafeWorkflowTarget('/admin/users')).toBe(false)
  })
})
