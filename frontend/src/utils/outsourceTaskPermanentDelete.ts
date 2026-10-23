export interface PermanentDeleteEligibility {
  eligible: boolean
  block_reasons: string[]
  references: {
    payment_count: number
    reconciliation_count: number
    cost_overlap_review_count: number
    legacy_deleted_payment_count: number
  }
}

export function canPermanentlyDelete(eligibility?: PermanentDeleteEligibility | null): boolean {
  return eligibility?.eligible === true
}

export function permanentDeleteBlockMessage(eligibility?: PermanentDeleteEligibility | null): string {
  if (!eligibility) return '尚未取得服务端删除资格，请刷新列表'
  if (eligibility.eligible) return '符合永久删除条件'
  return eligibility.block_reasons.join('；') || '当前任务不符合永久删除条件'
}

export function isPermanentDeleteConfirmationValid(
  expectedTaskNo: string,
  typedTaskNo: string,
  reason: string,
): boolean {
  const normalizedReason = reason.trim()
  return typedTaskNo.trim() === expectedTaskNo
    && normalizedReason.length >= 5
    && normalizedReason.length <= 500
}
