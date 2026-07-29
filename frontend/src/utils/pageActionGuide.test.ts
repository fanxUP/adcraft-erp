import { describe, expect, it } from 'vitest'
import {
  getPageGuideContinuation,
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
    alerts: [],
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

  it('verifies installation draft completion from checklist state', () => {
    const draftGuide: AiPageActionGuide = {
      label: '预览安装准备草稿',
      target_path: '/installation-tasks/44444444-4444-4444-4444-444444444444',
      target_key: 'installation-draft',
    }
    const checklist = {
      title: '安装准备清单',
      completed_items: 2,
      total_items: 3,
      items: [
        { key: 'assigned_to' as const, label: '负责人', state: 'completed' as const, detail: '已完成' },
        { key: 'address' as const, label: '安装地址', state: 'completed' as const, detail: '已完成' },
        { key: 'scheduled_at' as const, label: '计划时间', state: 'pending' as const, detail: '待处理' },
      ],
    }

    expect(hasPageActionCompleted(
      draftGuide,
      guidance({ checklist }),
    )).toBe(false)
    expect(hasPageActionCompleted(
      draftGuide,
      guidance({
        checklist: {
          ...checklist,
          completed_items: 3,
          items: checklist.items.map(item => ({ ...item, state: 'completed' as const })),
        },
      }),
    )).toBe(true)
  })

  it('verifies an installation field action from its matching checklist item', () => {
    const addressGuide: AiPageActionGuide = {
      label: '补充安装地址',
      target_path: '/installation-tasks/44444444-4444-4444-4444-444444444444',
      target_key: 'installation-address',
    }
    const checklist = {
      title: '安装准备清单',
      completed_items: 0,
      total_items: 1,
      items: [
        {
          key: 'address' as const,
          label: '安装地址',
          state: 'pending' as const,
          detail: '待处理',
          action: {
            label: '处理安装地址',
            target_page: '安装任务详情',
            target_path: addressGuide.target_path,
            target_key: addressGuide.target_key,
          },
        },
      ],
    }

    expect(hasPageActionCompleted(addressGuide, guidance({ checklist }))).toBe(false)
    expect(hasPageActionCompleted(addressGuide, guidance({
      checklist: {
        ...checklist,
        completed_items: 1,
        items: [{ ...checklist.items[0], state: 'completed' }],
      },
    }))).toBe(true)
  })

  it('continues automatically only when the next action moves to another page', () => {
    const parentOrderAction = {
      label: '进入生产阶段',
      target_page: '订单详情',
      target_path: '/orders/33333333-3333-3333-3333-333333333333',
      target_status: 'in_production',
      target_key: 'order-status-in_production',
    }
    const taskGuide: AiPageActionGuide = {
      label: '确认设计稿',
      target_path: '/design-tasks/22222222-2222-2222-2222-222222222222',
      target_key: 'task-status-confirmed',
      target_status: 'confirmed',
    }

    expect(getPageGuideContinuation(
      taskGuide,
      guidance({ next_action: parentOrderAction }),
    )).toEqual(parentOrderAction)
    expect(getPageGuideContinuation(
      guide,
      guidance({
        next_action: {
          ...parentOrderAction,
          target_path: guide.target_path,
        },
      }),
    )).toBeNull()
    expect(getPageGuideContinuation(
      taskGuide,
      guidance({
        next_action: {
          ...parentOrderAction,
          target_path: 'https://unsafe.example',
        },
      }),
    )).toBeNull()
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
