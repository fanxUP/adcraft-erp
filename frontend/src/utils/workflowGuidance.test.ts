import { describe, expect, it } from 'vitest'
import {
  extractWorkflowGuidance,
  getGuidanceContextKey,
  isSafeWorkflowTarget,
  matchesGuidanceContext,
  parseWorkflowGuidance,
} from './workflowGuidance'
import type { AiPageContext } from '@/types/aiAssistant'
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
      target_key: 'task-status-confirmed',
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
        target_key: 'task-status-confirmed',
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
    expect(isSafeWorkflowTarget(
      '/receivables?order_id=33333333-3333-3333-3333-333333333333',
    )).toBe(true)
    expect(isSafeWorkflowTarget('/receivables?order_id=not-a-uuid')).toBe(false)
    expect(isSafeWorkflowTarget('/receivables?next=https://example.com')).toBe(false)
    expect(isSafeWorkflowTarget('https://example.com/orders/1')).toBe(false)
    expect(isSafeWorkflowTarget('//example.com/orders/1')).toBe(false)
    expect(isSafeWorkflowTarget('/admin/users')).toBe(false)
  })

  it('creates a stable key only for workflow-aware business pages', () => {
    const context: AiPageContext = {
      business_type: 'order',
      business_id: '33333333-3333-3333-3333-333333333333',
      business_status: 'designing',
    }

    expect(getGuidanceContextKey(context)).toBe(
      'order:33333333-3333-3333-3333-333333333333',
    )
    expect(getGuidanceContextKey({ business_type: 'customer', business_id: context.business_id }))
      .toBeNull()
    expect(getGuidanceContextKey({ business_type: 'order' })).toBeNull()
  })

  it('detects whether guidance still belongs to the current business record', () => {
    const context: AiPageContext = {
      business_type: 'order',
      business_id: '33333333-3333-3333-3333-333333333333',
    }

    expect(matchesGuidanceContext(guidanceResult.result, context)).toBe(true)
    expect(matchesGuidanceContext(guidanceResult.result, {
      ...context,
      business_id: '44444444-4444-4444-4444-444444444444',
    })).toBe(false)
    expect(matchesGuidanceContext(null, context)).toBe(false)
  })

  it('parses additive workflow progress and structured alerts', () => {
    expect(parseWorkflowGuidance({
      ...guidanceResult.result,
      progress: {
        completed_steps: 1,
        total_steps: 6,
        percent: 17,
        current_stage_key: 'design',
        steps: [
          { key: 'order', label: '订单确认', state: 'completed', detail: '订单已确认' },
          { key: 'design', label: '设计', state: 'current', detail: '设计任务处理中' },
        ],
      },
      alerts: [
        {
          code: 'task_unassigned',
          severity: 'warning',
          title: '设计任务尚未分配负责人',
          detail: '分配负责人后才能明确责任人',
          action: {
            label: '分配任务负责人',
            target_page: '设计任务详情',
            target_path: '/design-tasks/22222222-2222-2222-2222-222222222222',
            target_key: 'task-assignee',
          },
        },
      ],
    })).toMatchObject({
      progress: {
        completed_steps: 1,
        current_stage_key: 'design',
        steps: [
          { key: 'order', state: 'completed' },
          { key: 'design', state: 'current' },
        ],
      },
      alerts: [
        {
          code: 'task_unassigned',
          severity: 'warning',
          action: {
            label: '分配任务负责人',
            target_key: 'task-assignee',
          },
        },
      ],
    })
  })

  it('parses an installation checklist and strictly bounded form draft', () => {
    const parsed = parseWorkflowGuidance({
      ...guidanceResult.result,
      checklist: {
        title: '安装准备清单',
        completed_items: 0,
        total_items: 3,
        items: [
          {
            key: 'address',
            label: '补充安装地址',
            state: 'pending',
            detail: '可引用订单地址',
            action: {
              label: '补充安装地址',
              target_page: '安装任务详情',
              target_path: '/installation-tasks/44444444-4444-4444-4444-444444444444',
              target_key: 'installation-address',
            },
          },
        ],
        draft_action: {
          label: '预览安装准备草稿',
          target_page: '安装任务详情',
          target_path: '/installation-tasks/44444444-4444-4444-4444-444444444444',
          target_key: 'installation-draft',
          draft: {
            kind: 'installation_task_update',
            title: '安装准备信息草稿',
            fields: [
              {
                key: 'address',
                label: '安装地址',
                value: '上海市静安区测试路 88 号',
                source: 'order',
                hint: '来自订单安装地址，请现场确认',
              },
              {
                key: 'unexpected_field',
                label: '越权字段',
                value: '不应采用',
                source: 'order',
                hint: '测试',
              },
            ],
          },
        },
      },
    })

    expect(parsed).toMatchObject({
      checklist: {
        title: '安装准备清单',
        items: [
          {
            key: 'address',
            state: 'pending',
            action: { target_key: 'installation-address' },
          },
        ],
        draft_action: {
          target_key: 'installation-draft',
          draft: {
            kind: 'installation_task_update',
            fields: [
              {
                key: 'address',
                value: '上海市静安区测试路 88 号',
                source: 'order',
              },
            ],
          },
        },
      },
    })
  })

  it('keeps old guidance compatible when progress fields are absent', () => {
    const parsed = parseWorkflowGuidance(guidanceResult.result)

    expect(parsed).not.toBeNull()
    expect(parsed?.progress).toBeUndefined()
    expect(parsed?.alerts).toEqual([])
  })
})
