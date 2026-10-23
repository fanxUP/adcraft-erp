import { describe, expect, it } from 'vitest'
import {
  canPermanentlyDelete,
  isPermanentDeleteConfirmationValid,
  permanentDeleteBlockMessage,
} from '@/utils/outsourceTaskPermanentDelete'

describe('外协任务回收站永久删除确认', () => {
  it('只允许后端明确标记为合格的任务发起永久删除', () => {
    expect(canPermanentlyDelete({
      eligible: true,
      block_reasons: [],
      references: { payment_count: 0, reconciliation_count: 0, cost_overlap_review_count: 0, legacy_deleted_payment_count: 0 },
    })).toBe(true)
    expect(canPermanentlyDelete({
      eligible: false,
      block_reasons: ['存在付款记录'],
      references: { payment_count: 1, reconciliation_count: 0, cost_overlap_review_count: 0, legacy_deleted_payment_count: 0 },
    })).toBe(false)
    expect(canPermanentlyDelete(undefined)).toBe(false)
  })

  it('将服务器阻止原因明确展示给操作人', () => {
    expect(permanentDeleteBlockMessage({
      eligible: false,
      block_reasons: ['历史已付金额非零', '存在核对记录'],
      references: { payment_count: 0, reconciliation_count: 1, cost_overlap_review_count: 0, legacy_deleted_payment_count: 0 },
    })).toBe('历史已付金额非零；存在核对记录')
  })

  it('必须准确确认任务编号并填写有效删除原因', () => {
    expect(isPermanentDeleteConfirmationValid('OT-001', 'OT-001', '确认重复记录')).toBe(true)
    expect(isPermanentDeleteConfirmationValid('OT-001', 'OT-002', '确认重复记录')).toBe(false)
    expect(isPermanentDeleteConfirmationValid('OT-001', 'OT-001', '删除')).toBe(false)
  })

  it('旧版已清除过付款流水的任务即使当前已付为零也不能误显示为可删除', () => {
    expect(canPermanentlyDelete({
      eligible: false,
      block_reasons: ['历史软删除日志显示曾清除付款流水，无法确认原始财务事实'],
      references: { payment_count: 0, reconciliation_count: 0, cost_overlap_review_count: 0, legacy_deleted_payment_count: 1 },
    })).toBe(false)
  })
})
