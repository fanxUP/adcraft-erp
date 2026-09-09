const CURRENCY_FORMATTER = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const NUMBER_FORMATTER = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 2,
})

/** 统一金额显示：空值使用短横线，金额始终保留两位小数。 */
export function formatMoney(value: number | null | undefined, currency = true): string {
  if (value == null || !Number.isFinite(Number(value))) return '-'
  const formatted = CURRENCY_FORMATTER.format(Number(value))
  return currency ? `¥ ${formatted}` : formatted
}

/** 统一非货币数字显示，避免各页面自行 toFixed 或遗漏空值。 */
export function formatNumber(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(Number(value))) return '-'
  return NUMBER_FORMATTER.format(Number(value))
}

/** 统一百分比显示；调用方传入 0-100 的数值。 */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(Number(value))) return '-'
  return `${NUMBER_FORMATTER.format(Math.min(100, Math.max(0, Number(value))))}%`
}
