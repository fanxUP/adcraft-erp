export interface ProjectCostAmounts {
  paymentAmount: number
  debtAmount: number
  totalAmount: number
}

function toCents(value: number | string | null | undefined, label: string): number {
  const numeric = typeof value === 'string' && value.trim() === '' ? 0 : Number(value ?? 0)
  if (!Number.isFinite(numeric)) throw new Error(`${label}必须是有效数字`)
  return Math.round(numeric * 100)
}

function fromCents(cents: number): number {
  return cents / 100
}

/**
 * Normalize the two entry amounts used by the project-cost form.
 * The API still persists totalAmount as `amount` and debtAmount as
 * `debt_amount`; paymentAmount is the part paid at registration time.
 */
export function normalizeProjectCostAmounts(
  paymentAmount: number | string | null | undefined,
  debtAmount: number | string | null | undefined,
): ProjectCostAmounts {
  const paymentCents = toCents(paymentAmount, '支付金额')
  const debtCents = toCents(debtAmount, '欠款金额')
  if (paymentCents < 0) throw new Error('支付金额不能小于0')
  if (debtCents < 0) throw new Error('欠款金额不能小于0')

  const totalCents = paymentCents + debtCents
  if (totalCents <= 0) throw new Error('支出总额必须大于0')

  return {
    paymentAmount: fromCents(paymentCents),
    debtAmount: fromCents(debtCents),
    totalAmount: fromCents(totalCents),
  }
}

/** Derive the amount paid when opening a historical cost record. */
export function getProjectCostPaymentAmount(
  totalAmount: number | string | null | undefined,
  debtAmount: number | string | null | undefined,
): number {
  const totalCents = toCents(totalAmount, '支出总额')
  const debtCents = toCents(debtAmount, '欠款金额')
  return fromCents(Math.max(0, totalCents - debtCents))
}
