/**
 * 时间显示工具：后端时间戳为「无时区的 UTC 时间」，浏览器需补 Z 后按本地时区显示。
 *
 * - formatDate:         本地日期 YYYY-MM-DD（纯日期字段原样返回）
 * - formatDateTime:     本地日期时间 YYYY-MM-DD HH:mm
 * - formatDateTimeFull: 本地日期时间(含秒) YYYY-MM-DD HH:mm:ss
 */

function parseUtc(ts: string): Date {
  const s = ts.trim()
  // 已带时区（Z 或 ±hh:mm）直接解析；否则按 UTC 补 Z
  const normalized = /(Z|[+-]\d{2}:?\d{2})$/.test(s) ? s : `${s}Z`
  return new Date(normalized)
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n)
}

export function formatDate(ts?: string | null): string {
  if (!ts) return '-'
  // 纯日期（YYYY-MM-DD，无时间部分）直接返回
  if (/^\d{4}-\d{2}-\d{2}$/.test(ts.trim())) return ts.trim()
  const d = parseUtc(ts)
  if (Number.isNaN(d.getTime())) return ts
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function formatDateTime(ts?: string | null): string {
  if (!ts) return '-'
  const d = parseUtc(ts)
  if (Number.isNaN(d.getTime())) return ts.replace('T', ' ').slice(0, 16)
  return `${formatDate(ts)} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function formatDateTimeFull(ts?: string | null): string {
  if (!ts) return '-'
  const d = parseUtc(ts)
  if (Number.isNaN(d.getTime())) return ts.replace('T', ' ').slice(0, 19)
  return `${formatDate(ts)} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
