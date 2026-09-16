export interface ExpenseAmountResult {
  amount: number
  payable_amount: number
}

/**
 * 支出登记金额归一化：没有填写支出总额时，允许用待付款金额作为总额。
 * 金额仍然按分比较，避免浮点数误差造成错误提示。
 */
export function normalizeExpenseAmounts(
  amount: number | null | undefined,
  payableAmount: number | null | undefined,
): ExpenseAmountResult {
  const totalInput = amount == null ? 0 : Number(amount)
  const payableInput = payableAmount == null ? 0 : Number(payableAmount)

  if (!Number.isFinite(totalInput) || totalInput < 0) {
    throw new Error('支出金额不能小于0')
  }
  if (!Number.isFinite(payableInput) || payableInput < 0) {
    throw new Error('待付款金额不能小于0')
  }

  const totalCents = Math.round(totalInput * 100)
  const payableCents = Math.round(payableInput * 100)
  const normalizedTotalCents = totalCents > 0 ? totalCents : payableCents

  if (normalizedTotalCents <= 0) {
    throw new Error('请填写支出金额或待付款金额')
  }
  if (payableCents > normalizedTotalCents) {
    throw new Error('待付款金额不能大于支出总额且不能小于0')
  }

  return {
    amount: normalizedTotalCents / 100,
    payable_amount: payableCents / 100,
  }
}
