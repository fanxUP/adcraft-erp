import { describe, expect, it } from 'vitest'
import type { TaskOrderItemOption } from '@/types/api'
import {
  getProductionSelectionBucket,
  getProductionSelectionItemIds,
  getStageSelectionState,
  toggleStageSelection,
} from './taskStageSelection'

type SelectionItem = Pick<
  TaskOrderItemOption,
  'id' | 'stage' | 'can_select' | 'capabilities' | 'is_linked' | 'task_status'
>

function makeItem(overrides: Partial<SelectionItem> = {}): SelectionItem {
  return {
    id: 'item-1',
    stage: 'in_production',
    can_select: true,
    is_linked: false,
    task_status: null,
    ...overrides,
  }
}

describe('制作任务按状态快速选择', () => {
  it('按本任务状态区分待制作和制作中，不把返工混入制作中', () => {
    expect(getProductionSelectionBucket(makeItem())).toBe('pending')
    expect(getProductionSelectionBucket(makeItem({
      id: 'linked-pending',
      is_linked: true,
      task_status: 'pending',
    }))).toBe('pending')
    expect(getProductionSelectionBucket(makeItem({
      id: 'linked-in-progress',
      is_linked: true,
      task_status: 'in_progress',
    }))).toBe('in_progress')
    expect(getProductionSelectionBucket(makeItem({
      id: 'rework',
      is_linked: true,
      task_status: 'rework',
    }))).toBeNull()
  })

  it('排除不可选择或未进入制作阶段的明细', () => {
    expect(getProductionSelectionBucket(makeItem({ can_select: false }))).toBeNull()
    expect(getProductionSelectionBucket(makeItem({
      capabilities: {
        select: {
          allowed: false,
          disabled_reason: '外协任务进行中',
          requires_confirmation: false,
        },
      },
    }))).toBeNull()
    expect(getProductionSelectionBucket(makeItem({ stage: 'designing' }))).toBeNull()
  })

  it('只返回指定分类的可选明细 ID', () => {
    const items = [
      makeItem({ id: 'new-item' }),
      makeItem({ id: 'pending-item', is_linked: true, task_status: 'pending' }),
      makeItem({ id: 'in-progress-item', is_linked: true, task_status: 'in_progress' }),
      makeItem({ id: 'rework-item', is_linked: true, task_status: 'rework' }),
    ]

    expect(getProductionSelectionItemIds(items, 'pending')).toEqual([
      'new-item',
      'pending-item',
    ])
    expect(getProductionSelectionItemIds(items, 'in_progress')).toEqual([
      'in-progress-item',
    ])
  })

  it('全选和取消全选只影响当前分类，并保持其他选择', () => {
    const pendingIds = ['pending-1', 'pending-2']
    const selected = ['in-progress-1', 'other-item']

    expect(toggleStageSelection(selected, pendingIds, true)).toEqual([
      'in-progress-1',
      'other-item',
      'pending-1',
      'pending-2',
    ])
    expect(toggleStageSelection(
      ['pending-1', 'in-progress-1', 'other-item'],
      pendingIds,
      false,
    )).toEqual(['in-progress-1', 'other-item'])
  })

  it('根据当前分类选择数量返回未选、半选和全选状态', () => {
    const ids = ['item-1', 'item-2']

    expect(getStageSelectionState([], ids)).toEqual({
      checked: false,
      indeterminate: false,
      selectedCount: 0,
    })
    expect(getStageSelectionState(['item-1'], ids)).toEqual({
      checked: false,
      indeterminate: true,
      selectedCount: 1,
    })
    expect(getStageSelectionState(['item-1', 'item-2', 'other'], ids)).toEqual({
      checked: true,
      indeterminate: false,
      selectedCount: 2,
    })
    expect(getStageSelectionState(['item-1'], [])).toEqual({
      checked: false,
      indeterminate: false,
      selectedCount: 0,
    })
  })
})
