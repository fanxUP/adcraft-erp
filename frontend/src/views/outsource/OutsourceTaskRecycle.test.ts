import { describe, expect, it } from 'vitest'
import {
  canPermanentlyDelete,
  isPermanentDeleteReasonValid,
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

  it('不再要求重复输入任务编号，但仍要求有效删除原因', () => {
    expect(isPermanentDeleteReasonValid('确认重复记录')).toBe(true)
    expect(isPermanentDeleteReasonValid('删')).toBe(false)
    expect(isPermanentDeleteReasonValid(' '.repeat(5))).toBe(false)
  })

  it('旧版付款清理记录作为审计信息保留，不再阻止直接关联财务数据清理', () => {
    expect(canPermanentlyDelete({
      eligible: true,
      block_reasons: [],
      references: { payment_count: 0, reconciliation_count: 0, cost_overlap_review_count: 0, legacy_deleted_payment_count: 1 },
    })).toBe(true)
  })
})
